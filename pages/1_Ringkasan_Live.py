import streamlit as st
import pandas as pd
import re
from datetime import datetime
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt

st.set_page_config(page_title="Ringkasan Live Radar", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
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
    </style>
""", unsafe_allow_html=True)

st.title("Ringkasan Eksekutif & Live Radar")
st.markdown("##### *Monitoring Kondisi Pasar, Indeks Sentimen, Tren Waktu & Analisis Kata Kunci*")
st.markdown("---")

df = st.session_state.get('df_hasil', None)
duration = st.session_state.get('duration_scan', 0)
skor_indeks = st.session_state.get('skor_indeks_val', 50.0)

STOPWORDS_ID = set(["yang", "di", "dan", "dengan", "untuk", "pada", "ke", "karena", "oleh", "dari", "ini", "itu", "akan", "juga", "atau", "bisa", "tidak", "ada", "seperti", "tahun", "saat", "menjadi", "lebih", "hari", "secara", "sudah", "dapat", "tersebut", "persen", "rp", "juta", "miliar", "triliun", "sebesar", "mencapai", "catat", "hingga"])

if df is None or df.empty:
    st.warning("Belum ada data pemindaian. Silakan jalankan pemindaian dari menu utama terlebih dahulu.")
else:
    n_pos = len(df[df['Sentimen'] == 'POSITIF'])
    n_neg = len(df[df['Sentimen'] == 'NEGATIF'])

    if skor_indeks >= 70: label_indeks, pen = "Sangat Positif (Bullish)", "Pasar didominasi sentimen positif."
    elif skor_indeks >= 55: label_indeks, pen = "Cenderung Positif", "Sentimen positif memimpin secara proporsional."
    elif skor_indeks >= 45: label_indeks, pen = "Netral / Seimbang", "Volume berita positif dan negatif seimbang."
    elif skor_indeks >= 30: label_indeks, pen = "Cenderung Negatif", "Sentimen negatif mulai mendominasi."
    else: label_indeks, pen = "Sangat Negatif (Bearish)", "Kepanikan mendominasi pasar."

    st.markdown(f"#### Indeks Sentimen Pasar: **{skor_indeks}%** — *{label_indeks}*")
    st.progress(int(skor_indeks))
    st.caption(f"{pen}")
    st.markdown("<br>", unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Berita", f"{len(df)} Artikel")
    m2.metric("Positif", f"{n_pos} Berita")
    m3.metric("Negatif", f"{n_neg} Berita")
    m4.metric("Durasi Scan", f"{duration} Detik")

    col_p1, col_p2 = st.columns([1.2, 1.8])
    with col_p1:
        st.markdown("**Porsi Distribusi Portal (Share of Voice)**")
        distribusi_portal = df['Sumber'].value_counts()
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.pie(distribusi_portal, labels=distribusi_portal.index, autopct='%1.1f%%', startangle=140, colors=plt.cm.tab20.colors, wedgeprops=dict(width=0.4, edgecolor='w'))
        ax.axis('equal')
        st.pyplot(fig)
    with col_p2:
        st.markdown("**Peta Sentimen per Media (Media Bias Analyzer)**")
        sentimen_media = df.groupby(['Sumber', 'Sentimen']).size().unstack(fill_value=0)
        for col in ['POSITIF', 'NEGATIF', 'NETRAL']:
            if col not in sentimen_media.columns: sentimen_media[col] = 0
        st.bar_chart(sentimen_media[['POSITIF', 'NEGATIF', 'NETRAL']], color=["#28a745", "#dc3545", "#adb5bd"], height=320, use_container_width=True)

    st.markdown("---")
    st.subheader("Tren Volume Berita per Jam")
    df_chart_valid = df[df['dt_sort'] != datetime.min].copy()
    if not df_chart_valid.empty:
        df_chart_valid['Jam'] = df_chart_valid['dt_sort'].dt.strftime('%H:00')
        tren_jam = df_chart_valid.groupby('Jam').size().reset_index(name='Jumlah Berita')
        st.line_chart(data=tren_jam.set_index('Jam'), use_container_width=True)
    else:
        st.info("Format tanggal berita tidak memuat informasi jam yang valid.")

    st.markdown("---")
    st.subheader("Analisis Tren Kata Kunci Berita")
    gabungan_teks = " ".join(df['Judul'].tolist() + df['Ringkasan Berita'].tolist()).lower()
    kata_kata = re.findall(r'\b[a-z]{3,}\b', gabungan_teks)
    kata_bersih = [k for k in kata_kata if k not in STOPWORDS_ID]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Visual Word Cloud**")
        if kata_bersih:
            wc = WordCloud(width=500, height=300, background_color='white', colormap='Blues').generate(" ".join(kata_bersih))
            fig, ax = plt.subplots(figsize=(6, 3.5))
            ax.imshow(wc, interpolation='bilinear')
            ax.axis("off")
            st.pyplot(fig)
    with c2:
        st.markdown("**Top 10 Kata Sering Muncul**")
        if kata_bersih:
            counter = Counter(kata_bersih)
            top_10 = pd.DataFrame(counter.most_common(10), columns=['Kata', 'Frekuensi'])
            st.bar_chart(top_10.set_index('Kata'))