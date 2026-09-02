"""
Named Entity Recognition untuk emiten Bursa Efek Indonesia.

Tujuan: Deteksi ticker saham (BBCA, TLKM, dll) DAN nama perusahaan
dari teks berita finansial.

Mengapa custom NER?
- Model NER Bahasa Indonesia (IndoBERT-NER) butuh 1+ GB & lambat
- Regex + kamus emiten sangat akurat untuk domain spesifik ini
- Bisa di-maintain: tambah emiten baru cukup edit dict
"""

import re
from typing import List, Dict, Tuple


# ============================================================
# KAMUS TICKER EMITEN IDX (50+ emiten likuid & populer)
# ============================================================
# Format: {ticker: [nama_lengkap, alias1, alias2, ...]}

EMITEN_IDX = {
    # Perbankan
    "BBCA": ["bank central asia", "bca"],
    "BBRI": ["bank rakyat indonesia", "bri"],
    "BMRI": ["bank mandiri"],
    "BBNI": ["bank negara indonesia", "bni"],
    "BRIS": ["bank syariah indonesia", "bsi"],
    "BBTN": ["bank tabungan negara", "btn"],
    "BJBR": ["bank jabr", "bank jabar banten"],
    "BDMN": ["bank danamon"],
    "BNGA": ["bank cimb niaga", "cimb niaga"],
    "MEGA": ["bank mega"],
    "PNBN": ["bank panin"],

    # Telekomunikasi & Teknologi
    "TLKM": ["telkom", "telekomunikasi indonesia"],
    "ISAT": ["indosat", "indosat ooredoo"],
    "EXCL": ["xl axiata", "axiata"],
    "MTEL": ["dayamitra telekomunikasi", "moratel"],
    "TOWR": ["sarana menara nusantara", "tower bersama"],
    "TBIG": ["tower bersama infrastructure"],

    # Konsumer & Ritel
    "ICBP": ["indofood cbp sukses makmur", "indofood cbp"],
    "INDF": ["indofood sukses makmur", "indofood"],
    "UNVR": ["unilever indonesia", "unilever"],
    "SIDO": ["industri jamu dan farmasi sido muncul", "sido muncul", "sido"],
    "MYOR": ["mayora indah", "mayora"],
    "AMRT": ["sumber alfaria trijaya", "alfamart", "alfamidi"],
    "ACES": ["aspirasi hidup indonesia", "aces hardware", "kawan lama"],
    "MAPI": ["mitra adi perkasa"],
    "ERAA": ["erajaya swasembada", "erajaya"],
    "LPPF": ["matahari department store", "matahari"],
    "RALS": ["ramayana lestari sentosa", "ramayana"],
    "PANI": ["pratama abadi nusantara industri"],
    "DIVA": ["diva digital broadcasting"],
    "GULA": ["pt sinar central produsen"],

    # Otomotif
    "ASII": ["astra international", "astra"],
    "AUTO": ["astra oto parts", "astra autoparts"],
    "SMSM": ["selamat sempurna", "smsm"],
    "INDR": ["indorama polymer", "indorama"],
    "GJTL": ["ga jaya wahana"],

    # Properti & Konstruksi
    "BSDE": ["bumi serpong damai"],
    "PWON": ["pakuwon jati", "pakuwon"],
    "CTRA": ["ciputra development", "ciputra"],
    "SMRA": ["summarecon agung", "summarecon"],
    "APLN": ["agung podomoro land", "podomoro"],
    "ASRI": ["alam sutera realty", "alam sutera"],
    "LPKR": ["lippo karawaci"],
    "JSMR": ["jasa marga"],
    "WIKA": ["wijaya karya"],
    "PTPP": ["PP persero", "pt pp"],
    "ADHI": ["adhi karya"],
    "WSKT": ["waskita karya"],
    "BEST": ["bekasi fajar industrial"],

    # Barang Konsumen & Farmasi
    "KAEF": ["kimia farma"],
    "INAF": ["indofarma"],
    "TSPC": ["tempo scan pacific", "tempo scan"],
    "KLBF": ["kalbe farma", "kalbe"],
    "MERK": ["merck"],

    # Tambang & Sumber Daya
    "PTBA": ["bukit asam", "ptba"],
    "ANTM": ["aneka tambang", "antam"],
    "INCO": ["vale indonesia", "vale"],
    "MDKA": ["merdeka copper gold", "merdeka"],
    "HRUM": ["harum energy", "harum"],
    "GEMS": ["golden energy"],
    "BYAN": ["bayan resources", "bayan"],
    "TINS": ["timah"],
    "SMGR": ["semen indonesia"],
    "INTP": ["indocement tunggal prakarsa", "indocement"],

    # Infrastruktur & Energi
    "PGAS": ["perusahaan gas negara", "pgn"],
    "AKRA": ["akr corporindo", "akr"],
    "ELSA": ["elsa jaya"],
    "JSMR": ["jasa marga"],

    # Keuangan & Asuransi
    "AMMN": ["amman mineral internasional"],
    "BREN": ["barito pacific"],

    # Saham Spesifik Portofolio User
    "ARNA": ["arwana citramulia", "arwana"],
}


# Set cepat untuk lookup
TICKER_SET = set(EMITEN_IDX.keys())
ALL_NAMES = []  # list of (name_lower, ticker)
for ticker, names in EMITEN_IDX.items():
    for name in names:
        ALL_NAMES.append((name.lower(), ticker))

# Sort by length (terpanjang dulu) agar matching multi-word lebih akurat
ALL_NAMES_SORTED = sorted(ALL_NAMES, key=lambda x: len(x[0]), reverse=True)


# Pattern untuk capture ticker langsung (e.g., "BBCA", "BBCA ")
TICKER_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(t) for t in sorted(TICKER_SET, key=len, reverse=True)) + r')\b',
    re.IGNORECASE
)


def extract_tickers(teks: str, top_n: int = 5) -> List[Dict]:
    """
    Ekstrak emiten/emitter entities dari teks.

    Returns:
        List of dict: [{"ticker": "BBCA", "matched_name": "bank central asia", "count": 2}, ...]
        Sorted by count descending.
    """
    if not teks:
        return []

    teks_lower = teks.lower()
    ticker_counts: Dict[str, Dict] = {}

    # 1. Match by ticker langsung (case-insensitive)
    for match in TICKER_PATTERN.finditer(teks):
        ticker = match.group(1).upper()
        if ticker not in ticker_counts:
            ticker_counts[ticker] = {"ticker": ticker, "matched_name": ticker, "count": 0}
        ticker_counts[ticker]["count"] += 1

    # 2. Match by full name / alias
    for name_lower, ticker in ALL_NAMES_SORTED:
        # Gunakan word boundary untuk akurasi
        pattern = r'\b' + re.escape(name_lower) + r'\b'
        matches = re.findall(pattern, teks_lower)
        if matches:
            count = len(matches)
            if ticker in ticker_counts:
                ticker_counts[ticker]["count"] += count
                # Update matched_name ke yang lebih panjang/informatif
                if len(name_lower) > len(ticker_counts[ticker]["matched_name"]):
                    ticker_counts[ticker]["matched_name"] = name_lower
            else:
                ticker_counts[ticker] = {
                    "ticker": ticker,
                    "matched_name": name_lower,
                    "count": count,
                }

    # Sort by count, return top_n
    results = sorted(ticker_counts.values(), key=lambda x: x["count"], reverse=True)
    return results[:top_n]


def get_primary_ticker(teks: str) -> str:
    """Ambil emiten paling dominan dari teks. Return 'UMUM' jika tidak ada."""
    entities = extract_tickers(teks, top_n=1)
    return entities[0]["ticker"] if entities else "UMUM"


def get_all_mentioned_tickers(teks: str) -> List[str]:
    """Return list semua ticker yang muncul (untuk multi-emiten context)."""
    entities = extract_tickers(teks, top_n=10)
    return [e["ticker"] for e in entities]


# ============================================================
# EMITEN PORTOFOLIO USER (dari config existing)
# ============================================================

USER_PORTFOLIO = {
    "ARNA", "BRIS", "SMSM", "SIDO", "PTBA", "ACES",  # dari app.py
}


def extract_portfolio_hits(teks: str) -> List[Dict]:
    """
    Khusus emiten yang ada di portofolio user.
    Lebih di-emphasize untuk watchlist.
    """
    all_entities = extract_tickers(teks, top_n=20)
    portfolio_hits = [e for e in all_entities if e["ticker"] in USER_PORTFOLIO]
    return portfolio_hits