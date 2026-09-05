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

    # ---- Kategori: Ekonomi & Bisnis Tambahan ----
    "Okezone Finance": {
        "rss_asli": "https://economy.okezone.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:economy.okezone.com+OR+site:finance.okezone.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Republika (Ekonomi)": {
        "rss_asli": "https://www.republika.co.id/rss/ekonomi",
        "rss_google": "https://news.google.com/rss/search?q=site:republika.co.id/ekonomi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "wrap__article-detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Jawa Pos (Bisnis)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:jawapos.com+bisnis+OR+ekonomi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-content", "butuh_page_all": False
    },
    "Bisnis Indonesia (Saham)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:market.bisnis.com+saham&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "details-content", "butuh_page_all": False
    },
    "Kedaulatan Rakyat (Bisnis)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:krjogja.com+bisnis+OR+ekonomi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-content", "butuh_page_all": False
    },
    "Suara Bisnis": {
        "rss_asli": "https://bisnis.suara.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:bisnis.suara.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Merdeka (Ekonomi)": {
        "rss_asli": "https://www.merdeka.com/rss/ekonomi.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:merdeka.com/ekonomi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "mdk-body-paragraph", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Astha Techno": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:astha.id+teknologi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "entry-content", "butuh_page_all": False
    },

    # ---- Kategori: Teknologi Tambahan ----
    "Liputan6 (Tekno)": {
        "rss_asli": "https://www.liputan6.com/rss/tekno",
        "rss_google": "https://news.google.com/rss/search?q=site:liputan6.com/tekno&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "article-content-body__item", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Suara (Teknologi)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:suara.com+teknologi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-content", "butuh_page_all": False
    },
    "Merdeka (Teknologi)": {
        "rss_asli": "https://www.merdeka.com/rss/teknologi.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:merdeka.com/teknologi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "mdk-body-paragraph", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Okezone (Techno)": {
        "rss_asli": "https://techno.okezone.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:techno.okezone.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Kompasiana (Teknologi)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:kompasiana.com+teknologi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read-content", "butuh_page_all": False
    },
    "Detik (Inet)": {
        "rss_asli": "https://rss.detik.com/index.php/inet",
        "rss_google": "https://news.google.com/rss/search?q=site:inet.detik.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail__body-text", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "Tempo (Inet)": {
        "rss_asli": "https://rss.tempo.co/inet",
        "rss_google": "https://news.google.com/rss/search?q=site:inet.tempo.co&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-konten", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },

    # ---- Kategori: Luar Negeri / Internasional Tambahan ----
    "Detik (Internasional)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:detik.com+internasional+OR+news+OR+dunia&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail__body-text", "butuh_page_all": True
    },
    "Kompas (Internasional)": {
        "rss_asli": "https://www.kompas.com/rss/internasional.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:www.kompas.com+internasional+OR+global&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read__content", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "Liputan6 (Global)": {
        "rss_asli": "https://www.liputan6.com/rss/global",
        "rss_google": "https://news.google.com/rss/search?q=site:liputan6.com/global&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "article-content-body__item", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Republika (Global)": {
        "rss_asli": "https://www.republika.co.id/rss/global",
        "rss_google": "https://news.google.com/rss/search?q=site:republika.co.id/global&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "wrap__article-detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Okezone (World)": {
        "rss_asli": "https://www.okezone.com/rss/world",
        "rss_google": "https://news.google.com/rss/search?q=site:okezone.com/world&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Merdeka (Internasional)": {
        "rss_asli": "https://www.merdeka.com/rss/internasional.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:merdeka.com/internasional&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "mdk-body-paragraph", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },

    # ---- Kategori: Saham & Investasi Khusus ----
    "Bisnis (Saham)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:market.bisnis.com+saham&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "details-content", "butuh_page_all": False
    },
    "Kontan (Investasi)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:investasi.kontan.co.id+saham+OR+reksadana&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "tmpt-desk-kon", "butuh_page_all": True
    },
    "PajakKu": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:pajakku.com+OR+site:pajak.go.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "entry-content", "butuh_page_all": False
    },
    "DPR (Media)": {
        "rss_asli": "https://www.dpr.go.id/jurnal/rss.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:dpr.go.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },

    # ---- Kategori: Energi & Komoditas ----
    "CNBC Indonesia (Energy)": {
        "rss_asli": "https://www.cnbcindonesia.com/energy/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:cnbcindonesia.com/energy&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail_text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Katadata (Energi)": {
        "rss_asli": "https://katadata.co.id/rss/energi",
        "rss_google": "https://news.google.com/rss/search?q=site:katadata.co.id+energi+OR+minyak+OR+batubara&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-body", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Bisnis (Energy)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:bisnis.com/energi&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "details-content", "butuh_page_all": False
    },
    "Detik (Properti)": {
        "rss_asli": "https://rss.detik.com/index.php/properti",
        "rss_google": "https://news.google.com/rss/search?q=site:properti.detik.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail__body-text", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },

    # ---- Kategori: Umum / Nasional ----
    "Kompas (Nasional)": {
        "rss_asli": "https://www.kompas.com/rss/nasional.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:www.kompas.com+nasional&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "read__content", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "CNN Indonesia (Nasional)": {
        "rss_asli": "https://www.cnnindonesia.com/nasional/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:cnnindonesia.com/nasional&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail_text", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Tempo (Nasional)": {
        "rss_asli": "https://rss.tempo.co/nasional",
        "rss_google": "https://news.google.com/rss/search?q=site:tempo.co/nasional&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-konten", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Antara (Nasional)": {
        "rss_asli": "https://www.antaranews.com/rss/topnews.xml",
        "rss_google": "https://news.google.com/rss/search?q=site:antaranews.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "wrap__article-detail-content", "butuh_page_all": True,
        "tanggal_terpercaya": True
    },
    "Republika (Nasional)": {
        "rss_asli": "https://www.republika.co.id/rss/berita",
        "rss_google": "https://news.google.com/rss/search?q=site:republika.co.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "wrap__article-detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Jawa Pos (Nasional)": {
        "rss_asli": "https://www.jawapos.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:jawapos.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Tribunnews": {
        "rss_asli": "https://www.tribunnews.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:tribunnews.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "article-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Suara (Nasional)": {
        "rss_asli": "https://www.suara.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:suara.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Okezone (News)": {
        "rss_asli": "https://www.okezone.com/rss/news",
        "rss_google": "https://news.google.com/rss/search?q=site:okezone.com/news&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },

    # ---- Kategori: Pemerintahan / Regulasi ----
    "Kemenkeu Go ID": {
        "rss_asli": "https://www.kemenkeu.go.id/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:kemenkeu.go.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "post-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Bank Indonesia": {
        "rss_asli": "https://www.bi.go.id/rss/berita",
        "rss_google": "https://news.google.com/rss/search?q=site:bi.go.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "news-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "OJK": {
        "rss_asli": "https://www.ojk.go.id/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:ojk.go.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "news-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Bursa Efek Indonesia (IDX)": {
        "rss_asli": "https://www.idx.co.id/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:idx.co.id&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "news-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },

    # ---- Kategori: BUMN & Korporasi ----
    "BUMN Track": {
        "rss_asli": "https://www.bumntrack.com/feed",
        "rss_google": "https://news.google.com/rss/search?q=site:bumntrack.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "entry-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Kontan (BUMN)": {
        "rss_asli": "",
        "rss_google": "https://news.google.com/rss/search?q=site:kontan.co.id+bumn&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "tmpt-desk-kon", "butuh_page_all": True
    },

    # ---- Kategori: Regional / Lokal ----
    "Pikiran Rakyat": {
        "rss_asli": "https://www.pikiran-rakyat.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:pikiran-rakyat.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "article-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Kedaulatan Rakyat": {
        "rss_asli": "https://www.krjogja.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:krjogja.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "detail-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Tribunnews Jabar": {
        "rss_asli": "https://jabar.tribunnews.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:jabar.tribunnews.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "article-content", "butuh_page_all": False,
        "tanggal_terpercaya": True
    },
    "Tribunnews Jatim": {
        "rss_asli": "https://jatim.tribunnews.com/rss",
        "rss_google": "https://news.google.com/rss/search?q=site:jatim.tribunnews.com&hl=id&gl=ID&ceid=ID:id",
        "tag": "div", "class": "article-content", "butuh_page_all": False,
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