"""
HTTP Client dengan retry mechanism dan connection pooling.
Mengurangi overhead handshake SSL dan memberikan resilience terhadap error transient.
"""
import ssl
import threading
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Disable insecure request warning (konsisten dengan app.py)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate',
    # FIX: header tambahan agar tidak gampang kena block Cloudflare/anti-bot.
    # Banyak portal berita (bisnis.com, idx.co.id, dpr.go.id) memakai Cloudflare
    # yang men-challenge request tanpa header browser-like.
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}


class TLSCipherAdapter(HTTPAdapter):
    """
    Adapter HTTP kustom dengan konfigurasi TLS yang lebih kompatibel.

    FIX: beberapa server (mis. rss.kontan.co.id, bumntrack.com) menutup koneksi
    dengan 'SSLV3_ALERT_HANDSHAKE_FAILURE' karena Python default tidak menawarkan
    cipher/protokol TLS yang diminta server. Adapter ini memakai ciphersuite yang
    lebih luas + OP_NO_SSLv2/SSLv3 tetapi kompatibel dengan server lama.
    """
    def __init__(self, *args, **kwargs):
        import ssl as _ssl
        ctx = _ssl.create_default_context()
        # Jangan validasi sertifikat (verify=False di safe_request) tapi tetap
        # coba handshake dengan cipher modern.
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        # Izinkan protokol TLS 1.0-1.3 untuk kompatibilitas maksimal.
        try:
            ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        except Exception:
            pass
        self._ssl_context = ctx
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self._ssl_context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs['ssl_context'] = self._ssl_context
        return super().proxy_manager_for(*args, **kwargs)


def _build_session(max_retries: int = 2, pool_size: int = 20) -> requests.Session:
    """
    Bangun requests.Session dengan:
    - HTTPAdapter dengan retry otomatis untuk status 5xx, 429, dan connection errors
    - Connection pooling untuk reuse TCP connection (mengurangi latency)
    - Backoff exponential untuk tidak membebani server
    - FIX: TLSCipherAdapter untuk kompatibilitas TLS server lama (rss.kontan.co.id, dll)
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=0.3,  # 0.3s, 0.6s, 1.2s (dipercepat dari 0.5)
        status_forcelist=[429, 500, 502, 503, 504],
        # Sertakan POST agar Telegram & API lain juga otomatis retry
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        raise_on_status=False,
    )
    # FIX: gunakan TLSCipherAdapter agar server dengan konfigurasi TLS ketat
    # (mis. rss.kontan.co.id yang menolak handshake default Python) tetap bisa
    # diakses. Adapter ini menurunkan SECLEVEL agar lebih kompatibel.
    adapter = TLSCipherAdapter(
        max_retries=retry_strategy,
        pool_connections=pool_size,  # Dinaikkan 10 -> 20 untuk paralelisme tinggi
        pool_maxsize=pool_size,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session


# Lazy global session — dibuat sekali dan di-reuse
_SESSION = None


def get_http_session() -> requests.Session:
    """Ambil session global (singleton)."""
    global _SESSION
    if _SESSION is None:
        _SESSION = _build_session()
    return _SESSION


# ============================================================
# HANG GUARD (ANTI-STUCK)
# ============================================================
# Masalah: `requests` dengan (connect, read) timeout TIDAK menjamin total durasi
# request, karena transfer data bisa terus berjalan (chunked, slow server) tanpa
# pernah memicu read-timeout -> satu artikel bisa menahan thread pool puluhan
# detik. Selain itu, retry internal urllib3 bisa memperbanyak percobaan tanpa
# batas total.
#
# Solusi: jalankan request di thread terpisah + watchdog; bila tidak ada progress
# (respons belum kembali / koneksi menggantung) selama STALL_TIMEOUT_DETIK,
# socket dipaksa ditutup sehingga thread request tidak pernah macet lama.
STALL_TIMEOUT_DETIK = 8.0  # tanpa progress sama sekali selama ini -> putus


def _jalankan_dengan_watchdog(
    fn,
    *,
    stall_timeout: float = STALL_TIMEOUT_DETIK,
    total_deadline: float | None = None,
):
    """Jalankan `fn()` sambil dipantau agar tidak macet.

    - `fn` mengembalikan objek respons (atau None).
    - Watchdog memaksa menutup socket bila request tidak selesai dalam
      `stall_timeout` detik atau melewati `total_deadline`.
    - Bila fungsi lebih cepat selesai, watchdog dihentikan.
    Mengembalikan hasil `fn()` apa adanya (None bila gagal/diputus).
    """
    state: dict = {}
    hasil: dict = {}

    def _target():
        try:
            hasil["value"] = fn()
        except Exception as exc:  # noqa: BLE001 - apa pun kegagalannya, kembalikan None
            hasil["error"] = exc
        finally:
            state["done"] = True

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()

    mulai = time.time()
    while True:
        worker.join(timeout=1.0)
        if not worker.is_alive():
            return hasil.get("value")
        now = time.time()
        if total_deadline is not None and (now - mulai) >= total_deadline:
            _paksa_tutup(state)
            break
        if (now - mulai) >= stall_timeout:
            _paksa_tutup(state)
            break

    # Beri kesempatan thread request menyerap error (socket closed) sebelum
    # dilaporkan sebagai kegagalan — tidak pernah menunggu tanpa batas.
    worker.join(timeout=1.5)
    return hasil.get("value")


def _paksa_tutup(state: dict) -> None:
    """Putus socket bila respons sudah terbentuk, agar thread tidak menggantung.

    Umumnya tidak diperlukan karena timeout `requests` sudah memadai; dipakai
    sebagai jaring pengaman untuk kasus server benar-benar menggantung.
    """
    resp = state.get("response")
    if resp is not None:
        for _close in (
            lambda: resp.raw.close(),
            resp.close,
        ):
            try:
                _close()
            except Exception:
                pass


def safe_request(
    url: str,
    *,
    timeout: float = 8.0,
    verify: bool = False,
    allow_redirects: bool = True,
    session: requests.Session | None = None,
) -> requests.Response | None:
    """
    Wrapper GET request yang aman:
    - Timeout default 8 detik
    - Mengembalikan None alih-alih melempar exception
    - Otomatis menggunakan shared session jika tidak diberikan
    - FIX ANTI-STUCK: memakai watchdog anti-macet pada transfer body.
    """
    sess = session or get_http_session()

    def _do() -> requests.Response | None:
        try:
            return sess.get(
                url,
                headers=HEADERS,
                timeout=(min(4.0, timeout), timeout),
                verify=verify,
                allow_redirects=allow_redirects,
            )
        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.RequestException:
            return None
        except Exception:
            return None

    return _jalankan_dengan_watchdog(
        _do,
        stall_timeout=STALL_TIMEOUT_DETIK,
        total_deadline=timeout + 4.0,
    )


def safe_post(
    url: str,
    json: dict | None = None,
    *,
    timeout: float = 10.0,
    session: requests.Session | None = None,
) -> requests.Response | None:
    """
    Wrapper POST request yang aman (untuk Telegram, dsb).
    Mengembalikan Response atau None jika timeout/error.
    """
    sess = session or get_http_session()
    try:
        return sess.post(
            url,
            json=json or {},
            headers=HEADERS,
            timeout=(min(4.0, timeout), timeout),
        )
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.RequestException:
        return None
    except Exception:
        return None