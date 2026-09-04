"""
Modul utility terpusat untuk konsistensi UI/UX & analisis di semua halaman.
Di-import oleh semua file di /pages untuk mencegah duplikasi CSS & helper.
"""
import math
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# =====================================================================
# Palet Warna Tema Gelap (GitHub Dark Inspired)
# =====================================================================
PALETTE = {
    "pos": "#2ea043",
    "neg": "#f85149",
    "net": "#8b949e",
    "primary": "#1f6feb",
    "primary_alt": "#58a6ff",
    "warning": "#d29922",
    "danger": "#db6d28",
    "purple": "#a371f7",
    "border": "#30363d",
    "text_muted": "#8b949e",
    "text_main": "#c9d1d9",
    "text_strong": "#f0f6fc",
    "bg_panel": "#161b22",
    "bg_panel_alt": "#1f242c",
    "bg_deep": "#0d1117",
}

SENTIMEN_COLORS = [PALETTE["pos"], PALETTE["net"], PALETTE["neg"]]
SENTIMEN_ORDER = ["POSITIF", "NETRAL", "NEGATIF"]

# Stopwords Indonesia + istilah finansial generik
STOPWORDS_ID = frozenset([
    "yang", "di", "dan", "dengan", "untuk", "pada", "ke", "karena",
    "oleh", "dari", "ini", "itu", "akan", "juga", "atau", "bisa",
    "tidak", "ada", "seperti", "tahun", "saat", "menjadi", "lebih",
    "hari", "secara", "sudah", "dapat", "tersebut", "persen", "rp",
    "juta", "miliar", "triliun", "sebesar", "mencapai", "catat",
    "hingga", "serta", "antara", "bahwa", "ia", "mereka", "kita",
    "kami", "anda", "nya", "lah", "pun", "masih", "sedang", "telah",
    "ujar", "kata", "menurut", "bahkan", "jadi", "masuk",
    "jakarta", "indonesia", "senilai", "cnn", "cnbc", "kontan",
])


# =====================================================================
# Path bootstrap: agar file di /pages bisa import modul root ini
# =====================================================================
def ensure_path():
    """Pastikan root project ada di sys.path. Aman dipanggil berulang."""
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


# =====================================================================
# Konfigurasi Global Matplotlib (tema gelap)
# =====================================================================
def apply_dark_theme():
    """Terapkan rcParams tema gelap untuk matplotlib. Panggil SEKALI per halaman."""
    plt.rcParams.update({
        "text.color": PALETTE["text_main"],
        "axes.labelcolor": PALETTE["text_main"],
        "xtick.color": PALETTE["text_muted"],
        "ytick.color": PALETTE["text_muted"],
        "figure.facecolor": "none",
        "axes.facecolor": "none",
        "grid.color": PALETTE["border"],
        "grid.linestyle": "--",
        "grid.alpha": 0.4,
        "font.family": "DejaVu Sans",
        "font.size": 10,
    })


def styled_axes(ax):
    """Hilangkan border atas/kanan, warnai spine kiri/bawah."""
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(PALETTE["border"])
    return ax


# =====================================================================
# CSS Terpusat (di-inject sekali per halaman)
# =====================================================================
SHARED_CSS = """
<style>
    /* === SIDEBAR === */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid #30363d;
        padding-top: 1rem;
    }
    [data-testid="stSidebarNav"]::before {
        content: "NAVIGASI UTAMA";
        display: block;
        margin-left: 20px;
        margin-bottom: 10px;
        font-size: 11px;
        font-weight: 800;
        color: #8b949e;
        letter-spacing: 1.2px;
    }
    [data-testid="stSidebarNav"] ul { gap: 6px; }
    [data-testid="stSidebarNav"] a {
        border-radius: 8px;
        padding: 8px 12px;
        color: #c9d1d9 !important;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: rgba(31, 111, 235, 0.15);
        color: #58a6ff !important;
        transform: translateX(4px);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: linear-gradient(135deg, #1f6feb 0%, #238636 100%);
        color: white !important;
        font-weight: 600;
        box-shadow: 0 3px 8px rgba(31, 111, 235, 0.3);
    }

    /* === TOMBOL PRIMER === */
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #1f6feb 0%, #238636 100%);
        color: white;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.2rem;
        box-shadow: 0 4px 12px rgba(35, 134, 54, 0.3);
        transition: all 0.2s ease;
    }
    .stButton button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(35, 134, 54, 0.5);
    }
    .stButton button[kind="primary"]:active,
    .stButton button[kind="primary"]:focus {
        background: linear-gradient(135deg, #1f6feb 0%, #238636 100%) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(35, 134, 54, 0.5) !important;
    }

    /* === HERO / HEADER === */
    .hero-title-box {
        background: linear-gradient(135deg, rgba(31, 111, 235, 0.15) 0%, rgba(35, 134, 54, 0.08) 100%);
        border: 1px solid #30363d;
        border-left: 6px solid #1f6feb;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .hero-title-box::after {
        content: "";
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(88, 166, 255, 0.08) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-title-box h1 {
        color: #f0f6fc;
        font-size: 2.1rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-title-box p {
        color: #8b949e;
        margin: 6px 0 0 0;
        font-size: 1rem;
    }

    /* === MAIN HEADER === */
    .main-header {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        padding: 2.2rem;
        border-radius: 16px;
        border: 1px solid #30363d;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }

    /* === SENTIMENT BANNER === */
    .sentiment-banner {
        background: linear-gradient(135deg, #161b22 0%, #1f242c 100%);
        border-left: 6px solid #2ea043;
        padding: 1.4rem;
        border-radius: 12px;
        border: 1px solid #30363d;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }

    /* === SECTION HEADER === */
    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f0f6fc;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #30363d;
    }

    /* === METRIC BADGE === */
    .metric-badge {
        background: rgba(31, 111, 235, 0.1);
        border: 1px solid rgba(56, 139, 253, 0.4);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        transition: all 0.2s ease;
    }
    .metric-badge:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 139, 253, 0.7);
        box-shadow: 0 6px 16px rgba(31, 111, 235, 0.2);
    }
    .metric-badge .val {
        font-size: 1.7rem;
        font-weight: 700;
        color: #58a6ff;
        line-height: 1.2;
    }
    .metric-badge .lbl {
        font-size: 0.78rem;
        color: #8b949e;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-badge .sub {
        font-size: 0.7rem;
        color: #6e7681;
        margin-top: 2px;
    }

    /* === INSIGHT CARD === */
    .insight-card {
        background: linear-gradient(135deg, rgba(31, 111, 235, 0.08) 0%, rgba(35, 134, 54, 0.05) 100%);
        border: 1px solid #30363d;
        border-left: 4px solid #1f6feb;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .insight-card.warning { border-left-color: #d29922; }
    .insight-card.danger { border-left-color: #f85149; }
    .insight-card.success { border-left-color: #2ea043; }
    .insight-card .insight-title {
        font-weight: 700;
        color: #f0f6fc;
        font-size: 0.9rem;
        margin-bottom: 4px;
    }
    .insight-card .insight-text {
        color: #c9d1d9;
        font-size: 0.85rem;
        line-height: 1.4;
    }

    /* === STATUS PILL === */
    .status-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 2px;
    }
    .status-pill.pos { background: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid rgba(35, 134, 54, 0.4); }
    .status-pill.neg { background: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid rgba(248, 81, 73, 0.4); }
    .status-pill.net { background: rgba(139, 148, 158, 0.2); color: #8b949e; border: 1px solid rgba(139, 148, 158, 0.4); }

    /* === PROGRESS BAR === */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #1f6feb 0%, #2ea043 100%);
    }

    /* === ANIMASI FADE-IN === */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* ===========================================================
       MOBILE RESPONSIVE (max-width: 768px)
       - Stack semua kolom horizontal jadi vertikal (jangan side-by-side
         yang sempit) untuk News Velocity dan metric cards
       - Perkecil font heading & padding agar tidak overflow horizontal
       - Paksa data tabel & dataframe scrollable horizontal di mobile
       =========================================================== */
    @media (max-width: 768px) {
        /* Heading lebih kecil agar muat di layar sempit */
        .header-title,
        .main-header h1,
        .hero-title-box h1 {
            font-size: 1.5rem !important;
            line-height: 1.2 !important;
        }
        .main-header,
        .header-card,
        .sentiment-banner,
        .hero-title-box {
            padding: 1rem !important;
            margin-bottom: 0.75rem !important;
        }
        /* Semua matplotlib & plot container responsif */
        [data-testid="stArrowVegaLiteChart"],
        [data-testid="stPlotlyChart"],
        .stImage,
        img {
            max-width: 100% !important;
            height: auto !important;
        }
        /* Dataframe: jangan paksa full-width table menjadi terpotong kanan */
        [data-testid="stDataFrame"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
        }
        [data-testid="stDataFrame"] table {
            font-size: 0.78rem !important;
        }
        /* Metric cards lebih ringkas */
        .metric-value {
            font-size: 1.3rem !important;
        }
        .metric-label {
            font-size: 0.65rem !important;
        }
        /* Insight card padding dikurangi */
        .insight-card {
            padding: 0.7rem 0.9rem !important;
        }
        /* Section header jangan terlalu besar */
        .section-header {
            font-size: 1.05rem !important;
            margin-top: 1rem !important;
        }
        /* Tag container wrap */
        .tag-container { flex-wrap: wrap !important; gap: 5px !important; }
        .tag { font-size: 0.75rem !important; padding: 3px 9px !important; }
        /* BUTTONS: full-width di mobile */
        [data-testid="stButton"] > button {
            width: 100% !important;
        }
        /* Tabs scrollable horizontal */
        [data-testid="stTabs"] [role="tablist"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
        }
        /* Box info panel lebih ringkas */
        .insight-card .insight-title {
            font-size: 0.95rem !important;
        }
        .insight-card .insight-text {
            font-size: 0.82rem !important;
            line-height: 1.4 !important;
        }
    }
</style>
"""


def inject_shared_css():
    """Inject CSS bersama ke halaman Streamlit."""
    st.markdown(SHARED_CSS, unsafe_allow_html=True)


# =====================================================================
# Header Komponen
# =====================================================================
def hero_header(title: str, subtitle: str = ""):
    """Render hero header seragam."""
    st.markdown(
        f"""
        <div class="hero-title-box">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main_header(title: str, subtitle: str = ""):
    """Render main header besar (untuk Ringkasan Live)."""
    st.markdown(
        f"""
        <div class="main-header">
            <h1 style="margin:0; color: #f0f6fc; font-size: 2.4rem; font-weight: 800; letter-spacing: -0.5px;">{title}</h1>
            <p style="margin: 8px 0 0 0; color: #8b949e; font-size: 1.15rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(icon: str, title: str):
    """Render section header dengan garis bawah."""
    st.markdown(
        f'<div class="section-header">{icon} {title}</div>',
        unsafe_allow_html=True,
    )


def metric_badge(value: str, label: str, sub: str = "", color: str = None):
    """Render metric badge."""
    val_style = f'color:{color};' if color else ""
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="metric-badge">
            <div class="val" style="{val_style}">{value}</div>
            <div class="lbl">{label}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_card(title: str, text: str, variant: str = "default"):
    """Render kartu insight (default|warning|danger|success)."""
    st.markdown(
        f"""
        <div class="insight-card {variant}">
            <div class="insight-title">{title}</div>
            <div class="insight-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(text: str, kind: str = "net") -> str:
    """Return HTML status pill string."""
    return f'<span class="status-pill {kind}">{text}</span>'


# =====================================================================
# Helper Analisis
# =====================================================================
@st.cache_data(show_spinner=False)
def hitung_sentimen_counts(df: pd.DataFrame) -> dict:
    """Agregasi sentimen dari dataframe. Return dict berisi total, pos, net, neg."""
    n = len(df)
    counts = df['Sentimen'].value_counts().to_dict()
    return {
        "total": n,
        "pos": counts.get('POSITIF', 0),
        "net": counts.get('NETRAL', 0),
        "neg": counts.get('NEGATIF', 0),
    }


@st.cache_data(show_spinner=False)
def hitung_kata_kunci(gabung_tuple: tuple, top_n: int = 10):
    """Tokenisasi teks gabungan untuk wordcloud & top-N. Return (tokens, df_top)."""
    gabung = " ".join(gabung_tuple).lower()
    tokens = re.findall(r'\b[a-z]{3,}\b', gabung)
    tokens = [t for t in tokens if t not in STOPWORDS_ID]
    if not tokens:
        return [], pd.DataFrame(columns=['Kata', 'Frekuensi'])
    top_df = pd.DataFrame(Counter(tokens).most_common(top_n), columns=['Kata', 'Frekuensi'])
    return tokens, top_df


def kategori_indeks(skor: float):
    """Return (label, penjelasan, warna) berdasarkan skor 0-100."""
    if skor >= 70:
        return ("Sangat Positif (Bullish)",
                "Pasar didominasi sentimen positif yang kuat dan ekspansif.",
                PALETTE["pos"])
    if skor >= 55:
        return ("Cenderung Positif",
                "Sentimen positif memimpin secara proporsional di berbagai sektor.",
                PALETTE["primary_alt"])
    if skor >= 45:
        return ("Netral / Seimbang",
                "Volume berita positif dan negatif berada dalam titik keseimbangan.",
                PALETTE["net"])
    if skor >= 30:
        return ("Cenderung Negatif",
                "Tekanan sentimen negatif mulai mendominasi pergerakan berita.",
                PALETTE["warning"])
    return ("Sangat Negatif (Bearish)",
            "Kepanikan atau sentimen negatif mayoritas mendominasi pasar.",
            PALETTE["neg"])


def hitung_risk_score_per_trigger(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Risk Score = (Negatif * 2 + Netral * 0.5 - Positif) / Total * 100
    Range: -100 (sangat positif) sampai +100 (sangat negatif).
    """
    if 'Trigger/Emiten' not in df.columns or 'Sentimen' not in df.columns:
        return pd.DataFrame()
    grp = df.groupby(['Trigger/Emiten', 'Sentimen']).size().unstack(fill_value=0)
    for col in SENTIMEN_ORDER:
        if col not in grp.columns:
            grp[col] = 0
    grp['Total'] = grp[SENTIMEN_ORDER].sum(axis=1)
    grp = grp[grp['Total'] >= 2]
    grp['Risk_Score'] = (
        (grp['NEGATIF'] * 2 + grp['NETRAL'] * 0.5 - grp['POSITIF'])
        / grp['Total'] * 100
    ).round(1)
    grp['Positif_Pct'] = (grp['POSITIF'] / grp['Total'] * 100).round(1)
    grp['Negatif_Pct'] = (grp['NEGATIF'] / grp['Total'] * 100).round(1)
    return grp.nlargest(top_n, 'Risk_Score').reset_index()


def hitung_diversity_index(df: pd.DataFrame, kolom: str = 'Sumber') -> float:
    """Shannon Diversity Index (0 = monoton, ~3 = sangat beragam)."""
    if kolom not in df.columns or df.empty:
        return 0.0
    counts = df[kolom].value_counts()
    total = counts.sum()
    if total == 0:
        return 0.0
    proportions = counts / total
    return round(-sum(p * math.log(p) for p in proportions if p > 0), 3)


def get_top_movers(df: pd.DataFrame, n: int = 5) -> dict:
    """Identifikasi emiten dengan lonjakan sentimen positif & negatif."""
    if 'Trigger/Emiten' not in df.columns or 'Sentimen' not in df.columns:
        return {"gainers": [], "losers": [], "most_discussed": []}
    grp = df.groupby(['Trigger/Emiten', 'Sentimen']).size().unstack(fill_value=0)
    for col in SENTIMEN_ORDER:
        if col not in grp.columns:
            grp[col] = 0
    grp['Total'] = grp[SENTIMEN_ORDER].sum(axis=1)
    grp = grp[grp['Total'] >= 1]
    grp['Sent_Ratio'] = (
        (grp['POSITIF'] - grp['NEGATIF']) / grp['Total'] * 100
    ).round(1)
    gainers = grp.nlargest(n, 'Sent_Ratio').reset_index()[['Trigger/Emiten', 'Sent_Ratio', 'Total', 'POSITIF']].to_dict('records')
    losers = grp.nsmallest(n, 'Sent_Ratio').reset_index()[['Trigger/Emiten', 'Sent_Ratio', 'Total', 'NEGATIF']].to_dict('records')
    most_discussed = grp.nlargest(n, 'Total').reset_index()[['Trigger/Emiten', 'Total', 'Sent_Ratio']].to_dict('records')
    return {"gainers": gainers, "losers": losers, "most_discussed": most_discussed}


def get_sentiment_trend_7d(df: pd.DataFrame) -> pd.DataFrame:
    """Tren indeks sentimen harian."""
    if 'dt_sort' not in df.columns or df.empty:
        return pd.DataFrame()
    df_valid = df[df['dt_sort'] != datetime.min].copy()
    if df_valid.empty:
        return pd.DataFrame()
    df_valid['Tanggal'] = df_valid['dt_sort'].dt.date
    trend = df_valid.groupby(['Tanggal', 'Sentimen']).size().unstack(fill_value=0)
    for col in SENTIMEN_ORDER:
        if col not in trend.columns:
            trend[col] = 0
    total = trend[SENTIMEN_ORDER].sum(axis=1).replace(0, 1)
    trend['Index'] = ((trend['POSITIF'] - trend['NEGATIF']) / total * 50 + 50).round(1)
    return trend.reset_index()


def get_news_velocity(df: pd.DataFrame) -> pd.DataFrame:
    """Kecepatan publikasi berita (artikel per jam) — deteksi anomali volume."""
    if 'dt_sort' not in df.columns or df.empty:
        return pd.DataFrame()
    df_valid = df[df['dt_sort'] != datetime.min].copy()
    if df_valid.empty:
        return pd.DataFrame()
    df_valid['Bucket'] = df_valid['dt_sort'].dt.floor('H')
    velocity = df_valid.groupby('Bucket').size().reset_index(name='Jumlah')
    if not velocity.empty:
        avg = velocity['Jumlah'].mean()
        std = velocity['Jumlah'].std()
        velocity['Anomali'] = velocity['Jumlah'].apply(
            lambda x: '🔥 Spike' if std > 0 and (x - avg) > 1.5 * std else 'Normal'
        )
    return velocity


def get_media_reliability(df: pd.DataFrame) -> pd.DataFrame:
    """Skor reliabilitas per portal."""
    if 'Sumber' not in df.columns:
        return pd.DataFrame()
    rekap = df.groupby('Sumber').agg(Total=('Judul', 'count')).reset_index()
    if 'Akses' in df.columns:
        rekap['Success_Rate'] = (df.groupby('Sumber')['Akses']
                                 .apply(lambda x: (x == 'Penuh').sum() / max(len(x), 1))
                                 .values * 100).round(1)
    else:
        rekap['Success_Rate'] = 100.0
    return rekap.sort_values('Total', ascending=False)


# =====================================================================
# Filter Utility
# =====================================================================
def get_dataframe_or_stop() -> pd.DataFrame | None:
    """Ambil dataframe dari session_state, tampilkan warning & stop jika kosong."""
    df = st.session_state.get('df_hasil', None)
    if df is None or df.empty:
        st.warning("⚠️ Belum ada data pemindaian. Silakan jalankan pemindaian dari menu utama terlebih dahulu.")
        st.stop()
    return df


def safe_pie_labels(labels, max_len: int = 18):
    """Potong label panjang agar pie chart tidak terpotong."""
    return [str(l)[:max_len] + "…" if len(str(l)) > max_len else str(l) for l in labels]


# =====================================================================
# Filter Panel Interaktif (BARU)
# =====================================================================
def render_global_filter(df: pd.DataFrame, key_prefix: str = "global") -> pd.DataFrame:
    """
    Panel filter interaktif yang digunakan di semua halaman.
    Return dataframe yang sudah difilter.
    """
    with st.container(border=True):
        st.markdown("##### ⚙️ **Panel Filter Global**")
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            list_kategori = sorted(df['Kategori Aset'].dropna().unique().tolist()) if 'Kategori Aset' in df.columns else []
            selected_kategori = st.multiselect(
                "📦 Kategori Aset",
                options=list_kategori,
                default=[],
                key=f"{key_prefix}_kategori"
            )
        with col_f2:
            list_sumber = sorted(df['Sumber'].dropna().unique().tolist()) if 'Sumber' in df.columns else []
            selected_sumber = st.multiselect(
                "📡 Sumber Portal",
                options=list_sumber,
                default=[],
                key=f"{key_prefix}_sumber"
            )
        with col_f3:
            list_sentimen = ['POSITIF', 'NETRAL', 'NEGATIF']
            selected_sentimen = st.multiselect(
                "🎯 Filter Sentimen",
                options=list_sentimen,
                default=[],
                key=f"{key_prefix}_sentimen"
            )

        # Filter tanggal (opsional)
        if 'dt_sort' in df.columns:
            df_temp = df.copy()
            df_temp['date_only'] = pd.to_datetime(df_temp['dt_sort'], errors='coerce').dt.date
            valid_dates = df_temp['date_only'].dropna()
            if not valid_dates.empty:
                min_d, max_d = valid_dates.min(), valid_dates.max()
                use_date = st.checkbox("📅 Aktifkan filter tanggal", value=False, key=f"{key_prefix}_use_date")
                if use_date:
                    date_range = st.date_input(
                        "Rentang tanggal",
                        value=(min_d, max_d),
                        min_value=min_d,
                        max_value=max_d,
                        key=f"{key_prefix}_date"
                    )
                else:
                    date_range = None
            else:
                date_range = None
        else:
            date_range = None

    # Terapkan filter
    df_filtered = df.copy()
    if selected_kategori and 'Kategori Aset' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Kategori Aset'].isin(selected_kategori)]
    if selected_sumber and 'Sumber' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Sumber'].isin(selected_sumber)]
    if selected_sentimen and 'Sentimen' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Sentimen'].isin(selected_sentimen)]
    if date_range and 'dt_sort' in df_filtered.columns and isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
        mask = (df_filtered['dt_sort'].dt.date >= start_d) & (df_filtered['dt_sort'].dt.date <= end_d)
        df_filtered = df_filtered[mask]

    # Tampilkan ringkasan filter
    if len(df_filtered) != len(df):
        st.info(f"📊 Menampilkan **{len(df_filtered):,}** dari **{len(df):,}** berita (setelah filter).")

    return df_filtered
