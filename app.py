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
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from dateutil import parser as date_parser

# ============================================================
# ZONA WAKTU INDONESIA (WIB = UTC+7) — FIX WAKTU RENTANG SCAN
# ============================================================
#
# Latar belakang masalah:
# - Server tempat Streamlit dijalankan bisa berada dalam zona UTC
#   (Docker, Linux container, VPS tanpa TZ=Asia/Jakarta, cloud runtimes).
# - `datetime.now()` pada server UTC akan menghasilkan waktu naive UTC,
#   sehingga label "WIB" yang dicetak ke UI SALAH dan batas atas
#   `apakah_dalam_rentang` ikut bergeser → berita yang sebenarnya masih
#   di rentang (mis. 07.23 WIB) terdeteksi "terlalu baru" / di luar rentang.
# - Indonesia tidak memberlakukan DST, jadi UTC+7 adalah konstanta sepanjang
#   tahun (WIT = UTC+9, WITA = UTC+8 dipakai hanya jika ingin multi-zona).
#
# Solusi: helper `wib_now()` — selalu kembalikan datetime naive yang
# merepresentasikan waktu WIB (UTC+7), independen dari zona waktu server.
# Sengaja mengembalikan datetime NAIVE agar kompatibel dengan sisa kode
# yang membandingkan `dt_berita.astimezone().replace(tzinfo=None)`.
# ============================================================

WIB_OFFSET = timezone(timedelta(hours=7))  # Asia/Jakarta (WIB)


def wib_now():
    """Return datetime naive yang merepresentasikan waktu WIB (UTC+7) saat ini.

    Tidak bergantung pada zona waktu sistem — selalu dikonversi dari UTC
    eksplisit ke UTC+7 terlebih dahulu. Aman untuk server Windows/Linux/
    Docker/VPS dengan zona waktu sistem apapun.
    """
    sekarang_utc = datetime.now(timezone.utc)  # aware UTC
    return sekarang_utc.astimezone(WIB_OFFSET).replace(tzinfo=None)  # naive WIB


# Catatan: konstanta performa adaptif didefinisikan SETELAH import `st`
# (lihat blok DOMAIN_WORKER_HINT di bawah) karena helper-nya membaca
# st.session_state.

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

# Adaptive concurrency hint: portal besar diberi worker lebih sedikit agar tidak kena rate-limit.
#
# FIX PERFORMA (rate-limit): daftar domain diperluas agar SEMUA portal yang
# dikenal rentan Cloudflare/anti-bot (bisnis, investor, kompas, katadata,
# detik, idxchannel, dst.) juga dibatasi — bukan hanya segelintir domain.
# Domain yang melakukan redirect/anti-bot pada halaman ARTIKEL diberi nilai 3
# agar tidak memicu blokir yang membuat satu portal "stuck" lama.
DOMAIN_WORKER_HINT = {
    "cnbcindonesia": 4,
    "detik": 5,
    "kompas": 4,
    "kontan": 4,
    "tempo.co": 5,
    "katadata": 5,
    "cnn": 5,
    "liputan6": 5,
    "kumparan": 6,
    "idnfinancials": 6,
    "antaranews": 6,
    "tribunnews": 4,
    "okezone": 5,
    "republika": 5,
    "jawapos": 5,
    "merdeka": 6,
    "pikiran-rakyat": 6,
    "suara.com": 6,
    "trenasia": 6,
    "wartaekonomi": 6,
    "metrotvnews": 5,
    "tvonenews": 5,
    # Portal bisnis.com melakukan redirect (301/302) pada halaman artikel;
    # request per-artikel 2x lebih lambat (harus resolve Google News URL dulu).
    "bisnis": 3,
    # Halaman artikel investor.id melakukan redirect & sering lambat.
    "investor.id": 3,
    # Domain yang bergantung 100% pada Google News (rss_asli kosong) selalu
    # melewati tahap resolve URL, jadi worker dibatasi agar tidak menumpuk.
    "bareksa": 4,
    "swa.co.id": 4,
    "rm.id": 4,
    "idxchannel": 5,
    "bloombergtechnoz": 5,
}

# ============================================================
# DOWNLOAD/METRIK PERFORMA
# ============================================================
# Ambang sinyal "portal ini bermasalah" — diukur dari METRIK NYATA
# (bukan dari nama domain saja), sehingga portal yang tadinya lambat
# bisa otomatis dipercepat pada scan berikutnya setelah pulih.
MIN_SAMPLE_UNTUK_ADAPTASI = 8       # minimal artikel selesai sebelum menilai portal
THRESHOLD_GAGAL_RASIO = 0.30        # >=30% gagal  -> turunkan worker 1 langkah
THRESHOLD_GAGAL_RASIO_PARAH = 0.60  # >=60% gagal  -> pakai worker minimum
THRESHOLD_DURASI_SLOW = 10.0        # rata-rata >=10s/artikel -> turunkan worker 1 langkah
TIMEOUT_ARTIKEL = 7.0               # timeout HTTP per artikel (detik)
NILAI_BACKOFF_GAGAL = -2            # penalti (detik palsu) saat artikel gagal total
# Batas maksimum durasi satu portal pada PORTAL TUNGGAL. Untuk scan >1 portal
# batas dinaikkan mengikuti skala adaptive worker (lihat _batas_durasi_portal).
DEADLINE_PORTAL_DETIK = 150.0
DEADLINE_PORTAL_MAKS_DETIK = 240.0
# Worker maksimum untuk thread prefetch feed (I/O-bound, jadi boleh lebih banyak
# dari worker artikel). Membuat waktu tunggu feed satu portal "kebanjiran" ke
# thread lain, alih-alih menahan seluruh scan secara berurutan.
MAX_WORKERS_FEED = 12
# Rasio kegagalan artikel per-portal yang membuat portal di-skip pada batch berikutnya.
# Ini mencegah portal yang benar-benar down (mis. 403 semua) memakan deadline
# berulang kali, sehingga total scan tetap cepat.
RASIO_GAGAL_SKIP_BATCH = 0.85
MIN_SAMPLE_SKIP_BATCH = 5


def get_adaptive_workers(nama_portal: str, max_workers: int) -> int:
    """Worker untuk portal ini = MIN(limit domain, max_workers dari slider).

    Sekarang juga memperhitungkan HISTORI PORTOFOLIO (metrik sukses/gagal & durasi
    per artikel dari scan sebelumnya) sehingga portal yang terbukti bermasalah
    otomatis diperlambat, dan portal yang terbukti cepat bisa memakai worker penuh.
    """
    key = (nama_portal or "").lower()
    batas = None
    for domain, hint in DOMAIN_WORKER_HINT.items():
        if domain in key:
            batas = hint if batas is None else min(batas, hint)
    worker = max_workers if batas is None else min(batas, max_workers)

    # Adaptasi berbasis metrik historis (opsional, aman bila belum ada data).
    metrik = st.session_state.get("performa_portal", {}).get(nama_portal)
    if isinstance(metrik, dict):
        try:
            rasio_gagal = float(metrik.get("rasio_gagal", 0.0) or 0.0)
            durasi_rata2 = float(metrik.get("durasi_rata_detik", 0.0) or 0.0)
            # Nilai sentinel NILAI_BACKOFF_GAGAL (durasi per artikel gagal) tidak
            # boleh dianggap sebagai durasi nyata, jadi dibersihkan di sini.
            if durasi_rata2 < 0:
                durasi_rata2 = 0.0
            if rasio_gagal >= THRESHOLD_GAGAL_RASIO_PARAH:
                worker = 1
            elif rasio_gagal >= THRESHOLD_GAGAL_RASIO or durasi_rata2 >= THRESHOLD_DURASI_SLOW:
                worker = max(1, worker - 1)
        except Exception:
            pass
    return max(1, int(worker))


def _batas_durasi_portal(effective_workers: int, total_portal: int) -> float:
    """Batas maksimum durasi satu portal (detik) agar scan tidak tertahan.

    Skalanya mengikuti jumlah worker adaptif portal tersebut: portal dengan
    lebih banyak worker boleh memakai waktu lebih lama karena memang memproses
    lebih banyak artikel paralel. Untuk PORTAL TUNGGAL, batas dinaikkan ke
    plafon agar pemindaian satu portal tidak terpotong.
    """
    if total_portal <= 1:
        return DEADLINE_PORTAL_MAKS_DETIK
    batas = DEADLINE_PORTAL_DETIK * (max(1, effective_workers) / 8.0)
    return float(max(60.0, min(DEADLINE_PORTAL_MAKS_DETIK, batas)))


def _catat_performa_portal(
    nama_portal: str,
    processed: int,
    failed: int,
    durasi_per_item: list,
    dipotong: bool = False,
) -> None:
    """Simpan metrik performa portal ke session_state untuk adaptasi scan berikutnya.

    Disimpan di session_state (bukan file) agar tidak mengubah fungsi publik
    maupun UI; halaman lain tidak terpengaruh karena key-nya baru.
    """
    try:
        durasi_valid = [d for d in durasi_per_item if isinstance(d, (int, float)) and d >= 0]
        durasi_rata = round(sum(durasi_valid) / len(durasi_valid), 2) if durasi_valid else 0.0
        metrik_lama = st.session_state.get("performa_portal", {}) or {}
        lama = metrik_lama.get(nama_portal) or {}
        # Rata-rata bergerak (60% data lama, 40% data baru) agar adaptasi tidak
        # berubah drastis hanya karena satu scan yang kebetulan buruk/baik.
        rasio_baru = (failed / processed) if processed else 1.0
        rasio_lama = float(lama.get("rasio_gagal", rasio_baru) or rasio_baru)
        durasi_lama = float(lama.get("durasi_rata_detik", durasi_rata) or durasi_rata)
        metrik_lama[nama_portal] = {
            "rasio_gagal": round(rasio_lama * 0.6 + rasio_baru * 0.4, 3),
            "durasi_rata_detik": round(durasi_lama * 0.6 + durasi_rata * 0.4, 2),
            "dipotong_deadline": bool(dipotong),
            "sample": int(lama.get("sample", 0)) + int(processed),
        }
        st.session_state["performa_portal"] = metrik_lama
    except Exception:
        # Metrik hanya optimasi — kegagalan pencatatan tidak boleh menggagalkan scan.
        pass


# ============================================================
# KONSTANTA KATEGORI & LEKSIKON
# ============================================================

KATEGORI_PORTOFOLIO = {
    "SAHAM_EMITEN": [
        "arna", "arwana citramulia",
        "bris", "bank syariah indonesia",
        "smsm", "selamat sempurna",
        "sido", "industri jamu dan farmasi sido muncul",
        "aces", "aspirasi hidup indonesia",
        "ultj", "ultra jaya milk industri",
        "tlkm", "tspc", "auto", "cmry","cpin",
    ],
    "SEKTOR_SAHAM": [
        "keramik", "properti", "konstruksi",
        "perbankan", "perbankan syariah",
        "otomotif", "spare part", "aftermarket",
        "farmasi", "herbal", "consumer health",
        "retail", "home improvement","laporan keuangan", "laba bersih",
        "dividen","market",
    ],
    "ETF": [
        "r-lq45x", "lq45", "indeks lq45", "rebalancing lq45",
        "konstituen lq45", "etf indonesia", "foreign flow", "spy", "indeks spy"
    ],
    "REKSADANA": [
        "majoris pasar uang syariah", "mandiri invasta dana syariah",
        "sucorinvest equity fund", "pasar uang syariah", "sukuk",
        "sbsn", "obligasi syariah", "reksadana saham", "reksadana obligasi",
        "majoris sukuk negara", "reksadana pasar uang", "reksadana campuran"
    ],
    "EMAS": [
        "emas", "gold", "xau", "xau/usd", "harga emas", "emas pegadaian", "emas antam", "pegadaian",
        "logam mulia", "lm antam", "lm pegadaian"
    ],
    "KOMODITAS": [
        "harga batu bara", "hba", "coal price", "harga minyak", "oil price",
        "brent"
    ],
    "MAKRO_INDONESIA": [
        "bi rate", "bank indonesia", "inflasi indonesia", "rupiah", "usd/idr",
        "gdp indonesia", "pertumbuhan ekonomi", "apbn", "yield obligasi",
        "ihsg", "foreign flow", "net buy asing", "net sell asing","harga pangan", "inflasi",
        "defisit neraca perdagangan", "ekspor-impor", "neraca perdagangan", "saham",
        "bursa efek indonesia", "inflasi ihk"
    ],
    "MAKRO_GLOBAL": [
        "federal reserve", "fed rate", "us cpi", "us pce", "us nfp",
        "us treasury yield", "dxy", "china economy", "china stimulus", "ftse", "msci",
        "biro statistik tenaga kerja as", "gubernur bank of japan", "boj"
    ],
    "REGULASI": [
        "ojk", "bei", "kementerian keuangan", "kementerian esdm",
        "kementerian perindustrian", "kementerian perdagangan",
        "kebijakan pemerintah", "aturan ekspor", "aturan impor", "kebijakan pajak", "dpr", "bkn", "menpanrb", "mahkamah konstitusi",
        "pemerintah kabupaten landak", "pemerintah provinsi kalimantan barat", "dprd kalbar", "dprd landak", "bps"
    ],
    # --- KATEGORI BARU ---
    # FIX: "suara" dihapus dari POLITIK — kata ini sangat umum ("suara", portal
    # Suara.com, "suara konsumen") dan menyebabkan false positive besar yang
    # membuat berita non-politik berlabel POLITIK.
    # CATATAN PRIORITAS: urutan dict menentukan fallback untuk kata kunci
    # yang tumpang tindih antar kategori (mis. "landak" ada di LOKAL & juga
    # nama daerah di berita kesehatan; "menteri" ada di POLITIK & dipakai
    # berita institusi). Kata kunci yang SANGAT spesifik sengaja diletakkan
    # di kategori tematiknya, dan urutan iterasi di atur oleh _KATEGORI_PRIORITAS.
    "POLITIK": [
        "politik", "berita politik", "pemilu", "pilkada", "pilpres", "pileg", "partai politik",
        "koalisi", "oposisi", "parlemen", "kabinet", "menteri", "kampanye", "legislatif",
        "eksekutif", "pemilihan umum", "fraksi", "ketua umum", "debat publik", "calon presiden",
        "calon wakil presiden", "capres", "cawapres", "caleg", "dpr", "dprd", "mpr", "dpd",
        "presiden", "wakil presiden", "gubernur", "bupati", "walikota", "menteri keuangan",
        "survei politik", "elektabilitas", "politikus", "konstitusi", "pemerintah", "pemda",
        "kebijakan politik", "kampanye pemilu", "kotak kosong", "real count", "quick count",
        "kotak suara", "tps", "sengketa pemilu"
    ],
    "LOKAL_KALBAR_NGABANG": [
        "kalimantan barat", "kalbar", "pontianak", "ngabang", "kabupaten landak",
        "singkawang", "sintang", "mempawah", "ketapang", "sanggau", "sambas", "kubu raya",
        "kayong utara", "melawi", "sekadau", "bengkayang", "pemkab landak", "gubernur kalbar",
        "bupati landak", "wako pontianak", "pemprov kalbar", "dprd kalbar", "dprd landak",
        "kecamatan ngabang", "kapuas hulu", "sungai raya", "tayan",
        "mempawah hulu", "ngabang landak", "kalimantan", "banjarmasin", "palangkaraya",
        "samarinda", "balikpapan", "tarakan", "kalimantan tengah", "kalimantan selatan",
        "kalimantan timur", "kalimantan utara", "ikn", "nusantara", "tanah dayak",
        "dayak", "khatulistiwa", "equator", "polda kalbar", "korem kalbar", "kota pontianak",
        "kabupaten sintang", "kabupaten bengkayang", "kabupaten sambas", "kabupaten sanggau",
        "kabupaten ketapang", "kabupaten mempawah", "kabupaten kubu raya", "kota singkawang",
        # FIX: "landak", "kubu", "pemkab" (generik) sengaja TIDAK dipakai
        # sebagai kata kunci berdiri sendiri — lihat catatan di _KATA_KUNCI_LOKAL_KUAT.
    ],
    "KESEHATAN": [
        "kesehatan", "berita kesehatan", "rsud", "rumah sakit", "menkes", "kementerian kesehatan",
        "kemenkes", "bpjs kesehatan", "bpjs", "vaksin", "vaksinasi", "imunisasi", "wabah",
        "virus", "pandemi", "endemi", "klinik", "puskesmas", "dokter", "dokter spesialis",
        "perawat", "obat", "obat-obatan", "stunting", "gizi", "gizi buruk", "epidemi",
        "obat murah", "bpom", "pusat kesehatan", "pasien", "demam berdarah", "dbd", "dengue",
        "malaria", "tuberkulosis", "tbc", "covid-19", "covid", "wabah penyakit", "kesehatan ibu",
        "kesehatan anak", "jiwa", "kesehatan mental", "gagal ginjal", "penyakit", "alkes",
        "jkn", "kartu indonesia sehat", "klaim bpjs", "rumah sakit umum", "posyandu",
        "air bersih", "sanitasi", "kekebalan", "vaksinasi massal"
    ],
    "INSTITUSI": [
        "institusi", "institusi negara", "lembaga", "lembaga negara", "lembaga pemerintah",
        "kpk", "komisi pemberantasan korupsi", "polri", "kepolisian", "kejaksaan agung",
        "kejaksaan", "tni", "tentara nasional indonesia", "mabes polri", "polda", "polres",
        "mahkamah agung", "mahkamah konstitusi", "komisi yudisial", "komnas ham",
        "ombudsman", "bpk", "bpkp", "bawaslu", "kpu", "kemenkumham", "bkn", "menpanrb",
        "polda kalbar", "polres landak", "peradilan", "pengadilan", "kejari", "penyidikan",
        "penyelidikan", "tersangka", "gratifikasi", "suap", "densus 88",
        # FIX: singkatan pendek yang rawan false positive dihapus/dipanjangkan:
        # "laos" (bentrok nama negara Laos), "lan" (kata umum), "mk"/"ky"
        # (sering muncul sebagai potongan kata lain).
        "lembaga sandi negara", "bssn", "bnpt", "bappenas", "brin", "asn", "pegawai negeri",
        "aparat penegak hukum", "penegakan hukum", "lembaga antikorupsi"
    ],
    "ASEAN": [
        "asean", "asia tenggara", "asean summit", "ktt asean", "ktt ke-asean", "sekretariat asean",
        "ekonomi asean", "masyarakat ekonomi asean", "mea", "apec", "rcep", "afta",
        "perhimpunan bangsa-bangsa asia tenggara", "jakarta asean", "keketuaan asean",
        "asean+3", "east asia summit", "zopfan", "kawasan asia tenggara", "negara asean",
        "negara-negara asean", "anggota asean", "asean outlook", "asean chair",
        "malaysia", "kuala lumpur", "johor", "sabah", "sarawak", "putrajaya",
        "singapura", "singapore", "thailand", "bangkok", "phuket", "filipina", "manila",
        "vietnam", "hanoi", "ho chi minh", "brunei", "brunei darussalam", "bandar seri begawan",
        "myanmar", "burma", "yangon", "naypyidaw", "kamboja", "cambodia", "phnom penh",
        "timor leste", "timor-leste", "dili",
        "mata uang asean", "kerja sama asean", "kawasan terorisme asean",
        "lao", "laos pdr"
    ],
    "TEKNOLOGI": [
        "kecerdasan buatan", "artificial intelligence", "ai", "chatgpt", "gpt",
        "machine learning", "deep learning", "llm", "model bahasa",
        "semikonduktor", "chip", "nvidia", "tsmc", "asml",
        "kripto", "cryptocurrency", "bitcoin", "ethereum", "blockchain", "web3",
        "fintech", "paylater", "dompet digital", "e-wallet",
        "e-commerce", "marketplace", "listrik kendaraan", "kendaraan listrik", "ev", "baterai litium",
        "data center", "pusat data", "cloud", "cloud computing", "aws",
        "5g", "jaringan 5g", "satelit", "starlink",
        "siber", "keamanan siber", "cybersecurity", "ransomware", "peretasan",
        "smartphone", "gadget", "aplikasi", "apps", "platform digital",
        "meta", "google", "alphabet", "microsoft", "apple", "openai", "bytedance",
        "metaverse", "augmented reality", "virtual reality", "ar/vr",
        "big data", "analitik data", "internet of things", "iot",
        "sistem operasi", "perangkat lunak", "software", "saas",
        "transformasi digital", "digitalisasi", "ekonomi digital",
        "goto", "gojek", "grab", "traveloka", "bukalapak"
    ],
    "LUAR_NEGERI": [
        "luar negeri", "global market", "pasar global", "global index", "global indices",
        "wall street", "new york stock exchange", "nyse", "nasdaq", "dow jones",
        "s&p 500", "sp500", "russell 2000", "vix", "fear and greed",
        "nikkei", "nikkei 225", "topix", "bursa jepang", "bursa tokyo",
        "hang seng", "hsi", "bursa hong kong",
        "shanghai composite", "sse", "szse", "bursa tiongkok", "bursa shanghai", "bursa shenzhen",
        "kospi", "bursa korea", "straits times", "sti", "bursa singapura", "sgx",
        "ftse 100", "bursa london", "dax", "cac 40", "asx 200", "nifty 50",
        "china", "amerika serikat", "as", "jepang", "korea selatan", "india", "eropa", "inggris"
    ],
    "UMUM": [
        "cpns", "seleksi cpns", "energi", "kelistrikan", "bbm", "daya beli",
        "indeks", "bencana", "anime", "game",
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
# URUTAN PRIORITAS KLASIFIKASI KATEGORI
# ============================================================
# `tentukan_kategori_aset` mengembalikan hasil KECOCOKAN PERTAMA, sehingga
# urutan di sini sangat menentukan. Kategori TEMATIK yang khas (lokal, asean,
# kesehatan, institusi, politik, teknologi) diprioritaskan di atas kategori
# generik (makro/umum) supaya berita "Vaksinasi di Landak" tidak dilabeli
# MAKRO_REGULASI dan berita "Penerbangan Vietnam-Thailand" tidak dilabeli
# LUAR_NEGERI. Khusus POLITIK sengaja diletakkan setelah LOKAL & ASEAN agar
# gelar jabatan (bupati/gubernur/menteri) tidak menelan berita daerah.
URUTAN_PRIORITAS_KATEGORI = [
    "SAHAM_EMITEN", "ETF", "REKSADANA", "EMAS", "KOMODITAS", "SEKTOR_SAHAM",
    "LOKAL_KALBAR_NGABANG", "ASEAN", "KESEHATAN", "INSTITUSI", "TEKNOLOGI",
    "POLITIK", "REGULASI", "MAKRO_INDONESIA", "MAKRO_GLOBAL", "LUAR_NEGERI", "UMUM",
]


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
# FIX: item dict disusun ulang mengikuti URUTAN_PRIORITAS_KATEGORI, dan
# kategori yang belum terdaftar di urutan tetap disertakan di akhir agar
# tidak pernah hilang dari proses klasifikasi.
_KATEGORI_PATTERNS = {
    kat: [
        re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
        for kw in sorted(set(KATEGORI_PORTOFOLIO[kat]), key=len, reverse=True)
    ]
    for kat in (
        [k for k in URUTAN_PRIORITAS_KATEGORI if k in KATEGORI_PORTOFOLIO]
        + [k for k in KATEGORI_PORTOFOLIO if k not in URUTAN_PRIORITAS_KATEGORI]
    )
}



# ============================================================
# PEMETAAN KATEGORI MENTAH -> LABEL RINGKAS
# ============================================================
# Label inilah yang tersimpan di kolom "Kategori Aset" dan dipakai
# konsisten oleh seluruh halaman (tabs Detail Berita, filter Ekspor,
# komposisi kategori di Ringkasan Live, heatmap Media Portal).
# Satu tabel eksplisit menggantikan rantai if/elif agar kategori baru
# tidak bisa "hilang" (jatuh ke fallback MAKRO_REGULASI) tanpa disadari.
PEMETAAN_KATEGORI = {
    "SAHAM_EMITEN": "SAHAM",
    "SEKTOR_SAHAM": "SAHAM",
    "ETF": "REKSADANA_ETF",
    "REKSADANA": "REKSADANA_ETF",
    "EMAS": "EMAS_KOMODITAS",
    "KOMODITAS": "EMAS_KOMODITAS",
    "MAKRO_INDONESIA": "MAKRO_REGULASI",
    "MAKRO_GLOBAL": "MAKRO_REGULASI",
    "REGULASI": "MAKRO_REGULASI",
    "POLITIK": "POLITIK",
    "LOKAL_KALBAR_NGABANG": "LOKAL_KALBAR_NGABANG",
    "KESEHATAN": "KESEHATAN",
    "INSTITUSI": "INSTITUSI",
    "ASEAN": "ASEAN",
    "TEKNOLOGI": "TEKNOLOGI",
    "LUAR_NEGERI": "LUAR_NEGERI",
    "UMUM": "UMUM",
}

# Label tampilan (emoji + nama) untuk setiap label kategori.
# Dipakai halaman Detail Berita & Ekspor agar penamaan kategori
# tidak lagi ditulis ulang di tiap file (satu sumber kebenaran).
LABEL_KATEGORI = {
    "SAHAM": "📈 Saham",
    "POLITIK": "🏛️ Politik",
    "LOKAL_KALBAR_NGABANG": "📍 Kalbar & Ngabang",
    "KESEHATAN": "🩺 Kesehatan",
    "INSTITUSI": "🏢 Institusi",
    "ASEAN": "🌏 ASEAN",
    "TEKNOLOGI": "💻 Teknologi",
    "LUAR_NEGERI": "🌐 Luar Negeri",
    "REKSADANA_ETF": "🧺 Reksadana & ETF",
    "EMAS_KOMODITAS": "🥇 Emas & Komoditas",
    "MAKRO_REGULASI": "🏦 Makro & Regulasi",
    "UMUM": "📋 Umum",
}


# ============================================================
# HELPER FUNCTIONS (TIDAK BERUBAH SIGNIFIKAN)
# ============================================================

def konversi_ke_datetime(tanggal_str):
    if not tanggal_str or tanggal_str == 'N/A':
        return wib_now()
    try:
        dt = date_parser.parse(tanggal_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return wib_now()


def apakah_dalam_rentang(tanggal_str, jam_maksimal, waktu_acuan=None):
    """Cek apakah tanggal berita berada dalam rentang jam_maksimal dari
    ``waktu_acuan`` dalam zona waktu WIB (UTC+7).

    FIX: gunakan wib_now() alih-alih datetime.now() agar batas atas konsisten
    dengan waktu scan (last_scan_at) — tidak bergantung pada zona waktu server.

    FIX AKURASI RENTANG: ``waktu_acuan`` (waktu mulai scan yang dikunci sekali
    di awal pemindaian) digunakan sebagai batas atas rentang. Sebelumnya fungsi
    ini memakai wib_now() pada saat tiap entry diproses, yang bisa bergeser
    selama scan berjalan — sehingga berita difilter dengan acuan waktu yang
    berbeda-beda dan label rentang (last_scan_at - jam) tidak sesuai dengan
    rentang saat filter benar-benar dievaluasi.

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
            # Konversi ke zona lokal server dulu (untuk membuang tzinfo),
            # lalu tambahkan offset agar representasi waktunya = WIB.
            # date_parser.parse tanpa tz diasumsikan WIB karena semua portal
            # berita di konfigurasi merupakan portal Indonesia.
            dt_berita = dt_berita.astimezone().replace(tzinfo=None)
        # Batas atas = waktu acuan (kunci di awal scan) supaya konsisten
        # dengan last_scan_at yang ditampilkan ke UI. Fallback ke wib_now()
        # hanya bila dipanggil tanpa waktu_acuan (panggilan lama/testing).
        waktu_sekarang = waktu_acuan if waktu_acuan is not None else wib_now()
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
    for kat, patterns in _KATEGORI_PATTERNS.items():
        for pat in patterns:
            if pat.search(teks_lower):
                # Tabel pemetaan kategori mentah -> label ringkas yang dipakai UI
                # (Tabs halaman Detail Berita, filter Ekspor, grafik kategori).
                return PEMETAAN_KATEGORI.get(kat, "MAKRO_REGULASI")
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


def _artikel_sudah_di_cache(link: str) -> bool:
    """Cek cepat apakah artikel sudah ada di cache (article/parsed).

    Dipakai saat deadline portal sudah lewat: artikel yang SUDAH ter-cache
    masih diproses (tanpa jaringan, jadi tetap instan), sedangkan artikel
    yang butuh jaringan di-skip agar portal bisa segera ditutup.
    """
    if not link:
        return False
    try:
        if cache_get_parsed is not None and cache_get_parsed(link) is not None:
            return True
        from utils.cache import cache_get as _cache_get
        return _cache_get("article", link) is not None
    except Exception:
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
    waktu_acuan=None,
    tenggat=None,
) -> Optional[dict]:
    """
    Proses satu entry RSS sampai menjadi record siap-simpan.
    Dipanggil paralel via ThreadPoolExecutor.
    Mengembalikan dict atau None jika di-skip.

    ``waktu_acuan`` = waktu mulai scan (WIB) yang dikunci sekali di awal
    pemindaian. Diteruskan ke ``apakah_dalam_rentang`` agar batas atas
    rentang filter konsisten untuk SEMUA entry — tidak bergeser selama
    scan berjalan. Konsisten dengan ``last_scan_at`` yang ditampilkan ke UI.

    ``tenggat`` = callable opsional yang mengembalikan batas waktu absolut
    (epoch) untuk portal ini. Bila tenggat sudah lewat, entry di-skip
    (kecuali sudah tersedia di cache) sehingga satu portal yang lambat/
    anti-bot tidak menahan seluruh proses pemindaian.
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
    tenggat_lewat = callable(tenggat) and time.time() >= tenggat()
    teks_pencocokan = (judul + " " + deskripsi).lower()
    match = _KK_PATTERN.search(teks_pencocokan)
    if match is None:
        return None
    trigger_terdeteksi = match.group(1).upper()
    if tenggat_lewat:
        # Sudah melewati deadline portal: hanya artikel yang sudah ada di cache
        # yang masih diproses (tanpa jaringan), sehingga deadline benar-benar
        # menyelesaikan portal tepat waktu tanpa membuang hasil cache.
        if not _artikel_sudah_di_cache(link):
            return None

    # CATATAN: Filter waktu pra-scrape HANYA untuk portal terpercaya
    # (field aturan['tanggal_terpercaya'] == True). Portal ini umumnya
    # menggunakan RSS asli (bukan Google News) sehingga tanggal RSS akurat
    # dan bisa dipakai untuk skip artikel lama SEBELUM scrape yang lambat.
    # Untuk portal non-terpercaya, filter waktu tetap dilakukan di akhir
    # (setelah scrape) dengan fallback tanggal dari HTML — lihat di bawah.
    if jam_filter < 87600 and aturan.get("tanggal_terpercaya"):
        if not apakah_dalam_rentang(tanggal, jam_filter, waktu_acuan=waktu_acuan):
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
        if not apakah_dalam_rentang(tanggal_efektif, jam_filter, waktu_acuan=waktu_acuan):
            # Fallback: ambil tanggal dari hasil scrape (lebih akurat dari HTML).
            tanggal_scrape = hasil.get("tanggal", "") or ""
            if tanggal_scrape and tanggal_scrape != tanggal and tanggal_scrape != 'N/A':
                if apakah_dalam_rentang(tanggal_scrape, jam_filter, waktu_acuan=waktu_acuan):
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
if 'scan_rentang_label' not in st.session_state:
    st.session_state.scan_rentang_label = None
if 'scan_jam_filter' not in st.session_state:
    st.session_state.scan_jam_filter = None
# Metrik performa per-portal (dipakai get_adaptive_workers untuk menyesuaikan
# jumlah worker pada scan BERIKUTNYA). Tidak ditampilkan di UI; key baru
# sehingga tidak mengubah UI maupun fungsi yang sudah ada.
if 'performa_portal' not in st.session_state:
    st.session_state.performa_portal = {}

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
            <span class="tag">Politik</span>
            <span class="tag">Kalbar & Ngabang</span>
            <span class="tag">Kesehatan</span>
            <span class="tag">Institusi</span>
            <span class="tag">ASEAN</span>
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
        caption_text = (
            f"🕒 Pemindaian terakhir: {last_scan_at.strftime('%d/%m/%Y %H:%M:%S')} "
            f"· Cache baru: {st.session_state.scan_stats.get('cache_hits', 0)} entry"
        )
        # FIX: tampilkan label rentang + periode efektif pada caption utama
        # sehingga user dapat langsung memverifikasi akurasi rentang waktu
        # di halaman utama (tidak perlu navigasi ke Ekspor dulu).
        rentang_label_caption = st.session_state.get('scan_rentang_label')
        scan_jam_filter_caption = st.session_state.get('scan_jam_filter')
        if rentang_label_caption:
            caption_text += f"\n📅 Rentang: {rentang_label_caption}"
            if (
                isinstance(scan_jam_filter_caption, (int, float))
                and 0 < scan_jam_filter_caption < 87600
            ):
                try:
                    batas_bawah_caption = last_scan_at - timedelta(hours=float(scan_jam_filter_caption))
                    caption_text += (
                        f"\n📆 Periode efektif: {batas_bawah_caption.strftime('%d/%m %H:%M')} "
                        f"→ {last_scan_at.strftime('%d/%m %H:%M')} WIB "
                        f"(±{scan_jam_filter_caption:.0f} jam)"
                    )
                except Exception:
                    pass
        st.caption(caption_text)
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

        # --- FILTER CEPAT BERDASARKAN KATEGORI TOPIK ---
        # Menandai portal yang memang khusus menyediakan kategori baru
        # (Politik, Kalbar/Ngabang, Kesehatan, Institusi, ASEAN) supaya user
        # bisa langsung memindai topik tersebut tanpa memilih satu per satu.
        kelompok_portal = {
            "🏛️ Politik": [k for k in semua_portal_keys if "(Politik)" in k or "(Nasional)" in k],
            "📍 Kalbar & Ngabang": [k for k in semua_portal_keys if "Kalbar" in k or "Landak" in k or "Ngabang" in k],
            "🩺 Kesehatan": [k for k in semua_portal_keys if "(Kesehatan)" in k],
            "🏢 Institusi": [k for k in semua_portal_keys if "(Institusi)" in k],
            "🌏 ASEAN": [k for k in semua_portal_keys if "(ASEAN)" in k or "(Regional" in k],
        }
        pilihan_cepat = st.multiselect(
            "⚡ Filter Cepat Kategori Topik:",
            options=list(kelompok_portal.keys()),
            default=[],
            help="Menambahkan portal yang relevan dengan topik terpilih ke daftar kanal.",
        )
        portal_tambahan_kategori = sorted({
            p for topik in pilihan_cepat for p in kelompok_portal[topik]
        })

        pilih_semua = st.checkbox("Pilih Semua Portal", value=True)
        default_portal = semua_portal_keys if pilih_semua else portal_tambahan_kategori
        portal_terpilih = st.multiselect(
            "Filter Kanal:",
            options=semua_portal_keys,
            default=default_portal,
        )
        if portal_tambahan_kategori:
            # Pastikan portal dari filter cepat benar-benar ikut dipindai,
            # walaupun user sebelumnya mencentang "Pilih Semua" lalu mengedit manual.
            portal_terpilih = sorted(set(portal_terpilih) | set(portal_tambahan_kategori))

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

        # FIX AKURASI RENTANG: Kunci waktu acuan (WIB) SEKALI di awal scan.
        # - Dipakai sebagai batas atas oleh apakah_dalam_rentang() untuk SEMUA
        #   entry yang diproses (tidak lagi memakai wib_now() yang bergeser
        #   selama scan berjalan paralel).
        # - Disimpan sebagai last_scan_at sehingga label "Periode efektif"
        #   dan rentang absolut di halaman Ekspor konsisten dengan batas
        #   yang dipakai saat filter berjalan.
        waktu_mulai_scan = wib_now()

        cache_hits_awal = get_cache_stats()
        cache_total_awal = cache_hits_awal["total"]

        # Loop utama: tiap portal di-fetch secara paralel di dalamnya
        # Statistik kegagalan per-portal (untuk laporan akhir)
        portal_failure_counts: dict[str, int] = {}
        portal_halted_flags: dict[str, bool] = {}
        # FIX: simpan alasan kegagalan feed per-portal untuk laporan diagnostik akhir.
        portal_feed_errors: dict[str, str] = {}
        portal_entry_counts: dict[str, tuple[int, int]] = {}  # (diproses, gagal)

        # ============================================================
        # PERFORMA: SIMPAN INCREMENTAL (debounce) + PREFETCH FEED PARALEL
        # ============================================================
        # Masalah sebelumnya:
        # 1. `st.session_state.df_hasil = pd.DataFrame(kumpulan_data_global)`
        #    dibangun ULANG dari SELURUH hasil di setiap akhir portal -> O(N^2)
        #    dan makin lambat saat portal makin banyak. Sekarang dibatasi
        #    ke 1 kali per interval agar hasil tetap tampil progresif.
        # 2. Feed RSS portal di-fetch SATU PER SATU di dalam loop, sehingga satu
        #    portal yang lambat/timeout menahan seluruh scan. Sekarang feed
        #    di-prefetch paralel, jadi penundaan satu portal tidak memblokir portal lain.
        _interval_simpan_incremental = 2.0
        # Mutable holder: dipakai alih-alih `nonlocal` karena helper ini
        # didefinisikan di dalam blok `if` (bukan scope fungsi), sehingga
        # `nonlocal` tidak valid di sini.
        _state_simpan = {"terakhir": 0.0}

        def _simpan_hasil_incremental(force: bool = False) -> None:
            """Perbarui df_hasil secara berkala-saja (bukan tiap portal).

            FIX PERFORMA: sebelumnya dataframe dibangun ulang dari SELURUH
            hasil di setiap akhir portal (O(N^2)). Kini dibatasi frekuensinya
            agar hasil tetap tampil progresif tanpa memboroskan waktu.
            """
            if not kumpulan_data_global:
                return
            sekarang_simpan = time.time()
            if not force and (sekarang_simpan - _state_simpan["terakhir"]) < _interval_simpan_incremental:
                return
            _state_simpan["terakhir"] = sekarang_simpan
            st.session_state.df_hasil = (
                pd.DataFrame(kumpulan_data_global)
                .sort_values(by="dt_sort", ascending=False)
                .reset_index(drop=True)
            )

        # Siapkan aturan per-portal (sekali saja) — dipakai oleh prefetch feed & scan artikel.
        _aturan_siap: dict[str, dict] = {}
        for nama_portal_awal in portal_terpilih:
            try:
                aturan_awal = dict(aturan_portal[nama_portal_awal])
            except Exception:
                aturan_awal = {}
            aturan_awal["__nama_portal"] = nama_portal_awal
            _aturan_siap[nama_portal_awal] = aturan_awal

        # PREFETCH PARALEL: ambil semua feed sekaligus (I/O-bound, boleh banyak thread).
        # Lihat catatan agregasi alasan kegagalan feed di bawah loop.
        _feed_hasil: dict[str, object] = {}
        _feed_error_gabung: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS_FEED, max(1, total_portal))) as _feed_exec:
            _future_feed = {
                _feed_exec.submit(dapatkan_feed_rss, _aturan_siap[nama_portal_feed]): nama_portal_feed
                for nama_portal_feed in portal_terpilih
            }
            for _fut in as_completed(_future_feed):
                _nama_feed = _future_feed[_fut]
                try:
                    _feed_hasil[_nama_feed] = _fut.result()
                except Exception as _feed_exc:
                    _feed_hasil[_nama_feed] = None
                    _feed_error_gabung[_nama_feed] = f"exception: {type(_feed_exc).__name__}: {str(_feed_exc)[:80]}"
                # FIX RACE: dict `aturan` per-portal hanya disentuh SATU thread,
                # tapi bacanya dilakukan SETELAH semua future selesai (di bawah),
                # sehingga __feed_error selalu konsisten per portal.
            _feed_exec.shutdown(wait=True)
        for _nama_feed, _aturan_feed in _aturan_siap.items():
            if _nama_feed in _feed_error_gabung:
                portal_feed_errors[_nama_feed] = _feed_error_gabung[_nama_feed]
            elif _aturan_feed.get("__feed_error"):
                portal_feed_errors[_nama_feed] = _aturan_feed.get("__feed_error")

        # Satu pool bersama untuk scan ARTIKEL semua portal.
        # Worker per-portal tetap dihormati dengan cara membatasi jumlah submit
        # (in-flight) per portal — jadi portal lambat tidak pernah memonopoli
        # thread, tetapi portal 1 (tunggal) tetap dapat paralelisme penuh.
        _pool_artikel = ThreadPoolExecutor(max_workers=max(2, min(24, max_workers + 6)))

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
                aturan = _aturan_siap[nama_portal]
                feed = _feed_hasil.get(nama_portal)
                if not feed or not hasattr(feed, "entries") or len(feed.entries) == 0:
                    progress_bar.progress((idx + 1) / total_portal)
                    portal_failure_counts[nama_portal] = portal_failure_counts.get(nama_portal, 0) + 1
                    # FIX: catat alasan kegagalan feed untuk laporan diagnostik.
                    portal_feed_errors.setdefault(
                        nama_portal,
                        aturan.get("__feed_error", "feed kosong / 0 entry"),
                    )
                    _simpan_hasil_incremental()
                    continue

                # Batasi jumlah entry yang akan diproses
                # OPTIMASI #6: sort by recency (entry terbaru diproses duluan),
                # sehingga hasil yang lolos filter waktu tampil lebih awal (progressive rendering).
                target_entries = sort_entries_by_recency(list(feed.entries))[:max_artikel_per_portal]

                # OPTIMASI #3: adaptive worker untuk portal rentan rate-limit.
                # Portal besar (Detik, Kompas, CNBC) pakai worker lebih sedikit.
                # FIX: sekarang juga memakai METRIK HISTORIS (rasio gagal & durasi
                # per artikel) sehingga portal yang terbukti bermasalah otomatis
                # diperlambat pada scan berikutnya.
                effective_workers = get_adaptive_workers(nama_portal, max_workers)

                # FIX "STUCK DI 1 PORTAL": batas durasi per portal. Jika sebuah
                # portal lambat/anti-bot, sisa entry-nya (yang belum mulai) tidak
                # diproses lagi — kecuali sudah ada di cache (tetap instan).
                batas_durasi = _batas_durasi_portal(effective_workers, total_portal)
                tenggat_portal = time.time() + batas_durasi

                processed_count = 0
                failed_count = 0
                lewat_deadline = 0
                durasi_per_item: list[float] = []

                # PARALEL: submit bertahap (window) agar worker per-portal dihormati
                # tanpa membuat satu pool per portal.
                _antrian = list(target_entries)
                _aktif: dict = {}
                _gagal_berturut = 0
                _stop_karena_gagal = False
                while _antrian or _aktif:
                    while _antrian and len(_aktif) < effective_workers:
                        _entry_next = _antrian.pop(0)
                        _fut = _pool_artikel.submit(
                            process_entry,
                            _entry_next, aturan, jam_filter,
                            aktifkan_deduplikasi, ambang_duplikat,
                            daftar_tersimpan, dedup_lock,
                            waktu_mulai_scan,
                            tenggat_portal,
                        )
                        _aktif[_fut] = (time.time(), _entry_next)

                    if not _aktif:
                        continue

                    _selesai = None
                    _timeout_poll = max(0.5, min(2.0, tenggat_portal - time.time()))
                    try:
                        for _fut_selesai in as_completed(list(_aktif), timeout=_timeout_poll):
                            _selesai = _fut_selesai
                            break
                    except Exception:
                        _selesai = None

                    if _selesai is None:
                        # Belum ada future selesai dalam polling window — cek deadline.
                        if time.time() >= tenggat_portal:
                            if not _antrian:
                                break  # semua entry sudah di-submit, tunggu selesai
                            # Batalkan sisa antrian (belum di-submit) -> portal berikutnya segera diproses.
                            lewat_deadline = len(_antrian)
                            _antrian.clear()
                        continue

                    _waktu_mulai_next, _ = _aktif.pop(_selesai)
                    _durasi_item = max(0.0, time.time() - _waktu_mulai_next)
                    processed_count += 1
                    try:
                        record = _selesai.result(timeout=5)
                    except Exception:
                        record = None

                    if record is None:
                        failed_count += 1
                        _gagal_berturut += 1
                        durasi_per_item.append(NILAI_BACKOFF_GAGAL)
                        # FIX ANTI-STUCK: bila mayoritas besar entry gagal (portal down/403),
                        # hentikan portal ini lebih awal — kecuali entry sisa sudah di cache.
                        if (
                            not _stop_karena_gagal
                            and _gagal_berturut >= MIN_SAMPLE_SKIP_BATCH
                            and (_gagal_berturut / max(1, processed_count)) >= RASIO_GAGAL_SKIP_BATCH
                        ):
                            _stop_karena_gagal = True
                            _sisa_antrian = [e for e in _antrian if _artikel_sudah_di_cache(e.get("link", ""))]
                            lewat_deadline += max(0, len(_antrian) - len(_sisa_antrian))
                            _antrian = _sisa_antrian
                        continue

                    # Sukses
                    _gagal_berturut = 0
                    durasi_per_item.append(_durasi_item)
                    kumpulan_data_global.append(record)

                portal_failure_counts[nama_portal] = failed_count
                portal_halted_flags[nama_portal] = False
                portal_entry_counts[nama_portal] = (processed_count, failed_count)

                # Simpan metrik performa untuk adaptasi worker pada scan berikutnya.
                _catat_performa_portal(
                    nama_portal, processed_count, failed_count,
                    durasi_per_item, dipotong=bool(lewat_deadline),
                )

                # Update progress
                progress_bar.progress((idx + 1) / total_portal)
                _catatan_deadline = (
                    f" | ⏱️ {lewat_deadline} entry dilewati (batas {batas_durasi:.0f}s)"
                    if lewat_deadline else ""
                )
                status_text.text(
                    f"✅ {nama_portal}: {processed_count}/{len(target_entries)} selesai "
                    f"(gagal: {failed_count}){_catatan_deadline} | "
                    f"Total: {len(kumpulan_data_global)} berita"
                )

                # Simpan incremental (debounced — lihat _simpan_hasil_incremental)
                _simpan_hasil_incremental()

                # Memory cleanup periodik
                if (idx + 1) % 5 == 0:
                    gc.collect()
            except Exception as portal_err:
                # Tangani error per-portal: log ke status, lewati portal, lanjut ke berikutnya.
                # Hindari satu portal bermasalah (mis. NameError/KeyError) menggagalkan seluruh scan.
                status_text.text(f"❌ Portal {nama_portal} dilewati karena error: {str(portal_err)[:100]}")
                portal_failure_counts[nama_portal] = -1
                portal_halted_flags[nama_portal] = False
                portal_feed_errors[nama_portal] = f"exception: {type(portal_err).__name__}: {str(portal_err)[:80]}"
                progress_bar.progress((idx + 1) / total_portal)
                continue

        # Pastikan hasil terakhir selalu tersimpan (tanpa debounce).
        _simpan_hasil_incremental(force=True)
        # Tutup pool artikel bersama (amankan bila ada future sisa dari portal terakhir).
        try:
            _pool_artikel.shutdown(wait=True, cancel_futures=True)
        except TypeError:
            _pool_artikel.shutdown(wait=True)
        except Exception:
            pass

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
            st.session_state.last_scan_at = waktu_mulai_scan
            st.session_state.scan_stats = {
                "paralel_workers": max_workers,
                "cache_hits": max(0, cache_hits_scan),
            }
            # Simpan metadata pemindaian agar halaman lain (mis. Ekspor)
            # bisa menampilkan waktu & rentang pemindaian yang AKURAT —
            # bukan waktu saat halaman dibuka/di-render ulang.
            st.session_state.scan_rentang_label = pilihan_rentang
            st.session_state.scan_jam_filter = jam_filter

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

        # ============================================================
        # LAPORAN DIAGNOSTIK PORTAL GAGAL (FIX)
        # ============================================================
        # Tampilkan portal mana yang gagal + alasannya agar user tahu
        # penyebab dan bisa mengambil tindakan (mis. ganti VPN, update URL, dll).
        # Sumber alasan: aturan['__feed_error'] yang diisi oleh dapatkan_feed_rss().
        portal_gagal_feed = [p for p, c in portal_failure_counts.items() if c != 0 and p not in portal_entry_counts]
        portal_gagal_artikel = {
            p: (proc, fail) for p, (proc, fail) in portal_entry_counts.items() if fail > 0
        }
        total_gagal_feed = len(portal_gagal_feed)
        total_berhasil = len([p for p in portal_failure_counts if p not in portal_gagal_feed and portal_failure_counts[p] == 0])

        if total_gagal_feed > 0 or portal_gagal_artikel:
            with st.expander(
                f"📋 Laporan Diagnostik Portal ({total_berhasil} berhasil, "
                f"{total_gagal_feed} gagal feed, {len(portal_gagal_artikel)} ada artikel gagal)",
                expanded=False
            ):
                if total_gagal_feed > 0:
                    st.markdown(f"**❌ Portal gagal mengambil feed ({total_gagal_feed}):**")
                    rows = []
                    for p in portal_gagal_feed:
                        alasan = portal_feed_errors.get(p, "tidak diketahui")
                        rows.append({"Portal": p, "Alasan Kegagalan": alasan})
                    st.dataframe(rows, use_container_width=True, hide_index=True)
                    st.caption(
                        "ℹ️ Kegagalan feed umumnya karena: (1) URL RSS portal berubah/hilang, "
                        "(2) portal memasang Cloudflare/anti-bot (403), (3) subdomain RSS sudah di-shutdown, "
                        "atau (4) masalah SSL/TLS sementara. Sistem otomatis fallback ke Google News RSS; "
                        "jika dua-duanya gagal, portal dilewati sesi ini."
                    )
                if portal_gagal_artikel:
                    st.markdown(f"**⚠️ Portal dengan sebagian artikel gagal di-scrape ({len(portal_gagal_artikel)}):**")
                    rows2 = []
                    for p, (proc, fail) in portal_gagal_artikel.items():
                        rate = round((fail / proc) * 100, 1) if proc else 0
                        rows2.append({
                            "Portal": p,
                            "Artikel Diproses": proc,
                            "Artikel Gagal": fail,
                            "Tingkat Gagal (%)": rate,
                        })
                    st.dataframe(rows2, use_container_width=True, hide_index=True)
                    st.caption(
                        "ℹ️ Kegagalan scraping artikel biasanya transient: rate-limit server (429), "
                        "timeout koneksi, atau halaman anti-bot. Sistem sudah retry 3x per artikel; "
                        "jika masih gagal, coba ulang pemindaian beberapa menit kemudian."
                    )

        # Simpan statistik diagnostik ke session state untuk halaman lain.
        st.session_state["portal_diagnostik"] = {
            "portal_gagal_feed": portal_gagal_feed,
            "portal_feed_errors": portal_feed_errors,
            "portal_entry_counts": portal_entry_counts,
            "total_berhasil": total_berhasil,
            "total_gagal_feed": total_gagal_feed,
        }

        # Final cleanup
        gc.collect()