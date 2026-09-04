"""
Halaman 1: Ringkasan Live Radar
==============================
Ringkasan eksekutif pasar, indeks sentimen, top movers, risk analytics,
tren 7 hari, news velocity, dan wordcloud kata kunci.
"""
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from wordcloud import WordCloud

# Import utility terpusat
from utils_ui import (
    PALETTE, SENTIMEN_COLORS, SENTIMEN_ORDER,
    apply_dark_theme, styled_axes,
    inject_shared_css, main_header, section_header, metric_badge, insight_card,
    hitung_sentimen_counts, hitung_kata_kunci, kategori_indeks,
    hitung_risk_score_per_trigger, hitung_diversity_index,
    get_top_movers, get_sentiment_trend_7d, get_news_velocity,
    get_dataframe_or_stop, safe_pie_labels, render_global_filter,
)

# =====================================================================
# Konfigurasi Halaman
# =====================================================================
st.set_page_config(
    page_title="Ringkasan Live Radar",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_dark_theme()
inject_shared_css()

# =====================================================================
# Header Utama
# =====================================================================
main_header(
    "Ringkasan Eksekutif & Live Radar",
    "Advanced Market Intelligence · Sentiment Index · NLP Keyword Tracking · Risk Analytics"
)

# =====================================================================
# Pengambilan & Validasi Data
# =====================================================================
df_raw = get_dataframe_or_stop()
duration = st.session_state.get('duration_scan', 0)
skor_indeks = float(st.session_state.get('skor_indeks_val', 50.0))

if 'Sentimen' not in df_raw.columns:
    st.error("❌ Kolom 'Sentimen' tidak ditemukan pada data.")
    st.stop()

# Filter panel interaktif
df = render_global_filter(df_raw, key_prefix="page1")

# =====================================================================
# Banner Indeks Sentimen
# =====================================================================
agg = hitung_sentimen_counts(df)
n_pos, n_net, n_neg, n_total = agg['pos'], agg['net'], agg['neg'], agg['total']
label_indeks, pen, banner_color = kategori_indeks(skor_indeks)

st.markdown(
    f"""
    <div class="sentiment-banner" style="border-left-color: {banner_color};">
        <h3 style="margin: 0 0 6px 0; color: #f0f6fc; font-weight: 700;">
            Indeks Sentimen Pasar: <span style="color: {banner_color};">{skor_indeks:.1f}%</span>
            — <em>{label_indeks}</em>
        </h3>
        <p style="margin: 0; color: #8b949e; font-size: 1rem;">{pen}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.progress(int(max(0, min(100, skor_indeks))))
st.markdown("<br>", unsafe_allow_html=True)

# =====================================================================
# Metrik Utama
# =====================================================================
pct_pos = round((n_pos / n_total) * 100, 1) if n_total else 0.0
pct_neg = round((n_neg / n_total) * 100, 1) if n_total else 0.0
pct_net = round((n_net / n_total) * 100, 1) if n_total else 0.0

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    metric_badge(f"{n_total:,}", "Total Berita", f"{n_total} aktif", PALETTE["primary_alt"])
with m2:
    metric_badge(f"{n_pos:,}", "Positif", f"{pct_pos}%", PALETTE["pos"])
with m3:
    metric_badge(f"{n_neg:,}", "Negatif", f"{pct_neg}%", PALETTE["neg"])
with m4:
    metric_badge(f"{n_net:,}", "Netral", f"{pct_net}%", PALETTE["net"])
with m5:
    diversity = hitung_diversity_index(df, 'Sumber')
    metric_badge(f"{diversity}", "Diversity Index", "Shannon", PALETTE["purple"])

st.markdown("---")

# =====================================================================
# Insight Cards Otomatis
# =====================================================================
col_ins1, col_ins2, col_ins3 = st.columns(3)
with col_ins1:
    if pct_pos > 60:
        insight_card("📈 Momentum Bullish", f"Sentimen positif mendominasi {pct_pos}% pemberitaan. Pertahankan eksposur pada emiten dengan fundamental kuat.", "success")
    elif pct_neg > 60:
        insight_card("⚠️ Tekanan Bearish", f"Berita negatif mencapai {pct_neg}%. Tinjau ulang portofolio dan pertimbangkan hedging.", "danger")
    else:
        insight_card("⚖️ Pasar Seimbang", f"Positif {pct_pos}% | Negatif {pct_neg}%. Pasar dalam fase konsolidasi.", "default")
with col_ins2:
    top_movers = get_top_movers(df, n=1)
    if top_movers['gainers'] and top_movers['gainers'][0]['Sent_Ratio'] > 50:
        g = top_movers['gainers'][0]
        insight_card("🚀 Top Gainer", f"<b>{g['Trigger/Emiten']}</b> dengan rasio sentimen +{g['Sent_Ratio']:.0f} dari {g['Total']} artikel.", "success")
    else:
        insight_card("ℹ️ Top Gainer", "Belum ada emiten dengan dominasi sentimen positif yang signifikan.", "default")
with col_ins3:
    if top_movers['losers'] and top_movers['losers'][0]['Sent_Ratio'] < -30:
        l = top_movers['losers'][0]
        insight_card("🔻 Top Loser", f"<b>{l['Trigger/Emiten']}</b> dengan rasio sentimen {l['Sent_Ratio']:.0f} dari {l['Total']} artikel. Pantau risiko.", "warning")
    else:
        insight_card("✅ Risiko Terkendali", "Tidak ada emiten dengan tekanan sentimen negatif yang ekstrem.", "success")

st.markdown("---")

# =====================================================================
# KELOMPOK 1: Proporsi & Komposisi Sentimen
# =====================================================================
c_inf1, c_inf2 = st.columns(2)
with c_inf1:
    with st.container(border=True):
        st.markdown("##### 🎯 **Proporsi Sentimen Keseluruhan**")
        if sum([n_pos, n_net, n_neg]) == 0:
            st.info("Tidak ada data sentimen untuk ditampilkan.")
        else:
            fig_donut, ax_donut = plt.subplots(figsize=(5, 4))
            _, _, autotexts = ax_donut.pie(
                [n_pos, n_net, n_neg],
                labels=['Positif', 'Netral', 'Negatif'],
                colors=SENTIMEN_COLORS,
                autopct='%1.1f%%',
                startangle=90,
                wedgeprops=dict(width=0.5, edgecolor=PALETTE['bg_panel'], linewidth=2),
            )
            for at in autotexts:
                at.set_color('white')
                at.set_weight('bold')
            ax_donut.axis('equal')
            st.pyplot(fig_donut)
            plt.close(fig_donut)

with c_inf2:
    with st.container(border=True):
        st.markdown("##### 📦 **Komposisi Sentimen per Kategori Aset**")
        if 'Kategori Aset' in df.columns and not df['Kategori Aset'].dropna().empty:
            pivot_kat_sentimen = df.groupby(['Kategori Aset', 'Sentimen']).size().unstack(fill_value=0)
            for col in SENTIMEN_ORDER:
                if col not in pivot_kat_sentimen.columns:
                    pivot_kat_sentimen[col] = 0
            st.bar_chart(
                pivot_kat_sentimen[SENTIMEN_ORDER],
                color=SENTIMEN_COLORS,
                height=245,
                use_container_width=True,
            )
        else:
            st.info("Data Kategori Aset belum tersedia.")

# =====================================================================
# KELOMPOK 2: Top Movers
# =====================================================================
section_header("🚀", "Top Movers — Emiten dengan Pergerakan Sentimen Signifikan")

movers = get_top_movers(df, n=5)
mv1, mv2, mv3 = st.columns(3)
with mv1:
    with st.container(border=True):
        st.markdown("##### 🟢 **Top Gainers (Sentimen Positif)**")
        if movers['gainers']:
            for g in movers['gainers']:
                st.markdown(
                    f"""
                    <div class="insight-card success">
                        <div class="insight-title">{g['Trigger/Emiten']}</div>
                        <div class="insight-text">
                            Rasio: <b style="color:#2ea043">+{g['Sent_Ratio']:.1f}</b> ·
                            {g['POSITIF']} positif dari {g['Total']} berita
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )
        else:
            st.info("Belum ada data gainer.")
with mv2:
    with st.container(border=True):
        st.markdown("##### 🔴 **Top Losers (Sentimen Negatif)**")
        if movers['losers']:
            for l in movers['losers']:
                variant = "danger" if l['Sent_Ratio'] < -50 else "warning"
                st.markdown(
                    f"""
                    <div class="insight-card {variant}">
                        <div class="insight-title">{l['Trigger/Emiten']}</div>
                        <div class="insight-text">
                            Rasio: <b style="color:#f85149">{l['Sent_Ratio']:.1f}</b> ·
                            {l['NEGATIF']} negatif dari {l['Total']} berita
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )
        else:
            st.info("Belum ada data loser.")
with mv3:
    with st.container(border=True):
        st.markdown("##### 📰 **Most Discussed (Paling Banyak Dibicarakan)**")
        if movers['most_discussed']:
            for m in movers['most_discussed']:
                warna = "#2ea043" if m['Sent_Ratio'] > 0 else "#f85149"
                st.markdown(
                    f"""
                    <div class="insight-card">
                        <div class="insight-title">{m['Trigger/Emiten']}</div>
                        <div class="insight-text">
                            <b>{m['Total']} artikel</b> · Sentimen: <b style="color:{warna}">{m['Sent_Ratio']:+.1f}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )
        else:
            st.info("Belum ada data.")

# =====================================================================
# KELOMPOK 3: Tren Sentimen 7 Hari + Velocity
# =====================================================================
section_header("📈", "Tren Sentimen Harian & Kecepatan Publikasi")

tr7_col1, tr7_col2 = st.columns([1.5, 1])
with tr7_col1:
    with st.container(border=True):
        st.markdown("##### 📊 **Tren Indeks Sentimen Harian (7 Hari Terakhir)**")
        trend_df = get_sentiment_trend_7d(df)
        if not trend_df.empty:
            fig_tr, ax_tr = plt.subplots(figsize=(10, 3.5))
            dates = pd.to_datetime(trend_df['Tanggal'])
            ax_tr.plot(
                dates, trend_df['Index'],
                marker='o', linewidth=2.5,
                color=PALETTE['primary_alt'],
                markersize=8,
                markerfacecolor=PALETTE['primary'],
                markeredgecolor='white',
                markeredgewidth=1.5,
            )
            ax_tr.axhline(y=50, color=PALETTE['net'], linestyle='--', alpha=0.5, label='Netral (50)')
            ax_tr.fill_between(dates, 50, trend_df['Index'],
                               where=(trend_df['Index'] >= 50),
                               color=PALETTE['pos'], alpha=0.15, interpolate=True)
            ax_tr.fill_between(dates, 50, trend_df['Index'],
                               where=(trend_df['Index'] < 50),
                               color=PALETTE['neg'], alpha=0.15, interpolate=True)
            styled_axes(ax_tr)
            ax_tr.set_ylim(0, 100)
            ax_tr.set_ylabel('Indeks', fontsize=10)
            ax_tr.grid(axis='y', linestyle='--', alpha=0.3)
            ax_tr.legend(loc='upper right', frameon=False, fontsize=9)
            st.pyplot(fig_tr)
            plt.close(fig_tr)
        else:
            st.info("Data tanggal tidak cukup untuk membuat tren 7 hari.")

with tr7_col2:
    with st.container(border=True):
        st.markdown("##### 🔥 **News Velocity (Kecepatan Publikasi per Jam)**")
        velocity = get_news_velocity(df)
        if not velocity.empty:
            st.metric("Rata-rata Berita/Jam", f"{velocity['Jumlah'].mean():.1f}",
                      delta=f"Puncak: {velocity['Jumlah'].max()} artikel")
            spikes = velocity[velocity['Anomali'] == '🔥 Spike']
            if not spikes.empty:
                st.markdown(f"**{len(spikes)} Spike Terdeteksi**")
                st.dataframe(
                    spikes.rename(columns={'Bucket': 'Waktu', 'Jumlah': 'Jml'})[['Waktu', 'Jml']],
                    hide_index=True, use_container_width=True, height=200
                )
            else:
                st.success("✅ Tidak ada anomali volume publikasi.")
        else:
            st.info("Data waktu tidak tersedia.")

# =====================================================================
# KELOMPOK 4: Risk Score per Trigger
# =====================================================================
section_header("⚠️", "Risk Analytics — Skor Risiko per Emiten")

with st.container(border=True):
    st.caption("Skor risiko: **(Negatif×2 + Netral×0.5 − Positif) / Total × 100**. Range: -100 (sangat positif) hingga +100 (sangat negatif).")
    risk_df = hitung_risk_score_per_trigger(df, top_n=10)
    if not risk_df.empty:
        fig_risk, ax_risk = plt.subplots(figsize=(10, 4.5))
        df_sorted = risk_df.sort_values('Risk_Score')
        colors_risk = [
            PALETTE['pos'] if s < 0 else PALETTE['neg'] if s > 30 else PALETTE['warning']
            for s in df_sorted['Risk_Score']
        ]
        bars = ax_risk.barh(
            df_sorted['Trigger/Emiten'],
            df_sorted['Risk_Score'],
            color=colors_risk, alpha=0.9, edgecolor='none',
        )
        for bar, val in zip(bars, df_sorted['Risk_Score']):
            x_pos = val + (2 if val >= 0 else -2)
            ha = 'left' if val >= 0 else 'right'
            ax_risk.text(x_pos, bar.get_y() + bar.get_height() / 2,
                         f'{val:+.1f}', va='center', ha=ha,
                         color='white', fontsize=9, fontweight='bold')
        styled_axes(ax_risk)
        ax_risk.axvline(x=0, color=PALETTE['border'], linewidth=0.8)
        ax_risk.set_xlabel('Risk Score', fontsize=10)
        ax_risk.grid(axis='x', linestyle='--', alpha=0.3)
        st.pyplot(fig_risk)
        plt.close(fig_risk)
    else:
        st.info("Data Trigger/Emiten tidak cukup untuk analisis risiko.")

# =====================================================================
# KELOMPOK 5: Share of Voice & Media Bias
# =====================================================================
section_header("📡", "Share of Voice & Media Bias Analyzer")

col_p1, col_p2 = st.columns([1.2, 1.8])
with col_p1:
    with st.container(border=True):
        st.markdown("##### 📊 **Porsi Distribusi Portal (Share of Voice)**")
        if 'Sumber' in df.columns and not df['Sumber'].dropna().empty:
            distribusi_portal = df['Sumber'].value_counts()
            fig_voice, ax_voice = plt.subplots(figsize=(5, 4.6))
            ax_voice.pie(
                distribusi_portal,
                labels=safe_pie_labels(distribusi_portal.index, max_len=16),
                autopct='%1.1f%%',
                startangle=140,
                colors=plt.cm.Paired.colors,
                wedgeprops=dict(width=0.5, edgecolor=PALETTE['bg_panel'], linewidth=2),
                textprops={'fontsize': 8.5},
            )
            ax_voice.axis('equal')
            st.pyplot(fig_voice)
            plt.close(fig_voice)
        else:
            st.info("Data sumber berita tidak tersedia.")
with col_p2:
    with st.container(border=True):
        st.markdown("##### 🎭 **Peta Sentimen per Media (Media Bias Analyzer)**")
        if 'Sumber' in df.columns and not df['Sumber'].dropna().empty:
            sentimen_media = df.groupby(['Sumber', 'Sentimen']).size().unstack(fill_value=0)
            for col in SENTIMEN_ORDER:
                if col not in sentimen_media.columns:
                    sentimen_media[col] = 0
            st.bar_chart(
                sentimen_media[SENTIMEN_ORDER],
                color=SENTIMEN_COLORS,
                height=315,
                use_container_width=True,
            )
        else:
            st.info("Data sumber berita tidak tersedia.")

# =====================================================================
# KELOMPOK 6: Dominasi Kategori Aset
# =====================================================================
section_header("📦", "Dominasi Kategori Aset Portofolio (Share of Assets)")

with st.container(border=True):
    if 'Kategori Aset' in df.columns and not df['Kategori Aset'].dropna().empty:
        aset_counts = df['Kategori Aset'].value_counts()
        fig_asset, ax_asset = plt.subplots(figsize=(10, 3.2))
        ax_asset.barh(
            aset_counts.index[::-1],
            aset_counts.values[::-1],
            color=PALETTE['primary'], height=0.6, edgecolor='none', alpha=0.9,
        )
        styled_axes(ax_asset)
        ax_asset.grid(axis='x', linestyle='--', alpha=0.3)
        ax_asset.set_xlabel('Jumlah Artikel', fontsize=10)
        st.pyplot(fig_asset)
        plt.close(fig_asset)
    else:
        st.info("Data Kategori Aset tidak tersedia.")

# =====================================================================
# KELOMPOK 7: Status Scraping & Tren Jam
# =====================================================================
section_header("🕒", "Performa Ekstraksi & Tren Waktu")

c_t1, c_t2 = st.columns(2)
with c_t1:
    with st.container(border=True):
        st.markdown("##### 🩺 **Status Keberhasilan Scraping Portal**")
        if 'Akses' in df.columns and not df['Akses'].dropna().empty:
            akses_counts = df['Akses'].value_counts()
            fig_aks, ax_aks = plt.subplots(figsize=(5, 3))
            ax_aks.bar(
                akses_counts.index.astype(str),
                akses_counts.values,
                color=[PALETTE['primary'], PALETTE['warning'], PALETTE['neg']],
                width=0.5, alpha=0.9,
            )
            styled_axes(ax_aks)
            ax_aks.grid(axis='y', linestyle='--', alpha=0.3)
            ax_aks.set_ylabel('Jumlah Berita', fontsize=10)
            st.pyplot(fig_aks)
            plt.close(fig_aks)
        else:
            st.info("Data status akses tidak tersedia.")

with c_t2:
    with st.container(border=True):
        st.markdown("##### ⏰ **Matriks Sentimen per Jam**")
        if 'dt_sort' in df.columns:
            df_chart_valid = df[df['dt_sort'] != datetime.min].copy()
            if not df_chart_valid.empty:
                df_chart_valid['Jam'] = df_chart_valid['dt_sort'].dt.strftime('%H:00')
                jam_order = sorted(df_chart_valid['Jam'].unique())
                tren_sentimen_jam = (
                    df_chart_valid.groupby(['Jam', 'Sentimen'])
                    .size().unstack(fill_value=0).reindex(jam_order)
                )
                for col in SENTIMEN_ORDER:
                    if col not in tren_sentimen_jam.columns:
                        tren_sentimen_jam[col] = 0
                st.bar_chart(
                    tren_sentimen_jam[SENTIMEN_ORDER],
                    color=SENTIMEN_COLORS,
                    height=200,
                    use_container_width=True,
                )
            else:
                st.info("Format tanggal tidak memuat informasi jam yang valid.")
        else:
            st.info("Kolom 'dt_sort' tidak tersedia.")

# =====================================================================
# KELOMPOK 8: Top Triggers & Word Cloud
# =====================================================================
section_header("🏷️", "Peringkat Trigger & Deep-Dive Kata Kunci")

with st.container(border=True):
    st.markdown("##### 🎯 **Top Trigger / Emiten Paling Sering Dibahas**")
    if 'Trigger/Emiten' in df.columns and not df['Trigger/Emiten'].dropna().empty:
        top_triggers = df['Trigger/Emiten'].value_counts().head(8).reset_index()
        top_triggers.columns = ['Trigger', 'Jumlah']
        fig_trig, ax_trig = plt.subplots(figsize=(10, 3.2))
        ax_trig.barh(
            top_triggers['Trigger'][::-1],
            top_triggers['Jumlah'][::-1],
            color=PALETTE['primary_alt'], height=0.6, alpha=0.9,
        )
        styled_axes(ax_trig)
        ax_trig.grid(axis='x', linestyle='--', alpha=0.3)
        ax_trig.set_xlabel('Jumlah Artikel', fontsize=10)
        st.pyplot(fig_trig)
        plt.close(fig_trig)
    else:
        st.info("Data trigger emiten tidak tersedia.")

text_columns = [c for c in ['Judul', 'Ringkasan Berita', 'Isi Berita'] if c in df.columns]
gabung_tuple = tuple(
    val for col in text_columns
    for val in df[col].dropna().astype(str).tolist()
)
kata_bersih, top_10_df = hitung_kata_kunci(gabung_tuple, top_n=10)

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.markdown("##### ☁️ **Visual Word Cloud**")
        if kata_bersih:
            wc = WordCloud(
                width=500, height=310,
                background_color=PALETTE['bg_panel'],
                colormap='Blues',
            ).generate(" ".join(kata_bersih))
            fig_wc, ax_wc = plt.subplots(figsize=(6, 3.4))
            ax_wc.imshow(wc, interpolation='bilinear')
            ax_wc.axis("off")
            st.pyplot(fig_wc)
            plt.close(fig_wc)
        else:
            st.info("Tidak cukup teks untuk membuat word cloud.")

with c2:
    with st.container(border=True):
        st.markdown("##### 🔤 **Top 10 Kata Kunci**")
        if not top_10_df.empty:
            st.bar_chart(
                top_10_df.set_index('Kata'),
                height=275,
                color=PALETTE['primary_alt'],
            )
        else:
            st.info("Belum ada kata kunci yang dapat dihitung.")
