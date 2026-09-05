"""
Konfigurasi semua portal berita yang di-scrape.
Dipisahkan dari app.py agar mudah di-maintain dan diimpor ulang dari page lain.
"""

aturan_portal = {
    "CNN Indonesia (Ekonomi)": {
        "rss_asli": "https://www.cnnindonesia.com/ekonomi/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:cnnindonesia.com/ekonomi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail_text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "CNBC Indonesia (Market)": {
        "rss_asli": "https://www.cnbcindonesia.com/market/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:cnbcindonesia.com/market&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail_text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "CNBC Indonesia (MyMoney)": {
        "rss_asli": "https://www.cnbcindonesia.com/mymoney/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:cnbcindonesia.com/mymoney&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail_text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "CNBC Indonesia (News)": {
        "rss_asli": "https://www.cnbcindonesia.com/news/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:cnbcindonesia.com/news&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail_text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Kontan Utama & Investasi": {
        "rss_asli": "https://www.kontan.co.id/feed",
        "rss_google": "https://news.google.com/rss/search?q=site:kontan.co.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "tmpt-desk-kon", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "Kontan Investasi": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:investasi.kontan.co.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "tmpt-desk-kon", "butuh_page_all": True
    },
    "Katadata": {
        "rss_asli": "https://katadata.co.id/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:katadata.co.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-body", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Bloomberg Technoz": {
        "rss_asli": "https://www.bloombergtechnoz.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:bloombergtechnoz.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Tempo Bisnis": {
        "rss_asli": "https://rss.tempo.co/bisnis",
        "rss_google": "https://news.google.com/rss/search?q=site:bisnis.tempo.co&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-konten", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "ANTARA Ekonomi": {
        "rss_asli": "https://www.antaranews.com/rss/ekonomi-bisnis.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:antaranews.com/ekonomi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "wrap__article-detail-content", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "IDX Channel": {
        "rss_asli": "https://www.idxchannel.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:idxchannel.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Detik Finance": {
        "rss_asli": "https://finance.detik.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:finance.detik.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail__body-text", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "Bisnis Indonesia": {
        "rss_asli": "https://www.bisnis.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:bisnis.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "details-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Bisnis Market": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:market.bisnis.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "details-content", "butuh_page_all": False
    },
    "SWA Online": {
        "rss_asli": "https://swa.co.id/feed",
        "rss_google": "https://news.google.com/rss/search?q=site:swa.co.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "entry-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Bareksa": {
        "rss_asli": "https://www.bareksa.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:bareksa.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "news-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "TrenAsia": {
        "rss_asli": "https://www.trenasia.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:trenasia.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "content-detail", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Warta Ekonomi": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:wartaekonomi.co.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read-content", "butuh_page_all": False
    },
    "RM.id Ekonomi": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:rm.id+ekonomi+OR+bumn+OR+saham&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "entry-content", "butuh_page_all": False
    },
    "IDNFinancials": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:idnfinancials.com/id/news&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "cb", "butuh_page_all": False
    },
    "Kompas Money": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:money.kompas.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read__content", "butuh_page_all": True
    },
    "Investor.id (Market & Fin)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:investor.id+(market+OR+finance+OR+saham)&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read-content", "butuh_page_all": False
    },
    "Investor.id (Macro & Investory)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:investor.id+(macroeconomy+OR+investory)&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read-content", "butuh_page_all": False
    },
    "MetroTV News": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:metrotvnews.com+OR+site:metrotvnews.com/news&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "container-flex pb-20", "butuh_page_all": False
    },
    "tvOne News": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:tvonenews.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "article", "class": "content-article", "butuh_page_all": False
    },
    # ---- Kategori: Informasi Teknologi ----
    "CNN Indonesia (Teknologi)": {
        "rss_asli": "https://www.cnnindonesia.com/teknologi/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:cnnindonesia.com/teknologi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail_text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Detik Tekno": {
        "rss_asli": "https://rss.detik.com/index.php/teknologi",
        "rss_google": "https://news.google.com/rss/search?q=site:detik.com/teknologi+OR+site:detik.com/inet&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail__body-text", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "Kompas Tekno": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:tekno.kompas.com+OR+site:inet.kompas.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read__content", "butuh_page_all": True
    },
    "Antara Teknologi": {
        "rss_asli": "https://www.antaranews.com/rss/tekno.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:antaranews.com/tekno&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "wrap__article-detail-content", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "Tempo Teknologi": {
        "rss_asli": "https://rss.tempo.co/teknologi",
        "rss_google": "https://news.google.com/rss/search?q=site:tekno.tempo.co+OR+site:inet.tempo.co&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-konten", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Katadata Teknologi": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:katadata.co.id+(teknologi+OR+digital)&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-body", "butuh_page_all": False
    },
    "Bisnis Indonesia (Teknologi)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:bisnis.com/teknologi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "details-content", "butuh_page_all": False
    },
    # ---- Kategori: Informasi Luar Negeri / Pasar Global ----
    "CNBC Indonesia (Global)": {
        "rss_asli": "https://www.cnbcindonesia.com/market/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:cnbcindonesia.com/market+(wall+street+OR+global+OR+ Dow+OR+nikkei+OR+china)&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail_text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Kontan (Global Market)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:kontan.co.id+(global+OR+wall+street+OR+pasar+global+OR+ Dow+Jones)&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "tmpt-desk-kon", "butuh_page_all": True
    },
    "Investor.id (Global)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:investor.id+(global+OR+market+OR+ Dow+OR+nikkei+OR+wall+street)&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read-content", "butuh_page_all": False
    },
    "Bisnis Global": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:bisnis.com+(global+OR+wall+street+OR+ Dow+Jones+OR+nikkei+OR+ china+OR+ eropa)&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "details-content", "butuh_page_all": False
    },
    "Kompas Money (Global)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:money.kompas.com+(global+OR+ Dow+Jones+OR+wall+street+OR+nikkei)&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read__content", "butuh_page_all": True
    },
    "Tempo (Internasional)": {
        "rss_asli": "https://rss.tempo.co/internasional",
        "rss_google": "https://news.google.com/rss/search?q=site:tempo.co/internasional&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-konten", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Antara (Internasional)": {
        "rss_asli": "https://www.antaranews.com/rss/dunia.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:antaranews.com/berita-dunia&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "wrap__article-detail-content", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "CNN Indonesia (Internasional)": {
        "rss_asli": "https://www.cnnindonesia.com/internasional/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:cnnindonesia.com/internasional&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail_text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Republika (Internasional)": {
        "rss_asli": "https://www.republika.co.id/rss/internasional",
        "rss_google": "https://news.google.com/rss/search?q=site:republika.co.id/internasional&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "wrap__article-detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },

    "Landak Pusat Informasi (Blogger)": {
        # Portal berita lokal Kalbar (Kab. Landak) berbasis template Blogger/EvoMagz.
        # Feed Blogger default: /feeds/posts/default?alt=rss (RSS 2.0 + Atom 1.0)
        # Kontainer isi berita: <div class="post-body entry-content"> (paragraf <p>)
        "rss_asli": "https://www.landakpusatinformasi.com/feeds/posts/default?alt=rss",
        "rss_google": "",
        "tag": "div", "class": "post-body entry-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
}