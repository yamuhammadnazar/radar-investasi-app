"""
Halaman 3: Detail Berita & Kategori Aset
========================================
Eksplorasi mendalam berita berdasarkan filter interaktif, bookmark,
sortable table, export Excel/CSV, dan visualisasi per kategori.
"""
import io

import pandas as pd
import streamlit as st

from utils_ui import (
    PALETTE,
    inject_shared_css, hero_header, section_header, metric_badge,
    status_pill, get_dataframe_or_stop, hitung_sentimen_counts,
)

# =====================================================================
# Konfigurasi
# =====================================================================
st.set_page_config(
    page_title="Detail Berita Aset",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_shared_css()
hero_header(
    "Detail Berita & Kategori Aset",
    "Eksplorasi Mendalam Berita Berdasarkan Kelompok Aset · Filter Risiko · Bookmark · Export"
)

# =====================================================================
# Inisialisasi Session State untuk Bookmark
# =====================================================================
if 'bookmarked_links' not in st.session_state:
    st.session_state['bookmarked_links'] = []

# =====================================================================
# Data
# =====================================================================
df_raw = get_dataframe_or_stop()

# =====================================================================
# Panel Filter Interaktif
# =====================================================================
with st.container(border=True):
    st.markdown("##### ⚙️ **Panel Kontrol & Filter Berita Interaktif**")

    col_f1, col_f2, col_f3 = st.columns(3, gap="medium")
    with col_f1:
        hanya_negatif = st.checkbox("🚨 Fokus Risiko (Hanya Negatif)", value=False, key="p3_hanya_neg")
        aktifkan_filter_tanggal = st.checkbox("📅 Aktifkan Filter Tanggal", value=False, key="p3_use_date")
    with col_f2:
        keyword_search = st.text_input("🔍 Cari Kata Kunci", value="", placeholder="Contoh: ACES, dividen, IHSG...",
                                        key="p3_keyword")
    with col_f3:
        sort_by = st.selectbox(
            "↕️ Urutkan Berdasarkan",
            options=['Tanggal (Terbaru)', 'Tanggal (Terlama)', 'Sentimen', 'Trigger/Emiten', 'Sumber'],
            index=0,
        )

    st.markdown("<hr style='margin: 12px 0; border-color: #30363d;'>", unsafe_allow_html=True)

    col_f4, col_f5, col_f6 = st.columns(3, gap="medium")
    list_kategori = sorted(df_raw['Kategori Aset'].dropna().unique().tolist()) if 'Kategori Aset' in df_raw.columns else []
    list_sumber = sorted(df_raw['Sumber'].dropna().unique().tolist()) if 'Sumber' in df_raw.columns else []
    list_sentimen = ['POSITIF', 'NETRAL', 'NEGATIF']

    with col_f4:
        selected_kategori = st.multiselect("📦 Kategori Aset", options=list_kategori, default=[], key="p3_kat")
    with col_f5:
        selected_sumber = st.multiselect("📡 Sumber Portal", options=list_sumber, default=[], key="p3_sum")
    with col_f6:
        selected_sentimen = st.multiselect("🎯 Filter Sentimen", options=list_sentimen, default=[], key="p3_sent")

    # Filter tanggal
    date_range = None
    if aktifkan_filter_tanggal:
        kolom_tgl = 'dt_sort' if 'dt_sort' in df_raw.columns else ('Tanggal' if 'Tanggal' in df_raw.columns else None)
        if kolom_tgl:
            try:
                df_raw['_temp_date'] = pd.to_datetime(df_raw[kolom_tgl], errors='coerce').dt.date
                valid_dates = df_raw['_temp_date'].dropna()
                if not valid_dates.empty:
                    min_d, max_d = valid_dates.min(), valid_dates.max()
                    date_range = st.date_input("Pilih Rentang Tanggal",
                                                value=(min_d, max_d),
                                                min_value=min_d, max_value=max_d, key="p3_date")
                else:
                    date_range = st.date_input("Pilih Rentang Tanggal", key="p3_date_empty")
            except Exception:
                date_range = st.date_input("Pilih Rentang Tanggal", key="p3_date_err")
        else:
            date_range = st.date_input("Pilih Rentang Tanggal", key="p3_date_no_col")

st.markdown("<br>", unsafe_allow_html=True)

# =====================================================================
# Terapkan Filter
# =====================================================================
df_display = df_raw.copy()
if 'dt_sort' in df_display.columns:
    # Keep dt_sort untuk filter
    pass

# Filter sentimen (Hanya negatif atau sesuai multiselect)
if hanya_negatif:
    df_tampil = df_display[df_display['Sentimen'] == 'NEGATIF']
else:
    df_tampil = df_display

# Filter kategori
if selected_kategori and 'Kategori Aset' in df_tampil.columns:
    df_tampil = df_tampil[df_tampil['Kategori Aset'].isin(selected_kategori)]
if selected_sumber and 'Sumber' in df_tampil.columns:
    df_tampil = df_tampil[df_tampil['Sumber'].isin(selected_sumber)]
if selected_sentimen and 'Sentimen' in df_tampil.columns:
    df_tampil = df_tampil[df_tampil['Sentimen'].isin(selected_sentimen)]

# Filter keyword
if keyword_search.strip():
    query = keyword_search.lower()
    mask = pd.Series([False] * len(df_tampil), index=df_tampil.index)
    for col in ['Judul', 'Trigger/Emiten', 'Sumber', 'Ringkasan Berita', 'Isi Berita']:
        if col in df_tampil.columns:
            mask = mask | df_tampil[col].astype(str).str.lower().str.contains(query, na=False)
    df_tampil = df_tampil[mask]

# Filter tanggal
if aktifkan_filter_tanggal and date_range and '_temp_date' in df_tampil.columns:
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
        df_tampil = df_tampil[
            (df_tampil['_temp_date'] >= start_d) & (df_tampil['_temp_date'] <= end_d)
        ]
    elif isinstance(date_range, tuple) and len(date_range) == 1:
        start_d = date_range[0]
        df_tampil = df_tampil[df_tampil['_temp_date'] >= start_d]

# Bersihkan kolom temp
if '_temp_date' in df_tampil.columns:
    df_tampil = df_tampil.drop(columns=['_temp_date'])

# Sort
if sort_by == 'Tanggal (Terbaru)' and 'dt_sort' in df_tampil.columns:
    df_tampil = df_tampil.sort_values('dt_sort', ascending=False)
elif sort_by == 'Tanggal (Terlama)' and 'dt_sort' in df_tampil.columns:
    df_tampil = df_tampil.sort_values('dt_sort', ascending=True)
elif sort_by == 'Sentimen' and 'Sentimen' in df_tampil.columns:
    sentimen_order_map = {'NEGATIF': 0, 'NETRAL': 1, 'POSITIF': 2}
    df_tampil['_sort_sent'] = df_tampil['Sentimen'].map(sentimen_order_map)
    df_tampil = df_tampil.sort_values('_sort_sent')
    df_tampil = df_tampil.drop(columns=['_sort_sent'])
elif sort_by == 'Trigger/Emiten' and 'Trigger/Emiten' in df_tampil.columns:
    df_tampil = df_tampil.sort_values('Trigger/Emiten')
elif sort_by == 'Sumber' and 'Sumber' in df_tampil.columns:
    df_tampil = df_tampil.sort_values('Sumber')

# Drop kolom teknis untuk tampilan (kecuali dt_sort untuk sorting)
df_for_tabs = df_tampil.copy()
if 'dt_sort' in df_for_tabs.columns:
    df_for_tabs = df_for_tabs.drop(columns=['dt_sort'])

# =====================================================================
# Ringkasan Filter
# =====================================================================
agg = hitung_sentimen_counts(df_tampil)
n_total_filt = agg['total']

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    metric_badge(f"{n_total_filt:,}", "Berita Difilter", f"dari {len(df_raw):,} total", PALETTE['primary_alt'])
with col_m2:
    metric_badge(f"{agg['pos']:,}", "Positif", color=PALETTE['pos'])
with col_m3:
    metric_badge(f"{agg['neg']:,}", "Negatif", color=PALETTE['neg'])
with col_m4:
    metric_badge(f"{len(st.session_state['bookmarked_links']):,}", "Bookmark Aktif", color=PALETTE['warning'])

st.markdown("---")

# =====================================================================
# Render Komponen
# =====================================================================
def render_badge_sentimen(sentimen: str) -> str:
    if "POSITIF" in str(sentimen):
        return status_pill("POSITIF", "pos")
    if "NEGATIF" in str(sentimen):
        return status_pill("NEGATIF", "neg")
    return status_pill("NETRAL", "net")


def render_badge_bursa(status_bursa) -> str:
    return f'<span style="background-color: rgba(110, 118, 129, 0.1); color: #c9d1d9; border: 1px solid #30363d; padding: 3px 8px; border-radius: 6px; font-size: 0.75em;">{status_bursa}</span>'


def tampilkan_konten_tab(df_sub: pd.DataFrame, tab_prefix: str = ""):
    """Render daftar berita dalam container dengan bookmark button."""
    if df_sub.empty:
        st.info("📭 Tidak ada berita pada kategori ini.")
        return

    for idx, r in df_sub.iterrows():
        with st.container(border=True):
            col_info, col_btn = st.columns([8, 2])
            with col_info:
                st.markdown(
                    f"**[{r['Trigger/Emiten']}]** &nbsp; "
                    f"{render_badge_sentimen(r['Sentimen'])} &nbsp; "
                    f"{render_badge_bursa(r.get('Status Bursa', '-'))} &nbsp; "
                    f"<small style='color: #8b949e;'>📰 {r['Sumber']} | ⏱️ {r['Tanggal']}</small>",
                    unsafe_allow_html=True,
                )
            with col_btn:
                link_key = r.get('Link', str(idx))
                is_bookmarked = link_key in st.session_state['bookmarked_links']
                btn_label = "⭐ Disimpan" if is_bookmarked else "☆ Tandai"
                if st.button(btn_label, key=f"bm_{tab_prefix}_{idx}", use_container_width=True):
                    if is_bookmarked:
                        st.session_state['bookmarked_links'].remove(link_key)
                    else:
                        st.session_state['bookmarked_links'].append(link_key)
                    st.rerun()

            st.markdown(f"#### [{r['Judul']}]({r['Link']})")
            st.write(f"**Ringkasan:** {r['Ringkasan Berita']}")
            with st.expander("📖 Baca Isi Berita Lengkap"):
                st.write(r.get('Isi Berita', '*(Konten tidak tersedia)*'))


# =====================================================================
# Tabs Kategori
# =====================================================================
tab_labels = [
    f"📰 Semua ({len(df_for_tabs)})",
    f"📈 Saham ({len(df_for_tabs[df_for_tabs['Kategori Aset'] == 'SAHAM']) if 'Kategori Aset' in df_for_tabs.columns else 0})",
    f"💼 ETF & RD ({len(df_for_tabs[df_for_tabs['Kategori Aset'] == 'REKSADANA_ETF']) if 'Kategori Aset' in df_for_tabs.columns else 0})",
    f"🥇 Emas ({len(df_for_tabs[df_for_tabs['Kategori Aset'] == 'EMAS_KOMODITAS']) if 'Kategori Aset' in df_for_tabs.columns else 0})",
    f"🏛️ Makro ({len(df_for_tabs[df_for_tabs['Kategori Aset'] == 'MAKRO_REGULASI']) if 'Kategori Aset' in df_for_tabs.columns else 0})",
    f"📂 Umum ({len(df_for_tabs[df_for_tabs['Kategori Aset'] == 'UMUM']) if 'Kategori Aset' in df_for_tabs.columns else 0})",
    f"⭐ Tersimpan ({len(st.session_state['bookmarked_links'])})",
]

t1, t2, t3, t4, t5, t6, t7 = st.tabs(tab_labels)

with t1:
    tampilkan_konten_tab(df_for_tabs, tab_prefix="t1")
with t2:
    if 'Kategori Aset' in df_for_tabs.columns:
        tampilkan_konten_tab(df_for_tabs[df_for_tabs['Kategori Aset'] == 'SAHAM'], tab_prefix="t2")
    else:
        st.info("Kolom Kategori Aset tidak tersedia.")
with t3:
    if 'Kategori Aset' in df_for_tabs.columns:
        tampilkan_konten_tab(df_for_tabs[df_for_tabs['Kategori Aset'] == 'REKSADANA_ETF'], tab_prefix="t3")
    else:
        st.info("Kolom Kategori Aset tidak tersedia.")
with t4:
    if 'Kategori Aset' in df_for_tabs.columns:
        tampilkan_konten_tab(df_for_tabs[df_for_tabs['Kategori Aset'] == 'EMAS_KOMODITAS'], tab_prefix="t4")
    else:
        st.info("Kolom Kategori Aset tidak tersedia.")
with t5:
    if 'Kategori Aset' in df_for_tabs.columns:
        tampilkan_konten_tab(df_for_tabs[df_for_tabs['Kategori Aset'] == 'MAKRO_REGULASI'], tab_prefix="t5")
    else:
        st.info("Kolom Kategori Aset tidak tersedia.")
with t6:
    if 'Kategori Aset' in df_for_tabs.columns:
        tampilkan_konten_tab(df_for_tabs[df_for_tabs['Kategori Aset'] == 'UMUM'], tab_prefix="t6")
    else:
        st.info("Kolom Kategori Aset tidak tersedia.")
with t7:
    if 'Link' in df_for_tabs.columns:
        df_saved = df_for_tabs[df_for_tabs['Link'].isin(st.session_state['bookmarked_links'])]
    else:
        df_saved = pd.DataFrame()
    if df_saved.empty:
        st.info("📭 Belum ada berita yang ditandai (Bookmark).")
    else:
        tampilkan_konten_tab(df_saved, tab_prefix="t7")

# =====================================================================
# Download Buttons
# =====================================================================
st.markdown("---")
section_header("📥", "Export Data Hasil Filter")

col_dl1, col_dl2, col_dl3 = st.columns(3)

# Siapkan dataframe untuk export
export_cols = ['Judul', 'Tanggal', 'Kategori Aset', 'Sentimen', 'Status Bursa',
               'Trigger/Emiten', 'Sumber', 'Ringkasan Berita', 'Link']
export_cols = [c for c in export_cols if c in df_tampil.columns]
df_csv = df_tampil[export_cols]

with col_dl1:
    st.download_button(
        "📄 Unduh CSV Ringkas",
        data=df_csv.to_csv(index=False).encode('utf-8'),
        file_name='laporan_berita.csv',
        mime='text/csv',
        use_container_width=True,
    )

with col_dl2:
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_csv.to_excel(writer, index=False, sheet_name='Berita')
        st.download_button(
            "📊 Unduh Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name='laporan_berita.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True,
        )
    except ImportError:
        st.info("💡 Install `openpyxl` untuk export Excel: `pip install openpyxl`")

with col_dl3:
    st.download_button(
        "🔗 Unduh JSON (untuk API)",
        data=df_csv.to_json(orient='records', indent=2, force_ascii=False).encode('utf-8'),
        file_name='laporan_berita.json',
        mime='application/json',
        use_container_width=True,
    )

st.caption(f"💡 *{len(df_csv)} berita akan diekspor sesuai filter aktif saat ini.*")
