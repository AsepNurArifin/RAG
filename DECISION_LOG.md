# DECISION_LOG.md — EnterpriseMind AI

> Format: Architecture Decision Record (ADR) ringkas. Setiap keputusan teknis signifikan dicatat di sini — bukan hanya di commit message. Urutan kronologis, terbaru di paling bawah.

---

### ADR-001 — Pemilihan Model LLM: Groq `gpt-oss-120b` / `gpt-oss-20b`
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Rencana awal menggunakan `llama-3.1-70b-versatile` dan `llama-3.1-8b-instant` di Groq.
**Keputusan:** Ganti ke `openai/gpt-oss-120b` (reasoning berat) dan `openai/gpt-oss-20b` (task ringan), karena model Llama 3.1 tersebut sudah decommissioned/dalam proses deprecation resmi oleh Groq (per pengumuman 17 Juni 2026).
**Konsekuensi:** Semua kode harus mengambil nama model dari `core/config.py`, tidak hardcode, untuk memudahkan migrasi jika terjadi deprecation lagi (risiko yang terbukti berulang).

---

### ADR-002 — Target Latensi Query Kompleks
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Target awal 8 detik untuk query kompleks dianggap terlalu ketat mengingat rantai 4-5 agent call.
**Keputusan:** Revisi target menjadi ≤ 12 detik untuk query kompleks, dengan strategi hybrid model (gpt-oss-20b untuk task ringan, gpt-oss-120b untuk task berat) sebagai mitigasi.
**Konsekuensi:** NFR-P2 di SRS direvisi. Perlu monitoring latensi aktual selama development untuk memastikan target ini realistis.

---

### ADR-003 — Target Concurrent Users untuk MVP
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Target awal 100 concurrent users dianggap tidak proporsional untuk MVP solo-developer tanpa infrastruktur enterprise.
**Keputusan:** Turunkan target ke simulasi 20-30 concurrent session via load testing (Locust), bukan infrastruktur produksi riil.
**Konsekuensi:** NFR-S2 di SRS direvisi.

---

### ADR-004 — Target Faithfulness Score
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Target awal 95% dianggap terlalu tinggi untuk model open-weight ukuran menengah.
**Keputusan:** Turunkan target ke ≥ 85% pada evaluasi RAGAS.
**Konsekuensi:** NFR-R1 di SRS direvisi. Tetap kompetitif untuk showcase portfolio.

---

### ADR-005 — Pemilihan Frontend: Next.js (bukan Streamlit)
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Streamlit lebih cepat dikembangkan, tapi hasil visual kurang polished untuk showcase portfolio.
**Keputusan:** Gunakan Next.js meski development lebih lama.
**Konsekuensi:** Roadmap Minggu 6 dialokasikan penuh khusus untuk UI dasar (chat interface), admin dashboard digeser ke awal Minggu 7. Risiko waktu molor dicatat di SRS Bagian B.6.

---

### ADR-006 — Pemilihan Observability: LangFuse (bukan LangSmith)
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** LangSmith native dengan LangChain tapi berbayar setelah kuota gratis habis; LangFuse open-source dan bisa self-host gratis.
**Keputusan:** Gunakan LangFuse.
**Konsekuensi:** Perlu setup self-hosting via Docker (atau gunakan LangFuse Cloud free tier sebagai alternatif lebih cepat) di Minggu 7.

---

### ADR-007 — Struktur Dokumentasi Proyek (AI-Agent Facing Docs)
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Dipertimbangkan 8 file dokumentasi terpisah (AI_RULES, ARCHITECTURE, CONSTRAINTS, CODING_STANDARDS, DEFINITION_OF_DONE, TASK_BACKLOG, PROMPT_LIBRARY, DECISION_LOG) untuk mengarahkan AI coding agent.
**Keputusan:** Gabungkan CONSTRAINTS.md ke dalam ARCHITECTURE.md untuk menghindari 3 sumber kebenaran berbeda soal batasan teknis (SRS constraints vs CONSTRAINTS.md vs AI_RULES.md). Tambahkan SECURITY.md sebagai file terpisah karena scope keamanan pada sistem agentic (prompt injection, tool permission scoping) cukup spesifik untuk berdiri sendiri.
**Konsekuensi:** Total 7 file dokumentasi pendukung: ARCHITECTURE.md, AI_RULES.md, CODING_STANDARDS.md, DEFINITION_OF_DONE.md, TASK_BACKLOG.md, PROMPT_LIBRARY.md, DECISION_LOG.md, ditambah SECURITY.md.

---

### ADR-008 — Pemilihan Supabase sebagai Database Metadata
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Rencana awal menggunakan PostgreSQL self-hosted (atau SQLite untuk dev cepat). Dipertimbangkan apakah managed database lebih efisien untuk solo-developer yang sudah harus mengelola banyak komponen.
**Keputusan:** Gunakan **Supabase** (PostgreSQL managed + Auth + File Storage) untuk metadata, dengan Chroma tetap terpisah di VPS untuk vector store. Arsitektur hybrid: Supabase untuk data terstruktur (metadata dokumen, user, log), Chroma untuk pencarian semantik.
**Konsekuensi:**
- Tidak perlu setup/maintain PostgreSQL sendiri di VPS — mengurangi beban operasional.
- Auth bawaan Supabase bisa langsung dipakai untuk login admin dashboard (FR6, NFR-SEC1), hemat waktu development.
- File Storage Supabase bisa menyimpan file dokumen asli sebelum diproses.
- `db/` di backend menggunakan Supabase Python client, bukan SQLAlchemy.
- Free tier limits: 500MB DB, 1GB storage — cukup untuk MVP, tapi perlu dipantau.

---

### ADR-009 — Deploy Backend di VPS (bukan Railway/Render)
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Rencana awal menggunakan Railway/Render/Fly.io (cloud gratis/murah). Pengembang memiliki VPS sendiri yang bisa digunakan.
**Keputusan:** Deploy backend (FastAPI + Chroma + opsional LangFuse self-hosted) di VPS milik pengembang. Frontend Next.js tetap di Vercel (free tier).
**Konsekuensi:**
- Tidak ada batasan jam aktif atau sleep setelah idle — link demo selalu aktif untuk recruiter.
- Bisa menjalankan FastAPI + Chroma + LangFuse sekaligus tanpa khawatir resource limit free tier cloud.
- Perlu setup Docker/Docker Compose di VPS dan konfigurasi CORS untuk menerima request dari domain Vercel.
- Biaya VPS sudah ditanggung pengembang (bukan biaya tambahan untuk proyek ini).

---

### ADR-010 — Tailwind CSS v4 Dipertahankan di Frontend
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Boilerplate Next.js yang sudah di-setup menggunakan Tailwind CSS v4 (terinstall di `package.json`). Dokumen CODING_STANDARDS.md belum menyebut Tailwind secara eksplisit.
**Keputusan:** Pertahankan Tailwind CSS v4 karena sudah terinstall. Ini konsisten dengan pilihan Next.js untuk produktivitas UI.
**Konsekuensi:** CODING_STANDARDS.md perlu ditambahkan aturan penggunaan Tailwind (utility-first, custom theme via `globals.css`).

---

### ADR-011 — Arsitektur Hybrid Page-Level Ingestion & Dedup
**Tanggal:** Juli 2026
**Status:** Diterima
**Konteks:** Docling (VLM) berjalan sangat lambat (8 menit per dokumen) jika memproses seluruh file PDF secara merata. Di sisi lain, vektor *deduplication* menggunakan *cosine similarity* di Milvus terlalu lambat untuk *real-time ingestion*.
**Keputusan:** 
1. Menerapkan **Page-Level Router**: Memecah PDF per halaman, menggunakan `pymupdf4llm` (teks polos) dan mengisolasi Docling khusus untuk halaman diagram/tabel.
2. Mengubah *signature* fungsi ekstraksi menjadi `List[dict]` dengan skema `PageExtraction` agar metadata `extraction_method` bisa diteruskan ke *chunk*.
3. **Deduplikasi Tingkat Lanjut**: Menggunakan algoritma hash (contoh: SHA-256 terhadap teks ternormalisasi) untuk *exact/near-exact dedup* di level *pre-chunking*, menghindari *similarity search* berat saat *ingestion*.
4. **Catatan Lisensi**: `pymupdf4llm` menggunakan lisensi AGPL-3.0. Hal ini diizinkan untuk skala portofolio/penelitian, namun perlu dicatat jika sistem berubah menjadi produk tertutup (komersial), *source code* wajib dibuka atau membutuhkan lisensi komersial dari Artifex.
**Konsekuensi:** Kinerja *ingestion* menjadi sangat cepat untuk teks biasa, efisiensi penyimpanan (*vector store*) meningkat karena *hash-based dedup*, dan dukungan kompatibilitas mundur (helper `flatten_pages`) tersedia untuk modul lain yang membutuhkan bentuk `string` utuh.

---

*Template untuk entri baru:*
```
### ADR-XXX — [Judul Keputusan]
**Tanggal:**
**Status:** Diterima / Dipertimbangkan / Ditolak
**Konteks:**
**Keputusan:**
**Konsekuensi:**
```

