"""
Stop Words bahasa Indonesia — EnterpriseMind AI.

150+ stop words umum bahasa Indonesia untuk BM25 tokenisasi.
Digunakan oleh hybrid_search.py untuk filtering kata tidak bermakna.

Sumber: Sastrawi stop word list + custom additions untuk domain enterprise.
"""

STOP_WORDS_ID: set[str] = {
    # ---- Kata ganti (pronouns) ----
    "aku", "saya", "kamu", "anda", "dia", "ia", "kami", "kita", "mereka",
    "ini", "itu", "tersebut", "yang",

    # ---- Kata depan (prepositions) ----
    "di", "ke", "dari", "pada", "dalam", "untuk", "dengan", "oleh",
    "antara", "tanpa", "sampai", "hingga", "selama", "setelah", "sebelum",
    "tentang", "terhadap", "atas", "bawah", "depan", "belakang",

    # ---- Kata penghubung (conjunctions) ----
    "dan", "atau", "tetapi", "namun", "serta", "juga", "bahkan",
    "karena", "sebab", "sehingga", "maka", "jika", "apabila", "bila",
    "ketika", "ketika", "waktu", "manakala", "sementara", "sedangkan",
    "yaitu", "yakni", "ialah", "adapun", "bahwa",

    # ---- Kata keterangan (adverbs) ----
    "sudah", "telah", "belum", "akan", "sedang", "lagi", "pernah",
    "tidak", "bukan", "jangan", "tiada", "tak", "tanda",
    "sangat", "amat", "sungguh", "sekali", "paling", "lebih", "agak",
    "cukup", "hampir", "nyaris", "sering", "selalu", "jarang",
    "masih", "saja", "hanya", "pun", "bahkan", "malah",

    # ---- Kata tanya (interrogatives) ----
    "apa", "siapa", "mengapa", "kenapa", "bagaimana", "mana",
    "kapan", "berapa", "dimana", "di mana",

    # ---- Kata kerja bantu (auxiliary verbs) ----
    "adalah", "merupakan", "ialah", "yakni", "yaitu",
    "bisa", "dapat", "mampu", "mau", "ingin", "harus", "perlu",
    "boleh", "diperbolehkan", "dilarang",

    # ---- Lain-lain (miscellaneous) ----
    "dan", "dll", "dsb", "dst", "dst", "sbg", "thd",
    "yg", "dgn", "krn", "spy", "utk", "pd", "dr", "tdk", "blm",
    "sdh", "aja", "jg", "jga", "lg", "lgi", "mrk", "org",

    # ---- Kata sambung umum ----
    "hal", "hal-hal", "bagian", "macam", "jenis", "tipe",
    "contoh", "misal", "misalnya", "seperti", "yakni",

    # ---- Angka dan satuan ----
    "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh",
    "pertama", "kedua", "ketiga", "keempat", "kelima",

    # ---- Kata umum tambahan ----
    "ada", "adanya", "akan", "antara", "artinya", "awal",
    "berbagai", "bersama", "besar", "bagaimanapun",
    "dahulu", "dalam", "dapat", "demikian", "dengan", "depan",
    "ia", "ialah", "ini", "itu", "jelas", "kali",
    "kami", "kalian", "kamu", "karena", "kira-kira",
    "kini", "lagi", "lain", "lalu", "lebih", "macam",
    "maka", "manusia", "masih", "mana", "mereka",
    "mula", "mulai", "nah", "namun", "nanti",
    "oleh", "oleh karena itu", "pada", "para", "pasti",
    "per", "perlu", "pula", "pun", "saat", "saling",
    "sama", "sangat", "secara", "sedang", "sejak", "selain",
    "selalu", "seluruh", "sementara", "semua", "seolah",
    "seorang", "sepanjang", "seperti", "sering", "serta",
    "sesuatu", "setiap", "siapa", "sini", "situ",
    "suatu", "sudah", "sungguh", "tadi", "tahu",
    "tahun", "tanpa", "tapi", "telah", "tentang", "tentu",
    "terdiri", "terhadap", "tersebut", "tiada", "tidak",
    "tinggi", "untuk", "walaupun", "yakin", "zaman",
}

# Jumlah stop words
STOP_WORDS_COUNT = len(STOP_WORDS_ID)
