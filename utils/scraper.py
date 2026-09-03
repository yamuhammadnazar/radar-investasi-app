"""
Modul scraping utama dengan:
- Concurrency (ThreadPoolExecutor)
- HTTP retry + connection pooling
- Caching untuk feed dan artikel
- Proteksi waktu (timeout per artikel)
"""
import time
import re
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from bs4 import BeautifulSoup

from .http_client import safe_request, get_http_session
from .cache import cache_get, cache_set, DEFAULT_FEED_TTL, DEFAULT_ARTICLE_TTL
from .portals import aturan_portal

# Batas paralelisme per scan (terlalu tinggi = bisa kena rate-limit / IP block)
DEFAULT_MAX_WORKERS = 5
MAX_ARTIKEL_PER_PORTAL = 15
SCRAPE_TIMEOUT = 7  # detik per artikel
MAX_ARTIKEL_LEN = 8000  # batasi panjang teks untuk mencegah memory blow-up


def dapatkan_feed_rss(aturan: dict):
    """
    Ambil feed RSS dengan fallback (rss_asli -> rss_google).
    Menggunakan cache 1 jam.
    Mengembalikan feedparser.FeedParserDict (kosong jika gagal).
    """
    rss_asli = aturan.get("rss_asli")
    cache_key_asli = rss_asli or aturan.get("rss_google", "")

    # Coba rss_asli
    if rss_asli:
        cached = cache_get("feed", rss_asli)
        if cached is not None:
            return feedparser.parse(cached.encode("utf-8"))

        response = safe_request(rss_asli, timeout=8)
        if response is not None and response.status_code == 200:
            cache_set("feed", rss_asli, response.text, ttl=DEFAULT_FEED_TTL)
            return feedparser.parse(response.content)

    # Fallback ke Google News
    rss_google = aturan.get("rss_google")
    if rss_google:
        cached = cache_get("feed", rss_google)
        if cached is not None:
            return feedparser.parse(cached.encode("utf-8"))

        response = safe_request(rss_google, timeout=8)
        if response is not None and response.status_code == 200:
            cache_set("feed", rss_google, response.text, ttl=DEFAULT_FEED_TTL)
            return feedparser.parse(response.content)

    return feedparser.parse("")


def dapatkan_url_asli(url_target: str) -> str:
    """Resolve Google News URL ke URL asli portal."""
    if "news.google.com" not in url_target:
        return url_target
    cached = cache_get("url", url_target)
    if cached is not None:
        return cached
    response = safe_request(url_target, timeout=10, allow_redirects=True)
    if response is not None:
        cache_set("url", url_target, response.url, ttl=86400)
        return response.url
    return url_target


def _ekstrak_isi_html(html_text: str, tag: str, class_name: str) -> tuple[str, str]:
    """
    Ekstrak isi artikel dari HTML.
    Mengembalikan (isi, status_akses) dengan logika fallback universal.
    """
    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception:
        return "Konten tidak dapat diekstrak.", "Error"

    html_lower = html_text.lower()

    # Deteksi paywall
    if any(p in html_lower for p in ["paywall", "berlangganan", "artikel premium", "konten berbayar"]):
        if len(soup.find_all("p")) < 3:
            return "Artikel Terkunci / Berbayar (Paywall)", "Paywall"

    # Coba ekstrak dari container spesifik
    artikel_body = soup.find(tag, class_=class_name)
    if artikel_body:
        paragraf = artikel_body.find_all("p")
        teks_paragraf = [p.text.strip() for p in paragraf if len(p.text.strip()) > 20]
        if teks_paragraf:
            return "\n\n".join(teks_paragraf)[:MAX_ARTIKEL_LEN], "Penuh"

    # Fallback universal
    semua_p = soup.find_all("p")
    teks_universal = [
        p.text.strip() for p in semua_p
        if len(p.text.strip()) > 30
        and not re.search(r"(cookie|privacy|baca juga)", p.text.strip(), re.IGNORECASE)
    ]
    if teks_universal:
        return "\n\n".join(teks_universal)[:MAX_ARTIKEL_LEN], "Penuh"

    return "Konten tidak dapat diekstrak.", "Terbatas"


# Batas percobaan ulang per artikel (retry di sisi aplikasi, di atas retry urllib3).
# Jika setelah MAX_SCRAPE_ATTEMPTS percobaan tetap gagal, kembalikan None
# agar caller bisa menghentikan proses jika kegagalan berturut-turut.
MAX_SCRAPE_ATTEMPTS = 3
# Threshold RASIO kegagalan (gagal/total) pada loop per-portal sebelum proses
# dihentikan dini. 2x gagal saja tidak cukup karena bisa jadi transient/rate-limit;
# kita hentikan hanya jika mayoritas entry benar-benar gagal akses (bukan di-skip).
HALT_FAILURE_RATIO = 0.7
HALT_MIN_SAMPLE = 5  # butuh minimal N entry selesai sebelum memutuskan halt


def scrape_artikel(
    entry,
    aturan: dict,
    *,
    session=None,
    timeout: float = SCRAPE_TIMEOUT,
) -> dict | None:
    """
    Scrape satu artikel dengan retry internal (MAX_SCRAPE_ATTEMPTS x).
    Mengembalikan dict hasil atau None jika semua percobaan gagal.
    Menggunakan cache untuk konten artikel.
    """
    judul = entry.get("title", "N/A")
    link = entry.get("link", "N/A")

    # Cek cache artikel dulu
    cached = cache_get("article", link)
    if cached is not None:
        return {
            "judul": judul,
            "link": link,
            "tanggal": cached.get("tanggal", ""),
            "isi": cached.get("isi", ""),
            "status_akses": cached.get("status_akses", "Cached"),
            "from_cache": True,
        }

    last_err: str | None = None
    for attempt in range(1, MAX_SCRAPE_ATTEMPTS + 1):
        start = time.time()
        try:
            # Resolve URL jika Google News
            url_asli = dapatkan_url_asli(link)
            link_target = url_asli + "?page=all" if aturan.get("butuh_page_all") else url_asli

            response = safe_request(link_target, timeout=timeout, session=session)
            if response is None:
                last_err = "timeout/conn"
                # exponential backoff kecil antar attempt
                if attempt < MAX_SCRAPE_ATTEMPTS:
                    time.sleep(0.3 * attempt)
                continue

            if time.time() - start > timeout + 1:
                last_err = "timeout"
                if attempt < MAX_SCRAPE_ATTEMPTS:
                    time.sleep(0.3 * attempt)
                continue

            if response.status_code == 200:
                isi, status_akses = _ekstrak_isi_html(
                    response.text, aturan["tag"], aturan["class"]
                )
                tanggal = entry.get("published", "") or entry.get("updated", "N/A")
                # Simpan ke cache
                cache_set(
                    "article",
                    link,
                    {"tanggal": tanggal, "isi": isi, "status_akses": status_akses},
                    ttl=DEFAULT_ARTICLE_TTL,
                )
                return {
                    "judul": judul,
                    "link": link,
                    "tanggal": tanggal,
                    "isi": isi,
                    "status_akses": status_akses,
                    "from_cache": False,
                }

            # HTTP non-200: tidak percobaan ulang untuk 4xx (client error),
            # tapi retry untuk 5xx (server error) & 429 (rate limit).
            last_err = f"http {response.status_code}"
            if response.status_code < 500 and response.status_code != 429:
                break
            if attempt < MAX_SCRAPE_ATTEMPTS:
                time.sleep(0.3 * attempt)
        except Exception as exc:
            last_err = f"exc:{type(exc).__name__}"
            if attempt < MAX_SCRAPE_ATTEMPTS:
                time.sleep(0.3 * attempt)

    # Semua attempt habis
    return {
        "judul": judul,
        "link": link,
        "tanggal": entry.get("published", "") or entry.get("updated", "N/A"),
        "isi": f"Gagal akses setelah {MAX_SCRAPE_ATTEMPTS}x percobaan ({last_err}).",
        "status_akses": "Error",
        "from_cache": False,
        "is_failure_marker": True,  # penanda untuk caller menghitung gagal
    }


def scrape_entries_parallel(
    entries: list,
    aturan: dict,
    *,
    max_workers: int = DEFAULT_MAX_WORKERS,
    max_items: int = MAX_ARTIKEL_PER_PORTAL,
) -> list[dict]:
    """
    Scrape banyak entry secara paralel menggunakan ThreadPoolExecutor.
    Mengembalikan list hasil (sudah difilter None).
    """
    if not entries:
        return []

    session = get_http_session()
    target_entries = list(entries)[:max_items]
    hasil: list[dict] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit semua tasks
        future_to_entry = {
            executor.submit(scrape_artikel, entry, aturan, session=session): entry
            for entry in target_entries
        }

        # Kumpulkan hasil dengan timeout global
        for future in as_completed(future_to_entry, timeout=SCRAPE_TIMEOUT * 2):
            try:
                result = future.result(timeout=SCRAPE_TIMEOUT + 2)
                if result is not None:
                    hasil.append(result)
            except Exception:
                # Skip entry yang error/timeout
                continue

    return hasil


def scrape_portal_parallel(
    nama_portal: str,
    aturan: dict,
    *,
    max_workers: int = DEFAULT_MAX_WORKERS,
    max_items: int = MAX_ARTIKEL_PER_PORTAL,
    progress_callback: Callable | None = None,
) -> list[dict]:
    """
    High-level: scrape satu portal dari feed RSS sampai isi artikel, paralel.
    progress_callback(current, total) dipanggil setiap artikel selesai.
    """
    feed = dapatkan_feed_rss(aturan)
    if not feed or not hasattr(feed, "entries") or len(feed.entries) == 0:
        if progress_callback:
            progress_callback(0, 0)
        return []

    entries = feed.entries
    total = min(len(entries), max_items)

    if progress_callback:
        progress_callback(0, total)

    results: list[dict] = []
    session = get_http_session()

    # Submit paralel dengan batch kecil agar tidak overwhelme server
    batch_size = max_workers
    processed = 0

    for i in range(0, total, batch_size):
        batch = list(entries[i:i + batch_size])
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_entry = {
                executor.submit(scrape_artikel, entry, aturan, session=session): entry
                for entry in batch
            }
            for future in as_completed(future_to_entry, timeout=SCRAPE_TIMEOUT * 2):
                try:
                    result = future.result(timeout=SCRAPE_TIMEOUT + 2)
                    if result is not None:
                        # Inject nama_portal di hasil
                        result["nama_portal"] = nama_portal
                        results.append(result)
                except Exception:
                    pass
                processed += 1
                if progress_callback:
                    progress_callback(processed, total)

    return results