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
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt

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
        "r-lq45x",
        "lq45",
        "indeks lq45",
        "rebalancing lq45",
        "konstituen lq45",
        "etf indonesia",
        "foreign flow"
    ],

    "REKSADANA": [
        "majoris pasar uang syariah",
        "mandiri invasta dana syariah",
        "sucorinvest equity fund",
        "pasar uang syariah",
        "sukuk",
        "sbsn",
        "obligasi syariah",
        "reksadana saham",
        "reksadana obligasi"
    ],

    "EMAS": [
        "emas",
        "gold",
        "xau",
        "xau/usd",
        "harga emas",
        "emas pegadaian",
        "emas antam"
    ],

    "KOMODITAS": [
        "harga batu bara",
        "hba",
        "coal price",
        "harga minyak",
        "oil price"
    ],

    "MAKRO_INDONESIA": [
        "bi rate",
        "bank indonesia",
        "inflasi indonesia",
        "rupiah",
        "usd/idr",
        "gdp indonesia",
        "pertumbuhan ekonomi",
        "apbn",
        "yield obligasi",
        "ihsg",
        "foreign flow",
        "net buy asing",
        "net sell asing"
    ],

    "MAKRO_GLOBAL": [
        "federal reserve",
        "fed rate",
        "us cpi",
        "us pce",
        "us nfp",
        "us treasury yield",
        "dxy",
        "china economy",
        "china stimulus",
        "ftse",
        "msci"
    ],

    "REGULASI": [
        "ojk",
        "bei",
        "bank indonesia",
        "kementerian keuangan",
        "kementerian esdm",
        "kementerian perindustrian",
        "kementerian perdagangan",
        "kebijakan pemerintah",
        "aturan ekspor",
        "aturan impor",
        "kebijakan pajak",
        "dpr"
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

# --- FUNGSI BADGE COLOR HELPER ---
def render_badge_sentimen(sentimen):
    if "POSITIF" in sentimen:
        return '<span style="background-color: #d4edda; color: #155724; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85em;">🟢 POSITIF</span>'
    elif "NEGATIF" in sentimen:
        return '<span style="background-color: #f8d7da; color: #721c24; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85em;">🔴 NEGATIF</span>'
    else:
        return '<span style="background-color: #e2e3e5; color: #383d41; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85em;">⚪ NETRAL</span>'

def render_badge_bursa(status_bursa):
    if "Buka" in status_bursa:
        return '<span style="background-color: #d1e7dd; color: #0f5132; padding: 4px 10px; border-radius: 12px; font-weight: 500; font-size: 0.85em;">🟢 Bursa Buka</span>'
    elif "Luar" in status_bursa:
        return '<span style="background-color: #cff4fc; color: #055160; padding: 4px 10px; border-radius: 12px; font-weight: 500; font-size: 0.85em;">🌙 Luar Jam Bursa</span>'
    elif "Tutup" in status_bursa:
        return '<span style="background-color: #f8d7da; color: #842029; padding: 4px 10px; border-radius: 12px; font-weight: 500; font-size: 0.85em;">🛑 Akhir Pekan</span>'
    else:
        return f'<span style="background-color: #e2e3e5; color: #41464b; padding: 4px 10px; border-radius: 12px; font-weight: 500; font-size: 0.85em;">{status_bursa}</span>'

# --- FUNGSI KIRIM NOTIFIKASI TELEGRAM ---
def kirim_notifikasi_telegram(bot_token, chat_id, pesan_text):
    if not bot_token or not chat_id:
        return False, "Token Bot atau Chat ID belum diisi."
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": pesan_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True, "Berhasil terkirim!"
        else:
            payload.pop("parse_mode")
            response_fallback = requests.post(url, json=payload, timeout=10)
            if response_fallback.status_code == 200:
                return True, "Berhasil terkirim (Fallback Plain Text)!"
            return False, f"Gagal kirim: {response_fallback.text}"
    except Exception as e:
        return False, f"Error koneksi Telegram: {e}"

# --- FUNGSI DETEKSI KATEGORI ASET ---
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

# --- FUNGSI DEDUPLIKASI CERDAS (JUDUL & LINK) ---
def bersihkan_judul(judul):
    j = re.sub(r'[^a-zA-Z0-9\s]', '', judul.lower())
    j = re.sub(r'\s+(cnbc|investor|kontan|katadata|tempo|antara|idxchannel|idnfinancials|detik|bloomberg).*$', '', j)
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

# --- FUNGSI PARSING TANGGAL & STATUS BURSA ---
def konversi_ke_datetime(tanggal_str):
    if not tanggal_str or tanggal_str == 'N/A':
        return datetime.min
    try:
        dt = date_parser.parse(tanggal_str)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return datetime.min

def apakah_dalam_rentang(tanggal_str, jam_maksimal):
    if not tanggal_str or tanggal_str == 'N/A':
        return True
    try:
        dt_berita = date_parser.parse(tanggal_str)
        if dt_berita.tzinfo is not None:
            dt_berita = dt_berita.replace(tzinfo=None)
            
        batas_waktu = datetime.now() - timedelta(hours=jam_maksimal)
        return dt_berita >= batas_waktu
    except Exception:
        return True

def cek_status_bursa(dt_obj):
    if dt_obj == datetime.min:
        return "⚪ Waktu N/A"
    
    hari = dt_obj.weekday()
    jam = dt_obj.hour
    
    if hari in [5, 6]:
        return "🛑 Akhir Pekan (Tutup)"
    
    if 9 <= jam < 16:
        return "🟢 Bursa Buka"
    else:
        return "🌙 Luar Jam Bursa"

# --- FUNGSI AUTO-SUMMARY ---
def ringkas_teks(teks, kata_kunci_list, max_kalimat=2):
    if not teks or "tidak dapat diekstrak" in teks or "terkunci" in teks:
        return "-"
    
    kalimat_list = re.split(r'(?<=[.!?]) +', teks)
    if len(kalimat_list) <= max_kalimat:
        return teks

    skor_kalimat = []
    for index, kalimat in enumerate(kalimat_list):
        kalimat_lower = kalimat.lower()
        skor = 0
        if index == 0:
            skor += 3
        elif index == 1:
            skor += 2
            
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

# --- FUNGSI ANALISIS SENTIMEN ---
def analisa_sentimen(teks):
    teks_lower = teks.lower()
    skor_positif = sum(1 for kata in KATA_POSITIF if kata in teks_lower)
    skor_negatif = sum(1 for kata in KATA_NEGATIF if kata in teks_lower)
    
    if skor_positif > skor_negatif:
        return "POSITIF 🟢"
    elif skor_negatif > skor_positif:
        return "NEGATIF 🔴"
    else:
        return "NETRAL ⚪"

# --- FUNGSI AMBIL RSS ---
def dapatkan_feed_rss(url_rss):
    try:
        response = requests.get(url_rss, headers=HEADERS, timeout=12, verify=False)
        if response.status_code == 200:
            return feedparser.parse(response.content)
    except Exception:
        pass
    return feedparser.parse(url_rss)

# --- FUNGSI EKSTRAKSI URL ASLI ---
def dapatkan_url_asli(url_target):
    if "news.google.com" in url_target:
        try:
            resp = requests.get(url_target, headers=HEADERS, timeout=10, verify=False, allow_redirects=True)
            return resp.url
        except Exception:
            return url_target
    return url_target

# --- FUNGSI KESEHATAN PORTAL ---
def cek_kesehatan_semua_portal(portal_list, aturan_dict):
    laporan_kesehatan = []
    for nama_portal in portal_list:
        url_rss = aturan_dict[nama_portal]["rss"]
        t0 = time.time()
        try:
            resp = requests.get(url_rss, headers=HEADERS, timeout=6, verify=False)
            latensi = round((time.time() - t0) * 1000, 0)
            
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                if hasattr(feed, 'entries') and len(feed.entries) > 0:
                    status = "🟢 Baik (Normal)"
                else:
                    status = "🟡 Kosong (Tanpa Entri)"
            else:
                status = f"🔴 Error (HTTP {resp.status_code})"
        except requests.exceptions.Timeout:
            status = "⏳ Timeout (Lambat/Diblokir)"
            latensi = 6000
        except Exception as e:
            status = "❌ Bermasalah"
            latensi = 0
            
        laporan_kesehatan.append({
            "Portal / Kanal": nama_portal,
            "Status": status,
            "Latensi (ms)": f"{latensi} ms"
        })
    return pd.DataFrame(laporan_kesehatan)

# --- FUNGSI SCRAPING KONTEN & DETEKSI PAYWALL ---
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
                    return "🔒 Artikel Terkunci / Berbayar (Paywall)", "🔒 Paywall"

            artikel_body = soup.find(tag_html, class_=class_html)
            
            if not artikel_body:
                url_check = response.url.lower()
                if "idnfinancials.com" in url_check:
                    artikel_body = soup.find('article', class_='article-content') or soup.find('div', class_='article-body') or soup.find('article')
                elif "cnbcindonesia.com" in url_check:
                    artikel_body = soup.find('div', class_='detail_text') or soup.find('div', class_='detail-text') or soup.find('article')
                elif "investor.id" in url_check:
                    artikel_body = soup.find('div', class_='body-content') or soup.find('div', class_='article-body') or soup.find('div', class_='detail-content') or soup.find('article')
                elif "detik.com" in url_check:
                    artikel_body = soup.find('div', class_='detail__body-text') or soup.find('div', class_='itp_bodyreader') or soup.find('article')
                    
            if artikel_body:
                paragraf = artikel_body.find_all('p')
                teks_paragraf = [p.text.strip() for p in paragraf if len(p.text.strip()) > 20]
                if teks_paragraf:
                    return "\n\n".join(teks_paragraf), "✅ Penuh"
            
            semua_p = soup.find_all('p')
            teks_universal = []
            for p in semua_p:
                txt = p.text.strip()
                if len(txt) > 30 and not re.search(r'(cookie|privacy|rights reserved|baca juga)', txt, re.IGNORECASE):
                    teks_universal.append(txt)
            
            if teks_universal:
                return "\n\n".join(teks_universal), "✅ Penuh"
                    
            return "Konten tidak dapat diekstrak (Struktur HTML berubah).", "🔒 Terbatas"
        return f"Gagal akses. Status: {response.status_code}", "❌ Error"
    except Exception as e:
        return f"Error: {e}", "❌ Error"

# --- KAMUS ATURAN PORTAL BERITA (Stabil dengan Google News RSS) ---
aturan_portal = {
    "IDNFinancials": {
        "rss": "https://news.google.com/rss/search?q=site:idnfinancials.com&hl=id&gl=ID&ceid=ID:id", 
        "tag": "article", "class": "article-content", "butuh_page_all": False
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
    "Investor.id (Market)": {
        "rss": "https://news.google.com/rss/search?q=site:investor.id+market&hl=id&gl=ID&ceid=ID:id", 
        "tag": "article", "class": "detail-article", "butuh_page_all": False
    },
    "Investor.id (Finance)": {
        "rss": "https://news.google.com/rss/search?q=site:investor.id+finance&hl=id&gl=ID&ceid=ID:id", 
        "tag": "article", "class": "detail-article", "butuh_page_all": False
    },
    "Investor.id (Macroeconomy)": {
        "rss": "https://news.google.com/rss/search?q=site:investor.id+macroeconomy&hl=id&gl=ID&ceid=ID:id", 
        "tag": "article", "class": "detail-article", "butuh_page_all": False
    },
    "Investor.id (Investory)": {
        "rss": "https://news.google.com/rss/search?q=site:investor.id+investory&hl=id&gl=ID&ceid=ID:id", 
        "tag": "article", "class": "detail-article", "butuh_page_all": False
    },
    "Kontan Investasi": {
        "rss": "https://news.google.com/rss/search?q=site:investasi.kontan.co.id&hl=id&gl=ID&ceid=ID:id", 
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
        "rss": "https://www.idxchannel.com/rss", 
        "tag": "div", "class": "detail-text", "butuh_page_all": False
    },
    "IDX Channel (Market News)": {
        "rss": "https://news.google.com/rss/search?q=site:idxchannel.com/market-news&hl=id&gl=ID&ceid=ID:id", 
        "tag": "div", "class": "detail-text", "butuh_page_all": False
    },
    "Detik Finance": {
        "rss": "https://news.google.com/rss/search?q=site:finance.detik.com&hl=id&gl=ID&ceid=ID:id", 
        "tag": "div", "class": "detail__body-text", "butuh_page_all": True
    },
    "Detik News": {
        "rss": "https://news.google.com/rss/search?q=site:news.detik.com&hl=id&gl=ID&ceid=ID:id", 
        "tag": "div", "class": "detail__body-text", "butuh_page_all": True
    }
}

kata_kunci_portofolio = [kw for sublist in KATEGORI_PORTOFOLIO.values() for kw in sublist]

# ==========================================
# STREAMLIT UI & SIDEBAR
# ==========================================
st.set_page_config(page_title="Radar Investasi Multi", layout="wide", initial_sidebar_state="expanded")

# --- SIDEBAR TERSTRUKTUR ---
st.sidebar.title("⚙️ Pengaturan Radar")

semua_portal_keys = list(aturan_portal.keys())

with st.sidebar.expander("🌐 Pilih Portal & Rentang Waktu", expanded=True):
    # 1. Ubah value menjadi True agar otomatis tercentang default
    pilih_semua = st.checkbox("✅ Pilih Semua Portal / Kanal", value=True)
    
    default_terpilih = semua_portal_keys if pilih_semua else [
        "IDNFinancials",
        "CNBC Indonesia (Market)", 
        "CNBC Indonesia (News)",
        "Investor.id (Market)",
        "Kontan Investasi",
        "IDX Channel (Market News)" 
    ]

    portal_terpilih = st.multiselect(
        "Kanal Berita Terpilih:",
        options=semua_portal_keys,
        default=default_terpilih
    )

    pilihan_rentang = st.selectbox(
        "📅 Rentang Waktu Berita:",
        options=[
            "3 Jam Terakhir",
            "6 Jam Terakhir",
            "24 Jam Terakhir (1 Hari)",
            "3 Hari Terakhir",
            "7 Hari Terakhir",
            "Semua Berita (Tanpa Batas)"
        ],
        # 2. Ubah index menjadi 1 karena "6 Jam Terakhir" berada di urutan indeks ke-1 (mulai dari 0)
        index=1
    )

map_jam = {
    "3 Jam Terakhir": 3,
    "6 Jam Terakhir": 6,
    "24 Jam Terakhir (1 Hari)": 24,
    "3 Hari Terakhir": 72,
    "7 Hari Terakhir": 168,
    "Semua Berita (Tanpa Batas)": 87600
}
jam_filter = map_jam[pilihan_rentang]

with st.sidebar.expander("⚡ Performa & Scraping", expanded=False):
    aktifkan_deduplikasi = st.checkbox("🚫 Perketat Anti-Duplikat (Scraping Cepat)", value=True)
    ambang_duplikat = st.slider(
        "Ambang Kemiripan Judul (Deduplikasi):", 
        min_value=0.50, max_value=0.95, value=0.75, step=0.05,
        help="Semakin rendah nilainya, semakin ketat sistem menghapus berita yang mirip."
    )

with st.sidebar.expander("🤖 Notifikasi Bot Telegram", expanded=False):
    aktifkan_telegram = st.checkbox("Kirim Alert Otomatis ke Telegram", value=True)
    bot_token = st.text_input("Bot Token Telegram:", value="", type="password", help="Dapatkan dari @BotFather")
    chat_id = st.text_input("Chat ID Telegram:", value="", help="Dapatkan dari @userinfobot")

with st.sidebar.expander("🏥 Status Kesehatan Portal", expanded=False):
    if st.button("🌐 Cek Koneksi Portal Sekarang", use_container_width=True):
        st.markdown("##### Hasil Tes Respon RSS:")
        for p_name in portal_terpilih:
            t0 = time.time()
            f_check = dapatkan_feed_rss(aturan_portal[p_name]["rss"])
            lat = round((time.time() - t0) * 1000, 0)
            if f_check and hasattr(f_check, 'entries') and len(f_check.entries) > 0:
                st.success(f"🟢 **{p_name}**: Online ({lat}ms)")
            else:
                st.error(f"🔴 **{p_name}**: Offline / Timeout")

# --- HERO SECTION & HEADER ---
st.title("📈 Radar Berita Portofolio Multi-Portal")
st.markdown("##### *Monitoring Real-time Emiten, ETF, Reksadana, Emas, Regulasi & Sentimen Pasar*")

# --- MODERNISED TARGET PORTOFOLIO SECTION ---
with st.expander("🔍 Target Pemantauan Portofolio Aktif", expanded=False):
    st.caption("Sistem memantau kata kunci berikut secara otomatis pada RSS Feed & Artikel berita:")
    
    st.markdown("""
        <style>
            .badge-tag {
                display: inline-block;
                background-color: #f0f2f6;
                color: #31333f;
                padding: 4px 10px;
                border-radius: 12px;
                margin: 3px 2px;
                font-size: 0.82em;
                font-weight: 500;
                border: 1px solid #d6d8db;
            }
        </style>
    """, unsafe_allow_html=True)
    
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    with col_k1:
        st.markdown("**📈 Saham & Sektor**")
        saham_kw = KATEGORI_PORTOFOLIO.get("SAHAM_EMITEN", []) + KATEGORI_PORTOFOLIO.get("SEKTOR_SAHAM", [])
        badges_saham = "".join([f'<span class="badge-tag">{kw.upper()}</span>' for kw in saham_kw[:10]])
        st.markdown(badges_saham, unsafe_allow_html=True)
        if len(saham_kw) > 10:
            st.caption(f"+{len(saham_kw)-10} kata kunci lainnya")

    with col_k2:
        st.markdown("**📊 ETF & Reksadana**")
        reksa_kw = KATEGORI_PORTOFOLIO.get("ETF", []) + KATEGORI_PORTOFOLIO.get("REKSADANA", [])
        badges_reksa = "".join([f'<span class="badge-tag">{kw.upper()}</span>' for kw in reksa_kw[:10]])
        st.markdown(badges_reksa, unsafe_allow_html=True)
        if len(reksa_kw) > 10:
            st.caption(f"+{len(reksa_kw)-10} kata kunci lainnya")

    with col_k3:
        st.markdown("**🥇 Emas & Komoditas**")
        emas_kw = KATEGORI_PORTOFOLIO.get("EMAS", []) + KATEGORI_PORTOFOLIO.get("KOMODITAS", [])
        badges_emas = "".join([f'<span class="badge-tag">{kw.upper()}</span>' for kw in emas_kw])
        st.markdown(badges_emas, unsafe_allow_html=True)

    with col_k4:
        st.markdown("**🏦 Makro & Regulasi**")
        makro_kw = KATEGORI_PORTOFOLIO.get("MAKRO_INDONESIA", []) + KATEGORI_PORTOFOLIO.get("MAKRO_GLOBAL", []) + KATEGORI_PORTOFOLIO.get("REGULASI", [])
        badges_makro = "".join([f'<span class="badge-tag">{kw.upper()}</span>' for kw in makro_kw[:10]])
        st.markdown(badges_makro, unsafe_allow_html=True)
        if len(makro_kw) > 10:
            st.caption(f"+{len(makro_kw)-10} kata kunci lainnya")

st.markdown("---")

# --- PANEL PEMANTAU KESEHATAN PORTAL (HEALTH CHECK) ---
with st.expander("🏥 Dashboard Kesehatan & Status Portal (Health Check)", expanded=False):
    st.caption("Memeriksa status koneksi, latensi, dan potensi error/timeout pada portal yang dipilih:")
    if st.button("🔍 Jalankan Cek Kesehatan Portal Sekarang", use_container_width=True):
        with st.spinner("Sedang memeriksa koneksi server portal..."):
            df_sehat = cek_kesehatan_semua_portal(portal_terpilih, aturan_portal)
            st.dataframe(df_sehat, use_container_width=True, hide_index=True)

st.markdown("---")

# --- EXECUTION BUTTON ---
if st.button("🚀 Mulai Pemindaian Radar Multi-Portal!", type="primary", use_container_width=True):
    
    if len(portal_terpilih) == 0:
        st.warning("⚠️ Silakan pilih minimal satu portal/kanal berita di sidebar terlebih dahulu.")
    else:
        kumpulan_data_global = []
        daftar_tersimpan = []
        jumlah_duplikat_dilewati = 0
        
        status_teks = st.empty()
        timer_container = st.empty()
        progress_bar = st.progress(0)
        
        start_time = time.time()
        total_portal = len(portal_terpilih)
        
        # LOGIKA PEMINDAIAN
        for idx, nama_portal in enumerate(portal_terpilih):
            elapsed_time = round(time.time() - start_time, 1)
            timer_container.info(f"⏱️ **Waktu Proses:** `{elapsed_time} detik` | 🔍 Memindai: **{nama_portal}** ({idx+1}/{total_portal})")
            
            aturan = aturan_portal[nama_portal]
            feed = dapatkan_feed_rss(aturan["rss"])
            
            if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                for entry in feed.entries:
                    elapsed_time = round(time.time() - start_time, 1)
                    timer_container.info(f"⏱️ **Waktu Proses:** `{elapsed_time} detik` | 🔍 Memindai: **{nama_portal}** ({idx+1}/{total_portal})")
                    
                    judul = entry.get('title', 'N/A')
                    link = entry.get('link', 'N/A')
                    tanggal = entry.get('published', 'N/A')
                    deskripsi = entry.get('summary', '') + " " + entry.get('description', '')
                    
                    # 1. Cek Waktu
                    if not apakah_dalam_rentang(tanggal, jam_filter):
                        continue
                    
                    # 2. Perluas Pencocokan Kata Kunci (Menggunakan Regex)
                    teks_pencocokan = (judul + " " + deskripsi).lower()
                    cocok = False
                    trigger_terdeteksi = "UMUM"
                    
                    for kunci in kata_kunci_portofolio:
                        if re.search(rf'\b{re.escape(kunci)}\b', teks_pencocokan):
                            cocok = True
                            trigger_terdeteksi = kunci.upper()
                            break 
                            
                    if not cocok:
                        continue 
                    
                    # 3. Cek Duplikat dengan Filter Cerdas & Slider Ambang Batas
                    if aktifkan_deduplikasi and apakah_duplikat(judul, link, daftar_tersimpan, ambang_duplikat):
                        jumlah_duplikat_dilewati += 1
                        continue
                    
                    # 4. Ambil Konten Berita
                    isi, status_akses = ambil_isi_berita(link, aturan["tag"], aturan["class"], aturan["butuh_page_all"])
                    sentimen_label = analisa_sentimen(judul + " " + isi)
                    ringkasan_teks = ringkas_teks(isi, kata_kunci_portofolio, max_kalimat=2)
                    kategori_aset = tentukan_kategori_aset(teks_pencocokan)
                    
                    dt_obj = konversi_ke_datetime(tanggal)
                    status_bursa_val = cek_status_bursa(dt_obj)
                    
                    kumpulan_data_global.append({
                        "Sumber": nama_portal,
                        "Kategori Aset": kategori_aset,
                        "Trigger/Emiten": trigger_terdeteksi,
                        "Sentimen": sentimen_label,
                        "Status Bursa": status_bursa_val,
                        "Akses": status_akses,
                        "Judul": judul,
                        "Tanggal": tanggal,
                        "dt_sort": dt_obj,
                        "Ringkasan Berita": ringkasan_teks,
                        "Link": link,
                        "Isi Berita": isi
                    })
                    
                    # Simpan data ke riwayat deduplikasi
                    daftar_tersimpan.append({
                        "link": link,
                        "judul_bersih": bersihkan_judul(judul)
                    })
                    
                    time.sleep(0.3) 
            else:
                st.error(f"Gagal membaca RSS dari {nama_portal}.")
                
            progress_bar.progress((idx + 1) / total_portal)
        
        duration = round(time.time() - start_time, 2)
        timer_container.empty()
        
        if len(kumpulan_data_global) > 0:
            pesan_sukses = f"🎉 **Radar Selesai dalam {duration} detik!** Menemukan **{len(kumpulan_data_global)}** berita unik ({pilihan_rentang}) dari {total_portal} portal/kanal."
            if aktifkan_deduplikasi and jumlah_duplikat_dilewati > 0:
                pesan_sukses += f" *(Berhasil melewati {jumlah_duplikat_dilewati} berita duplikat sebelum scraping)*."
                
            st.success(pesan_sukses)
            
            df = pd.DataFrame(kumpulan_data_global)
            df = df.sort_values(by='dt_sort', ascending=False).reset_index(drop=True)
            
            # --- EKSEKUSI KIRIM TELEGRAM ALERT PER KATEGORI ---
            if aktifkan_telegram:
                df_alert = df.copy()
                
                if not df_alert.empty:
                    waktu_sekarang = datetime.now().strftime("%d-%m-%Y %H:%M WIB")
                    
                    pesan_header = f"🚨 RADAR BERITA PORTOFOLIO\n"
                    pesan_header += f"📅 Update: {waktu_sekarang} ({pilihan_rentang})\n"
                    pesan_header += f"📊 Total Berita Ditemukan: {len(df_alert)} Artikel\n"
                    pesan_header += "==================================\n"
                    
                    status_hdr, err_hdr = kirim_notifikasi_telegram(bot_token, chat_id, pesan_header)
                    if not status_hdr:
                        st.error(f"⚠️ Gagal mengirim Header ke Telegram: {err_hdr}")
                    
                    kategori_map = {
                        "SAHAM": "📈 KATEGORI: SAHAM EMITEN",
                        "REKSADANA_ETF": "📊 KATEGORI: REKSADANA & ETF",
                        "EMAS_KOMODITAS": "🥇 KATEGORI: EMAS & KOMODITAS",
                        "MAKRO_REGULASI": "🏦 KATEGORI: MAKRO & REGULASI"
                    }
                    
                    for kat_key, kat_title in kategori_map.items():
                        df_kat = df_alert[df_alert['Kategori Aset'] == kat_key]
                        
                        if not df_kat.empty:
                            pesan_kategori = f"{kat_title} ({len(df_kat)} Berita)\n"
                            pesan_kategori += "----------------------------------\n\n"
                            
                            no = 1
                            for _, r in df_kat.iterrows():
                                item_text = f"{no}. [{r['Trigger/Emiten']}] {r['Sentimen']} | {r['Status Bursa']}\n"
                                item_text += f"   📰 {r['Judul']}\n"
                                item_text += f"   ⏱️ {r['Tanggal']}\n"
                                item_text += f"   💡 Ringkasan: {r['Ringkasan Berita']}\n"
                                item_text += f"   🔗 Link: {r['Link']}\n\n"
                                
                                if len(pesan_kategori) + len(item_text) > 3800:
                                    kirim_notifikasi_telegram(bot_token, chat_id, pesan_kategori)
                                    pesan_kategori = f"{kat_title} (Lanjutan)\n----------------------------------\n\n"
                                
                                pesan_kategori += item_text
                                no += 1
                            
                            st_msg, msg_err = kirim_notifikasi_telegram(bot_token, chat_id, pesan_kategori)
                            if not st_msg:
                                st.warning(f"⚠️ Gagal kirim kategori {kat_key}: {msg_err}")
                            time.sleep(0.5)
                            
                    st.toast(f"📲 Laporan berhasil diproses ke Telegram!", icon="✅")
                else:
                    st.info("ℹ️ Tidak ada berita yang memuat kata kunci portofoliomu saat ini.")

            # ==========================================
            # DASHBOARD METRIC CARDS & MARKET SENTIMENT INDEX
            # ==========================================
            st.markdown("### 📊 Ringkasan Eksekutif")
            
            n_pos = len(df[df['Sentimen'] == 'POSITIF 🟢'])
            n_neg = len(df[df['Sentimen'] == 'NEGATIF 🔴'])
            total_sentimen_non_netral = n_pos + n_neg
            
            if total_sentimen_non_netral > 0:
                skor_indeks = round((n_pos / total_sentimen_non_netral) * 100, 1)
            else:
                skor_indeks = 50.0

            if skor_indeks >= 70:
                label_indeks = "🟢 Sangat Positif (Bullish)"
                penjelasan_indeks = "Pasar didominasi oleh sentimen positif. Kondisi sangat kondusif bagi portofolio."
            elif skor_indeks >= 55:
                label_indeks = "🟢 Cenderung Positif"
                penjelasan_indeks = "Sentimen positif memimpin secara proporsional dibanding berita negatif."
            elif skor_indeks >= 45:
                label_indeks = "⚪ Netral / Seimbang"
                penjelasan_indeks = "Volume berita positif dan negatif seimbang. Pasar dalam kondisi cenderung konsolidasi."
            elif skor_indeks >= 30:
                label_indeks = "🔴 Cenderung Negatif"
                penjelasan_indeks = "Sentimen negatif mulai mendominasi. Diperlukan kehati-hatian pada emiten terkait."
            else:
                label_indeks = "🔴 Sangat Negatif (Bearish)"
                penjelasan_indeks = "Kepanikan/berita buruk mendominasi. Waspadai risiko tinggi pada portofolio."

            with st.container():
                st.markdown(f"#### 🎯 Indeks Sentimen Pasar: **{skor_indeks}%** — *{label_indeks}*")
                st.progress(int(skor_indeks))
                st.caption(f"💡 {penjelasan_indeks}")
                st.markdown("<br>", unsafe_allow_html=True)

            with st.container():
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("📰 Total Berita Unik", f"{len(df)} Artikel")
                m2.metric("🟢 Sentimen Positif", f"{n_pos} Berita")
                m3.metric("🔴 Sentimen Negatif", f"{n_neg} Berita")
                m4.metric("⏱️ Waktu Pemindaian", f"{duration} Detik")

            st.markdown("<br>", unsafe_allow_html=True)

            # ==========================================
            # ANALISIS SUMBER MEDIA & DISTRIBUSI PORTAL
            # ==========================================
            st.subheader("📰 Analisis Sumber Portal Berita")
            st.caption("Menganalisis dominasi media (Share of Voice) dan kecenderungan sentimen (Media Bias) dari portal yang dipindai.")
            
            col_portal1, col_portal2 = st.columns([1.2, 1.8])
            
            with col_portal1:
                st.markdown("**Porsi Distribusi Portal (Share of Voice)**")
                distribusi_portal = df['Sumber'].value_counts()
                
                fig_donut, ax_donut = plt.subplots(figsize=(6, 6))
                ax_donut.pie(distribusi_portal, labels=distribusi_portal.index, autopct='%1.1f%%', startangle=140, 
                             colors=plt.cm.tab20.colors, wedgeprops=dict(width=0.4, edgecolor='w'))
                ax_donut.axis('equal')
                
                for text in ax_donut.texts:
                    text.set_fontsize(9)
                st.pyplot(fig_donut)
                
            with col_portal2:
                st.markdown("**Peta Sentimen per Media (Media Bias Analyzer)**")
                sentimen_media = df.groupby(['Sumber', 'Sentimen']).size().unstack(fill_value=0)
                
                for col in ['POSITIF 🟢', 'NEGATIF 🔴', 'NETRAL ⚪']:
                    if col not in sentimen_media.columns:
                        sentimen_media[col] = 0
                        
                sentimen_media = sentimen_media[['POSITIF 🟢', 'NEGATIF 🔴', 'NETRAL ⚪']]
                sentimen_media['Total'] = sentimen_media.sum(axis=1)
                sentimen_media = sentimen_media.sort_values(by='Total', ascending=False).drop(columns=['Total'])
                
                try:
                    st.bar_chart(sentimen_media, color=["#28a745", "#dc3545", "#adb5bd"], height=350, use_container_width=True)
                except TypeError:
                    st.bar_chart(sentimen_media, height=350, use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)

            # ==========================================
            # LEADERBOARD PORTAL & ECHO CHAMBER ALERT
            # ==========================================
            col_lead, col_alert = st.columns([1.5, 1.5])
            
            with col_lead:
                st.markdown("**🏆 Leaderboard Portal Paling Aktif**")
                st.caption("Peringkat sumber berita berdasarkan volume, keterbukaan akses, dan dominasi sentimen.")
                
                portal_summary = df.groupby('Sumber').agg(
                    Total_Berita=('Judul', 'count'),
                    Artikel_Premium=('Akses', lambda x: sum(x.str.contains('🔒', na=False)))
                ).reset_index()
                
                dom_sent = df.groupby('Sumber')['Sentimen'].agg(lambda x: x.mode()[0] if not x.mode().empty else 'NETRAL ⚪').reset_index()
                
                portal_summary = portal_summary.merge(dom_sent, on='Sumber')
                portal_summary.columns = ['Nama Portal', 'Total Berita', 'Artikel Terkunci (Paywall)', 'Sentimen Dominan']
                portal_summary = portal_summary.sort_values(by='Total Berita', ascending=False).reset_index(drop=True)
                
                st.dataframe(portal_summary, use_container_width=True, hide_index=True)

            with col_alert:
                st.markdown("**🚨 Peringatan 'Satu Suara' (Echo Chamber Alert)**")
                st.caption("Mendeteksi jika pemberitaan suatu emiten/aset didominasi oleh satu media (>80%).")
                
                echo_chamber_alerts = []
                
                for emiten, group in df.groupby('Trigger/Emiten'):
                    total_emiten_news = len(group)
                    
                    if total_emiten_news >= 3: 
                        sumber_terbanyak = group['Sumber'].value_counts().head(1)
                        nama_sumber = sumber_terbanyak.index[0]
                        jumlah_sumber = sumber_terbanyak.values[0]
                        persentase = (jumlah_sumber / total_emiten_news) * 100
                        
                        if persentase >= 80:
                            echo_chamber_alerts.append(
                                f"• **{emiten}**: **{persentase:.0f}%** berita hanya bersumber dari **{nama_sumber}** ({jumlah_sumber} dari {total_emiten_news} artikel)."
                            )
                
                if echo_chamber_alerts:
                    st.warning("⚠️ **Perhatian! Ditemukan potensi bias informasi pada aset berikut:**\n\n" + "\n".join(echo_chamber_alerts))
                else:
                    st.success("✅ **Distribusi Informasi Sehat:** Tidak terdeteksi adanya dominasi narasi tunggal (Echo Chamber) yang berlebihan (>80%) dari satu portal pada seluruh pantauan.")
                    
            st.markdown("---")

            st.markdown("<br>", unsafe_allow_html=True)
            col_v1, col_v2 = st.columns(2)
            
            with col_v1:
                df_valid_time = df[df['dt_sort'] != datetime.min]
                if not df_valid_time.empty:
                    rentang_jam_aktual = (datetime.now() - df_valid_time['dt_sort'].min()).total_seconds() / 3600
                    rentang_jam_aktual = max(rentang_jam_aktual, 1)
                    velocity = round(len(df) / rentang_jam_aktual, 1)
                else:
                    velocity = 0.0
                
                if velocity > 5:
                    status_velocity = "🔥 Tinggi (Pasar Agresif / Banyak Rilis Berita)"
                elif velocity > 2:
                    status_velocity = "⚡ Sedang (Aktivitas Berita Normal)"
                else:
                    status_velocity = "☕ Rendah (Pasar Cenderung Tenang)"
                    
                st.metric("⚡ Indeks Kecepatan Berita (Velocity)", f"{velocity} Berita/Jam", status_velocity)
                
            with col_v2:
                total_berita_all = len(df)
                if total_berita_all > 0:
                    persen_negatif = round((n_neg / total_berita_all) * 100, 1)
                else:
                    persen_negatif = 0.0
                    
                if persen_negatif >= 40:
                    risk_label = "🔴 Risiko Tinggi (Waspada Tekanan Jual)"
                elif persen_negatif >= 20:
                    risk_label = "🟡 Risiko Menengah (Perhatikan Emiten Terkait)"
                else:
                    risk_label = "🟢 Risiko Rendah (Kondisi Relatif Aman)"
                    
                st.metric("🛡️ Skor Risiko Portofolio", f"{persen_negatif}% Sentimen Negatif", risk_label)

            # ==========================================
            # TOP KEY CATEGORY BREAKDOWN
            # ==========================================
            st.subheader("📌 Kategori Paling Vokal & Analisis Risiko (Top Key Category Breakdown)")
            st.caption("Pemetaan tingkat kerawanan dan dominasi pemberitaan per kelompok aset:")

            kat_dict = {
                "SAHAM": "📈 Saham Emiten",
                "REKSADANA_ETF": "📊 ETF & Reksadana",
                "EMAS_KOMODITAS": "🥇 Emas & Komoditas",
                "MAKRO_REGULASI": "🏦 Makro & Regulasi"
            }

            breakdown_list = []
            for k_code, k_nama in kat_dict.items():
                sub_df = df[df['Kategori Aset'] == k_code]
                total_k = len(sub_df)
                pos_k = len(sub_df[sub_df['Sentimen'] == 'POSITIF 🟢'])
                neg_k = len(sub_df[sub_df['Sentimen'] == 'NEGATIF 🔴'])
                net_k = len(sub_df[sub_df['Sentimen'] == 'NETRAL ⚪'])
                
                if total_k > 0:
                    if neg_k > pos_k:
                        status_k = "🔴 RAWAN (Risiko Tinggi)"
                    elif pos_k > neg_k:
                        status_k = "🟢 KONDUSIF (Positif)"
                    else:
                        status_k = "⚪ NETRAL / STABIL"
                else:
                    status_k = "⚪ TIDAK ADA BERITA"

                breakdown_list.append({
                    "Kelompok Aset": k_nama,
                    "Total Berita": total_k,
                    "Positif 🟢": pos_k,
                    "Negatif 🔴": neg_k,
                    "Netral ⚪": net_k,
                    "Status Kerawanan": status_k
                })

            df_breakdown = pd.DataFrame(breakdown_list)
            df_breakdown = df_breakdown.sort_values(by="Total Berita", ascending=False).reset_index(drop=True)

            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            cols_map = [col_b1, col_b2, col_b3, col_b4]

            for i, row_b in df_breakdown.iterrows():
                with cols_map[i]:
                    st.markdown(f"##### {row_b['Kelompok Aset']}")
                    st.markdown(f"**Total:** `{row_b['Total Berita']} Berita`")
                    st.write(f"🟢 Positif: **{row_b['Positif 🟢']}** | 🔴 Negatif: **{row_b['Negatif 🔴']}**")
                    st.markdown(f"**Status:** {row_b['Status Kerawanan']}")

            st.markdown("---")

            # ==========================================
            # RASIO SENTIMEN, EMITEN BERISIK & SECTOR HOTSPOT
            # ==========================================
            st.markdown("<br>", unsafe_allow_html=True)
            col_extra1, col_extra2, col_extra3 = st.columns(3)
            
            with col_extra1:
                if n_neg > 0:
                    rasio_val = round(n_pos / n_neg, 1)
                    rasio_str = f"{rasio_val} : 1"
                else:
                    rasio_str = f"{n_pos} : 0 (Tanpa Negatif)" if n_pos > 0 else "0 : 0"
                
                if n_pos >= n_neg:
                    rasio_desc = "🟢 Dominasi Bullish"
                else:
                    rasio_desc = "🔴 Dominasi Bearish"
                    
                st.metric("⚖️ Rasio Sentimen (Positif : Negatif)", rasio_str, rasio_desc)
                
            with col_extra2:
                df_emiten_saja = df[df['Trigger/Emiten'] != 'UMUM']
                if not df_emiten_saja.empty:
                    top_emiten = df_emiten_saja['Trigger/Emiten'].value_counts().idxmax()
                    jumlah_top = df_emiten_saja['Trigger/Emiten'].value_counts().max()
                    sub_emiten_df = df_emiten_saja[df_emiten_saja['Trigger/Emiten'] == top_emiten]
                    sentimen_top = sub_emiten_df['Sentimen'].mode()[0] if not sub_emiten_df['Sentimen'].mode().empty else "NETRAL"
                    
                    emiten_display = f"{top_emiten} ({jumlah_top} Berita)"
                    emiten_status = f"Dominan: {sentimen_top}"
                else:
                    emiten_display = "Tidak Ada Data Emiten"
                    emiten_status = "Fokus Berita Makro/Umum"
                    
                st.metric("🚨 Emiten Paling 'Berisik'", emiten_display, emiten_status)
                
            with col_extra3:
                if not df['Kategori Aset'].empty:
                    top_kategori = df['Kategori Aset'].value_counts().idxmax()
                    jumlah_kat = df['Kategori Aset'].value_counts().max()
                    
                    label_kat_map = {
                        "SAHAM": "📈 Saham Emiten",
                        "REKSADANA_ETF": "📊 Reksadana & ETF",
                        "EMAS_KOMODITAS": "🥇 Emas & Komoditas",
                        "MAKRO_REGULASI": "🏦 Makro & Regulasi"
                    }
                    nama_hotspot = label_kat_map.get(top_kategori, top_kategori)
                else:
                    nama_hotspot = "N/A"
                    jumlah_kat = 0
                    
                st.metric("🗂️ Indeks Kategori Terpanas", nama_hotspot, f"{jumlah_kat} Artikel Terindeks")

            # ==========================================
            # GRAFIK TREN WAKTU BERITA (HOURLY SPIKE CHART)
            # ==========================================
            st.subheader("📈 Tren Volume Berita per Jam (Hourly Spike Chart)")
            st.caption("Memetakan lonjakan jumlah publikasi berita berdasarkan jam untuk memantau waktu kepanikan atau rilis info penting:")
            
            df_chart = df.copy()
            df_chart_valid = df_chart[df_chart['dt_sort'] != datetime.min].copy()
            
            if not df_chart_valid.empty:
                df_chart_valid['Jam'] = df_chart_valid['dt_sort'].dt.strftime('%H:00')
                tren_jam = df_chart_valid.groupby('Jam').size().reset_index(name='Jumlah Berita')
                tren_jam = tren_jam.sort_values(by='Jam')
                
                st.line_chart(
                    data=tren_jam.set_index('Jam'),
                    use_container_width=True
                )
            else:
                st.info("Format tanggal berita tidak memuat informasi jam yang valid untuk membuat grafik tren.")

            st.markdown("---")
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("🔥 Top Trigger / Emiten")
                counts_emiten = df['Trigger/Emiten'].value_counts()
                st.bar_chart(counts_emiten)
                
            with col_chart2:
                st.subheader("🎭 Distribusi Sentimen Pasar")
                counts_sentimen = df['Sentimen'].value_counts()
                st.bar_chart(counts_sentimen)
                
            st.markdown("---")

            # ==========================================
            # WORD CLOUD & TREND ANALYZER
            # ==========================================
            st.markdown("### ☁️ Analisis Tren Kata Kunci Berita Hari Ini")
            
            gabungan_teks = " ".join(df['Judul'].tolist() + df['Ringkasan Berita'].tolist()).lower()
            kata_kata = re.findall(r'\b[a-z]{3,}\b', gabungan_teks)
            kata_bersih = [k for k in kata_kata if k not in STOPWORDS_ID]
            
            col_wc1, col_wc2 = st.columns(2)
            
            with col_wc1:
                st.subheader("Visual Word Cloud")
                if kata_bersih:
                    wc = WordCloud(width=600, height=350, background_color='white', colormap='Blues').generate(" ".join(kata_bersih))
                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.imshow(wc, interpolation='bilinear')
                    ax.axis("off")
                    st.pyplot(fig)
                else:
                    st.info("Data kata belum cukup untuk membuat Word Cloud.")
                    
            with col_wc2:
                st.subheader("Top 10 Kata Paling Sering Muncul")
                counter = Counter(kata_bersih)
                top_10 = pd.DataFrame(counter.most_common(10), columns=['Kata/Topik', 'Frekuensi'])
                st.bar_chart(top_10.set_index('Kata/Topik'))

            st.markdown("---")

            df_display = df.drop(columns=['dt_sort'])

            # ==========================================
            # TAB VIEW TERPISAH PER KATEGORI ASET (DIBUNGKUS EXPANDER)
            # ==========================================
            with st.expander("### 📋 Detail Data Berita per Kategori Aset", expanded=True):
                col_fltr1, col_fltr2 = st.columns([1, 2])
                with col_fltr1:
                    hanya_negatif = st.checkbox("⚠️ Tampilkan Hanya Berita Negatif (Fokus Risiko)", value=False)

                df_tampil = df_display[df_display['Sentimen'] == 'NEGATIF 🔴'] if hanya_negatif else df_display

                if hanya_negatif and df_tampil.empty:
                    st.info("🎉 Aman! Tidak ada berita bersentimen negatif yang ditemukan saat ini.")

                def tampilkan_konten_tab(df_sub):
                    if df_sub.empty:
                        st.info("Tidak ada berita yang sesuai dengan kriteria kategori ini.")
                        return
                    
                    for _, r in df_sub.iterrows():
                        with st.container():
                            badge_s = render_badge_sentimen(r['Sentimen'])
                            badge_b = render_badge_bursa(r['Status Bursa'])
                            
                            st.markdown(
                                f"**[{r['Trigger/Emiten']}]** &nbsp; {badge_s} &nbsp; {badge_b} &nbsp; "
                                f"<small style='color: gray;'>📰 {r['Sumber']} | ⏱️ {r['Tanggal']}</small>", 
                                unsafe_allow_html=True
                            )
                            st.markdown(f"#### [{r['Judul']}]({r['Link']})")
                            st.write(f"💡 **Ringkasan:** {r['Ringkasan Berita']}")
                            
                            with st.expander("📄 Baca Isi Berita Lengkap"):
                                st.write(r['Isi Berita'])
                            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

                tab_semua, tab_saham, tab_reksa_etf, tab_emas, tab_makro = st.tabs([
                    "🌐 Semua Berita", 
                    "📈 Saham Emiten", 
                    "📊 ETF & Reksadana", 
                    "🥇 Emas & Komoditas", 
                    "🏦 Makro & Regulasi"
                ])
                
                with tab_semua:
                    tampilkan_konten_tab(df_tampil)
                    
                with tab_saham:
                    tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'SAHAM'])
                        
                with tab_reksa_etf:
                    tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'REKSADANA_ETF'])
                        
                with tab_emas:
                    tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'EMAS_KOMODITAS'])
                        
                with tab_makro:
                    tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'MAKRO_REGULASI'])

                df_csv = df_tampil[['Judul', 'Tanggal', 'Kategori Aset', 'Sentimen', 'Status Bursa', 'Akses', 'Ringkasan Berita', 'Isi Berita']]
                csv_data = df_csv.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Unduh CSV Ringkas",
                    data=csv_data,
                    file_name='laporan_berita_ringkas.csv',
                    mime='text/csv',
                    use_container_width=True
                )

            st.markdown("---")

            # ==========================================
            # LAPORAN RINGKAS SIAP KIRIM (DIBUNGKUS EXPANDER)
            # ==========================================
            with st.expander("### 📝 Ringkasan Teks Siap Kirim", expanded=True):
                st.caption("Gunakan tombol salin di pojok kanan atas kotak kode di bawah atau unduh sebagai dokumen teks (.txt):")

                waktu_sekarang = datetime.now().strftime("%d-%m-%Y %H:%M WIB")
                teks_laporan = f"📌 *RADAR BERITA PORTOFOLIO*\n"
                teks_laporan += f"📅 {waktu_sekarang} | 🎯 Indeks: {skor_indeks}%\n"
                teks_laporan += f"📊 Total Berita: {len(df_tampil)} Artikel\n"
                teks_laporan += "----------------------------------------\n\n"

                for i, row in df_tampil.reset_index(drop=True).iterrows():
                    judul_clean = re.sub(r'\s+', ' ', row['Judul']).strip()
                    ringkasan_clean = re.sub(r'\s+', ' ', row['Ringkasan Berita']).strip()
                    
                    link_asli = row['Link']
                    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', link_asli)
                    domain_pendek = domain_match.group(1) if domain_match else "Link Berita"
                    
                    teks_laporan += f"{i+1}. *{row['Trigger/Emiten']}* ({row['Sentimen']})\n"
                    teks_laporan += f"   📰 {judul_clean}\n"
                    teks_laporan += f"   💡 _{ringkasan_clean}_\n"
                    teks_laporan += f"   🔗 [Baca via {domain_pendek}]({link_asli})\n\n"

                # Menampilkan teks dalam blok kode yang memiliki tombol salin bawaan (*Copy to Clipboard*)
                st.code(teks_laporan, language="markdown")

                # Tombol unduh dokumen teks (.txt)
                st.download_button(
                    label="📥 Unduh Ringkasan sebagai Dokumen Teks (.txt)",
                    data=teks_laporan,
                    file_name=f"ringkasan_radar_investasi_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        else:
            st.warning(f"Belum ada berita yang memuat kata kuncimu dalam rentang waktu **{pilihan_rentang}** saat ini.")