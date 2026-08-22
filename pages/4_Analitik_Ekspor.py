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

        .metric-card-export {
            background: rgba(22, 27, 34, 0.7);
            border: 1px solid #30363d;
            padding: 1.2rem;
            border-radius: 10px;
            text-align: center;
        }
        .metric-card-export .val {
            font-size: 1.5rem;
            font-weight: 700;
            color: #58a6ff;
        }
        .metric-card-export .lbl {
            font-size: 0.8rem;
            color: #8b949e;
            margin-top: 4px;
            text-transform: uppercase;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="hero-title-box">
        <h1>Pusat Ekspor Laporan & Teks Siap Kirim</h1>
        <p>Salin Laporan Ringkas atau Unduh sebagai Dokumen Teks (.txt)</p>
    </div>
""", unsafe_allow_html=True)

df = st.session_state.get('df_hasil', None)
skor_indeks = st.session_state.get('skor_indeks_val', 50.0)

if df is None or df.empty:
    st.warning("Belum ada data pemindaian. Jalankan pemindaian terlebih dahulu dari menu utama.")
else:
    waktu_sekarang = datetime.now().strftime("%d-%m-%Y %H:%M WIB")
    
    total_artikel = len(df)
    total_saham = len(df[df['Kategori Aset'] == 'SAHAM']) if 'Kategori Aset' in df.columns else 0
    total_negatif = len(df[df['Sentimen'] == 'NEGATIF']) if 'Sentimen' in df.columns else 0

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown(f'<div class="metric-card-export"><div class="val">{total_artikel} Artikel</div><div class="lbl">Total Terarsip</div></div>', unsafe_allow_html=True)
    with col_m2:
        st.markdown(f'<div class="metric-card-export"><div class="val" style="color:#238636">{skor_indeks}%</div><div class="lbl">Skor Indeks Portofolio</div></div>', unsafe_allow_html=True)
    with col_m3:
        st.markdown(f'<div class="metric-card-export"><div class="val" style="color:#f85149">{total_negatif} Isu</div><div class="lbl">Sentimen Negatif</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    teks_laporan = f"RADAR BERITA PORTOFOLIO\n{waktu_sekarang} | Indeks: {skor_indeks}%\nTotal Berita: {total_artikel} Artikel\n----------------------------------------\n\n"

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

    with st.container(border=True):
        st.markdown("### 📥 Panel Aksi & Pratinjau Dokumen")
        st.markdown("<p style='color: #8b949e; font-size: 0.95rem; margin-bottom: 1.2rem;'>Unduh hasil kompilasi berita portofolio dalam bentuk file teks bersih atau periksa langsung melalui kotak pratinjau di bawah.</p>", unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([1, 1], gap="medium")
        with col_btn1:
            st.download_button(
                label="📥 Unduh Dokumen Ringkasan (.txt)",
                data=teks_laporan,
                file_name=f"ringkasan_radar_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col_btn2:
            st.button("📋 Status Kompilasi: Siap Ekspor", disabled=True, use_container_width=True)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("**Pratinjau Format Teks:**")
        st.code(teks_laporan, language="markdown")