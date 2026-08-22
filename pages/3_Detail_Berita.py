import streamlit as st
import pandas as pd

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

        .hero-title-box {
            background: linear-gradient(135deg, rgba(31, 111, 235, 0.15) 0%, rgba(35, 134, 54, 0.08) 100%);
            border: 1px solid #30363d;
            border-left: 6px solid #1f6feb;
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
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
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="hero-title-box">
        <h1>Detail Berita & Kategori Aset</h1>
        <p>Eksplorasi Mendalam Berita Berdasarkan Kelompok Aset & Filter Risiko</p>
    </div>
""", unsafe_allow_html=True)

df = st.session_state.get('df_hasil', None)

if 'bookmarked_links' not in st.session_state:
    st.session_state['bookmarked_links'] = []

if df is None or df.empty:
    st.warning("Belum ada data pemindaian. Jalankan pemindaian terlebih dahulu dari menu utama.")
else:
    with st.container(border=True):
        st.markdown("##### ⚙️ Panel Kontrol & Filter Berita Interaktif")
        
        col_f1, col_f2 = st.columns([1, 1], gap="large")
        
        with col_f1:
            hanya_negatif = st.checkbox("🚨 Fokus Risiko (Hanya Berita Negatif)", value=False)
            aktifkan_filter_tanggal = st.checkbox("📅 Aktifkan Filter Rentang Tanggal", value=False)
            
        with col_f2:
            keyword_search = st.text_input("🔍 Cari Kata Kunci", value="", placeholder="Contoh: ACES, dividen, IHSG...")

        if aktifkan_filter_tanggal:
            st.markdown("<hr style='margin: 15px 0; border-color: #30363d;'>", unsafe_allow_html=True)
            kolom_tgl = 'dt_sort' if 'dt_sort' in df.columns else ('Tanggal' if 'Tanggal' in df.columns else None)
            if kolom_tgl:
                try:
                    df['temp_date'] = pd.to_datetime(df[kolom_tgl], errors='coerce').dt.date
                    min_d = df['temp_date'].min()
                    max_d = df['temp_date'].max()
                    if pd.isna(min_d) or pd.isna(max_d):
                        date_range = st.date_input("Pilih Rentang Tanggal")
                    else:
                        date_range = st.date_input("Pilih Rentang Tanggal", value=(min_d, max_d), min_value=min_d, max_value=max_d)
                except Exception:
                    date_range = st.date_input("Pilih Rentang Tanggal")
            else:
                date_range = st.date_input("Pilih Rentang Tanggal")

    st.markdown("<br>", unsafe_allow_html=True)

    if 'dt_sort' in df.columns:
        df_display = df.drop(columns=['dt_sort'])
    else:
        df_display = df

    df_tampil = df_display[df_display['Sentimen'] == 'NEGATIF'] if hanya_negatif else df_display

    if keyword_search.strip():
        query = keyword_search.lower()
        mask = (
            df_tampil['Judul'].astype(str).str.lower().str.contains(query, na=False) |
            df_tampil['Trigger/Emiten'].astype(str).str.lower().str.contains(query, na=False) |
            df_tampil['Sumber'].astype(str).str.lower().str.contains(query, na=False) |
            df_tampil['Ringkasan Berita'].astype(str).str.lower().str.contains(query, na=False)
        )
        df_tampil = df_tampil[mask]

    if aktifkan_filter_tanggal and 'temp_date' in df.columns:
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_d, end_d = date_range
            df_tampil = df_tampil[(df_tampil['temp_date'] >= start_d) & (df_tampil['temp_date'] <= end_d)]
        elif isinstance(date_range, tuple) and len(date_range) == 1:
            start_d = date_range[0]
            df_tampil = df_tampil[df_tampil['temp_date'] >= start_d]

    if 'temp_date' in df.columns:
        df_tampil = df_tampil.drop(columns=['temp_date'])

    if df_tampil.empty:
        st.info("Tidak ada berita yang cocok dengan filter atau kata kunci yang dipilih.")

    def render_badge_sentimen(sentimen):
        if "POSITIF" in sentimen: 
            return '<span style="background-color: rgba(35, 134, 54, 0.15); color: #3fb950; border: 1px solid rgba(35, 134, 54, 0.4); padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.75em;">POSITIF</span>'
        elif "NEGATIF" in sentimen: 
            return '<span style="background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid rgba(248, 81, 73, 0.4); padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.75em;">NEGATIF</span>'
        return '<span style="background-color: rgba(139, 148, 158, 0.15); color: #8b949e; border: 1px solid rgba(139, 148, 158, 0.4); padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.75em;">NETRAL</span>'

    def render_badge_bursa(status_bursa):
        return f'<span style="background-color: rgba(110, 118, 129, 0.1); color: #c9d1d9; border: 1px solid #30363d; padding: 3px 8px; border-radius: 6px; font-size: 0.75em;">{status_bursa}</span>'

    def tampilkan_konten_tab(df_sub, tab_prefix=""):
        if df_sub.empty:
            st.info("Tidak ada berita pada kategori ini.")
            return
        
        for idx, r in df_sub.iterrows():
            with st.container(border=True):
                col_info, col_btn = st.columns([8, 2])
                with col_info:
                    st.markdown(f"**[{r['Trigger/Emiten']}]** &nbsp; {render_badge_sentimen(r['Sentimen'])} &nbsp; {render_badge_bursa(r['Status Bursa'])} &nbsp; <small style='color: #8b949e;'>📰 {r['Sumber']} | ⏱️ {r['Tanggal']}</small>", unsafe_allow_html=True)
                with col_btn:
                    link_key = r['Link']
                    is_bookmarked = link_key in st.session_state['bookmarked_links']
                    btn_label = "⭐ Disimpan" if is_bookmarked else "☆ Tandai"
                    if st.button(btn_label, key=f"bm_{tab_prefix}_{idx}"):
                        if is_bookmarked:
                            st.session_state['bookmarked_links'].remove(link_key)
                        else:
                            st.session_state['bookmarked_links'].append(link_key)
                        st.rerun()

                st.markdown(f"#### [{r['Judul']}]({r['Link']})")
                st.write(f"**Ringkasan:** {r['Ringkasan Berita']}")
                with st.expander("Baca Isi Berita Lengkap"):
                    st.write(r['Isi Berita'])

    t1, t2, t3, t4, t5, t6 = st.tabs(["Semua Berita", "Saham Emiten", "ETF & Reksadana", "Emas & Komoditas", "Makro & Regulasi", "⭐ Tersimpan"])
    
    with t1: tampilkan_konten_tab(df_tampil, tab_prefix="t1")
    with t2: tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'SAHAM'], tab_prefix="t2")
    with t3: tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'REKSADANA_ETF'], tab_prefix="t3")
    with t4: tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'EMAS_KOMODITAS'], tab_prefix="t4")
    with t5: tampilkan_konten_tab(df_tampil[df_tampil['Kategori Aset'] == 'MAKRO_REGULASI'], tab_prefix="t5")
    with t6:
        df_saved = df_display[df_display['Link'].isin(st.session_state['bookmarked_links'])]
        if df_saved.empty:
            st.info("Belum ada berita yang ditandai (Bookmark).")
        else:
            tampilkan_konten_tab(df_saved, tab_prefix="t6")

    st.markdown("<br>", unsafe_allow_html=True)
    df_csv = df_tampil[['Judul', 'Tanggal', 'Kategori Aset', 'Sentimen', 'Status Bursa', 'Ringkasan Berita']]
    st.download_button("Unduh CSV Ringkas", data=df_csv.to_csv(index=False).encode('utf-8'), file_name='laporan_berita.csv', mime='text/csv', use_container_width=True)