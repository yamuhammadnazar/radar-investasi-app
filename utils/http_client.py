"""
HTTP Client dengan retry mechanism dan connection pooling.
Mengurangi overhead handshake SSL dan memberikan resilience terhadap error transient.
"""
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
}


def _build_session(max_retries: int = 3, pool_size: int = 10) -> requests.Session:
    """
    Bangun requests.Session dengan:
    - HTTPAdapter dengan retry otomatis untuk status 5xx, 429, dan connection errors
    - Connection pooling untuk reuse TCP connection (mengurangi latency)
    - Backoff exponential untuk tidak membebani server
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=0.5,  # 0.5s, 1s, 2s
        status_forcelist=[429, 500, 502, 503, 504],
        # Sertakan POST agar Telegram & API lain juga otomatis retry
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=pool_size,
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