import streamlit as st
import re
from datetime import datetime

st.set_page_config(page_title="Pusat Ekspor Laporan", layout="wide", initial_sidebar_state="expanded")

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

st.title("Pusat Ekspor Laporan & Teks Siap Kirim")
st.markdown("##### *Salin Laporan Ringkas atau Unduh sebagai Dokumen Teks (.txt)*")
st.markdown("---")

df = st.session_state.get('df_hasil', None)
skor_indeks = st.session_state.get('skor_indeks_val', 50.0)

if df is None or df.empty:
    st.warning("Belum ada data pemindaian. Jalankan pemindaian terlebih dahulu dari menu utama.")
else:
    waktu_sekarang = datetime.now().strftime("%d-%m-%Y %H:%M WIB")
    teks_laporan = f"RADAR BERITA PORTOFOLIO\n{waktu_sekarang} | Indeks: {skor_indeks}%\nTotal Berita: {len(df)} Artikel\n----------------------------------------\n\n"

    for i, row in df.reset_index(drop=True).iterrows():
        judul_clean = re.sub(r'\s+', ' ', row['Judul']).strip()
        ringkasan_clean = re.sub(r'\s+', ' ', row['Ringkasan Berita']).strip()
        link_asli = row['Link']
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', link_asli)
        domain_pendek = domain_match.group(1) if domain_match else "Link Berita"

        teks_laporan += f"{i+1}. {row['Trigger/Emiten']} ({row['Sentimen']})\n"
        teks_laporan += f"   {judul_clean}\n"
        teks_laporan += f"   _{ringkasan_clean}_\n"
        teks_laporan += f"   [Baca via {domain_pendek}]({link_asli})\n\n"

    st.download_button(
        label="Unduh Ringkasan sebagai Dokumen Teks (.txt)",
        data=teks_laporan,
        file_name=f"ringkasan_radar_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.code(teks_laporan, language="markdown")