"""
Advanced Sentiment Analysis untuk teks finansial Bahasa Indonesia.

FITUR:
- Lexicon-based dengan bobot (tidak sekadar 1/0)
- Negation handling ("tidak naik", "belum turun")
- Intensifier & diminisher ("sangat", "agak", "sedikit")
- Confidence score (skor -1.0 sampai 1.0)
- Multi-class: POSITIF, NEGATIF, NETRAL

Mengapa bukan VADER/IndoBERT?
- VADER: tidak support bahasa Indonesia secara native
- IndoBERT: butuh ~500MB model + GPU/lambat di CPU
- Custom lexicon: balance antara akurasi & performa
"""

import re
from typing import Tuple


# ============================================================
# LEKSIKON DENGAN BOBOT (weight -3.0 s/d +3.0)
# ============================================================

# Kata positif: bobot lebih tinggi untuk yang lebih kuat
LEKSIKON_POSITIF = {
    # sangat positif (+3)
    "meroket": 3.0, "melejit": 3.0, "rekor": 3.0, "rekor tertinggi": 3.0,
    "all time high": 3.0, "ath": 3.0, "explosif": 3.0,
    # positif kuat (+2)
    "laba": 2.0, "laba bersih": 2.5, "laba operasional": 2.0,
    "untung": 2.0, "keuntungan": 2.0, "profit": 2.0,
    "naik": 1.5, "kenaikan": 1.5, "menguat": 1.8, "penguatan": 1.8,
    "meningkat": 1.8, "peningkatan": 1.8,
    "tumbuh": 1.8, "pertumbuhan": 1.8, "ekspansi": 2.0,
    "bullish": 2.0, "surplus": 2.0, "dividen": 2.0, "deviden": 2.0,
    "dividen yield": 2.0, "buyback": 2.0,
    "positif": 1.5, "prospek cerah": 2.5, "prospek baik": 2.0,
    "optimis": 2.0, "optimisme": 2.0,
    # positif moderat (+1)
    "terangkat": 1.2, "terdongkrak": 1.5, "terdukung": 1.0,
    "stabil": 0.8, "konsisten": 1.0, "berhasil": 1.5,
    "raih": 1.5, "mencapai": 1.0, "kokoh": 1.0,
}

LEKSIKON_NEGATIF = {
    # sangat negatif (-3)
    "bangkrut": 3.0, "pailit": 3.0, "gagal bayar": 3.0,
    "default": 2.5, "delisting": 3.0, "suspend": 2.0,
    "anjlok": 2.5, "terperosok": 2.5, "merosot tajam": 2.5,
    "krisis": 2.5, "resesi": 2.5, "panic selling": 2.5,
    # negatif kuat (-2)
    "rugi": 2.0, "kerugian": 2.0, "loss": 2.0,
    "turun": 1.5, "penurunan": 1.5, "melemah": 1.8, "pelemahan": 1.8,
    "menurun": 1.8, "anjlok": 2.0,
    "bearish": 2.0, "defisit": 2.0, "sanksi": 1.8, "denda": 1.5,
    "gugatan": 1.5, "kasus": 1.0, "sengketa": 1.5,
    "korupsi": 2.5, "penyelewengan": 2.0, "penipuan": 2.0,
    "negatif": 1.5, "tekanan": 1.5, "tertekan": 1.8,
    "pemecatan": 1.5, "phk": 2.0, "gagal": 1.5,
    # negatif moderat (-1)
    "melemahkan": 1.2, "menekan": 1.2, "menghambat": 1.2,
    "lesu": 1.0, "lesuan": 1.0, "lesu": 1.0,
    "terkoreksi": 1.2, "koreksi": 1.0,
    "waspada": 0.8, "hati-hati": 0.8,
}

# Negasi: membalik polaritas (-2.5 kata setelahnya)
NEGASI = {
    "tidak", "tak", "bukan", "belum", "jangan", "tanpa",
    "nggak", "gak", "ga", "ndak", "kagak", "belum pernah",
}

# Intensifier: memperkuat/melemahkan sentimen
INTENSIFIER = {
    # amplifier (+30% s/d +50%)
    "sangat": 1.5, "amat": 1.4, "sekali": 1.3, "sangatlah": 1.5,
    "luar biasa": 1.6, "ekstrem": 1.7, "parah": 1.4,
    "tajam": 1.4, "drastis": 1.5, "signifikan": 1.3,
    # diminisher (-30% s/d -50%)
    "agak": 0.7, "sedikit": 0.7, "lumayan": 0.8, "cukup": 0.8,
    "relatif": 0.8, "kurang": 0.7, "hampir": 0.9,
}


def _tokenize(text: str) -> list[str]:
    """Tokenisasi sederhana + normalisasi."""
    text = text.lower()
    # Pisahkan dengan mempertimbangkan multi-word
    text = re.sub(r'([.,!?;:])\s*', r' \1 ', text)
    tokens = text.split()
    return tokens


def _cari_window(tokens: list[str], idx: int, window: int = 3) -> list[str]:
    """Ambil token dalam window sebelum idx (untuk cek negasi/intensifier)."""
    start = max(0, idx - window)
    return tokens[start:idx]


def analisa_sentimen_advanced(teks: str) -> Tuple[str, float, dict]:
    """
    Analisis sentimen lanjutan dengan negasi & intensifier.

    Returns:
        (label, confidence, debug_info)
        - label: "POSITIF" | "NEGATIF" | "NETRAL"
        - confidence: -1.0 s/d 1.0 (negatif = sentimen negatif)
        - debug_info: dict berisi breakdown
    """
    if not teks or len(teks.strip()) < 5:
        return "NETRAL", 0.0, {"skor": 0.0, "matches": []}

    tokens = _tokenize(teks)
    skor_total = 0.0
    matches = []

    # Gabungkan leksikon untuk lookup
    leksikon_all = {}
    for kata, bobot in LEKSIKON_POSITIF.items():
        leksikon_all[kata] = bobot
    for kata, bobot in LEKSIKON_NEGATIF.items():
        leksikon_all[kata] = -bobot  # negatif jadi negatif

    # Cari match (single word dan multi-word)
    i = 0
    while i < len(tokens):
        matched = False

        # Cek multi-word dulu (2 & 3 kata)
        for n in [3, 2]:
            if i + n <= len(tokens):
                phrase = " ".join(tokens[i:i + n])
                if phrase in leksikon_all:
                    bobot = leksikon_all[phrase]
                    window = _cari_window(tokens, i, window=3)

                    # Cek negasi dalam window
                    has_negasi = any(t in NEGASI for t in window)
                    if has_negasi:
                        bobot = -bobot * 0.8  # negate with slight reduction

                    # Cek intensifier dalam window
                    multiplier = 1.0
                    for t in window:
                        if t in INTENSIFIER:
                            multiplier *= INTENSIFIER[t]

                    skor_total += bobot * multiplier
                    matches.append({
                        "kata": phrase,
                        "bobot": bobot,
                        "multiplier": multiplier,
                        "negated": has_negasi,
                    })
                    i += n
                    matched = True
                    break

        if matched:
            continue

        # Cek single word
        if tokens[i] in leksikon_all:
            bobot = leksikon_all[tokens[i]]
            window = _cari_window(tokens, i, window=3)

            has_negasi = any(t in NEGASI for t in window)
            if has_negasi:
                bobot = -bobot * 0.8

            multiplier = 1.0
            for t in window:
                if t in INTENSIFIER:
                    multiplier *= INTENSIFIER[t]

            skor_total += bobot * multiplier
            matches.append({
                "kata": tokens[i],
                "bobot": bobot,
                "multiplier": multiplier,
                "negated": has_negasi,
            })

        i += 1

    # Normalisasi: skor_total biasanya -10 sampai +10
    # Konversi ke confidence -1.0 sampai 1.0 dengan tanh-like
    if skor_total > 0:
        confidence = min(1.0, skor_total / 8.0)
    elif skor_total < 0:
        confidence = max(-1.0, skor_total / 8.0)
    else:
        confidence = 0.0

    # Threshold untuk label
    if confidence >= 0.15:
        label = "POSITIF"
    elif confidence <= -0.15:
        label = "NEGATIF"
    else:
        label = "NETRAL"

    debug = {
        "skor": round(skor_total, 2),
        "confidence": round(confidence, 3),
        "matches": matches,
        "n_matches": len(matches),
    }

    return label, confidence, debug


def get_sentiment_breakdown(teks: str) -> dict:
    """
    Versi ringan yang hanya mengembalikan dict info (untuk logging/UI).
    """
    label, conf, debug = analisa_sentimen_advanced(teks)
    return {
        "sentimen": label,
        "confidence": conf,
        "skor_raw": debug["skor"],
        "n_keyword_matches": debug["n_matches"],
    }