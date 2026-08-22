import streamlit as st
import pandas as pd
import re
from datetime import datetime
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt

st.set_page_config(page_title="Ringkasan Live Radar", layout="wide", initial_sidebar_state="expanded")

# Konfigurasi Global Matplotlib agar Selaras dengan Tema Gelap Dasbor
plt.rcParams.update({
    "text.color": "#c9d1d9",
    "axes.labelcolor": "#c9d1d9",
    "xtick.color": "#8b949e",
    "ytick.color": "#8b949e",
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "grid.color": "#30363d",
    "grid.linestyle": "--",
    "grid.alpha": 0.5
})

st.markdown("""
    <style>
        /* CSS Sidebar Asli Anda */
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

        /* UI Enhancements */
        .main-header {
            background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            padding: 2.2rem;
            border-radius: 16px;
            border: 1px solid #30363d;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .sentiment-banner {
            background: linear-gradient(135deg, #161b22 0%, #1f242c 100%);
            border-left: 6px solid #2ea043;
            padding: 1.4rem;
            border-radius: 12px;
            border: 1px solid #30363d;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .section-header {
            font-size: 1.25rem;
            font-weight: 700;
            color: #f0f6fc;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# Header Utama Executive Style
st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; color: #f0f6fc; font-size: 2.4rem; font-weight: 800; letter-spacing: -0.5px;">Ringkasan Eksekutif & Live Radar</h1>
        <p style="margin: 8px 0 0 0; color: #8b949e; font-size: 1.15rem;">Advanced Market Intelligence, Sentiment Index & Automated NLP Keyword Tracking</p>
    </div>
""", unsafe_allow_html=True)

df = st.session_state.get('df_hasil', None)
duration = st.session_state.get('duration_scan', 0)
skor_indeks = st.session_state.get('skor_indeks_val', 50.0)

STOPWORDS_ID = set(["yang", "di", "dan", "dengan", "untuk", "pada", "ke", "karena", "oleh", "dari", "ini", "itu", "akan", "juga", "atau", "bisa", "tidak", "ada", "seperti", "tahun", "saat", "menjadi", "lebih", "hari", "secara", "sudah", "dapat", "tersebut", "persen", "rp", "juta", "miliar", "triliun", "sebesar", "mencapai", "catat", "hingga"])

if df is None or df.empty:
    st.warning("Belum ada data pemindaian. Silakan jalankan pemindaian dari menu utama terlebih dahulu.")
else:
    n_pos = len(df[df['Sentimen'] == 'POSITIF'])
    n_neg = len(df[df['Sentimen'] == 'NEGATIF'])
    n_net = len(df[df['Sentimen'] == 'NETRAL'])

    if skor_indeks >= 70: 
        label_indeks, pen, banner_color = "Sangat Positif (Bullish)", "Pasar didominasi sentimen positif yang kuat dan ekspansif.", "#2ea043"
    elif skor_indeks >= 55: 
        label_indeks, pen, banner_color = "Cenderung Positif", "Sentimen positif memimpin secara proporsional di berbagai sektor.", "#58a6ff"
    elif skor_indeks >= 45: 
        label_indeks, pen, banner_color = "Netral / Seimbang", "Volume berita positif dan negatif berada dalam titik keseimbangan.", "#8b949e"
    elif skor_indeks >= 30: 
        label_indeks, pen, banner_color = "Cenderung Negatif", "Tekanan sentimen negatif mulai mendominasi pergerakan berita.", "#d29922"
    else: 
        label_indeks, pen, banner_color = "Sangat Negatif (Bearish)", "Kepanikan atau sentimen negatif mayoritas mendominasi pasar.", "#f85149"

    # Banner Indeks Sentimen Modern
    st.markdown(f"""
        <div class="sentiment-banner" style="border-left-color: {banner_color};">
            <h3 style="margin: 0 0 6px 0; color: #f0f6fc; font-weight: 700;">Indeks Sentimen Pasar: <span style="color: {banner_color};">{skor_indeks}%</span> — <em>{label_indeks}</em></h3>
            <p style="margin: 0; color: #8b949e; font-size: 1rem;">{pen}</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.progress(int(skor_indeks))
    st.markdown("<br>", unsafe_allow_html=True)

    # Metrik Utama
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Berita", f"{len(df)} Artikel", delta="Active Feed")
    with m2:
        st.metric("Positif", f"{n_pos} Berita", delta=f"{round((n_pos/len(df))*100, 1)}%" if len(df)>0 else "0%")
    with m3:
        st.metric("Negatif", f"{n_neg} Berita", delta=f"-{round((n_neg/len(df))*100, 1)}%" if len(df)>0 else "0%", delta_color="inverse")
    with m4:
        st.metric("Durasi Scan", f"{duration} Detik", delta="Real-time")

    st.markdown("---")

    # --- KELOMPOK 1: Proporsi & Komposisi Sentimen ---
    c_inf1, c_inf2 = st.columns(2)
    with c_inf1:
        with st.container(border=True):
            st.markdown("##### **Proporsi Sentimen Keseluruhan**")
            fig_donut, ax_donut = plt.subplots(figsize=(5, 4))
            sentimen_counts = [n_pos, n_net, n_neg]
            sentimen_labels = ['Positif', 'Netral', 'Negatif']
            sentimen_colors = ['#2ea043', '#8b949e', '#f85149']
            
            wedges, texts, autotexts = ax_donut.pie(
                sentimen_counts, labels=sentimen_labels, colors=sentimen_colors, 
                autopct='%1.1f%%', startangle=90, 
                wedgeprops=dict(width=0.5, edgecolor='#161b22', linewidth=2)
            )
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_weight('bold')
            ax_donut.axis('equal')
            st.pyplot(fig_donut)
        
    with c_inf2:
        with st.container(border=True):
            st.markdown("##### **Komposisi Sentimen per Kategori Aset**")
            if 'Kategori Aset' in df.columns:
                pivot_kat_sentimen = df.groupby(['Kategori Aset', 'Sentimen']).size().unstack(fill_value=0)
                for col in ['POSITIF', 'NETRAL', 'NEGATIF']:
                    if col not in pivot_kat_sentimen.columns: pivot_kat_sentimen[col] = 0
                st.bar_chart(pivot_kat_sentimen[['POSITIF', 'NETRAL', 'NEGATIF']], color=["#2ea043", "#8b949e", "#f85149"], height=245, use_container_width=True)
            else:
                st.info("Data Kategori Aset belum tersedia.")

    # --- KELOMPOK 2: Dominasi Kategori Aset Portofolio ---
    st.markdown("---")
    st.markdown('<div class="section-header">📊 Dominasi Kategori Aset Portofolio (Share of Assets)</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if 'Kategori Aset' in df.columns:
            aset_counts = df['Kategori Aset'].value_counts()
            fig_asset, ax_asset = plt.subplots(figsize=(10, 3.2))
            bars = ax_asset.barh(aset_counts.index[::-1], aset_counts.values[::-1], color='#1f6feb', height=0.6, edgecolor='none', alpha=0.9)
            ax_asset.spines['top'].set_visible(False)
            ax_asset.spines['right'].set_visible(False)
            ax_asset.spines['left'].set_color('#30363d')
            ax_asset.spines['bottom'].set_color('#30363d')
            ax_asset.grid(axis='x', linestyle='--', alpha=0.3)
            ax_asset.set_xlabel('Jumlah Artikel', fontsize=10)
            st.pyplot(fig_asset)
        else:
            st.info("Data Kategori Aset tidak tersedia.")

    # --- KELOMPOK 3: Share of Voice & Media Bias Analyzer ---
    st.markdown("---")
    col_p1, col_p2 = st.columns([1.2, 1.8])
    with col_p1:
        with st.container(border=True):
            st.markdown("##### **Porsi Distribusi Portal (Share of Voice)**")
            distribusi_portal = df['Sumber'].value_counts()
            fig, ax = plt.subplots(figsize=(5, 4.6))
            ax.pie(
                distribusi_portal, labels=distribusi_portal.index, autopct='%1.1f%%', 
                startangle=140, colors=plt.cm.Paired.colors, 
                wedgeprops=dict(width=0.5, edgecolor='#161b22', linewidth=2),
                textprops={'fontsize': 9}
            )
            ax.axis('equal')
            st.pyplot(fig)
    with col_p2:
        with st.container(border=True):
            st.markdown("##### **Peta Sentimen per Media (Media Bias Analyzer)**")
            sentimen_media = df.groupby(['Sumber', 'Sentimen']).size().unstack(fill_value=0)
            for col in ['POSITIF', 'NEGATIF', 'NETRAL']:
                if col not in sentimen_media.columns: sentimen_media[col] = 0
            st.bar_chart(sentimen_media[['POSITIF', 'NEGATIF', 'NETRAL']], color=["#2ea043", "#f85149", "#8b949e"], height=315, use_container_width=True)

    # --- KELOMPOK 4: Kesehatan Portal & Tren Jam ---
    st.markdown("---")
    st.markdown('<div class="section-header">🕒 Analisis Performa Ekstraksi & Tren Waktu (Hourly Trend)</div>', unsafe_allow_html=True)
    
    c_t1, c_t2 = st.columns(2)
    with c_t1:
        with st.container(border=True):
            st.markdown("##### **Status Keberhasilan Scraping Portal**")
            if 'Akses' in df.columns:
                akses_counts = df['Akses'].value_counts()
                fig_aks, ax_aks = plt.subplots(figsize=(5, 3))
                ax_aks.bar(akses_counts.index, akses_counts.values, color=['#1f6feb', '#d29922', '#f85149'], width=0.5, alpha=0.9)
                ax_aks.spines['top'].set_visible(False)
                ax_aks.spines['right'].set_visible(False)
                ax_aks.spines['left'].set_color('#30363d')
                ax_aks.spines['bottom'].set_color('#30363d')
                ax_aks.grid(axis='y', linestyle='--', alpha=0.3)
                ax_aks.set_ylabel('Jumlah Berita', fontsize=10)
                st.pyplot(fig_aks)
            else:
                st.info("Data status akses tidak tersedia.")
            
    with c_t2:
        with st.container(border=True):
            st.markdown("##### **Matriks Sentimen per Jam**")
            df_chart_valid = df[df['dt_sort'] != datetime.min].copy()
            if not df_chart_valid.empty:
                df_chart_valid['Jam'] = df_chart_valid['dt_sort'].dt.strftime('%H:00')
                tren_sentimen_jam = df_chart_valid.groupby(['Jam', 'Sentimen']).size().unstack(fill_value=0)
                for col in ['POSITIF', 'NETRAL', 'NEGATIF']:
                    if col not in tren_sentimen_jam.columns: tren_sentimen_jam[col] = 0
                st.bar_chart(tren_sentimen_jam[['POSITIF', 'NETRAL', 'NEGATIF']], color=["#2ea043", "#8b949e", "#f85149"], height=200, use_container_width=True)
            else:
                st.info("Format tanggal berita tidak memuat informasi jam yang valid.")

    # --- KELOMPOK 5: Peringkat Trigger & Analisis Kata Kunci ---
    st.markdown("---")
    st.markdown('<div class="section-header">🏷️ Peringkat Trigger & Deep-Dive Analisis Kata Kunci</div>', unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("##### **Top Trigger / Emiten Berita Paling Sering Dibahas**")
        if 'Trigger/Emiten' in df.columns:
            top_triggers = df['Trigger/Emiten'].value_counts().head(8).reset_index()
            top_triggers.columns = ['Trigger', 'Jumlah']
            fig_trig, ax_trig = plt.subplots(figsize=(10, 3.2))
            ax_trig.barh(top_triggers['Trigger'][::-1], top_triggers['Jumlah'][::-1], color='#58a6ff', height=0.6, alpha=0.9)
            ax_trig.spines['top'].set_visible(False)
            ax_trig.spines['right'].set_visible(False)
            ax_trig.spines['left'].set_color('#30363d')
            ax_trig.spines['bottom'].set_color('#30363d')
            ax_trig.grid(axis='x', linestyle='--', alpha=0.3)
            ax_trig.set_xlabel('Jumlah Artikel', fontsize=10)
            st.pyplot(fig_trig)
        else:
            st.info("Data trigger emiten tidak tersedia.")

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("##### **Visual Word Cloud**")
            gabungan_teks = " ".join(df['GitHub'].tolist() if 'GitHub' in df.columns else [] + df['Judul'].tolist() + df['Ringkasan Berita'].tolist()).lower()
            kata_kata = re.findall(r'\b[a-z]{3,}\b', gabungan_teks)
            kata_bersih = [k for k in kata_kata if k not in STOPWORDS_ID]
            if kata_bersih:
                # Wordcloud dengan background transparan/gelap agar menyatu
                wc = WordCloud(width=500, height=310, background_color='#161b22', colormap='Blues').generate(" ".join(kata_bersih))
                fig, ax = plt.subplots(figsize=(6, 3.4))
                ax.imshow(wc, interpolation='bilinear')
                ax.axis("off")
                st.pyplot(fig)
            
    with c2:
        with st.container(border=True):
            st.markdown("##### **Top 10 Kata Sering Muncul**")
            if kata_bersih:
                counter = Counter(kata_bersih)
                top_10 = pd.DataFrame(counter.most_common(10), columns=['Kata', 'Frekuensi'])
                st.bar_chart(top_10.set_index('Kata'), height=275)