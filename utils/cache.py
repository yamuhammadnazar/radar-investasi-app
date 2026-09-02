"""
Caching layer berbasis SQLite untuk feed RSS dan isi artikel.

Tujuan:
- Mengurangi request ke server portal (rate-limit friendly)
- Mempercepat scan berulang (user menekan tombol dua kali)
- Tetap fresh melalui TTL
"""
import os
import sqlite3
import time
import hashlib
import json
from threading import Lock as _Lock

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "radar_cache.db")
CACHE_LOCK = _Lock()

# TTL default: 1 jam untuk feed, 6 jam untuk artikel (artikel lebih stabil)
DEFAULT_FEED_TTL = 3600
DEFAULT_ARTICLE_TTL = 21600


def init_cache_db() -> None:
    """Inisialisasi tabel cache jika belum ada."""
    with CACHE_LOCK:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    expires_at REAL,
                    created_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
            conn.commit()
        finally:
            conn.close()


def _make_key(prefix: str, identifier: str) -> str:
    """Buat key cache yang aman (hash SHA256)."""
    raw = f"{prefix}:{identifier}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def cache_get(prefix: str, identifier: str):
    """
    Ambil value dari cache. Mengembalikan None jika:
    - Key tidak ada
    - Sudah expired
    - Decode gagal
    """
    try:
        key = _make_key(prefix, identifier)
        now = time.time()
        with CACHE_LOCK:
            conn = sqlite3.connect(DB_PATH)
            try:
                row = conn.execute(
                    "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
                ).fetchone()
            finally:
                conn.close()

        if row is None:
            return None

        value_blob, expires_at = row
        if expires_at < now:
            return None

        return json.loads(value_blob.decode("utf-8"))
    except Exception:
        return None


def cache_set(prefix: str, identifier: str, value, ttl: int = DEFAULT_FEED_TTL) -> bool:
    """
    Simpan value ke cache. Mengembalikan True jika berhasil.
    TTL dalam detik.
    """
    try:
        key = _make_key(prefix, identifier)
        now = time.time()
        expires_at = now + ttl
        blob = json.dumps(value, ensure_ascii=False).encode("utf-8")

        with CACHE_LOCK:
            conn = sqlite3.connect(DB_PATH)
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache (key, value, expires_at, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, blob, expires_at, now),
                )
                conn.commit()
            finally:
                conn.close()
        return True
    except Exception:
        return False


def cache_clear_expired() -> int:
    """Bersihkan entry yang sudah expired. Return jumlah yang dihapus."""
    try:
        with CACHE_LOCK:
            conn = sqlite3.connect(DB_PATH)
            try:
                cur = conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
                conn.commit()
                return cur.rowcount
            finally:
                conn.close()
    except Exception:
        return 0


def get_cache_stats() -> dict:
    """Statistik cache untuk ditampilkan di sidebar."""
    try:
        with CACHE_LOCK:
            conn = sqlite3.connect(DB_PATH)
            try:
                total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
                active = conn.execute(
                    "SELECT COUNT(*) FROM cache WHERE expires_at > ?", (time.time(),)
                ).fetchone()[0]
                expired = total - active
                # ukuran db
                size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
                return {
                    "total": total,
                    "active": active,
                    "expired": expired,
                    "size_mb": round(size_mb, 2),
                }
            finally:
                conn.close()
    except Exception:
        return {"total": 0, "active": 0, "expired": 0, "size_mb": 0.0}


# Auto-init saat modul diimpor
init_cache_db()