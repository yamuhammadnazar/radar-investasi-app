import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud

st.set_page_config(page_title="Analisis Media & Portal", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        /* CSS SIDEBAR (KODE ASLI ANDA - TIDAK DIUBAH SAMA SEKALI) */
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
        
        /* TOMBOL (KODE ASLI ANDA) */
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

        /* HEADER BANNER */
        .hero-title-box {
            background: linear-gradient(135deg, rgba(31, 111, 235, 0.15) 0%, rgba(35, 134, 54, 0.08) 100%);
            border: 1px solid #30363d;
            border-left: 6px solid #1f6feb;
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.8rem;
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
        .metric-badge {
            background: rgba(31, 111, 235, 0.1);
            border: 1px solid rgba(56, 139, 253, 0.4);
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
        }
        .metric-badge .val {
            font-size: 1.8rem;
            font-weight: 700;
            color: #58a6ff;
        }
        .metric-badge .lbl {
            font-size: 0.85rem;
            color: #8b949e;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
    </style>
""", unsafe_allow_html=True)

# Header Banner
st.markdown("""
    <div class="hero-title-box">
        <h1>Analisis Mendalam Media & Portal Berita</h1>
        <p>Eksplorasi Fokus Topik Aset, Perilaku Pemberitaan & Status Kesehatan Portal</p>
    </div>
""", unsafe_allow_html=True)

df = st.session_state.get('df_hasil', None)

SEMUA_PORTAL_LIST = [
    "CNN Indonesia (Ekonomi)",
    "CNBC Indonesia (Market)",
    "CNBC Indonesia (MyMoney)",
    "CNBC Indonesia (News)",
    "Kontan Utama & Investasi",
    "Kontan Investasi",
    "Katadata",
    "Bloomberg Technoz",
    "Tempo Bisnis",
    "ANTARA Ekonomi",
    "IDX Channel",
    "Detik Finance",
    "Bisnis Indonesia",
    "Bisnis Market",
    "SWA Online",
    "Bareksa",
    "TrenAsia",
    "Warta Ekonomi",
    "RM.id Ekonomi",
    "IDNFinancials",
    "Kompas Money",
    "Investor.id (Market & Fin)",
    "Investor.id (Macro & Investory)",
    "MetroTV News",
    "tvOne News"
]

if df is None or df.empty:
    st.warning("Belum ada data pemindaian. Jalankan pemindaian terlebih dahulu dari menu utama (`app.py`).")
else:
    # --- BAGIAN 1: SEBARAN FOKUS KATEGORI ASET ---
    with st.container(border=True):
        st.subheader("📊 Sebaran Fokus Kategori Aset per Portal Berita")
        st.caption("Grafik ini menunjukkan kategori aset apa yang paling sering diliput oleh masing-masing portal berita.")
        
        pivot_portal_aset = df.groupby(['Sumber', 'Kategori Aset']).size().unstack(fill_value=0)
        st.bar_chart(pivot_portal_aset, height=360, use_container_width=True)

    # --- BAGIAN 2: WORD CLOUD & TIME HEATMAP (FITUR BARU) ---
    col_f1, col_f2 = st.columns(2, gap="large")

    with col_f1:
        with st.container(border=True):
            st.subheader("☁️ Word Cloud Judul Berita")
            st.caption("Visualisasi kata kunci yang paling sering muncul dalam judul berita saat ini.")
            
            if 'Judul' in df.columns and not df['Judul'].isnull().all():
                text_gabungan = " ".join(df['Judul'].dropna().astype(str).tolist())
                if len(text_gabungan.strip()) > 0:
                    wordcloud = WordCloud(
                        width=600, height=350, 
                        background_color='#0e1117', 
                        colormap='Blues',
                        max_words=100
                    ).generate(text_gabungan)
                    
                    fig_wc, ax_wc = plt.subplots(figsize=(5, 3))
                    fig_wc.patch.set_facecolor('#0e1117')
                    ax_wc.imshow(wordcloud, interpolation='bilinear')
                    ax_wc.axis('off')
                    st.pyplot(fig_wc)
                else:
                    st.info("Teks judul tidak mencukupi untuk membuat Word Cloud.")
            else:
                st.info("Kolom 'Judul' tidak ditemukan dalam data.")

    with col_f2:
        with st.container(border=True):
            st.subheader("⏰ Distribusi Waktu Publikasi")
            st.caption("Analisis jam atau waktu rilis berita dominan dari hasil pemindaian.")
            
            kolom_waktu = None
            for col in ['Waktu', 'Tanggal', 'Jam', 'Timestamp']:
                if col in df.columns:
                    kolom_waktu = col
                    break
            
            if kolom_waktu:
                try:
                    df['Jam_Temp'] = pd.to_datetime(df[kolom_waktu], errors='coerce').dt.hour
                    jam_counts = df['Jam_Temp'].value_counts().sort_index()
                    if not jam_counts.empty:
                        st.bar_chart(jam_counts, height=220, use_container_width=True)
                    else:
                        st.info("Format waktu tidak dapat diurai ke dalam jam.")
                except Exception:
                    st.info("Gagal memproses data waktu publikasi.")
            else:
                st.info("Kolom waktu/tanggal spesifik belum terdeteksi di data pemindaian. Pastikan dataframe memiliki kolom waktu jika ingin menampilkan grafik tren jam.")

    # --- BAGIAN 3 & 4: DUA KOLOM PRODUKTIVITAS & DOMINASI ---
    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            st.subheader("🏆 Portal Paling Produktif")
            top_portal = df['Sumber'].value_counts().idxmax()
            jumlah_top = df['Sumber'].value_counts().max()
            
            st.success(f"**{top_portal}** menjadi penyumbang berita terbanyak dengan total **{jumlah_top} artikel** dalam pemindaian sesi ini.")
            
            st.markdown("**Rincian Jumlah Berita per Kanal:**")
            st.dataframe(
                df['Sumber'].value_counts().reset_index().rename(columns={'index': 'Portal', 'count': 'Jumlah Berita', 'Sumber': 'Portal'}),
                use_container_width=True,
                height=260
            )

    with col2:
        with st.container(border=True):
            st.subheader("📈 Dominasi Fokus Kategori Aset")
            top_kategori = df['Kategori Aset'].value_counts().idxmax()
            jumlah_kat = df['Kategori Aset'].value_counts().max()
            
            st.info(f"Kategori aset yang paling mendominasi pemberitaan saat ini adalah **{top_kategori}** sebanyak **{jumlah_kat} artikel**.")
            
            st.markdown("**Persentase Kategori Aset:**")
            kat_counts = df['Kategori Aset'].value_counts()
            
            fig, ax = plt.subplots(figsize=(4, 3.2))
            fig.patch.set_facecolor('#0e1117')
            ax.set_facecolor('#0e1117')
            
            colors = ['#1f6feb', '#238636', '#d29922', '#db6d28', '#a371f7', '#f85149']
            wedges, texts, autotexts = ax.pie(
                kat_counts, 
                labels=kat_counts.index, 
                autopct='%1.1f%%', 
                startangle=90, 
                colors=colors[:len(kat_counts)],
                pctdistance=0.75,
                wedgeprops=dict(width=0.4, edgecolor='#0e1117', linewidth=2)
            )
            
            for text in texts:
                text.set_color('#c9d1d9')
                text.set_fontsize(8)
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(8)
                autotext.set_weight('bold')
                
            ax.axis('equal')
            
            c_left, c_mid, c_right = st.columns([1, 4, 1])
            with c_mid:
                st.pyplot(fig)

    # --- BAGIAN 5: LAPORAN KESEHATAN PORTAL ---
    with st.container(border=True):
        st.subheader("🩺 Laporan Kesehatan & Performa Scraping Seluruh Portal")
        st.caption("Memantau seluruh kanal terdaftar untuk mengetahui portal mana yang berhasil menyumbang berita dan mana yang kosong/tidak ada data.")

        if 'Akses' in df.columns and 'Sumber' in df.columns:
            rekap_aktual = df.groupby('Sumber').agg(
                Total_Artikel=('Judul', 'count'),
                Konten_Penuh=('Akses', lambda x: (x == 'Penuh').sum()),
                Terbatas_Paywall=('Akses', lambda x: x.isin(['Terbatas', 'Paywall']).sum()),
                Error_Gagal=('Akses', lambda x: x.str.contains('Error|Gagal', case=False, na=False).sum())
            ).reset_index()

            df_master_portal = pd.DataFrame({'Sumber': SEMUA_PORTAL_LIST})
            rekap_portal = pd.merge(df_master_portal, rekap_aktual, on='Sumber', how='left').fillna({
                'Total_Artikel': 0,
                'Konten_Penuh': 0,
                'Terbatas_Paywall': 0,
                'Error_Gagal': 0
            })

            rekap_portal['Tingkat Sukses (%)'] = ((rekap_portal['Konten_Penuh'] / rekap_portal['Total_Artikel'].replace(0, 1)) * 100).round(1)

            def tentukan_status_sehat(row):
                if row['Total_Artikel'] == 0:
                    return "⚪ 0 Artikel / Tidak Ada Berita Sesuai Filter"
                elif row['Error_Gagal'] > 0:
                    return "🔴 Gangguan / Error"
                elif row['Terbatas_Paywall'] > row['Konten_Penuh']:
                    return "🟡 Banyak Paywall / Terbatas"
                else:
                    return "🟢 Sangat Sehat (Optimal)"

            rekap_portal['Status Sistem'] = rekap_portal.apply(tentukan_status_sehat, axis=1)
            rekap_portal = rekap_portal[['Sumber', 'Status Sistem', 'Total_Artikel', 'Konten_Penuh', 'Terbatas_Paywall', 'Error_Gagal', 'Tingkat Sukses (%)']]
            rekap_portal = rekap_portal.sort_values(by='Total_Artikel', ascending=False).reset_index(drop=True)

            total_portal_scan = len(rekap_portal)
            portal_aktif = len(rekap_portal[rekap_portal['Total_Artikel'] > 0])
            portal_kosong = len(rekap_portal[rekap_portal['Total_Artikel'] == 0])

            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f'<div class="metric-badge"><div class="val">{total_portal_scan}</div><div class="lbl">Total Kanal Terdaftar</div></div>', unsafe_allow_html=True)
            with m2:
                st.markdown(f'<div class="metric-badge"><div class="val" style="color:#238636">{portal_aktif}</div><div class="lbl">Kanal Berisi Berita</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="metric-badge"><div class="val" style="color:#8b949e">{portal_kosong}</div><div class="lbl">Kanal 0 Artikel / Kosong</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(rekap_portal, use_container_width=True, hide_index=True)
            st.caption("ℹ️ *Catatan: Status '0 Artikel' menandakan bahwa portal aktif diperiksa, namun tidak ada berita yang cocok dengan kata kunci portofolio atau rentang waktu yang Anda pilih pada sesi pemindaian tersebut.*")
        else:
            st.info("Data status akses belum tersedia.")