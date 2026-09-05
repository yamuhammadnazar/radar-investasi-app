"""
Radar Portofolio - Main Application
===================================
Terminal monitoring real-time untuk aset dan sentimen pasar strategis.

ARSITEKTUR:
- utils/portals.py    : Konfigurasi portal berita
- utils/http_client.py: Session HTTP dengan retry + connection pooling
- utils/cache.py      : Caching layer berbasis SQLite
- utils/scraper.py    : Scraping concurrent dengan ThreadPoolExecutor
- utils/sentiment.py  : Advanced sentiment (negation + intensifier)
- utils/tickers.py    : NER emiten IDX (regex + kamus emiten)
- utils/telegram_notifier.py: Notifikasi Telegram real-time

PERFORMA:
- Paralelisme: 5 worker per portal, batch processing
- Caching: SQLite TTL (1 jam feed, 6 jam artikel)
- Retry otomatis untuk status 5xx & 429

FITUR:
- Sentiment analisis dengan negasi & intensifier
- Auto-detect emiten via ticker/nama perusahaan
- Telegram notifier dengan filter & quiet hours
"""
import streamlit as st
import pandas as pd
import time
import re
import gc
from datetime import datetime, timedelta
from functools import lru_cache
from dateutil import parser as date_parser
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Optional
from utils import (
    aturan_portal,
    dapatkan_feed_rss,
    scrape_artikel,
    get_http_session,
    get_cache_stats,
    cache_clear_expired,
    analisa_sentimen_advanced,
    extract_tickers,
    extract_portfolio_hits,
    TelegramNotifier,
    TelegramConfig,
    test_connection,
)
# Import cache parsed layer (skip seluruh proses scrape+parse pada hit kedua untuk link yang sama)
try:
    from utils.cache import cache_get_parsed, cache_set_parsed  # noqa: F401
except Exception:  # pragma: no cover - fallback aman bila modul tersedia tanpa cache parsed
    cache_get_parsed = None
    cache_set_parsed = None

from utils.scraper import HALT_FAILURE_RATIO, HALT_MIN_SAMPLE  # noqa: F401  (dipertahankan untuk kompatibilitas, fitur tidak digunakan)

# Adaptive concurrency hint: portal besar diberi worker lebih sedikit agar tidak kena rate-limit
DOMAIN_WORKER_HINT = {
    "detik": 5, "kompas": 5, "cnbcindonesia": 4,
    "kontan": 4, "tempo.co": 6, "katadata": 8,
    "cnn": 5, "liputan6": 5, "kumparan": 6,
    "idnfinancials": 6, "antaranews": 6,
    "tribunnews": 5, "okezone": 5, "republika": 6,
    "jawapos": 6, "merdeka": 6, "pikiran-rakyat": 6,
    "bisnis.com": 5, "metrotvnews": 6, "tvonenews": 6,
    "suara.com": 7, "trenasia": 8, "wartaekonomi": 8,
}


def get_adaptive_workers(nama_portal: str, max_workers: int) -> int:
    """Turunkan worker untuk portal yang rentan rate-limit (bertemu max_workers limit)."""
    key = nama_portal.lower()
    for domain, hint in DOMAIN_WORKER_HINT.items():
        if domain in key:
            return min(hint, max_workers)
    return max_workers


# ============================================================
# KONSTANTA KATEGORI & LEKSIKON
# ============================================================

KATEGORI_PORTOFOLIO = {
    "SAHAM_EMITEN": [
        "arna", "arwana citramulia",
        "bris", "bank syariah indonesia",
        "smsm", "selamat sempurna",
        "sido", "industri jamu dan farmasi sido muncul",
        "ptba", "bukit asam",
        "aces", "aspirasi hidup indonesia",
        "laporan keuangan", "Laba bersih",
    ],
    "SEKTOR_SAHAM": [
        "keramik", "properti", "konstruksi",
        "perbankan", "perbankan syariah",
        "otomotif", "spare part", "aftermarket",
        "farmasi", "herbal", "consumer health",
        "retail", "home improvement",
        "batu bara"
    ],
    "ETF": [
        "r-lq45x", "lq45", "indeks lq45", "rebalancing lq45",
        "konstituen lq45", "etf indonesia", "foreign flow", "SPY", "Indeks SPY"
    ],
    "REKSADANA": [
        "majoris pasar uang syariah", "mandiri invasta dana syariah",
        "sucorinvest equity fund", "pasar uang syariah", "sukuk",
        "sbsn", "obligasi syariah", "reksadana saham", "reksadana obligasi",
        "majoris sukuk negara", "reksadana pasar uang", "reksadana campuran"
    ],
    "EMAS": [
        "emas", "gold", "xau", "xau/usd", "harga emas", "emas pegadaian", "emas antam", "Pegadaian",
        "logam mulia", "LM Antam", "LM Pegadaian"
    ],
    "KOMODITAS": [
        "harga batu bara", "hba", "coal price", "harga minyak", "oil price"
    ],
    "MAKRO_INDONESIA": [
        "bi rate", "bank indonesia", "inflasi indonesia", "rupiah", "usd/idr",
        "gdp indonesia", "pertumbuhan ekonomi", "apbn", "yield obligasi",
        "ihsg", "foreign flow", "net buy asing", "net sell asing","Harga pangan", "inflasi",
        "defisit neraca perdagangan", "ekspor-impor", "neraca perdagangan",
    ],
    "MAKRO_GLOBAL": [
        "federal reserve", "fed rate", "us cpi", "us pce", "us nfp",
        "us treasury yield", "dxy", "china economy", "china stimulus", "ftse", "msci"
    ],
    "REGULASI": [
        "ojk", "bei", "kementerian keuangan", "kementerian esdm",
        "kementerian perindustrian", "kementerian perdagangan",
        "kebijakan pemerintah", "aturan ekspor", "aturan impor", "kebijakan pajak", "dpr", "BKN", "MenPanRp", "Mahkamah Konstitusi",
        "pemerintah kabupaten landak", "pemerintah provinsi kalimantan barat", "ngabang", "kalbar",
    ],
    "TEKNOLOGI": [
        "teknologi", "technology", "startup", "unicorn", "decacorn",
        "kecerdasan buatan", "artificial intelligence", "ai", "chatgpt", "gpt",
        "machine learning", "deep learning", "llm", "model bahasa",
        "semikonduktor", "chip", "nvidia", "tsmc", "asml",
        "kripto", "cryptocurrency", "bitcoin", "ethereum", "blockchain", "web3",
        "fintech", "paylater", "dompet digital", "e-wallet",
        "e-commerce", "marketplace", "tokopedia", "shopee", "bukalapak",
        "listrik kendaraan", "kendaraan listrik", "ev", "baterai litium",
        "data center", "pusat data", "cloud", "cloud computing", "aws",
        "5g", "jaringan 5g", "satelit", "starlink",
        "siber", "keamanan siber", "cybersecurity", "ransomware", "peretasan",
        "smartphone", "gadget", "aplikasi", "apps", "platform digital",
        "meta", "google", "alphabet", "microsoft", "apple", "openai", "bytedance",
        "metaverse", "augmented reality", "virtual reality", "ar/vr",
        "big data", "analitik data", "internet of things", "iot",
        "sistem operasi", "perangkat lunak", "software", "saas",
        "transformasi digital", "digitalisasi", "ekonomi digital",
        "GoTo", "Gojek", "Grab", "Traveloka", "Bukalapak",
        "industri kreatif digital", "penjualan daring", "online shopping",
        "penipuan daring", "penipuan online", "judi online"
    ],
    "LUAR_NEGERI": [
        "luar negeri", "global market", "pasar global", "global index", "global indices",
        "wall street", "new york stock exchange", "nyse", "nasdaq", "dow jones",
        "s&p 500", "sp500", "russell 2000", "vix", "fear and greed",
        "nikkei", "nikkei 225", "topix", "bursa jepang", "bursa tokyo",
        "hang seng", "hsi", "bursa hong kong",
        "shanghai composite", "sse", "szse", "bursa tiongkok", "bursa shanghai", "bursa shenzhen",
        "kospi", "bursa korea", "bursa selatan",
        "straits times", "sti", "bursa singapura", "sgx",
        "ftse 100", "bursa london", "london stock exchange", "lse",
        "dax", "bursa jerman", "bursa frankfurt",
        "cac 40", "bursa prancis", "bursa paris",
        "eurostoxx", "stoxx 600", "bursa eropa", "euronext",
        "asx 200", "bursa australia",
        "bse sensex", "nifty 50", "bursa india",
        "bursa thailand", "set index", "bursa filipina", "psei",
        "bursa vietnam", "bursa malaysia", "bursa indonesia",
        "emerging market", "pasar berkembang", "em market",
        "foreign exchange", "forex", "fx", "mata uang asing",
        "eur/usd", "usd/jpy", "usd/cny", "usd/sgd", "gbp/usd",
        "offshore", "capital outflow", "capital inflow", "foreign investment",
        "multi national company", "multinational", "mnc",
        "economic data", "manufacturing pmi", "services pmi",
        "trade deficit", "trade surplus", "tariff", "bea masuk",
        "apple", "microsoft", "nvidia", "tesla", "amazon", "meta", "google",
        "berita luar negeri", "berita internasional", "internasional",
        "inflasi global", "resesi global", "pertumbuhan global", "global growth"
    ],
    "UMUM": [
        "cpns", "seleksi cpns", "energi", "kelistrikan", "bbm", "daya beli",
        "Indeks", "Bencana", "Anime", "Game"
    ]
}

KATA_POSITIF = [
    "laba", "untung", "naik", "melonjak", "meroket", "tumbuh", "ekspansi",
    "dividen", "deviden", "surplus", "bullish", "rekor", "positif", "penguatan",
    "terangkat", "melejit", "dividen yield", "buyback", "prospek cerah"
]

KATA_NEGATIF = [
    "rugi", "kerugian", "anjlok", "turun", "merosot", "terperosok", "gugatan",
    "sanksi", "denda", "bearish", "negatif", "pelemahan", "tertekan", "kasus",
    "pailit", "bangkrut", "korupsi", "sengketa", "gagal bayar", "pemecatan", "phk"
]

STOPWORDS_ID = set([
    "yang", "di", "dan", "dengan", "untuk", "pada", "ke", "karena", "oleh", "dari",
    "ini", "itu", "akan", "juga", "atau", "bisa", "tidak", "ada", "seperti", "tahun",
    "saat", "menjadi", "lebih", "hari", "secara", "sudah", "dapat", "tersebut", "persen",
    "rp", "juta", "miliar", "triliun", "sebesar", "mencapai", "catat", "hingga"
])

kata_kunci_portofolio = [kw for sublist in KATEGORI_PORTOFOLIO.values() for kw in sublist]

# ============================================================
# PRE-COMPILED REGEX untuk performa
# ============================================================
# Membuat satu pola besar sekali saja (O(1) kompilasi) dibanding
# mem-build regex di dalam loop process_entry untuk ~80 kata kunci.
_KK_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(set(kata_kunci_portofolio), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Pre-compiled per kategori untuk tentukan_kategori_aset (menghindari
# mem-build ulang ~80 pola regex di hot path).
_KATEGORI_PATTERNS = {
    kat: [
        re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
        for kw in sorted(set(keywords), key=len, reverse=True)
    ]
    for kat, keywords in KATEGORI_PORTOFOLIO.items()
}



# ============================================================
# HELPER FUNCTIONS (TIDAK BERUBAH SIGNIFIKAN)
# ============================================================

def konversi_ke_datetime(tanggal_str):
    if not tanggal_str or tanggal_str == 'N/A':
        return datetime.now()
    try:
        dt = date_parser.parse(tanggal_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return datetime.now()


def apakah_dalam_rentang(tanggal_str, jam_maksimal):
    """Cek apakah tanggal berita berada dalam rentang jam_maksimal dari sekarang.

    Toleransi waktu bersifat PROPORSIONAL terhadap rentang yang diminta:
      - 10% dari jam_maksimal, dengan minimum 30 menit dan maksimum 2 jam.
    Tujuan: mencegah toleransi tetap (2 jam) yang melebar dramatis pada
    rentang pendek (mis. '3 Jam Terakhir' efektif menjadi 5 jam / +66%).
    """
    if not tanggal_str or tanggal_str == 'N/A':
        return True
    try:
        dt_berita = date_parser.parse(tanggal_str)
        if dt_berita.tzinfo is not None:
            dt_berita = dt_berita.astimezone().replace(tzinfo=None)
        waktu_sekarang = datetime.now()
        batas_waktu = waktu_sekarang - timedelta(hours=jam_maksimal)
        # Toleransi proporsional: 10% rentang, dibatasi 0.5 jam .. 2 jam.
        toleransi_jam = max(0.5, min(2.0, jam_maksimal * 0.10))
        batas_waktu_dengan_toleransi = batas_waktu - timedelta(hours=toleransi_jam)
        return batas_waktu_dengan_toleransi <= dt_berita <= waktu_sekarang
    except Exception:
        return True


def cek_status_bursa(dt_obj):
    if dt_obj == datetime.min:
        return "Waktu N/A"
    hari = dt_obj.weekday()
    jam = dt_obj.hour
    if hari in [5, 6]:
        return "Akhir Pekan (Tutup)"
    if 9 <= jam < 16:
        return "Bursa Buka"
    return "Luar Jam Bursa"


def tentukan_kategori_aset(teks_lower):
    # Pre-compiled patterns grouped by kategori agar O(n) loop tanpa rebuild regex
    for kat, patterns in _KATEGORI_PATTERNS.items():
        for pat in patterns:
            if pat.search(teks_lower):
                # Mapping kategori -> label output
                if kat in ("SAHAM_EMITEN", "SEKTOR_SAHAM"):
                    return "SAHAM"
                if kat in ("ETF", "REKSADANA"):
                    return "REKSADANA_ETF"
                if kat in ("EMAS", "KOMODITAS"):
                    return "EMAS_KOMODITAS"
                if kat in ("MAKRO_INDONESIA", "MAKRO_GLOBAL", "REGULASI"):
                    return "MAKRO_REGULASI"
                if kat == "TEKNOLOGI":
                    return "TEKNOLOGI"
                if kat == "LUAR_NEGERI":
                    return "LUAR_NEGERI"
                if kat == "UMUM":
                    return "UMUM"
    return "MAKRO_REGULASI"


@lru_cache(maxsize=4096)
def bersihkan_judul(judul):
    j = re.sub(r'[^a-zA-Z0-9\s]', '', judul.lower())
    j = re.sub(
        r'\s+(cnbc|investor|kontan|katadata|tempo|antara|idxchannel|idnfinancials|detik|bloomberg|cnn|kompas|bisnis|swa|bareksa|trenasia|wartaekonomi|rm).*$',
        '', j
    )
    kata_inti = [kata for kata in j.split() if kata not in STOPWORDS_ID]
    return " ".join(kata_inti).strip()


def sort_entries_by_recency(entries: list) -> list:
    """Sort RSS entry paling baru dulu. Yang datetime.min taruh di akhir."""
    def parse_dt(entry):
        t = entry.get("published", "") or entry.get("updated", "")
        if not t or t == 'N/A':
            return datetime.min
        try:
            return date_parser.parse(t)
        except Exception:
            return datetime.min
    return sorted(entries, key=parse_dt, reverse=True)


def rasio_kemiripan(a, b):
    return SequenceMatcher(None, a, b).ratio()


def apakah_duplikat(judul_baru, link_baru, daftar_tersimpan, ambang):
    judul_bersih = bersihkan_judul(judul_baru)
    for item in daftar_tersimpan:
        if link_baru == item['link']:
            return True
        if rasio_kemiripan(judul_bersih, item['judul_bersih']) >= ambang:
            return True
    return False


def ringkas_teks(teks, kata_kunci_list, max_kalimat=2):
    if not teks or "tidak dapat diekstrak" in teks or "terkunci" in teks:
        return "-"
    kalimat_list = re.split(r'(?<=[.!?]) +', teks)
    if len(kalimat_list) <= max_kalimat:
        return teks
    skor_kalimat = []
    for index, kalimat in enumerate(kalimat_list):
        kalimat_lower = kalimat.lower()
        skor = 3 if index == 0 else (2 if index == 1 else 0)
        for kw in kata_kunci_list:
            if kw in kalimat_lower:
                skor += 2
        for kw in KATA_POSITIF + KATA_NEGATIF:
            if kw in kalimat_lower:
                skor += 1.5
        skor_kalimat.append((skor, index, kalimat))
    kalimat_terpilih = sorted(skor_kalimat, key=lambda x: x[0], reverse=True)[:max_kalimat]
    kalimat_terpilih_urut = sorted(kalimat_terpilih, key=lambda x: x[1])
    return " ".join([k[2] for k in kalimat_terpilih_urut])


# ============================================================
# CORE: PROCESS SINGLE ENTRY (untuk ThreadPoolExecutor)
# ============================================================

def process_entry(
    entry,
    aturan: dict,
    jam_filter: int,
    aktifkan_deduplikasi: bool,
    ambang_duplikat: float,
    daftar_tersimpan: list,
    dedup_lock: Optional[Lock] = None,
) -> Optional[dict]:
    """
    Proses satu entry RSS sampai menjadi record siap-simpan.
    Dipanggil paralel via ThreadPoolExecutor.
    Mengembalikan dict atau None jika di-skip.
    """
    judul = entry.get("title", "N/A")
    link = entry.get("link", "N/A")
    tanggal = entry.get("published", "") or entry.get("updated", "N/A")
    deskripsi = entry.get("summary", "") + " " + entry.get("description", "")

    # OPTIMASI #1 (pra-scrape skip): entry tanpa judul/link valid di-skip
    # sebelum mem-build teks_pencocokan atau scrape_artikel().
    if not judul or judul == "N/A" or not link or link == "N/A":
        return None

    # OPTIMASI: Filter kata kunci portofolio DULU (cepat, regex pre-compiled)
    # sebelum scrape body artikel (lambat). Mencegah scrape artikel yang
    # jelas tidak relevan dan menghemat waktu signifikan.
    teks_pencocokan = (judul + " " + deskripsi).lower()
    match = _KK_PATTERN.search(teks_pencocokan)
    if match is None:
        return None
    trigger_terdeteksi = match.group(1).upper()

    # CATATAN: Filter waktu pra-scrape HANYA untuk portal terpercaya
    # (field aturan['tanggal_terpercaya'] == True). Portal ini umumnya
    # menggunakan RSS asli (bukan Google News) sehingga tanggal RSS akurat
    # dan bisa dipakai untuk skip artikel lama SEBELUM scrape yang lambat.
    # Untuk portal non-terpercaya, filter waktu tetap dilakukan di akhir
    # (setelah scrape) dengan fallback tanggal dari HTML — lihat di bawah.
    if jam_filter < 87600 and aturan.get("tanggal_terpercaya"):
        if not apakah_dalam_rentang(tanggal, jam_filter):
            return None

    # Deduplication: check + reserve harus atomik agar dua thread tidak
    # memproses artikel yang sama secara bersamaan.
    if aktifkan_deduplikasi:
        if dedup_lock is None:
            if apakah_duplikat(judul, link, daftar_tersimpan, ambang_duplikat):
                return None
            daftar_tersimpan.append({"link": link, "judul_bersih": bersihkan_judul(judul)})
        else:
            with dedup_lock:
                if apakah_duplikat(judul, link, daftar_tersimpan, ambang_duplikat):
                    return None
                daftar_tersimpan.append({"link": link, "judul_bersih": bersihkan_judul(judul)})

    # Scrape isi artikel (dengan cache & retry internal)
    hasil = scrape_artikel(entry, aturan)
    if hasil is None:
        return None

    isi = hasil.get("isi", "Konten tidak dapat diekstrak.")
    status_akses = hasil.get("status_akses", "Error")

    # OPTIMASI: Filter waktu di-akhir, setelah kita punya tanggal & isi aktual.
    # Strategi dua-tingkat untuk akurasi maksimal:
    #   1. Cek tanggal RSS ( cepat tapi sering tidak akurat, terutama Google News).
    #   2. Jika tanggal RSS gagal/tidak dalam rentang, coba tanggal dari hasil
    #      scrape halaman artikel (lebih akurat karena di-parse dari HTML).
    #   3. Jika keduanya gagal, baru artikel dibuang — kecuali user minta
    #      "Semua Berita" (jam_filter == 87600, tanpa filter).
    if jam_filter < 87600:
        tanggal_efektif = tanggal
        if not apakah_dalam_rentang(tanggal_efektif, jam_filter):
            # Fallback: ambil tanggal dari hasil scrape (lebih akurat dari HTML).
            tanggal_scrape = hasil.get("tanggal", "") or ""
            if tanggal_scrape and tanggal_scrape != tanggal and tanggal_scrape != 'N/A':
                if apakah_dalam_rentang(tanggal_scrape, jam_filter):
                    tanggal = tanggal_scrape  # pakai tanggal scrape untuk record
                else:
                    return None
            else:
                return None

    # ============================================================
    # ANALISIS LANJUTAN: SENTIMENT + NER
    # ============================================================

    # 1. Advanced sentiment (dengan negasi & intensifier)
    full_text = judul + " " + isi
    sentimen_label, sentimen_conf, sentimen_debug = analisa_sentimen_advanced(full_text)

    # 2. NER: deteksi ticker emiten dari teks
    ticker_entities = extract_tickers(full_text, top_n=3)
    primary_ticker = ticker_entities[0]["ticker"] if ticker_entities else trigger_terdeteksi

    # 3. Highlight jika portofolio user terkena
    portfolio_hits = extract_portfolio_hits(full_text)
    is_portfolio = len(portfolio_hits) > 0

    # 4. Ringkasan & kategori
    ringkasan_teks = ringkas_teks(isi, kata_kunci_portofolio, max_kalimat=2)
    kategori_aset = tentukan_kategori_aset(teks_pencocokan)
    dt_obj = konversi_ke_datetime(tanggal)

    record = {
        "Sumber": aturan.get("__nama_portal", "N/A"),
        "Kategori Aset": kategori_aset,
        "Trigger/Emiten": trigger_terdeteksi,
        "PrimaryTicker": primary_ticker,
        "TickerEntities": ticker_entities,
        "IsPortfolio": is_portfolio,
        "Sentimen": sentimen_label,
        "SentimenConfidence": sentimen_conf,
        "SentimenSkor": sentimen_debug["skor"],
        "Status Bursa": cek_status_bursa(dt_obj),
        "Akses": status_akses,
        "Judul": judul,
        "Tanggal": tanggal,
        "dt_sort": dt_obj,
        "Ringkasan Berita": ringkasan_teks,
        "Link": link,
        "Isi Berita": isi,
    }

    return record


# ============================================================
# STREAMLIT UI
# ============================================================

st.set_page_config(
    page_title="Radar Investasi Multi",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .stApp { background-color: #0d1117; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
            border-right: 1px solid #30363d;
            padding-top: 1rem;
        }
        [data-testid="stSidebarNav"]::before {
            content: "NAVIGASI UTAMA";
            display: block; margin-left: 20px; margin-bottom: 10px;
            font-size: 11px; font-weight: 800; color: #8b949e; letter-spacing: 1.2px;
        }
        [data-testid="stSidebarNav"] ul { gap: 6px; }
        [data-testid="stSidebarNav"] a {
            border-radius: 8px; padding: 8px 12px;
            color: #c9d1d9 !important; font-weight: 500;
            transition: all 0.2s ease-in-out;
        }
        [data-testid="stSidebarNav"] a:hover {
            background-color: rgba(31, 111, 235, 0.15);
            color: #58a6ff !important;
            transform: translateX(4px);
        }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: linear-gradient(135deg, #1f6feb 0%, #238636 100%);
            color: white !important; font-weight: 600;
            box-shadow: 0 3px 8px rgba(31, 111, 235, 0.3);
        }
        div.stExpander {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .metric-card {
            background-color: #161b22;
            padding: 18px;
            border-radius: 12px;
            border: 1px solid #30363d;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 22px; font-weight: 700;
            color: #58a6ff; margin-top: 4px;
        }
        .metric-label {
            font-size: 11px; color: #8b949e;
            text-transform: uppercase; letter-spacing: 1px;
        }
        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #1f6feb 0%, #238636 100%);
            color: white; font-weight: 600;
            border-radius: 8px; border: none;
            padding: 0.6rem 1.2rem;
            box-shadow: 0 4px 12px rgba(35, 134, 54, 0.3);
        }
        .stButton button[kind="primary"]:active,
        .stButton button[kind="primary"]:focus {
            background: linear-gradient(135deg, #1f6feb 0%, #238636 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(35, 134, 54, 0.5) !important;
        }
        @media (max-width: 768px) {
            .header-title { font-size: 1.6rem !important; line-height: 1.2; }
            .header-card { padding: 1rem !important; }
            .header-subtitle { font-size: 0.95rem !important; }
            .tag-container { flex-wrap: wrap !important; gap: 5px !important; }
            .tag { font-size: 0.72rem !important; padding: 3px 8px !important; }
            .metric-card { margin-bottom: 10px !important; padding: 12px !important; }
            .metric-value { font-size: 1.3rem !important; }
            .metric-label { font-size: 0.62rem !important; letter-spacing: 0.8px; }
            /* Dataframe jangan overflow di mobile */
            [data-testid="stDataFrame"] { overflow-x: auto !important; }
            [data-testid="stDataFrame"] table { font-size: 0.78rem !important; }
            /* Buttons full-width */
            [data-testid="stButton"] > button { width: 100% !important; }
            /* Plot container responsif */
            [data-testid="stPlotlyChart"], img { max-width: 100% !important; height: auto !important; }
            /* Tabs scrollable horizontal */
            [data-testid="stTabs"] [role="tablist"] {
                overflow-x: auto !important;
                flex-wrap: nowrap !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

# Session state
if 'df_hasil' not in st.session_state:
    st.session_state.df_hasil = None
if 'duration_scan' not in st.session_state:
    st.session_state.duration_scan = 0
if 'last_scan_at' not in st.session_state:
    st.session_state.last_scan_at = None
if 'skor_indeks_val' not in st.session_state:
    st.session_state.skor_indeks_val = 50.0
if 'scan_stats' not in st.session_state:
    st.session_state.scan_stats = {"paralel_workers": 8, "cache_hits": 0}

# Header
st.markdown("""
    <style>
        .header-card {
            background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            padding: 2rem; border-radius: 16px;
            border: 1px solid #30363d;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            margin-bottom: 2rem;
        }
        .header-title {
            font-size: 2.5rem; font-weight: 800;
            color: #ffffff; margin: 0;
            background: linear-gradient(to right, #ffffff, #8b949e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-subtitle {
            color: #8b949e; font-size: 1.1rem;
            margin-top: 0.5rem; font-weight: 400;
        }
        .tag-container { display: flex; gap: 10px; margin-top: 1.5rem; }
        .tag {
            background: rgba(88, 166, 255, 0.1); color: #58a6ff;
            padding: 4px 12px; border-radius: 20px;
            font-size: 0.85rem; font-weight: 600;
            border: 1px solid rgba(88, 166, 255, 0.2);
        }
    </style>
    <div class="header-card">
        <h1 class="header-title">Radar Portofolio 📡</h1>
        <p class="header-subtitle">Terminal monitoring real-time untuk aset dan sentimen pasar strategis.</p>
        <div class="tag-container">
            <span class="tag">Emiten</span>
            <span class="tag">ETF & Reksadana</span>
            <span class="tag">Komoditas</span>
            <span class="tag">Makro & Regulasi</span>
            <span class="tag">Umum (CPNS)</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Metric cards
if st.session_state.df_hasil is not None:
    df_mem = st.session_state.df_hasil
    tot_berita = len(df_mem)
    tot_pos = len(df_mem[df_mem['Sentimen'] == 'POSITIF'])
    tot_neg = len(df_mem[df_mem['Sentimen'] == 'NEGATIF'])
    dur_scan = st.session_state.duration_scan

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        f'<div class="metric-card"><div class="metric-label">Total Berita</div>'
        f'<div class="metric-value">{tot_berita} Artikel</div></div>',
        unsafe_allow_html=True
    )
    c2.markdown(
        f'<div class="metric-card"><div class="metric-label">Positif</div>'
        f'<div class="metric-value" style="color: #2ea043;">{tot_pos} Berita</div></div>',
        unsafe_allow_html=True
    )
    c3.markdown(
        f'<div class="metric-card"><div class="metric-label">Negatif</div>'
        f'<div class="metric-value" style="color: #f85149;">{tot_neg} Berita</div></div>',
        unsafe_allow_html=True
    )
    c4.markdown(
        f'<div class="metric-card"><div class="metric-label">Waktu Scan</div>'
        f'<div class="metric-value">{dur_scan} Detik</div></div>',
        unsafe_allow_html=True
    )
    last_scan_at = st.session_state.get("last_scan_at")
    if last_scan_at:
        st.caption(
            f"🕒 Pemindaian terakhir: {last_scan_at.strftime('%d/%m/%Y %H:%M:%S')} "
            f"· Cache baru: {st.session_state.scan_stats.get('cache_hits', 0)} entry"
        )
    st.markdown("<br>", unsafe_allow_html=True)

# Info panel
st.markdown("""
    <div style="background: rgba(31, 111, 235, 0.05); border-left: 4px solid #1f6feb;
         padding: 15px; border-radius: 4px; margin-bottom: 20px;">
        <p style="margin: 0; font-size: 1rem; color: #c9d1d9;">
            <strong style="color: #58a6ff;">💡 Siap Memindai?</strong>
            Sesuaikan parameter di <strong>Panel Pengaturan</strong> (bawah),
            lalu tekan tombol <strong>Mulai Pemindaian</strong> untuk mendapatkan insight pasar terkini.
        </p>
    </div>
""", unsafe_allow_html=True)


# ============================================================
# KONFIGURASI PANEL
# ============================================================

with st.expander("⚙️ Konfigurasi Radar & Notifikasi", expanded=False):
    tab1, tab2, tab3 = st.tabs(["🗄️ Sumber Berita", "🔔 Notifikasi & Opsi", "⚡ Performa"])

    with tab1:
        st.markdown("### Pilih Kanal Berita")
        semua_portal_keys = list(aturan_portal.keys())
        pilih_semua = st.checkbox("Pilih Semua Portal", value=True)
        portal_terpilih = st.multiselect(
            "Filter Kanal:",
            options=semua_portal_keys,
            default=semua_portal_keys if pilih_semua else []
        )

        pilihan_rentang = st.select_slider(
            "Rentang Waktu Pemindaian:",
            options=["3 Jam Terakhir", "6 Jam Terakhir", "12 Jam Terakhir",
                     "24 Jam Terakhir (1 Hari)", "3 Hari Terakhir",
                     "Semua Berita (Tanpa Batas)"],
            value="24 Jam Terakhir (1 Hari)"
        )
        map_jam = {
            "3 Jam Terakhir": 3,
            "6 Jam Terakhir": 6,
            "12 Jam Terakhir": 12,
            "24 Jam Terakhir (1 Hari)": 24,
            "3 Hari Terakhir": 72,
            "Semua Berita (Tanpa Batas)": 87600,
        }
        jam_filter = map_jam[pilihan_rentang]

    with tab2:
        st.markdown("### Parameter & Bot")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            aktifkan_deduplikasi = st.toggle("Anti-Duplikat", value=True)
        with col_c2:
            ambang_duplikat = st.slider("Ambang Kemiripan:", 0.5, 0.95, 0.75, 0.05)

        st.markdown("---")
        st.markdown("**📲 Integrasi Telegram Notifier**")
        telegram_aktif = st.toggle(
            "Aktifkan Notifikasi Telegram",
            value=False,
            help="Kirim alert otomatis ke Telegram saat ada berita sesuai filter"
        )
        col_tg1, col_tg2 = st.columns(2)
        with col_tg1:
            bot_token = st.text_input("Bot Token:", placeholder="123456:ABC-DEF...", type="password")
        with col_tg2:
            chat_id = st.text_input("Chat ID:", placeholder="-1001234567890 atau @username", value="")

        # Filter notifikasi
        st.markdown("##### 🔔 Filter Notifikasi")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            telegram_min_sentimen = st.selectbox(
                "Kirim hanya sentimen:",
                ["ANY", "POSITIF", "NEGATIF"],
                help="Filter apa saja yang dikirim ke Telegram"
            )
        with col_f2:
            telegram_only_portfolio = st.toggle(
                "Hanya emiten portofolio",
                value=False,
                help="Hanya kirim jika emiten ada di watchlist (ARNA, BRIS, SMSM, dll)"
            )

        telegram_batch_mode = st.checkbox(
            "Mode Batch (kirim digest setiap 10 berita)",
            value=False
        )

        # Test koneksi button
        if bot_token and chat_id:
            if st.button("🔌 Tes Koneksi Telegram"):
                success, msg = test_connection(bot_token, chat_id)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    with tab3:
        st.markdown("### ⚡ Optimasi Performa")
        max_workers = st.slider(
            "Worker Paralel:",
            min_value=1, max_value=15, value=8,
            help="Jumlah thread paralel. Rekomendasi: 6-10 untuk keseimbangan kecepatan & rate-limit."
        )
        max_artikel_per_portal = st.slider(
            "Maks Artikel per Portal:",
            min_value=5, max_value=50, value=40,
            help="Batas artikel yang di-scrape per portal."
        )

        st.markdown("---")
        st.markdown("**📊 Status Cache**")
        cache_stats = get_cache_stats()
        col_cs1, col_cs2, col_cs3 = st.columns(3)
        col_cs1.metric("Total Entry", cache_stats["total"])
        col_cs2.metric("Aktif", cache_stats["active"], help=f"Entry expired: {cache_stats['expired']}")
        col_cs3.metric("Ukuran DB", f"{cache_stats['size_mb']} MB")

        if st.button("🧹 Bersihkan Cache Expired"):
            cleared = cache_clear_expired()
            st.success(f"{cleared} entry expired dihapus.")

st.markdown("<br>", unsafe_allow_html=True)

# Tombol Aksi
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    tombol_scan = st.button("🚀 Mulai Pemindaian Radar Sekarang!", type="primary", use_container_width=True)
with col_btn2:
    tombol_stop = st.button("🛑 Stop & Tampilkan Hasil Sementara", use_container_width=True)

st.markdown("---")

if tombol_stop:
    if st.session_state.df_hasil is not None:
        st.success("Pemindaian dihentikan. Menampilkan data yang sudah berhasil terkumpul sejauh ini.")
        st.rerun()
    else:
        st.warning("Belum ada data yang terkumpul untuk ditampilkan.")


# ============================================================
# EKSEKUSI SCAN (PARALEL)
# ============================================================

if tombol_scan:
    if len(portal_terpilih) == 0:
        st.warning("Pilih minimal satu portal berita terlebih dahulu.")
    else:
        kumpulan_data_global: list[dict] = []
        daftar_tersimpan: list[dict] = []
        dedup_lock = Lock()
        timer_container = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()

        start_time = time.time()
        total_portal = len(portal_terpilih)

        cache_hits_awal = get_cache_stats()
        cache_total_awal = cache_hits_awal["total"]

        # Loop utama: tiap portal di-fetch secara paralel di dalamnya
        # Statistik kegagalan per-portal (untuk laporan akhir)
        portal_failure_counts: dict[str, int] = {}
        portal_halted_flags: dict[str, bool] = {}

        for idx, nama_portal in enumerate(portal_terpilih):
            elapsed_time = round(time.time() - start_time, 1)
            timer_container.markdown(f"""
                <div style="background: rgba(31, 111, 235, 0.1); border: 1px solid #1f6feb;
                     padding: 10px 15px; border-radius: 8px; color: #c9d1d9;
                     display: flex; justify-content: space-between; align-items: center;">
                    <span>📡 Sedang Memindai: <strong style="color: #58a6ff;">{nama_portal}</strong>
                    <span style="color: #8b949e; font-size: 0.9em;">({idx+1}/{total_portal})</span></span>
                    <span style="font-family: monospace; color: #3fb950; font-weight: bold;">⏱️ {elapsed_time}s</span>
                </div>
            """, unsafe_allow_html=True)

            # Lindungi per-portal: error fatal pada satu portal tidak menggagalkan seluruh scan.
            try:
                aturan = dict(aturan_portal[nama_portal])  # copy agar tidak modify global
                aturan["__nama_portal"] = nama_portal

                feed = dapatkan_feed_rss(aturan)
                if not feed or not hasattr(feed, "entries") or len(feed.entries) == 0:
                    progress_bar.progress((idx + 1) / total_portal)
                    portal_failure_counts[nama_portal] = portal_failure_counts.get(nama_portal, 0) + 1
                    continue

                # Batasi jumlah entry yang akan diproses
                # OPTIMASI #6: sort by recency (entry terbaru diproses duluan),
                # sehingga hasil yang lolos filter waktu tampil lebih awal (progressive rendering).
                target_entries = sort_entries_by_recency(list(feed.entries))[:max_artikel_per_portal]
                session = get_http_session()

                # OPTIMASI #3: adaptive worker untuk portal rentan rate-limit.
                # Portal besar (Detik, Kompas, CNBC) pakai worker lebih sedikit.
                effective_workers = get_adaptive_workers(nama_portal, max_workers)

                # PARALEL: ThreadPoolExecutor untuk entry dalam 1 portal.
                # FITUR HENTI DINI DINONAKTIFKAN — semua entry akan diproses
                # sampai selesai (timeout) untuk hasil scrapping maksimal,
                # walau sebagian ada yang gagal akses (transient/rate-limit).
                processed_count = 0
                failed_count = 0

                # PARALEL: ThreadPoolExecutor untuk entry dalam 1 portal
                with ThreadPoolExecutor(max_workers=effective_workers) as executor:
                    # Submit semua entry
                    future_to_entry = {
                        executor.submit(
                            process_entry,
                            entry, aturan, jam_filter,
                            aktifkan_deduplikasi, ambang_duplikat,
                            daftar_tersimpan, dedup_lock,
                        ): entry
                        for entry in target_entries
                    }

                    # Kumpulkan hasil — semua future dibiarkan selesai,
                    # tidak ada cancel/break. Hanya hitung statistik gagal.
                    for future in as_completed(future_to_entry, timeout=120):
                        processed_count += 1
                        try:
                            record = future.result(timeout=10)
                        except Exception:
                            record = None

                        if record is None:
                            failed_count += 1
                            continue

                        # Sukses
                        kumpulan_data_global.append(record)

                portal_failure_counts[nama_portal] = failed_count
                portal_halted_flags[nama_portal] = False

                # Update progress
                progress_bar.progress((idx + 1) / total_portal)
                status_text.text(
                    f"✅ {nama_portal}: {processed_count}/{len(target_entries)} selesai "
                    f"(gagal: {failed_count}) | "
                    f"Total: {len(kumpulan_data_global)} berita"
                )

                # Simpan incremental
                if kumpulan_data_global:
                    st.session_state.df_hasil = (
                        pd.DataFrame(kumpulan_data_global)
                        .sort_values(by="dt_sort", ascending=False)
                        .reset_index(drop=True)
                    )

                # Memory cleanup periodik
                if (idx + 1) % 5 == 0:
                    gc.collect()
            except Exception as portal_err:
                # Tangani error per-portal: log ke status, lewati portal, lanjut ke berikutnya.
                # Hindari satu portal bermasalah (mis. NameError/KeyError) menggagalkan seluruh scan.
                status_text.text(f"❌ Portal {nama_portal} dilewati karena error: {str(portal_err)[:100]}")
                portal_failure_counts[nama_portal] = -1
                portal_halted_flags[nama_portal] = False
                progress_bar.progress((idx + 1) / total_portal)
                continue

        # Selesai
        duration = round(time.time() - start_time, 2)
        timer_container.empty()
        progress_bar.empty()
        status_text.empty()

        # Hitung cache hit selama scan
        cache_stats_akhir = get_cache_stats()
        cache_hits_scan = cache_stats_akhir["total"] - cache_total_awal

        if kumpulan_data_global:
            df = (
                pd.DataFrame(kumpulan_data_global)
                .sort_values(by="dt_sort", ascending=False)
                .reset_index(drop=True)
            )
            st.session_state.df_hasil = df
            st.session_state.duration_scan = duration
            st.session_state.last_scan_at = datetime.now()
            st.session_state.scan_stats = {
                "paralel_workers": max_workers,
                "cache_hits": max(0, cache_hits_scan),
            }

            n_pos = len(df[df["Sentimen"] == "POSITIF"])
            n_neg = len(df[df["Sentimen"] == "NEGATIF"])
            non_netral = n_pos + n_neg
            st.session_state.skor_indeks_val = (
                round((n_pos / non_netral) * 100, 1) if non_netral > 0 else 50.0
            )

            # ============================================================
            # TELEGRAM NOTIFICATION (jika aktif)
            # ============================================================
            telegram_sent = 0
            telegram_terakhir_error = None
            if telegram_aktif and bot_token and chat_id:
                try:
                    tg_config = TelegramConfig(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        enabled=True,
                        min_sentiment=telegram_min_sentimen,
                        portfolio_only=telegram_only_portfolio,
                        batch_mode=telegram_batch_mode,
                    )
                    notifier = TelegramNotifier(tg_config)
                    for record in kumpulan_data_global:
                        if notifier.notify_artikel(record):
                            telegram_sent += 1
                    # Flush sisa batch
                    if telegram_batch_mode:
                        notifier.flush_batch()
                except Exception as e:
                    telegram_terakhir_error = str(e)[:80]

            success_msg = (
                f"🎯 Radar Selesai! Menemukan {len(df)} berita unik dalam {duration} detik "
                f"(workers={max_workers}, cache entries baru={max(0, cache_hits_scan)})."
            )
            if telegram_aktif and bot_token and chat_id:
                if telegram_terakhir_error:
                    success_msg += f" ⚠️ Telegram error: {telegram_terakhir_error}"
                else:
                    success_msg += f" 📲 Telegram: {telegram_sent} notif terkirim."
            st.success(success_msg)
        else:
            st.warning("Tidak ada berita yang sesuai dengan kriteria waktu & kata kunci portofolio.")

        # Final cleanup
        gc.collect()