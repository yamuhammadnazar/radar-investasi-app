"""
HTTP Client dengan retry mechanism dan connection pooling.
Mengurangi overhead handshake SSL dan memberikan resilience terhadap error transient.
"""
import ssl
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
    """
    sess = session or get_http_session()
    try:
        return sess.get(
            url,
            headers=HEADERS,
            timeout=timeout,
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
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.RequestException:
        return None
    except Exception:
        return None