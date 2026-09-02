"""
Halaman 4: Pusat Ekspor Laporan
==============================
Export TXT, Markdown, Excel, JSON, dengan executive summary
auto-generated, opsi multi-section, dan watermark waktu.
"""
import io
import json
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from utils_ui import (
    PALETTE,
    inject_shared_css, hero_header, section_header, metric_badge,
    kategori_indeks, hitung_sentimen_counts, get_top_movers, hitung_risk_score_per_trigger,
    hitung_diversity_index, get_dataframe_or_stop,
)

# =====================================================================
# Konfigurasi
# =====================================================================
st.set_page_config(
    page_title="Pusat Ekspor Laporan",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_shared_css()
hero_header(
    "Pusat Ekspor Laporan & Teks Siap Kirim",
    "TXT · Markdown · Excel · JSON · Executive Summary Auto-Generated"
)

# =====================================================================
# Data
# =====================================================================
df_raw = get_dataframe_or_stop()
skor_indeks = float(st.session_state.get('skor_indeks_val', 50.0))

# =====================================================================
# Panel Kustomisasi
# =====================================================================
with st.container(border=True):
    st.markdown("##### ⚙️ **Kustomisasi Format & Filter Laporan**")

    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    with col_c1:
        opt_hanya_negatif = st.checkbox("🚨 Hanya Berita Negatif", value=False, key="ex_neg")
    with col_c2:
        opt_sertakan_ringkasan = st.checkbox("📝 Sertakan Ringkasan", value=True, key="ex_ringkas")
    with col_c3:
        opt_sertakan_link = st.checkbox("🔗 Sertakan Tautan", value=True, key="ex_link")
    with col_c4:
        opt_sertakan_risk = st.checkbox("⚠️ Sertakan Risk Analytics", value=False, key="ex_risk")

    st.markdown("<hr style='margin: 12px 0; border-color: #30363d;'>", unsafe_allow_html=True)

    col_f1, col_f2, col_f3 = st.columns(3)
    list_kategori = sorted(df_raw['Kategori Aset'].dropna().unique().tolist()) if 'Kategori Aset' in df_raw.columns else []
    list_sumber = sorted(df_raw['Sumber'].dropna().unique().tolist()) if 'Sumber' in df_raw.columns else []
    list_sentimen = ['POSITIF', 'NETRAL', 'NEGATIF']

    with col_f1:
        selected_kategori = st.multiselect("📦 Filter Kategori Aset", options=list_kategori, default=[], key="ex_kat")
    with col_f2:
        selected_sumber = st.multiselect("📡 Filter Sumber Portal", options=list_sumber, default=[], key="ex_sum")
    with col_f3:
        selected_sentimen = st.multiselect("🎯 Filter Sentimen", options=list_sentimen, default=[], key="ex_sent")

st.markdown("<br>", unsafe_allow_html=True)

# =====================================================================
# Terapkan Filter
# =====================================================================
df_export = df_raw.copy()
if opt_hanya_negatif and 'Sentimen' in df_export.columns:
    df_export = df_export[df_export['Sentimen'] == 'NEGATIF']
if selected_kategori and 'Kategori Aset' in df_export.columns:
    df_export = df_export[df_export['Kategori Aset'].isin(selected_kategori)]
if selected_sumber and 'Sumber' in df_export.columns:
    df_export = df_export[df_export['Sumber'].isin(selected_sumber)]
if selected_sentimen and 'Sentimen' in df_export.columns:
    df_export = df_export[df_export['Sentimen'].isin(selected_sentimen)]

# =====================================================================
# Metrik Ekspor
# =====================================================================
waktu_sekarang = datetime.now().strftime("%d-%m-%Y %H:%M WIB")
label_indeks, pen_indeks, _ = kategori_indeks(skor_indeks)
total_artikel = len(df_export)
agg = hitung_sentimen_counts(df_export)
total_negatif_all = len(df_raw[df_raw['Sentimen'] == 'NEGATIF']) if 'Sentimen' in df_raw.columns else 0

section_header("📊", "Ringkasan Ekspor")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    metric_badge(f"{total_artikel:,}", "Total Diekspor", "artikel", PALETTE['primary_alt'])
with col_m2:
    metric_badge(f"{skor_indeks:.0f}%", label_indeks.split('(')[0].strip(),
                 pen_indeks[:35] + "...", PALETTE['primary_alt'])
with col_m3:
    metric_badge(f"{total_negatif_all:,}", "Total Isu Negatif", "keseluruhan", PALETTE['neg'])
with col_m4:
    metric_badge(f"{agg['pos']}/{agg['neg']}/{agg['net']}",
                 "Pos/Neg/Net", "distribusi", PALETTE['purple'])

st.markdown("---")

# =====================================================================
# Generator Teks Laporan (TXT & Markdown)
# =====================================================================
def generate_txt_report(include_summary: bool = True) -> str:
    """Generate plain text report."""
    lines = []
    lines.append("=" * 60)
    lines.append("RADAR BERITA PORTOFOLIO SAHAM LOKAL")
    lines.append(f"Generated: {waktu_sekarang}")
    lines.append(f"Indeks Sentimen: {skor_indeks:.1f}% — {label_indeks}")
    lines.append(f"Total Berita: {total_artikel} Artikel")
    lines.append(f"Positif: {agg['pos']} | Netral: {agg['net']} | Negatif: {agg['neg']}")
    lines.append("=" * 60)
    lines.append("")

    if include_summary:
        lines.append("## RINGKASAN EKSEKUTIF")
        lines.append(pen_indeks)
        lines.append("")
        top_movers = get_top_movers(df_export, n=3)
        if top_movers['gainers']:
            lines.append("Top Gainers:")
            for g in top_movers['gainers']:
                lines.append(f"  • {g['Trigger/Emiten']} (rasio: +{g['Sent_Ratio']:.1f})")
        if top_movers['losers']:
            lines.append("Top Losers:")
            for l in top_movers['losers']:
                lines.append(f"  • {l['Trigger/Emiten']} (rasio: {l['Sent_Ratio']:.1f})")
        lines.append("")
        lines.append("-" * 60)

    lines.append("## DAFTAR BERITA")
    lines.append("-" * 60)
    lines.append("")

    for i, row in df_export.reset_index(drop=True).iterrows():
        judul_clean = re.sub(r'\s+', ' ', str(row.get('Judul', ''))).strip()
        kategori_teks = f" [{row.get('Kategori Aset', '')}]" if row.get('Kategori Aset') else ""
        sentimen = row.get('Sentimen', '-')
        status_bursa = row.get('Status Bursa', '-')
        trigger = row.get('Trigger/Emiten', '-')

        lines.append(f"{i+1}. [{trigger}] ({sentimen}){kategori_teks} - {status_bursa}")
        lines.append(f"   {judul_clean}")

        if opt_sertakan_ringkasan:
            ringkasan_clean = re.sub(r'\s+', ' ', str(row.get('Ringkasan Berita', ''))).strip()
            if ringkasan_clean:
                lines.append(f"   _{ringkasan_clean}_")

        if opt_sertakan_link:
            link_asli = str(row.get('Link', ''))
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', link_asli)
            domain_pendek = domain_match.group(1) if domain_match else "Link"
            lines.append(f"   [Baca via {domain_pendek}]({link_asli})")

        lines.append("")

    if opt_sertakan_risk:
        lines.append("-" * 60)
        lines.append("## RISK ANALYTICS — Top 10 Emiten Berisiko")
        lines.append("-" * 60)
        risk_df = hitung_risk_score_per_trigger(df_export, top_n=10)
        if not risk_df.empty:
            for _, r in risk_df.iterrows():
                lines.append(f"  • {r['Trigger/Emiten']}: Risk Score = {r['Risk_Score']:+.1f} "
                             f"(P:{r['Positif_Pct']:.0f}% / N:{r['Negatif_Pct']:.0f}%)")
        lines.append("")

    lines.append("=" * 60)
    lines.append("Akhir Laporan — Radar Berita Portofolio Saham Lokal")
    return "\n".join(lines)


def generate_markdown_report() -> str:
    """Generate markdown report (untuk GitHub/Notion)."""
    md = []
    md.append(f"# 📊 Laporan Radar Berita Portofolio")
    md.append(f"**Generated:** {waktu_sekarang}  ")
    md.append(f"**Indeks Sentimen:** {skor_indeks:.1f}% — *{label_indeks}*  ")
    md.append(f"**Total Berita:** {total_artikel} artikel")
    md.append("")
    md.append("---")
    md.append("")

    # Executive Summary
    md.append("## 📋 Executive Summary")
    md.append(f"> {pen_indeks}")
    md.append("")
    md.append(f"| Metrik | Nilai |")
    md.append(f"|---|---|")
    md.append(f"| Positif | {agg['pos']} ({agg['pos']/max(total_artikel,1)*100:.1f}%) |")
    md.append(f"| Netral | {agg['net']} ({agg['net']/max(total_artikel,1)*100:.1f}%) |")
    md.append(f"| Negatif | {agg['neg']} ({agg['neg']/max(total_artikel,1)*100:.1f}%) |")
    md.append(f"| Diversity Index (Sumber) | {hitung_diversity_index(df_export, 'Sumber')} |")
    md.append("")

    # Top Movers
    top_movers = get_top_movers(df_export, n=3)
    if top_movers['gainers']:
        md.append("### 🚀 Top Gainers")
        md.append("| Emiten | Rasio Sentimen | Total |")
        md.append("|---|---|---|")
        for g in top_movers['gainers']:
            md.append(f"| {g['Trigger/Emiten']} | +{g['Sent_Ratio']:.1f} | {g['Total']} |")
        md.append("")
    if top_movers['losers']:
        md.append("### 🔻 Top Losers")
        md.append("| Emiten | Rasio Sentimen | Total |")
        md.append("|---|---|---|")
        for l in top_movers['losers']:
            md.append(f"| {l['Trigger/Emiten']} | {l['Sent_Ratio']:.1f} | {l['Total']} |")
        md.append("")

    md.append("---")
    md.append("")

    # Daftar Berita
    md.append("## 📰 Daftar Berita Lengkap")
    md.append("")

    for i, row in df_export.reset_index(drop=True).iterrows():
        judul = re.sub(r'\s+', ' ', str(row.get('Judul', ''))).strip()
        kategori_teks = f"`{row.get('Kategori Aset', '')}`" if row.get('Kategori Aset') else ""
        sentimen = row.get('Sentimen', '-')
        sentimen_emoji = {'POSITIF': '🟢', 'NEGATIF': '🔴', 'NETRAL': '⚪'}.get(sentimen, '⚪')

        md.append(f"### {i+1}. {sentimen_emoji} {row.get('Trigger/Emiten', '-')} — {judul}")
        md.append(f"**Sentimen:** {sentimen} | **Kategori:** {kategori_teks} | **Status:** {row.get('Status Bursa', '-')}  ")
        md.append(f"**Sumber:** {row.get('Sumber', '-')} | **Tanggal:** {row.get('Tanggal', '-')}  ")

        if opt_sertakan_ringkasan:
            ringkasan = re.sub(r'\s+', ' ', str(row.get('Ringkasan Berita', ''))).strip()
            if ringkasan:
                md.append(f"\n> {ringkasan}")

        if opt_sertakan_link:
            link = row.get('Link', '')
            if link:
                md.append(f"\n🔗 [Baca selengkapnya]({link})")
        md.append("")

    if opt_sertakan_risk:
        md.append("---")
        md.append("## ⚠️ Risk Analytics")
        risk_df = hitung_risk_score_per_trigger(df_export, top_n=10)
        if not risk_df.empty:
            md.append("| Emiten | Risk Score | Positif % | Negatif % |")
            md.append("|---|---|---|---|")
            for _, r in risk_df.iterrows():
                md.append(f"| {r['Trigger/Emiten']} | {r['Risk_Score']:+.1f} | {r['Positif_Pct']:.1f}% | {r['Negatif_Pct']:.1f}% |")
        md.append("")

    md.append("---")
    md.append(f"*Laporan dibuat otomatis oleh Radar Berita Portofolio Saham Lokal pada {waktu_sekarang}*")
    return "\n".join(md)


# Generate konten
txt_content = generate_txt_report(include_summary=True)
md_content = generate_markdown_report()

# =====================================================================
# Panel Export
# =====================================================================
section_header("📥", "Pilih Format & Download Laporan")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    st.markdown("##### 📄 **Format Teks (TXT)**")
    st.caption("Plain text — mudah disalin ke WhatsApp, Telegram, atau email.")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    st.download_button(
        label="📥 Unduh Laporan TXT",
        data=txt_content,
        file_name=f"ringkasan_radar_{timestamp}.txt",
        mime="text/plain",
        use_container_width=True,
        type="primary",
    )
    with st.expander("👁️ Pratinjau Teks"):
        st.code(txt_content[:3000] + ("\n\n... (dipotong)" if len(txt_content) > 3000 else ""),
                language="text")

with col_btn2:
    st.markdown("##### 📝 **Format Markdown (.md)**")
    st.caption("Markdown — untuk GitHub, Notion, Obsidian, atau blog.")
    st.download_button(
        label="📥 Unduh Laporan Markdown",
        data=md_content,
        file_name=f"ringkasan_radar_{timestamp}.md",
        mime="text/markdown",
        use_container_width=True,
        type="primary",
    )
    with st.expander("👁️ Pratinjau Markdown"):
        st.code(md_content[:3000] + ("\n\n... (dipotong)" if len(md_content) > 3000 else ""),
                language="markdown")

st.markdown("---")

col_btn3, col_btn4 = st.columns(2)
with col_btn3:
    st.markdown("##### 📊 **Format Excel (.xlsx)**")
    st.caption("Spreadsheet multi-sheet — Positif, Negatif, Netral.")
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Sheet utama
            export_cols_xl = ['Judul', 'Tanggal', 'Kategori Aset', 'Sentimen', 'Status Bursa',
                              'Trigger/Emiten', 'Sumber', 'Ringkasan Berita', 'Link']
            export_cols_xl = [c for c in export_cols_xl if c in df_export.columns]
            df_export[export_cols_xl].to_excel(writer, index=False, sheet_name='Semua')

            # Sheet per sentimen
            if 'Sentimen' in df_export.columns:
                for sent in ['POSITIF', 'NEGATIF', 'NETRAL']:
                    df_sent = df_export[df_export['Sentimen'] == sent]
                    if not df_sent.empty:
                        sheet_name = sent[:31]  # Excel limit
                        df_sent[export_cols_xl].to_excel(writer, index=False, sheet_name=sheet_name)

            # Sheet risk analytics
            if opt_sertakan_risk:
                risk_df = hitung_risk_score_per_trigger(df_export, top_n=20)
                if not risk_df.empty:
                    risk_df.to_excel(writer, index=False, sheet_name='Risk Analytics')

        st.download_button(
            label="📥 Unduh Excel Multi-Sheet",
            data=buffer.getvalue(),
            file_name=f"ringkasan_radar_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
    except ImportError:
        st.warning("💡 Install `openpyxl` terlebih dahulu: `pip install openpyxl`")

with col_btn4:
    st.markdown("##### 🔗 **Format JSON (API-Ready)**")
    st.caption("JSON terstruktur — untuk integrasi API, webhook, atau automation.")
    # Filter kolom agar JSON lebih ramping
    json_cols = ['Judul', 'Tanggal', 'Kategori Aset', 'Sentimen', 'Trigger/Emiten',
                 'Sumber', 'Link']
    json_cols = [c for c in json_cols if c in df_export.columns]
    json_payload = {
        "metadata": {
            "generated_at": waktu_sekarang,
            "skor_indeks": skor_indeks,
            "label_indeks": label_indeks,
            "total_artikel": total_artikel,
            "agregat_sentimen": agg,
        },
        "berita": df_export[json_cols].to_dict(orient='records'),
    }
    if opt_sertakan_risk:
        risk_df = hitung_risk_score_per_trigger(df_export, top_n=10)
        if not risk_df.empty:
            json_payload["risk_analytics"] = risk_df.to_dict(orient='records')

    st.download_button(
        label="📥 Unduh JSON",
        data=json.dumps(json_payload, indent=2, ensure_ascii=False).encode('utf-8'),
        file_name=f"ringkasan_radar_{timestamp}.json",
        mime="application/json",
        use_container_width=True,
        type="primary",
    )

st.markdown("---")
st.caption(f"💡 *{total_artikel} berita akan diekspor sesuai filter aktif. Indeks Sentimen: {skor_indeks:.1f}%*")
