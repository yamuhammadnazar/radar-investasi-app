"""Uji cepat: pastikan kategori baru terklasifikasi benar & terdaftar di UI.

Jalankan: python _uji_kategori.py   (hapus file ini setelah verifikasi)
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# --- Ambil KATEGORI_PORTOFOLIO & PEMETAAN_KATEGORI dari app.py tanpa
# menjalankan UI Streamlit: baca AST-nya saja (aman, tanpa import streamlit).
with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as f:
    pohon = ast.parse(f.read())

KATEGORI_PORTOFOLIO = None
PEMETAAN_KATEGORI = None
URUTAN_PRIORITAS_KATEGORI = None
for node in pohon.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "KATEGORI_PORTOFOLIO":
                KATEGORI_PORTOFOLIO = ast.literal_eval(node.value)
            if isinstance(t, ast.Name) and t.id == "PEMETAAN_KATEGORI":
                PEMETAAN_KATEGORI = ast.literal_eval(node.value)
            if isinstance(t, ast.Name) and t.id == "URUTAN_PRIORITAS_KATEGORI":
                URUTAN_PRIORITAS_KATEGORI = ast.literal_eval(node.value)

assert KATEGORI_PORTOFOLIO and PEMETAAN_KATEGORI, "Gagal membaca konstanta dari app.py"
assert URUTAN_PRIORITAS_KATEGORI, "Gagal membaca URUTAN_PRIORITAS_KATEGORI dari app.py"

urutan = [k for k in URUTAN_PRIORITAS_KATEGORI if k in KATEGORI_PORTOFOLIO] + [
    k for k in KATEGORI_PORTOFOLIO if k not in URUTAN_PRIORITAS_KATEGORI
]
_POLA = {
    kat: [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in sorted(set(KATEGORI_PORTOFOLIO[kat]), key=len, reverse=True)]
    for kat in urutan
}


def tentukan(teks):
    teks = teks.lower()
    for kat, pola in _POLA.items():
        for p in pola:
            if p.search(teks):
                return PEMETAAN_KATEGORI.get(kat, "MAKRO_REGULASI")
    return "MAKRO_REGULASI"


KASUS = {
    "politik": [
        ("Pilkada Kalbar 2024: KPU tetapkan jadwal kampanye", "POLITIK / LOKAL"),
        ("Presiden panggil menteri bahas koalisi partai politik", "POLITIK"),
        ("DPR sahkan RUU, fraksi menyampaikan pendapat akhir", "POLITIK"),
    ],
    "kalbar/ngabang": [
        ("Bupati Landak resmikan jalan di Kecamatan Ngabang", "LOKAL_KALBAR_NGABANG"),
        ("Pemkab Landak bersama Pemprov Kalbar bahas banjir", "LOKAL_KALBAR_NGABANG"),
        ("Banjir rendam Pontianak, BPBD siapkan posko", "LOKAL_KALBAR_NGABANG"),
    ],
    "kesehatan": [
        ("Kemenkes tambah kuota vaksin imunisasi anak", "KESEHATAN"),
        ("RSUD Landak buka layanan baru, klaim BPJS tetap gratis", "KESEHATAN"),
        ("Kasus demam berdarah di Singkawang meningkat", "KESEHATAN"),
        ("Puskesmas perkuat stunting dan gizi ibu hamil", "KESEHATAN"),
    ],
    "institusi": [
        ("KPK tetapkan tersangka kasus korupsi dana desa", "INSTITUSI"),
        ("Polri dan Kejaksaan Agung sepakat percepat penyidikan", "INSTITUSI"),
        ("Mahkamah Konstitusi gelar sidang uji materi", "INSTITUSI"),
    ],
    "asean": [
        ("KTT ASEAN digelar di Jakarta, bahas Myanmar", "ASEAN"),
        ("Timor Leste dorong keanggotaan penuh ASEAN", "ASEAN"),
        ("Malaysia dan Singapura sepakat kerja sama ekonomi digital", "ASEAN"),
        ("Perhimpunan Bangsa-Bangsa Asia Tenggara perkuat ZOPFAN", "ASEAN"),
        ("Penerbangan langsung Vietnam-Thailand kembali dibuka", "ASEAN"),
        ("Ekonomi Laos tumbuh, Vientiane tarik investor", "ASEAN"),
    ],
    "negatif/false positive": [
        ("Promo tools powerom XL di toko online", "BUKAN POLITIK"),
        ("IHSG ditutup menguat ke level 7.500", "SAHAM/MAKRO"),
        ("Harga batu bara acuan HBA naik pekan ini", "EMAS_KOMODITAS"),
    ],
}

# Ekspektasi resmi per baris (dipakai untuk hitung lulus/gagal otomatis).
HARAPAN = {
    "Pilkada Kalbar 2024: KPU tetapkan jadwal kampanye": {"POLITIK", "LOKAL_KALBAR_NGABANG"},
    "Presiden panggil menteri bahas koalisi partai politik": {"POLITIK"},
    "DPR sahkan RUU, fraksi menyampaikan pendapat akhir": {"POLITIK"},
    "Bupati Landak resmikan jalan di Kecamatan Ngabang": {"LOKAL_KALBAR_NGABANG"},
    "Pemkab Landak bersama Pemprov Kalbar bahas banjir": {"LOKAL_KALBAR_NGABANG"},
    "Banjir rendam Pontianak, BPBD siapkan posko": {"LOKAL_KALBAR_NGABANG"},
    "Kemenkes tambah kuota vaksin imunisasi anak": {"KESEHATAN"},
    "RSUD Landak buka layanan baru, klaim BPJS tetap gratis": {"KESEHATAN"},
    "Kasus demam berdarah di Singkawang meningkat": {"KESEHATAN", "LOKAL_KALBAR_NGABANG"},
    "Puskesmas perkuat stunting dan gizi ibu hamil": {"KESEHATAN"},
    "KPK tetapkan tersangka kasus korupsi dana desa": {"INSTITUSI"},
    "Polri dan Kejaksaan Agung sepakat percepat penyidikan": {"INSTITUSI"},
    "Mahkamah Konstitusi gelar sidang uji materi": {"INSTITUSI"},
    "KTT ASEAN digelar di Jakarta, bahas Myanmar": {"ASEAN"},
    "Timor Leste dorong keanggotaan penuh ASEAN": {"ASEAN"},
    "Malaysia dan Singapura sepakat kerja sama ekonomi digital": {"ASEAN"},
    "Perhimpunan Bangsa-Bangsa Asia Tenggara perkuat ZOPFAN": {"ASEAN"},
    "Penerbangan langsung Vietnam-Thailand kembali dibuka": {"ASEAN"},
    "Ekonomi Laos tumbuh, Vientiane tarik investor": {"ASEAN"},
    "Promo tools powerom XL di toko online": {"MAKRO_REGULASI", "UMUM"},
    "IHSG ditutup menguat ke level 7.500": {"MAKRO_REGULASI", "SAHAM"},
    "Harga batu bara acuan HBA naik pekan ini": {"EMAS_KOMODITAS"},
}

print("=" * 70)
for kelompok, daftar in KASUS.items():
    print(f"\n[{kelompok}]")
    for teks, harapan in daftar:
        hasil = tentukan(teks)
        sesuai = hasil in HARAPAN.get(teks, {harapan})
        print(f"  {'OK   ' if sesuai else 'CEK  '}{teks[:56]:<56} -> {hasil:<20} (harap: {harapan})")

print("\n" + "=" * 70)
gagal = 0
# Cek integrasi UI
from utils_ui import KATEGORI_UTAMA, label_kategori  # noqa: E402

kode_ui = [k for k, _ in KATEGORI_UTAMA]
print("Kategori di KATEGORI_UTAMA :", kode_ui)
for wajib in ["POLITIK", "LOKAL_KALBAR_NGABANG", "KESEHATAN", "INSTITUSI", "ASEAN"]:
    if wajib in kode_ui:
        print(f"  OK  {wajib} -> {label_kategori(wajib)}")
    else:
        gagal += 1
        print(f"  GAGAL {wajib} tidak ada di KATEGORI_UTAMA")

# Cek kategori mentah app.py semuanya punya pemetaan (anti 'hilang' -> MAKRO_REGULASI)
belum_dipetakan = [k for k in KATEGORI_PORTOFOLIO if k not in PEMETAAN_KATEGORI]
print("Kategori mentah tanpa pemetaan :", belum_dipetakan or "TIDAK ADA (semua terpetakan)")
gagal += len(belum_dipetakan)
print("Urutan prioritas klasifikasi  :", urutan[:6], "...")

# Cek portal baru tersedia
from utils.portals import aturan_portal  # noqa: E402

kunci = list(aturan_portal)
cek_portal = {
    "Politik": "CNN Indonesia (Politik)",
    "Kalbar/Ngabang": "Landak Pusat Informasi (Blogger)",
    "Kesehatan": "Antara (Kesehatan)",
    "Institusi": "KPK (Media)",
    "ASEAN": "ASEAN (Google News)",
}
print("\nPortal kategori baru:")
for topik, nama in cek_portal.items():
    ada = nama in kunci
    gagal += 0 if ada else 1
    print(f"  {'OK  ' if ada else 'GAGAL'} {topik:<16} {nama}")
print("  OK   duplikat 'Landak Pusat Informasi' dihapus:",
      sum(1 for k in kunci if k.startswith("Landak Pusat Informasi")) == 1)
print(f"\nTotal portal: {len(kunci)}")
print("\nHASIL UJI:", "SEMUA LULUS" if gagal == 0 else f"{gagal} MASALAH")
sys.exit(1 if gagal else 0)