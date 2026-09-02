"""
Halaman 2: Analisis Media & Portal
=================================
Eksplorasi fokus topik per portal, perilaku pemberitaan, status kesehatan
portal, media reliability score, dan word cloud judul berita.
"""
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from wordcloud import WordCloud

from utils_ui import (
    PALETTE,
    apply_dark_theme, styled_axes,
    inject_shared_css, hero_header, section_header, metric_badge, insight_card,
    hitung_sentimen_counts, hitung_diversity_index,
    get_media_reliability, get_dataframe_or_stop, safe_pie_labels,
    render_global_filter,
)

# =====================================================================
# Konfigurasi
# =====================================================================
st.set_page_config(
    page_title="Analisis Media & Portal",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_dark_theme()
inject_shared_css()
hero_header(
    "Analisis Mendalam Media & Portal Berita",
    "Eksplorasi Fokus Topik Aset · Perilaku Pemberitaan · Status Kesehatan Portal · Media Reliability"
)

# =====================================================================
# Master daftar portal terdaftar
# =====================================================================
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

# =====================================================================
# Data & Filter
# =====================================================================
df_raw = get_dataframe_or_stop()
df = render_global_filter(df_raw, key_prefix="page2")

# =====================================================================
# BAGIAN 1: Ringkasan Performa Media
# =====================================================================
section_header("📊", "Ringkasan Performa Media")

agg = hitung_sentimen_counts(df)
div_sumber = hitung_diversity_index(df, 'Sumber')
div_kategori = hitung_diversity_index(df, 'Kategori Aset')

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_badge(f"{df['Sumber'].nunique() if 'Sumber' in df.columns else 0}",
                 "Portal Aktif", f"dari {len(SEMUA_PORTAL_LIST)} terdaftar",
                 PALETTE['primary_alt'])
with c2:
    metric_badge(f"{agg['total']:,}", "Total Berita", "setelah filter",
                 PALETTE['primary_alt'])
with c3:
    metric_badge(f"{div_sumber}", "Diversity Sumber", "Shannon Index",
                 PALETTE['purple'])
with c4:
    metric_badge(f"{div_kategori}", "Diversity Kategori", "Shannon Index",
                 PALETTE['purple'])

st.markdown("<br>", unsafe_allow_html=True)

# =====================================================================
# BAGIAN 2: Heatmap Portal-Aset (BARU)
# =====================================================================
section_header("🔥", "Heatmap Sebaran Fokus Kategori Aset per Portal")

with st.container(border=True):
    st.caption("Heatmap ini menunjukkan intensitas pembahasan kategori aset oleh masing-masing portal. Warna lebih gelap = lebih banyak artikel.")
    if 'Sumber' in df.columns and 'Kategori Aset' in df.columns:
        pivot_portal_aset = df.groupby(['Sumber', 'Kategori Aset']).size().unstack(fill_value=0)
        # Normalisasi per baris untuk lihat proporsi
        pivot_normalized = pivot_portal_aset.div(pivot_portal_aset.sum(axis=1), axis=0).fillna(0) * 100

        fig_hm, ax_hm = plt.subplots(figsize=(11, max(4, len(pivot_portal_aset) * 0.35)))
        im = ax_hm.imshow(pivot_normalized.values, aspect='auto', cmap='YlOrRd', vmin=0)
        ax_hm.set_xticks(range(len(pivot_normalized.columns)))
        ax_hm.set_xticklabels(pivot_normalized.columns, rotation=30, ha='right', fontsize=9)
        ax_hm.set_yticks(range(len(pivot_normalized.index)))
        ax_hm.set_yticklabels(safe_pie_labels(pivot_normalized.index, max_len=24), fontsize=9)
        # Annotasi nilai
        for i in range(len(pivot_normalized.index)):
            for j in range(len(pivot_normalized.columns)):
                val = pivot_normalized.values[i, j]
                if val > 0:
                    color = 'white' if val > 40 else PALETTE['text_main']
                    ax_hm.text(j, i, f'{val:.0f}%', ha='center', va='center',
                               color=color, fontsize=7.5, fontweight='bold')
        cbar = plt.colorbar(im, ax=ax_hm, fraction=0.025, pad=0.02)
        cbar.set_label('% Pembahasan', color=PALETTE['text_main'], fontsize=9)
        cbar.ax.yaxis.set_tick_params(color=PALETTE['text_muted'])
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color=PALETTE['text_muted'])
        styled_axes(ax_hm)
        st.pyplot(fig_hm)
        plt.close(fig_hm)
    else:
        st.info("Data Sumber / Kategori Aset tidak tersedia.")

# =====================================================================
# BAGIAN 3: Word Cloud & Distribusi Waktu
# =====================================================================
section_header("☁️", "Word Cloud & Analisis Temporal")

col_f1, col_f2 = st.columns(2, gap="large")
with col_f1:
    with st.container(border=True):
        st.subheader("☁️ Word Cloud Judul Berita")
        st.caption("Visualisasi kata kunci paling sering muncul dalam judul berita.")
        if 'Judul' in df.columns and not df['Judul'].isnull().all():
            text_gabungan = " ".join(df['Judul'].dropna().astype(str).tolist())
            if len(text_gabungan.strip()) > 0:
                wordcloud = WordCloud(
                    width=600, height=350,
                    background_color='#0e1117',
                    colormap='Blues',
                    max_words=100,
                ).generate(text_gabungan)
                fig_wc, ax_wc = plt.subplots(figsize=(5, 3))
                fig_wc.patch.set_facecolor('#0e1117')
                ax_wc.imshow(wordcloud, interpolation='bilinear')
                ax_wc.axis('off')
                st.pyplot(fig_wc)
                plt.close(fig_wc)
            else:
                st.info("Teks judul tidak mencukupi untuk membuat Word Cloud.")
        else:
            st.info("Kolom 'Judul' tidak ditemukan dalam data.")

with col_f2:
    with st.container(border=True):
        st.subheader("⏰ Distribusi Waktu Publikasi")
        st.caption("Analisis jam rilis berita dominan dari hasil pemindaian.")
        kolom_waktu = None
        for col in ['Waktu', 'Tanggal', 'Jam', 'Timestamp', 'dt_sort']:
            if col in df.columns:
                kolom_waktu = col
                break
        if kolom_waktu:
            try:
                df['Jam_Temp'] = pd.to_datetime(df[kolom_waktu], errors='coerce').dt.hour
                jam_counts = df['Jam_Temp'].value_counts().sort_index()
                if not jam_counts.empty:
                    # Tandai jam puncak
                    peak_hour = jam_counts.idxmax()
                    peak_count = jam_counts.max()
                    st.metric("Jam Paling Produktif", f"{int(peak_hour):02d}:00",
                              delta=f"{int(peak_count)} artikel")
                    st.bar_chart(jam_counts, height=220, use_container_width=True)
                else:
                    st.info("Format waktu tidak dapat diurai ke dalam jam.")
            except Exception as e:
                st.info(f"Gagal memproses data waktu publikasi: {e}")
        else:
            st.info("Kolom waktu tidak terdeteksi di data.")

# =====================================================================
# BAGIAN 4: Produktivitas & Dominasi
# =====================================================================
section_header("🏆", "Produktivitas Portal & Dominasi Kategori")

col1, col2 = st.columns(2, gap="large")
with col1:
    with st.container(border=True):
        st.subheader("🏆 Portal Paling Produktif")
        if 'Sumber' in df.columns and not df['Sumber'].empty:
            top_portal = df['Sumber'].value_counts().idxmax()
            jumlah_top = df['Sumber'].value_counts().max()
            st.success(f"**{top_portal}** menjadi penyumbang berita terbanyak dengan total **{jumlah_top} artikel** dalam pemindaian sesi ini.")
            st.markdown("**📋 Rincian Jumlah Berita per Kanal:**")
            st.dataframe(
                df['Sumber'].value_counts().reset_index().rename(
                    columns={'index': 'Portal', 'count': 'Jumlah Berita', 'Sumber': 'Portal'}
                ),
                use_container_width=True, height=260,
            )
        else:
            st.info("Data Sumber tidak tersedia.")

with col2:
    with st.container(border=True):
        st.subheader("📈 Dominasi Fokus Kategori Aset")
        if 'Kategori Aset' in df.columns and not df['Kategori Aset'].empty:
            top_kategori = df['Kategori Aset'].value_counts().idxmax()
            jumlah_kat = df['Kategori Aset'].value_counts().max()
            st.info(f"Kategori aset yang paling mendominasi pemberitaan saat ini adalah **{top_kategori}** sebanyak **{jumlah_kat} artikel**.")
            st.markdown("**🥧 Persentase Kategori Aset:**")
            kat_counts = df['Kategori Aset'].value_counts()
            colors_kat = [PALETTE['primary'], PALETTE['pos'], PALETTE['warning'],
                          PALETTE['danger'], PALETTE['purple'], PALETTE['neg']]
            fig, ax = plt.subplots(figsize=(5, 4))
            fig.patch.set_facecolor('none')
            ax.set_facecolor('none')
            wedges, texts, autotexts = ax.pie(
                kat_counts,
                labels=safe_pie_labels(kat_counts.index, max_len=20),
                autopct='%1.1f%%', startangle=90,
                colors=colors_kat[:len(kat_counts)],
                pctdistance=0.75,
                wedgeprops=dict(width=0.42, edgecolor=PALETTE['bg_deep'], linewidth=2),
                textprops={'fontsize': 9, 'color': PALETTE['text_main']},
            )
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(8.5)
                autotext.set_weight('bold')
            ax.axis('equal')
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("Data Kategori Aset tidak tersedia.")

# =====================================================================
# BAGIAN 5: Media Reliability Score (BARU)
# =====================================================================
section_header("🩺", "Skor Reliabilitas & Performa Portal")

with st.container(border=True):
    st.caption("Mengukur reliabilitas portal berdasarkan volume artikel, tingkat keberhasilan scraping, dan konsistensi.")
    rekap = get_media_reliability(df)
    if not rekap.empty:
        # Tambahkan kategori reliabilitas
        def reliability_grade(row):
            if row['Total'] == 0:
                return "⚪ Tidak Aktif"
            if row['Total'] >= 10 and row['Success_Rate'] >= 80:
                return "🟢 Sangat Andal"
            if row['Total'] >= 5 and row['Success_Rate'] >= 60:
                return "🟡 Andal"
            if row['Total'] > 0:
                return "🟠 Perlu Perhatian"
            return "⚪ Tidak Aktif"

        rekap['Kategori'] = rekap.apply(reliability_grade, axis=1)
        st.dataframe(
            rekap[['Sumber', 'Kategori', 'Total', 'Success_Rate']].rename(
                columns={'Success_Rate': 'Success Rate (%)'}
            ),
            use_container_width=True, hide_index=True, height=350
        )
    else:
        st.info("Data tidak cukup untuk analisis reliabilitas.")

# =====================================================================
# BAGIAN 6: Laporan Kesehatan Portal
# =====================================================================
section_header("🏥", "Laporan Kesehatan & Performa Scraping Seluruh Portal")

with st.container(border=True):
    st.caption("Memantau seluruh kanal terdaftar untuk mengetahui portal mana yang berhasil menyumbang berita dan mana yang kosong.")

    if 'Akses' in df.columns and 'Sumber' in df.columns:
        rekap_aktual = df.groupby('Sumber').agg(
            Total_Artikel=('Judul', 'count'),
            Konten_Penuh=('Akses', lambda x: (x == 'Penuh').sum()),
            Terbatas_Paywall=('Akses', lambda x: x.isin(['Terbatas', 'Paywall']).sum()),
            Error_Gagal=('Akses', lambda x: x.astype(str).str.contains('Error|Gagal', case=False, na=False).sum())
        ).reset_index()

        df_master_portal = pd.DataFrame({'Sumber': SEMUA_PORTAL_LIST})
        rekap_portal = pd.merge(df_master_portal, rekap_aktual, on='Sumber', how='left').fillna({
            'Total_Artikel': 0, 'Konten_Penuh': 0,
            'Terbatas_Paywall': 0, 'Error_Gagal': 0
        })

        rekap_portal['Tingkat Sukses (%)'] = (
            (rekap_portal['Konten_Penuh'] / rekap_portal['Total_Artikel'].replace(0, 1)) * 100
        ).round(1)

        def tentukan_status_sehat(row):
            if row['Total_Artikel'] == 0:
                return "⚪ 0 Artikel / Tidak Ada Berita"
            elif row['Error_Gagal'] > 0:
                return "🔴 Gangguan / Error"
            elif row['Terbatas_Paywall'] > row['Konten_Penuh']:
                return "🟡 Banyak Paywall / Terbatas"
            else:
                return "🟢 Sangat Sehat (Optimal)"

        rekap_portal['Status Sistem'] = rekap_portal.apply(tentukan_status_sehat, axis=1)
        rekap_portal = rekap_portal[[
            'Sumber', 'Status Sistem', 'Total_Artikel', 'Konten_Penuh',
            'Terbatas_Paywall', 'Error_Gagal', 'Tingkat Sukses (%)'
        ]]
        rekap_portal = rekap_portal.sort_values(by='Total_Artikel', ascending=False).reset_index(drop=True)

        total_portal_scan = len(rekap_portal)
        portal_aktif = len(rekap_portal[rekap_portal['Total_Artikel'] > 0])
        portal_kosong = len(rekap_portal[rekap_portal['Total_Artikel'] == 0])

        m1, m2, m3 = st.columns(3)
        with m1:
            metric_badge(f"{total_portal_scan}", "Total Kanal Terdaftar",
                         color=PALETTE['primary_alt'])
        with m2:
            metric_badge(f"{portal_aktif}", "Kanal Berisi Berita",
                         color=PALETTE['pos'])
        with m3:
            metric_badge(f"{portal_kosong}", "Kanal 0 Artikel / Kosong",
                         color=PALETTE['net'])

        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(rekap_portal, use_container_width=True, hide_index=True, height=420)
        st.caption("ℹ️ *Status '0 Artikel' menandakan portal aktif diperiksa, namun tidak ada berita yang cocok dengan kata kunci portofolio atau rentang waktu pada sesi pemindaian tersebut.*")
    else:
        st.info("Data status akses belum tersedia.")
