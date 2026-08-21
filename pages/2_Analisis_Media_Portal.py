import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Analisis Media & Portal", layout="wide", initial_sidebar_state="expanded")

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

st.title("Analisis Mendalam Media & Portal Berita")
st.markdown("##### *Eksplorasi Fokus Topik Aset, Perilaku Pemberitaan & Status Kesehatan Portal*")
st.markdown("---")

df = st.session_state.get('df_hasil', None)

# Daftar lengkap seluruh portal acuan dari app.py
SEMUA_PORTAL_LIST = [
    "IDNFinancials",
    "Kompas Money",
    "CNN Indonesia (Ekonomi)",
    "CNBC Indonesia (Market)",
    "CNBC Indonesia (MyMoney)",
    "CNBC Indonesia (News)",
    "Investor.id (Market & Fin)",
    "Investor.id (Macro & Investory)",
    "Kontan Utama & Investasi",
    "Katadata",
    "Bloomberg Technoz",
    "Tempo Bisnis",
    "ANTARA Ekonomi",
    "IDX Channel",
    "Detik Finance"
]

if df is None or df.empty:
    st.warning("Belum ada data pemindaian. Jalankan pemindaian terlebih dahulu dari menu utama (`app.py`).[cite: 3]")
else:
    st.subheader("Sebaran Fokus Kategori Aset per Portal Berita")
    st.markdown("Grafik ini menunjukkan kategori aset apa yang paling sering diliput oleh masing-masing portal berita.[cite: 3]")
    
    pivot_portal_aset = df.groupby(['Sumber', 'Kategori Aset']).size().unstack(fill_value=0)
    st.bar_chart(pivot_portal_aset, height=380, use_container_width=True)
    
    st.markdown("---")
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.markdown("### Portal Paling Produktif")
        top_portal = df['Sumber'].value_counts().idxmax()
        jumlah_top = df['Sumber'].value_counts().max()
        st.success(f"**{top_portal}** menjadi penyumbang berita terbanyak dengan total **{jumlah_top} artikel** dalam pemindaian sesi ini.[cite: 3]")
        
        st.markdown("### Rincian Jumlah Berita per Kanal:")
        st.dataframe(df['Sumber'].value_counts().reset_index().rename(columns={'index': 'Portal', 'count': 'Jumlah Berita', 'Sumber': 'Portal'}), use_container_width=True)
        
    with col_stat2:
        st.markdown("### Dominasi Fokus Kategori Aset")
        top_kategori = df['Kategori Aset'].value_counts().idxmax()
        jumlah_kat = df['Kategori Aset'].value_counts().max()
        st.info(f"Kategori aset yang paling mendominasi pemberitaan saat ini adalah **{top_kategori}** sebanyak **{jumlah_kat} artikel**.[cite: 3]")
        
        st.markdown("### Persentase Kategori Aset:")
        kat_counts = df['Kategori Aset'].value_counts()
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie(kat_counts, labels=kat_counts.index, autopct='%1.1f%%', startangle=90, colors=plt.cm.Pastel1.colors)
        ax.axis('equal')
        st.pyplot(fig)

    # --- STATUS KESEHATAN & DIAGNOSTIK SELURUH PORTAL (TERMASUK YANG 0 ARTIKEL) ---
    st.markdown("---")
    st.subheader("🩺 Laporan Kesehatan & Performa Scraping Seluruh Portal")
    st.markdown("Memantau seluruh kanal terdaftar untuk mengetahui portal mana yang berhasil menyumbang berita dan mana yang kosong/tidak ada data.[cite: 3]")

    if 'Akses' in df.columns and 'Sumber' in df.columns:
        # Buat rekap dari data yang ada
        rekap_aktual = df.groupby('Sumber').agg(
            Total_Artikel=('Judul', 'count'),
            Konten_Penuh=('Akses', lambda x: (x == 'Penuh').sum()),
            Terbatas_Paywall=('Akses', lambda x: x.isin(['Terbatas', 'Paywall']).sum()),
            Error_Gagal=('Akses', lambda x: x.str.contains('Error|Gagal', case=False, na=False).sum())
        ).reset_index()

        # Gabungkan dengan daftar SEMUA_PORTAL_LIST agar portal yang 0 artikel tetap muncul di tabel
        df_master_portal = pd.DataFrame({'Sumber': SEMUA_PORTAL_LIST})
        rekap_portal = pd.merge(df_master_portal, rekap_aktual, on='Sumber', how='left').fillna({
            'Total_Artikel': 0,
            'Konten_Penuh': 0,
            'Terbatas_Paywall': 0,
            'Error_Gagal': 0
        })

        # Menghitung persentase sukses ekstraksi konten penuh
        rekap_portal['Tingkat Sukses (%)'] = ((rekap_portal['Konten_Penuh'] / rekap_portal['Total_Artikel'].replace(0, 1)) * 100).round(1)

        # Menentukan Status Kesehatan Termasuk Penanganan 0 Artikel
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

        # Susun ulang kolom agar lebih rapi
        rekap_portal = rekap_portal[['Sumber', 'Status Sistem', 'Total_Artikel', 'Konten_Penuh', 'Terbatas_Paywall', 'Error_Gagal', 'Tingkat Sukses (%)']]
        rekap_portal = rekap_portal.sort_values(by='Total_Artikel', ascending=False).reset_index(drop=True)

        # Tampilkan metrik ringkasan di atas tabel
        m1, m2, m3 = st.columns(3)
        total_portal_scan = len(rekap_portal)
        portal_aktif = len(rekap_portal[rekap_portal['Total_Artikel'] > 0])
        portal_kosong = len(rekap_portal[rekap_portal['Total_Artikel'] == 0])

        m1.metric("Total Kanal Terdaftar", f"{total_portal_scan} Kanal")
        m2.metric("Kanal Berisi Berita", f"{portal_aktif} Kanal")
        m3.metric("Kanal 0 Artikel / Kosong", f"{portal_kosong} Kanal")

        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(rekap_portal, use_container_width=True, hide_index=True)
        
        st.caption("ℹ️ *Catatan: Status '0 Artikel' menandakan bahwa portal aktif diperiksa, namun tidak ada berita yang cocok dengan kata kunci portofolio atau rentang waktu yang Anda pilih pada sesi pemindaian tersebut.*[cite: 3]")
    else:
        st.info("Data status akses belum tersedia.[cite: 3]")