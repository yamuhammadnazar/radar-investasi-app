import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import urllib3
import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from difflib import SequenceMatcher

# Mematikan peringatan SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
}

# --- KELOMPOK KATEGORI PORTOFOLIO ---
KATEGORI_PORTOFOLIO = {
    "SAHAM_EMITEN": [
        "arna", "arwana citramulia",
        "bris", "bank syariah indonesia",
        "smsm", "selamat sempurna",
        "sido", "industri jamu dan farmasi sido muncul",
        "ptba", "bukit asam",
        "aces", "aspirasi hidup indonesia"
    ],
    "SEKTOR_SAHAM": [
        "keramik", "properti", "konstruksi",
        "perbankan", "perbankan syariah",
        "otomotif", "spare part", "aftermarket",
        "farmasi", "herbal", "consumer health",
        "retail", "home improvement",
        "batu bara", "energi", "kelistrikan", "bbm"
    ],
    "ETF": [
        "r-lq45x", "lq45", "indeks lq45", "rebalancing lq45", 
        "konstituen lq45", "etf indonesia", "foreign flow"
    ],
    "REKSADANA": [
        "majoris pasar uang syariah", "mandiri invasta dana syariah", 
        "sucorinvest equity fund", "pasar uang syariah", "sukuk", 
        "sbsn", "obligasi syariah", "reksadana saham", "reksadana obligasi"
    ],
    "EMAS": [
        "emas", "gold", "xau", "xau/usd", "harga emas", "emas pegadaian", "emas antam"
    ],
    "KOMODITAS": [
        "harga batu bara", "hba", "coal price", "harga minyak", "oil price"
    ],
    "MAKRO_INDONESIA": [
        "bi rate", "bank indonesia", "inflasi indonesia", "rupiah", "usd/idr", 
        "gdp indonesia", "pertumbuhan ekonomi", "apbn", "yield obligasi", 
        "ihsg", "foreign flow", "net buy asing", "net sell asing"
    ],
    "MAKRO_GLOBAL": [
        "federal reserve", "fed rate", "us cpi", "us pce", "us nfp", 
        "us treasury yield", "dxy", "china economy", "china stimulus", "ftse", "msci"
    ],
    "REGULASI": [
        "ojk", "bei", "kementerian keuangan", "kementerian esdm", 
        "kementerian perindustrian", "kementerian perdagangan", 
        "kebijakan pemerintah", "aturan ekspor", "aturan impor", "kebijakan pajak", "dpr"
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
    if not tanggal_str or tanggal_str == 'N/A':
        return True
    try:
        dt_berita = date_parser.parse(tanggal_str)
        if dt_berita.tzinfo is not None:
            dt_berita = dt_berita.astimezone().replace(tzinfo=None)
            
        waktu_sekarang = datetime.now()
        batas_waktu = waktu_sekarang - timedelta(hours=jam_maksimal)
        
        # Toleransi waktu 2 jam untuk selisih zona waktu / server RSS
        batas_waktu_dengan_toleransi = batas_waktu - timedelta(hours=2)
        
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
    else:
        return "Luar Jam Bursa"

def tentukan_kategori_aset(teks_lower):
    for kat, kw_list in KATEGORI_PORTOFOLIO.items():
        for kw in kw_list:
            if re.search(rf'\b{re.escape(kw)}\b', teks_lower):
                if kat in ["SAHAM_EMITEN", "SEKTOR_SAHAM"]:
                    return "SAHAM"
                elif kat in ["ETF", "REKSADANA"]:
                    return "REKSADANA_ETF"
                elif kat in ["EMAS", "KOMODITAS"]:
                    return "EMAS_KOMODITAS"
                elif kat in ["MAKRO_INDONESIA", "MAKRO_GLOBAL", "REGULASI"]:
                    return "MAKRO_REGULASI"
    return "MAKRO_REGULASI"

def bersihkan_judul(judul):
    j = re.sub(r'[^a-zA-Z0-9\s]', '', judul.lower())
    j = re.sub(r'\s+(cnbc|investor|kontan|katadata|tempo|antara|idxchannel|idnfinancials|detik|bloomberg|cnn|kompas).*$', '', j)
    kata_inti = [kata for kata in j.split() if kata not in STOPWORDS_ID]
    return " ".join(kata_inti).strip()

def rasio_kemiripan(judul_bersih_a, judul_bersih_b):
    return SequenceMatcher(None, judul_bersih_a, judul_bersih_b).ratio()

def apakah_duplikat(judul_baru, link_baru, daftar_tersimpan, ambang_kemiripan):
    judul_bersih_baru = bersihkan_judul(judul_baru)
    for item in daftar_tersimpan:
        if link_baru == item['link']:
            return True
        if rasio_kemiripan(judul_bersih_baru, item['judul_bersih']) >= ambang_kemiripan:
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
            if kw in kalimat_lower: skor += 2
        for kw in KATA_POSITIF + KATA_NEGATIF:
            if kw in kalimat_lower: skor += 1.5
        skor_kalimat.append((skor, index, kalimat))
    kalimat_terpilih = sorted(skor_kalimat, key=lambda x: x[0], reverse=True)[:max_kalimat]
    kalimat_terpilih_urut = sorted(kalimat_terpilih, key=lambda x: x[1])
    return " ".join([k[2] for k in kalimat_terpilih_urut])

def analisa_sentimen(teks):
    teks_lower = teks.lower()
    skor_positif = sum(1 for kata in KATA_POSITIF if kata in teks_lower)
    skor_negatif = sum(1 for kata in KATA_NEGATIF if kata in teks_lower)
    if skor_positif > skor_negatif: return "POSITIF"
    elif skor_negatif > skor_positif: return "NEGATIF"
    else: return "NETRAL"

def dapatkan_feed_rss(url_rss):
    try:
        response = requests.get(url_rss, headers=HEADERS, timeout=12, verify=False)
        if response.status_code == 200:
            return feedparser.parse(response.content)
    except Exception:
        pass
    return feedparser.parse(url_rss)

def dapatkan_url_asli(url_target):
    if "news.google.com" in url_target:
        try:
            resp = requests.get(url_target, headers=HEADERS, timeout=10, verify=False, allow_redirects=True)
            return resp.url
        except Exception:
            return url_target
    return url_target

def ambil_isi_berita(url_input, tag_html, class_html, butuh_page_all):
    try:
        url_asli = dapatkan_url_asli(url_input)
        link_target = url_asli + "?page=all" if butuh_page_all else url_asli
        response = requests.get(link_target, headers=HEADERS, timeout=12, verify=False, allow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            html_text = response.text.lower()
            if any(p in html_text for p in ["paywall", "berlangganan", "artikel premium", "sumber terpercaya", "konten berbayar"]):
                if len(soup.find_all('p')) < 3:
                    return "Artikel Terkunci / Berbayar (Paywall)", "Paywall"
            artikel_body = soup.find(tag_html, class_=class_html)
            if artikel_body:
                paragraf = artikel_body.find_all('p')
                teks_paragraf = [p.text.strip() for p in paragraf if len(p.text.strip()) > 20]
                if teks_paragraf: return "\n\n".join(teks_paragraf), "Penuh"
            semua_p = soup.find_all('p')
            teks_universal = [p.text.strip() for p in semua_p if len(p.text.strip()) > 30 and not re.search(r'(cookie|privacy|baca juga)', p.text.strip(), re.IGNORECASE)]
            if teks_universal: return "\n\n".join(teks_universal), "Penuh"
            return "Konten tidak dapat diekstrak.", "Terbatas"
        return f"Gagal akses. Status: {response.status_code}", "Error"
    except Exception as e:
        return f"Error: {e}", "Error"

# --- ATURAN PORTAL LENGKAP TERBARU ---
aturan_portal = {
    "IDNFinancials": {
        "rss": "https://news.google.com/rss/search?q=site:idnfinancials.com/id/news&hl=id&gl=ID&ceid=ID:id", 
        "tag": "div", "class": "cb", "butuh_page_all": False
    },
    "Kompas Money": {
        "rss": "https://news.google.com/rss/search?q=site:money.kompas.com&hl=id&gl=ID&ceid=ID:id", 
        "tag": "div", "class": "read__content", "butuh_page_all": True
    },
    "CNN Indonesia (Ekonomi)": {
        "rss": "https://www.cnnindonesia.com/ekonomi/rss", 
        "tag": "div", "class": "detail_text", "butuh_page_all": False
    },
    "CNBC Indonesia (Market)": {
        "rss": "https://www.cnbcindonesia.com/market/rss", 
        "tag": "div", "class": "detail_text", "butuh_page_all": False
    },
    "CNBC Indonesia (MyMoney)": {
        "rss": "https://www.cnbcindonesia.com/mymoney/rss", 
        "tag": "div", "class": "detail_text", "butuh_page_all": False
    },
    "CNBC Indonesia (News)": {
        "rss": "https://www.cnbcindonesia.com/news/rss", 
        "tag": "div", "class": "detail_text", "butuh_page_all": False
    },
    "Investor.id (Market & Fin)": {
        "rss": "https://news.google.com/rss/search?q=site:investor.id+(market+OR+finance+OR+saham)&hl=id&gl=ID&ceid=ID:id", 
        "tag": "div", "class": "read-content", "butuh_page_all": False
    },
    "Investor.id (Macro & Investory)": {
        "rss": "https://news.google.com/rss/search?q=site:investor.id+(macroeconomy+OR+investory)&hl=id&gl=ID&ceid=ID:id", 
        "tag": "div", "class": "read-content", "butuh_page_all": False
    },
    "Kontan Utama & Investasi": {
        "rss": "https://www.kontan.co.id/feed", 
        "tag": "div", "class": "tmpt-desk-kon", "butuh_page_all": True
    },
    "Katadata": {
        "rss": "https://katadata.co.id/rss", 
        "tag": "div", "class": "detail-body", "butuh_page_all": False
    },
    "Bloomberg Technoz": {
        "rss": "https://www.bloombergtechnoz.com/rss", 
        "tag": "div", "class": "detail-content", "butuh_page_all": False
    },
    "Tempo Bisnis": {
        "rss": "https://rss.tempo.co/bisnis", 
        "tag": "div", "class": "detail-konten", "butuh_page_all": False
    },
    "ANTARA Ekonomi": {
        "rss": "https://www.antaranews.com/rss/ekonomi-bisnis.xml", 
        "tag": "div", "class": "wrap__article-detail-content", "butuh_page_all": True
    },
    "IDX Channel": {
        "rss": "https://news.google.com/rss/search?q=site:idxchannel.com&hl=id&gl=ID&ceid=ID:id", 
        "tag": "div", "class": "detail-text", "butuh_page_all": False
    },
    "Detik Finance": {
        "rss": "https://finance.detik.com/rss", 
        "tag": "div", "class": "detail__body-text", "butuh_page_all": True
    }
}

kata_kunci_portofolio = [kw for sublist in KATEGORI_PORTOFOLIO.values() for kw in sublist]

st.set_page_config(page_title="Radar Investasi Multi", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        .stApp {
            background-color: #0d1117;
        }
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
        [data-testid="stSidebarNav"] ul {
            gap: 6px;
        }
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
            font-size: 22px;
            font-weight: 700;
            color: #58a6ff;
            margin-top: 4px;
        }
        .metric-label {
            font-size: 11px;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #1f6feb 0%, #238636 100%);
            color: white;
            font-weight: 600;
            border-radius: 8px;
            border: none;
            padding: 0.6rem 1.2rem;
            box-shadow: 0 4px 12px rgba(35, 134, 54, 0.3);
        }
        .stButton button[kind="primary"]:active, 
        .stButton button[kind="primary"]:focus {
            background: linear-gradient(135deg, #1f6feb 0%, #238636 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(35, 134, 54, 0.5) !important;
        }
        
        /* --- CSS RESPONSIF UNTUK PERANGKAT MOBILE --- */
        @media (max-width: 768px) {
            .header-title {
                font-size: 1.8rem !important;
            }
            .header-card {
                padding: 1.2rem !important;
            }
            .tag-container {
                flex-wrap: wrap !important;
                gap: 6px !important;
            }
            .metric-card {
                margin-bottom: 10px !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

if 'df_hasil' not in st.session_state: st.session_state.df_hasil = None
if 'duration_scan' not in st.session_state: st.session_state.duration_scan = 0
if 'skor_indeks_val' not in st.session_state: st.session_state.skor_indeks_val = 50.0

# --- MODERN HEADER DESIGN ---
st.markdown("""
    <style>
        .header-card {
            background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            padding: 2rem;
            border-radius: 16px;
            border: 1px solid #30363d;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            margin-bottom: 2rem;
        }
        .header-title {
            font-size: 2.5rem;
            font-weight: 800;
            color: #ffffff;
            margin: 0;
            background: linear-gradient(to right, #ffffff, #8b949e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-subtitle {
            color: #8b949e;
            font-size: 1.1rem;
            margin-top: 0.5rem;
            font-weight: 400;
        }
        .tag-container {
            display: flex;
            gap: 10px;
            margin-top: 1.5rem;
        }
        .tag {
            background: rgba(88, 166, 255, 0.1);
            color: #58a6ff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
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
        </div>
    </div>
""", unsafe_allow_html=True)

# --- METRIC KARTU STATISTIK DI ATAS ---
if st.session_state.df_hasil is not None:
    df_mem = st.session_state.df_hasil
    tot_berita = len(df_mem)
    tot_pos = len(df_mem[df_mem['Sentimen'] == 'POSITIF'])
    tot_neg = len(df_mem[df_mem['Sentimen'] == 'NEGATIF'])
    dur_scan = st.session_state.duration_scan

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-card"><div class="metric-label">Total Berita</div><div class="metric-value">{tot_berita} Artikel</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><div class="metric-label">Positif</div><div class="metric-value" style="color: #2ea043;">{tot_pos} Berita</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><div class="metric-label">Negatif</div><div class="metric-value" style="color: #f85149;">{tot_neg} Berita</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><div class="metric-label">Waktu Scan</div><div class="metric-value">{dur_scan} Detik</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

st.markdown("""
    <div style="background: rgba(31, 111, 235, 0.05); border-left: 4px solid #1f6feb; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
        <p style="margin: 0; font-size: 1rem; color: #c9d1d9;">
            <strong style="color: #58a6ff;">💡 Siap Memindai?</strong> 
            Sesuaikan parameter di <strong>Panel Pengaturan</strong> (bawah), lalu tekan tombol <strong>Mulai Pemindaian</strong> untuk mendapatkan insight pasar terkini.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- PANEL PENGATURAN & PARAMETER PEMINDAIAN ---
with st.expander("⚙️ Konfigurasi Radar & Notifikasi", expanded=False):
    tab1, tab2 = st.tabs(["🗄️ Sumber Berita", "🔔 Notifikasi & Opsi"])
    
    with tab1:
        st.markdown("### Pilih Kanal Berita")
        semua_portal_keys = list(aturan_portal.keys())
        pilih_semua = st.checkbox("Pilih Semua Portal", value=True)
        portal_terpilih = st.multiselect(
            "Filter Kanal:", 
            options=semua_portal_keys, 
            default=semua_portal_keys if pilih_semua else ["IDNFinancials", "Kontan Utama & Investasi"]
        )

        pilihan_rentang = st.select_slider(
            "Rentang Waktu Pemindaian:",
            options=["3 Jam Terakhir", "6 Jam Terakhir", "24 Jam Terakhir (1 Hari)", "3 Hari Terakhir", "Semua Berita (Tanpa Batas)"],
            value="3 Jam Terakhir"
        )
        map_jam = {
            "3 Jam Terakhir": 3, 
            "6 Jam Terakhir": 6, 
            "24 Jam Terakhir (1 Hari)": 24, 
            "3 Hari Terakhir": 72, 
            "Semua Berita (Tanpa Batas)": 87600
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
        st.markdown("**Integrasi Telegram**")
        col_tg1, col_tg2 = st.columns(2)
        with col_tg1:
            bot_token = st.text_input("Bot Token:", placeholder="Masukkan token...", type="password")
        with col_tg2:
            chat_id = st.text_input("Chat ID:", placeholder="Masukkan chat ID...", value="")

st.markdown("<br>", unsafe_allow_html=True)

col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    tombol_scan = st.button("Mulai Pemindaian Radar Sekarang!", type="primary", use_container_width=True)

st.markdown("---")

if tombol_scan:
    if len(portal_terpilih) == 0:
        st.warning("Pilih minimal satu portal berita terlebih dahulu.")
    else:
        kumpulan_data_global, daftar_tersimpan = [], []
        timer_container = st.empty()
        progress_bar = st.progress(0)
        start_time = time.time()
        total_portal = len(portal_terpilih)
        
        for idx, nama_portal in enumerate(portal_terpilih):
            elapsed_time = round(time.time() - start_time, 1)
            timer_container.markdown(f"""
                <div style="background: rgba(31, 111, 235, 0.1); border: 1px solid #1f6feb; padding: 10px 15px; border-radius: 8px; color: #c9d1d9; display: flex; justify-content: space-between; align-items: center;">
                    <span>📡 Sedang Memindai: <strong style="color: #58a6ff;">{nama_portal}</strong> <span style="color: #8b949e; font-size: 0.9em;">({idx+1}/{total_portal})</span></span>
                    <span style="font-family: monospace; color: #3fb950; font-weight: bold;">⏱️ {elapsed_time}s</span>
                </div>
            """, unsafe_allow_html=True)
            
            aturan = aturan_portal[nama_portal]
            feed = dapatkan_feed_rss(aturan["rss"])
            if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                for entry in feed.entries:
                    judul = entry.get('title', 'N/A')
                    link = entry.get('link', 'N/A')
                    tanggal = entry.get('published', '') or entry.get('updated', 'N/A')
                    deskripsi = entry.get('summary', '') + " " + entry.get('description', '')
                    
                    if not apakah_dalam_rentang(tanggal, jam_filter): continue
                    teks_pencocokan = (judul + " " + deskripsi).lower()
                    
                    cocok, trigger_terdeteksi = False, "UMUM"
                    for kunci in kata_kunci_portofolio:
                        if re.search(rf'\b{re.escape(kunci)}\b', teks_pencocokan):
                            cocok, trigger_terdeteksi = True, kunci.upper()
                            break
                    if not cocok: continue
                    
                    is_dedup_active = locals().get('aktifkan_deduplikasi', True)
                    similarity_threshold = locals().get('ambang_duplikat', 0.75)
                    
                    if is_dedup_active and apakah_duplikat(judul, link, daftar_tersimpan, similarity_threshold): continue
                    
                    isi, status_akses = ambil_isi_berita(link, aturan["tag"], aturan["class"], aturan["butuh_page_all"])
                    sentimen_label = analisa_sentimen(judul + " " + isi)
                    ringkasan_teks = ringkas_teks(isi, kata_kunci_portofolio, max_kalimat=2)
                    kategori_aset = tentukan_kategori_aset(teks_pencocokan)
                    dt_obj = konversi_ke_datetime(tanggal)
                    
                    kumpulan_data_global.append({
                        "Sumber": nama_portal, "Kategori Aset": kategori_aset, "Trigger/Emiten": trigger_terdeteksi,
                        "Sentimen": sentimen_label, "Status Bursa": cek_status_bursa(dt_obj), "Akses": status_akses,
                        "Judul": judul, "Tanggal": tanggal, "dt_sort": dt_obj, "Ringkasan Berita": ringkasan_teks,
                        "Link": link, "Isi Berita": isi
                    })
                    daftar_tersimpan.append({"link": link, "judul_bersih": bersihkan_judul(judul)})
                    time.sleep(0.2)
            progress_bar.progress((idx + 1) / total_portal)
        
        duration = round(time.time() - start_time, 2)
        timer_container.empty()
        
        if kumpulan_data_global:
            df = pd.DataFrame(kumpulan_data_global).sort_values(by='dt_sort', ascending=False).reset_index(drop=True)
            st.session_state.df_hasil = df
            st.session_state.duration_scan = duration
            n_pos = len(df[df['Sentimen'] == 'POSITIF'])
            n_neg = len(df[df['Sentimen'] == 'NEGATIF'])
            non_netral = n_pos + n_neg
            st.session_state.skor_indeks_val = round((n_pos / non_netral) * 100, 1) if non_netral > 0 else 50.0
            st.success(f"Radar Selesai! Menemukan {len(df)} berita unik dalam {duration} detik. (Silakan muat ulang/klik menu lain atau gulir untuk melihat pembaruan metrik kartu di atas).")
        else:
            st.session_state.df_hasil = None
            st.warning("Tidak ada berita yang sesuai dengan kriteria waktu & kata kunci portofolio.")