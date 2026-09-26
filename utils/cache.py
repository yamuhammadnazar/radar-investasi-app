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
from threading import Lock as _Lock, local as _local

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "radar_cache.db")
CACHE_LOCK = _Lock()

# TTL default: 1 jam untuk feed, 6 jam untuk artikel (artikel lebih stabil)
DEFAULT_FEED_TTL = 3600
DEFAULT_ARTICLE_TTL = 21600
# TTL khusus parsed article: skip langkah BeautifulSoup+regex pada hit kedua
DEFAULT_PARSED_TTL = 21600
# FIX ANTI-STUCK: lama maksimum SQLite menunggu lock ditulis oleh thread lain.
# Pada scraping paralel, default 5 detik terlalu pendek sehingga cache_get/set
# bisa gagal senyap -> artikel di-scrape ulang -> scan terasa lambat.
SQLITE_BUSY_TIMEOUT = 20.0


def cache_get_parsed(link: str):
    """Shortcut untuk cache parsed article (prefix='parsed')."""
    return cache_get("parsed", link)


def cache_set_parsed(link: str, payload, ttl: int = DEFAULT_PARSED_TTL) -> bool:
    """Shortcut untuk simpan hasil scrape+parse ke cache."""
    return cache_set("parsed", link, payload, ttl=ttl)


def init_cache_db() -> None:
    """Inisialisasi tabel cache jika belum ada."""
    with CACHE_LOCK:
        # FIX ANTI-STUCK: beri busy timeout agar operasi DDL tidak langsung gagal
        # saat ada writer lain (scraping paralel) yang sedang memegang lock.
        conn = sqlite3.connect(DB_PATH, timeout=SQLITE_BUSY_TIMEOUT)
        try:
            conn.execute(f"PRAGMA busy_timeout={int(SQLITE_BUSY_TIMEOUT * 1000)};")
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


# ============================================================
# THREAD-LOCAL CONNECTION POOL
# ============================================================
# Setiap thread (termasuk thread dari ThreadPoolExecutor) memiliki
# koneksi SQLite sendiri. Menghindari overhead connect/disconnect
# berulang yang sangat terasa saat scraping paralel 100+ artikel.
_thread_local = _local()


def _get_conn() -> sqlite3.Connection:
    """Ambil koneksi SQLite milik thread ini (lazy create)."""
    conn = getattr(_thread_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(
            DB_PATH,
            timeout=SQLITE_BUSY_TIMEOUT,
            check_same_thread=False,  # setiap thread punya instance sendiri
        )
        conn.execute("PRAGMA journal_mode=WAL")  # tulis-bersamaan (parallel) lebih cepat
        conn.execute("PRAGMA synchronous=NORMAL")  # keseimbangan performa & durability
        # FIX ANTI-STUCK: SQLite default hanya menunggu lock 5 detik; pada
        # scraping paralel (banyak writer) itu membuat cache_set/cache_get
        # gagal senyap dan memperlambat scan. Naikkan & konsistenkan.
        conn.execute(f"PRAGMA busy_timeout={int(SQLITE_BUSY_TIMEOUT * 1000)};")
        _thread_local.conn = conn
    return conn


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
        conn = _get_conn()
        row = conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        ).fetchone()

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

        conn = _get_conn()
        with CACHE_LOCK:
            # Hanya menyimpan created_at pertama kali; tidak di-reset tiap update
            conn.execute(
                """
                INSERT INTO cache (key, value, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    expires_at=excluded.expires_at
                """,
                (key, blob, expires_at, now),
            )
            conn.commit()
        return True
    except Exception:
        return False


def cache_clear_expired() -> int:
    """Bersihkan entry yang sudah expired. Return jumlah yang dihapus."""
    try:
        conn = _get_conn()
        with CACHE_LOCK:
            cur = conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
            conn.commit()
            return cur.rowcount
    except Exception:
        return 0


def get_cache_stats() -> dict:
    """Statistik cache untuk ditampilkan di sidebar."""
    try:
        conn = _get_conn()
        total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM cache WHERE expires_at > ?", (time.time(),)
        ).fetchone()[0]
        expired = total - active
        size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
        return {
            "total": total,
            "active": active,
            "expired": expired,
            "size_mb": round(size_mb, 2),
        }
    except Exception:
        return {"total": 0, "active": 0, "expired": 0, "size_mb": 0.0}


# ============================================================
# INVALIDASI CACHE SAAT SKEMA KATEGORI BERUBAH
# ============================================================
# `cache_set_parsed` menyimpan hasil scrape + analisis LENGKAP, termasuk
# kolom "Kategori Aset". Ketika daftar kategori/kata kunci di app.py berubah
# (mis. penambahan Politik, Kalbar & Ngabang, Kesehatan, Institusi, ASEAN),
# entry parsed lama akan tetap membawa kategori versi lama hingga TTL habis
# (6 jam). Akibatnya kategori baru "tidak muncul" walau kode sudah benar.
#
# Solusi: versi skema kategori disimpan di tabel cache_meta. Bila versi di
# kode berbeda dengan yang tersimpan, seluruh entry parsed dihapus sekali.
SCHEMA_KATEGORI_VERSION = 2


def invalidasi_cache_parsed_jika_perlu(versi: int = SCHEMA_KATEGORI_VERSION) -> int:
    """Hapus cache 'parsed' bila versi skema kategori berubah.

    Return jumlah entry parsed yang dihapus (0 bila tidak perlu).
    Dipanggil otomatis saat modul diimpor.
    """
    try:
        with CACHE_LOCK:
            conn = _get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            row = conn.execute(
                "SELECT value FROM cache_meta WHERE key = 'schema_kategori_version'"
            ).fetchone()
            versi_tersimpan = int(row[0]) if row and str(row[0]).isdigit() else 0
            if versi_tersimpan >= versi:
                return 0
            cur = conn.execute("DELETE FROM cache WHERE key LIKE 'parsed:%'")
            dihapus = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            conn.execute(
                "INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)",
                ("schema_kategori_version", str(versi)),
            )
            conn.commit()
            return dihapus
    except Exception:
        # Cache hanya optimasi — kegagalan invalidasi tidak boleh
        # menghentikan aplikasi.
        return 0


# Auto-init saat modul diimpor
init_cache_db()
# FIX: pastikan artikel yang ter-cache SEBELUM kategori baru ditambahkan
# tidak lagi dipakai, sehingga hasil scan berikutnya sudah memakai kategori
# Politik / Kalbar-Ngabang / Kesehatan / Institusi / ASEAN.
invalidasi_cache_parsed_jika_perlu()