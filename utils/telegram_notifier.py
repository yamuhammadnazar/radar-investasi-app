"""
Modul notifikasi Telegram real-time.

FITUR:
- Kirim pesan individual untuk artikel high-priority
- Filter berdasarkan sentimen & kategori
- Rate limiting (maks 20 msg/menit untuk comply dengan Telegram limits)
- Markdown formatting yang aman
- Quiet hours (jangan kirim di jam malam)
- Batch digest mode (kirim ringkasan berkala)
"""

import time
import re
import threading
from datetime import datetime
from typing import List, Dict, Optional
from queue import Queue, Empty
from dataclasses import dataclass

from .http_client import safe_post
from .http_client import get_http_session  # noqa: F401  (tetap tersedia jika perlu)


# Logger sederhana untuk debug Telegram
import logging as _logging
_logger = _logging.getLogger("telegram_notifier")
if not _logger.handlers:
    _h = _logging.StreamHandler()
    _h.setFormatter(_logging.Formatter("%(asctime)s [%(name)s] %(message)s"))
    _logger.addHandler(_h)
    _logger.setLevel(_logging.WARNING)


# Telegram API limits
TELEGRAM_MSG_LIMIT = 4096  # max karakter per pesan
TELEGRAM_RATE_LIMIT = 20   # messages per minute
RATE_WINDOW = 60           # seconds


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    enabled: bool = False
    min_sentiment: str = "ANY"  # ANY, POSITIF, NEGATIF
    categories: List[str] = None  # None = semua kategori
    portfolio_only: bool = False  # hanya emiten watchlist
    quiet_hours_start: int = 22  # jam mulai quiet
    quiet_hours_end: int = 7     # jam selesai quiet
    batch_mode: bool = False     # kumpulkan lalu kirim 1 batch


class TelegramNotifier:
    """Thread-safe Telegram notifier dengan rate limiting."""

    def __init__(self, config: TelegramConfig):
        self.config = config
        self._sent_timestamps: List[float] = []
        self._lock = threading.Lock()
        self._queue: Queue = Queue()
        self._batch_buffer: List[Dict] = []
        self._last_batch_send = time.time()

    def _is_quiet_time(self) -> bool:
        """Cek apakah sedang dalam quiet hours."""
        hour = datetime.now().hour
        if self.config.quiet_hours_start < self.config.quiet_hours_end:
            return self.config.quiet_hours_start <= hour < self.config.quiet_hours_end
        # Handle overnight (e.g., 22-7)
        return hour >= self.config.quiet_hours_start or hour < self.config.quiet_hours_end

    def _can_send(self) -> bool:
        """Rate limit check."""
        now = time.time()
        with self._lock:
            # Hapus timestamp > 60 detik
            self._sent_timestamps = [
                t for t in self._sent_timestamps if now - t < RATE_WINDOW
            ]
            return len(self._sent_timestamps) < TELEGRAM_RATE_LIMIT

    def _record_sent(self):
        with self._lock:
            self._sent_timestamps.append(time.time())

    def _send_message(self, text: str) -> bool:
        """Low-level: kirim 1 pesan ke Telegram (POST)."""
        if not self.config.bot_token or not self.config.chat_id:
            return False

        if not self._can_send():
            return False

        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        resp = safe_post(url, json=payload, timeout=10)
        if resp is None:
            return False
        if resp.status_code == 200:
            self._record_sent()
            return True
        # Log error Telegram untuk debugging
        if resp.status_code >= 500 or resp.status_code == 429:
            _logger.debug(f"Telegram status {resp.status_code}: {resp.text[:200]}")
        return False

    def _format_artikel(self, artikel: Dict) -> str:
        """Format 1 artikel jadi pesan Markdown Telegram."""
        emoji_map = {"POSITIF": "🟢", "NEGATIF": "🔴", "NETRAL": "⚪"}
        emoji = emoji_map.get(artikel.get("Sentimen", ""), "⚪")

        ticker = artikel.get("PrimaryTicker", artikel.get("Trigger/Emiten", ""))
        ticker_line = f"`{ticker}`" if ticker else ""

        judul = artikel.get("Judul", "(tanpa judul)")
        # Escape karakter markdown khusus
        judul_safe = re.sub(r'([_*\[\]`])', r'\\\1', judul)

        kategori = artikel.get("Kategori Aset", "")
        ringkasan = artikel.get("Ringkasan Berita", "")[:200]
        link = artikel.get("Link", "")

        text = (
            f"{emoji} *{artikel.get('Sentimen', 'NETRAL')}* {ticker_line}\n\n"
            f"📰 *{judul_safe}*\n\n"
        )
        if kategori:
            text += f"📁 _{kategori}_\n"
        if ringkasan and ringkasan != "-":
            text += f"\n{ringkasan}...\n"
        if link:
            text += f"\n🔗 [Baca Selengkapnya]({link})"

        return text[:TELEGRAM_MSG_LIMIT]

    def _format_batch(self, artikels: List[Dict]) -> str:
        """Format batch jadi 1 pesan ringkasan."""
        if not artikels:
            return ""

        n = len(artikels)
        n_pos = sum(1 for a in artikels if a.get("Sentimen") == "POSITIF")
        n_neg = sum(1 for a in artikels if a.get("Sentimen") == "NEGATIF")
        n_net = n - n_pos - n_neg

        header = (
            f"📡 *Radar Portofolio — Digest*\n"
            f"🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"📊 {n} berita ({n_pos} positif, {n_net} netral, {n_neg} negatif)\n\n"
        )

        # Sort by sentiment strength (negatif dulu, lalu positif)
        items = sorted(
            artikels,
            key=lambda a: 0 if a.get("Sentimen") == "NEGATIF"
                       else 1 if a.get("Sentimen") == "NETRAL"
                       else 2
        )

        lines = []
        for a in items[:10]:  # max 10 item di digest
            emoji_map = {"POSITIF": "🟢", "NEGATIF": "🔴", "NETRAL": "⚪"}
            emoji = emoji_map.get(a.get("Sentimen", ""), "⚪")
            ticker = a.get("PrimaryTicker", "")
            ticker_str = f"`{ticker}` " if ticker else ""
            judul = a.get("Judul", "")[:80]
            lines.append(f"{emoji} {ticker_str}{judul}")

        if len(artikels) > 10:
            lines.append(f"\n_...dan {len(artikels) - 10} lainnya_")

        return header + "\n".join(lines)

    def should_send(self, artikel: Dict) -> bool:
        """Filter logic: cek apakah artikel ini harus dikirim."""
        if not self.config.enabled:
            return False

        if self._is_quiet_time():
            return False

        # Filter sentimen
        if self.config.min_sentiment == "POSITIF":
            if artikel.get("Sentimen") not in ["POSITIF"]:
                return False
        elif self.config.min_sentiment == "NEGATIF":
            if artikel.get("Sentimen") not in ["NEGATIF"]:
                return False

        # Filter kategori
        if self.config.categories:
            if artikel.get("Kategori Aset") not in self.config.categories:
                return False

        # Filter portfolio
        if self.config.portfolio_only:
            ticker = artikel.get("PrimaryTicker", "")
            if not ticker or ticker == "UMUM":
                return False

        return True

    def notify_artikel(self, artikel: Dict) -> bool:
        """Kirim notifikasi untuk 1 artikel."""
        if not self.should_send(artikel):
            return False

        if self.config.batch_mode:
            self._batch_buffer.append(artikel)
            # Auto-flush setiap 10 item atau 5 menit
            if (len(self._batch_buffer) >= 10 or
                time.time() - self._last_batch_send > 300):
                return self.flush_batch()
            return True

        # Immediate mode
        msg = self._format_artikel(artikel)
        return self._send_message(msg)

    def flush_batch(self) -> bool:
        """Kirim batch buffer sebagai 1 pesan digest."""
        if not self._batch_buffer:
            return False
        msg = self._format_batch(self._batch_buffer)
        self._batch_buffer = []
        self._last_batch_send = time.time()
        return self._send_message(msg)

    def send_custom(self, text: str) -> bool:
        """Kirim pesan custom (untuk notifikasi summary)."""
        return self._send_message(text[:TELEGRAM_MSG_LIMIT])


def test_connection(bot_token: str, chat_id: str) -> tuple[bool, str]:
    """
    Test koneksi ke bot Telegram.
    Returns (success, message).
    """
    if not bot_token or not chat_id:
        return False, "Bot token dan chat ID harus diisi."

    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        sess = get_http_session()
        resp = sess.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                bot_name = data.get("result", {}).get("username", "bot")
                return True, f"✅ Terhubung ke bot @{bot_name}"
            return False, f"❌ API error: {data.get('description', 'unknown')}"
        return False, f"❌ HTTP {resp.status_code}"
    except Exception as e:
        return False, f"❌ Error: {str(e)[:100]}"