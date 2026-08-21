import streamlit as st

st.set_page_config(page_title="Detail Berita Aset", layout="wide", initial_sidebar_state="expanded")

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

st.title("Detail Berita & Kategori Aset")
st.markdown("##### *Eksplorasi Mendalam Berita Berdasarkan Kelompok Aset & Filter Risiko*")
st.markdown("---")

df = st.session_state.get('df_hasil', None)

if df is None or df.empty:
    st.warning("Belum ada data pemindaian. Jalankan pemindaian terlebih dahulu dari menu utama.")
else:
    col_f1, _ = st.columns([1, 2])
    with col_f1:
        hanya_negatif = st.checkbox("Tampilkan Hanya Berita Negatif (Fokus Risiko)", value=False)

    df_display = df.drop(columns=['dt_sort'])
    df_tampil = df_display[df_display['Sentimen'] == 'NEGATIF'] if hanya_negatif else df_display

    if hanya_negatif and df_tampil.empty:
        st.info("Aman! Tidak ada berita bersentimen negatif.")

    def render_badge_sentimen(sentimen):
        if "POSITIF" in sentimen: return '<span style="background-color: #d4edda; color: #155724; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 0.8em;">POSITIF</span>'
        elif "NEGATIF" in sentimen: return '<span style="background-color: #f8d7da; color: #721c24; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 0.8em;">NEGATIF</span>'
        return '<span style="background-color: #e2e3e5; color: #383d41; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 0.8em;">NETRAL</span>'

    def render_badge_bursa(status_bursa):
        return f'<span style="background-color: #e2e3e5; color: #41464b; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;">{status_bursa}</span>'

    def tampilkan_konten_tab(df_sub):
        if df_sub.empty:
            st.info("Tidak ada berita pada kategori ini.")
            return
        for _, r in df_sub.iterrows():
            with st.container():
                st.markdown(f"**[{r['Trigger/Emiten']}]** &nbsp; {render_badge_sentimen(r['Sentimen'])} &nbsp; {render_badge_bursa(r['Status Bursa'])} &nbsp; <small style='color: gray;'>📰 {r['Sumber']} | ⏱️ {r['Tanggal']}</small>", unsafe_allow_html=True)
                st.markdown(f"#### [{r['Judul']}]({r['Link']})")
                st.write(f"**Ringkasan:** {r['Ringkasan Berita']}")
                with st.expander("Baca Isi Berita Lengkap"):
                    st.write(r['Isi Berita'])
                st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(["Semua Berita", "Saham Emiten", "ETF & Reksadana", "Emas & Komoditas", "Makro & Regulasi"])
    
    with t1: tampilkan_konten_tab(df_tampil)
    with t2: tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'SAHAM'])
    with t3: tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'REKSADANA_ETF'])
    with t4: tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'EMAS_KOMODITAS'])
    with t5: tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'MAKRO_REGULASI'])

    df_csv = df_tampil[['Judul', 'Tanggal', 'Kategori Aset', 'Sentimen', 'Status Bursa', 'Ringkasan Berita']]
    st.download_button("Unduh CSV Ringkas", data=df_csv.to_csv(index=False).encode('utf-8'), file_name='laporan_berita.csv', mime='text/csv', use_container_width=True)