# EnterpriseMind AI — Intelligent Multi-Agent Knowledge Assistant
### Software Requirements Specification (SRS) & Product Requirements Document (PRD)

**Versi:** 2.0 (Revisi — Tech Stack Diperbarui Juli 2026)
**Status:** Draft untuk Portfolio Project
**Tipe Proyek:** Portfolio independen (tidak terhubung dengan riset akademik lain)

---

## Catatan Revisi dari Versi Sebelumnya

| Item | Versi Lama | Versi Baru | Alasan |
|---|---|---|---|
| Model reasoning utama | `llama-3.1-70b-versatile` | `openai/gpt-oss-120b` | Model lama sudah *decommissioned* total di Groq |
| Model cepat/murah | `llama-3.1-8b-instant` | `openai/gpt-oss-20b` | Deprecated per 17 Juni 2026, migrasi resmi ke gpt-oss-20b |
| Strategi verifikasi | Single model | Hybrid routing (gpt-oss-120b vs 20b) | Efisiensi biaya + latensi |
| Target concurrent users | 100 users (enterprise-grade) | Disesuaikan untuk skala demo (lihat NFR) | Realistis untuk MVP solo-developer |
| Frontend | Streamlit/Next.js (belum diputuskan) | **Next.js** | Prioritas hasil visual polished untuk portfolio, meski development lebih lama |
| Observability | LangSmith/LangFuse (belum diputuskan) | **LangFuse** (self-hosted/cloud free tier) | Open-source, tidak terikat kuota berbayar |

---

## Tech Stack Summary

| Layer | Teknologi Terpilih | Alternatif yang Dipertimbangkan |
|---|---|---|
| LLM Provider | Groq Cloud API | OpenRouter (fallback jika Groq bermasalah) |
| Model reasoning berat | `openai/gpt-oss-120b` | — (cek ulang di console.groq.com/docs/models sebelum implementasi) |
| Model cepat/ringan | `openai/gpt-oss-20b` | — |
| Orchestration | LangGraph + LangChain | CrewAI, AutoGen |
| Vector DB | Chroma (di VPS, terpisah dari metadata DB) | Qdrant, Pinecone, Weaviate |
| Backend API | FastAPI | Flask |
| Frontend | Next.js (React) + Tailwind CSS v4 | Streamlit |
| Database metadata | **Supabase** (PostgreSQL managed + Auth + File Storage) | PostgreSQL self-hosted, SQLite |
| Observability | LangFuse (self-hosted/cloud free tier) | LangSmith |
| Evaluasi | RAGAS | TruLens |
| Deployment | **VPS** (backend + Chroma + LangFuse) + **Vercel** (frontend) | Railway, Render, Fly.io |
| Load testing | Locust | k6 |

## Diagram Arsitektur
*(Tautkan di sini setelah dibuat — direkomendasikan menggunakan Excalidraw atau draw.io)*

Diagram wajib mencakup minimal:
- Alur ingestion: Dokumen → Extraction → Chunking → Embedding → Vector Store
- Alur query: User → Orchestrator → (Researcher / Verifier / Summarizer / Executor) → Response
- Titik integrasi tools (web search, kalkulasi, query DB) dan observability (LangFuse hook di setiap agent call)

**Link diagram:** `[ISI SETELAH DIBUAT]`

---

## A.1 Pendahuluan

### A.1.1 Tujuan Dokumen
Dokumen ini mendefinisikan kebutuhan fungsional dan non-fungsional untuk **EnterpriseMind AI**, sebuah sistem Agentic RAG (Retrieval-Augmented Generation) berbasis arsitektur multi-agent yang dirancang untuk mengelola, mencari, memverifikasi, dan menganalisis dokumen internal perusahaan secara otonom.

### A.1.2 Ruang Lingkup Produk
Sistem mencakup:
- Pipeline ingestion dokumen (PDF, DOCX, TXT) ke dalam vector store dengan metadata terstruktur.
- Lapisan agentic (multi-agent orchestration) menggunakan LangGraph untuk memproses query pengguna secara reasoning-based, bukan sekadar retrieval-jawab.
- Mekanisme verifikasi fakta dan sitasi sumber untuk mengurangi hallucination.
- Antarmuka chat berbasis web untuk end user, serta dashboard admin untuk monitoring dokumen dan performa sistem.
- Observability penuh (tracing, evaluasi otomatis, cost monitoring) sebagai bagian dari *production-readiness* yang ditampilkan dalam portfolio.

**Di luar ruang lingkup MVP:** integrasi native Slack/Teams, GraphRAG, voice I/O, dan role-based access control granular — ini masuk kategori *Could Have* pada roadmap lanjutan.

### A.1.3 Definisi, Akronim, dan Singkatan

| Istilah | Definisi |
|---|---|
| RAG | Retrieval-Augmented Generation — teknik menggabungkan pencarian dokumen dengan generasi teks oleh LLM |
| Agentic AI | Sistem AI yang mampu melakukan reasoning multi-langkah, memanggil tools, dan mengambil keputusan otonom |
| LangGraph | Framework orchestration untuk membangun agent berbasis graph/state machine |
| Orchestrator Agent | Agent yang mengatur alur kerja dan mendelegasikan tugas ke agent spesialis lain |
| Faithfulness Score | Metrik yang mengukur seberapa konsisten jawaban model terhadap sumber dokumen yang diambil |
| Hallucination | Fenomena LLM menghasilkan informasi yang tidak berdasar pada sumber data yang valid |
| Chunking | Proses memecah dokumen panjang menjadi bagian-bagian kecil sebelum di-embed |

### A.1.4 Referensi
- Dokumentasi resmi LangGraph & LangChain
- Dokumentasi model Groq (`console.groq.com/docs/models`) — **wajib dicek ulang sebelum implementasi**, karena Groq mendeprecate model dengan frekuensi tinggi (tercatat 4 gelombang deprecation dalam 12 bulan terakhir)
- RAGAS Documentation untuk metrik evaluasi RAG

---

## A.2 Deskripsi Umum Sistem

### A.2.1 Perspektif Produk

*Lihat Diagram Arsitektur di bagian awal dokumen untuk gambaran visual alur ingestion dan alur query multi-agent.*

EnterpriseMind AI adalah evolusi dari sistem pencarian dokumen konvensional (keyword search) dan RAG generasi pertama (single-pass retrieve-then-generate). Perbedaan utamanya:

| Aspek | Search Konvensional | Naive RAG | EnterpriseMind AI (Agentic RAG) |
|---|---|---|---|
| Proses | Cocokkan kata kunci | Retrieve → Generate sekali | Reasoning loop multi-agent dengan verifikasi |
| Verifikasi fakta | Tidak ada | Tidak ada | Ada (Verifier Agent) |
| Tool calling | Tidak ada | Terbatas/tidak ada | Ya (search, kalkulasi, query DB) |
| Output | Daftar dokumen | Jawaban naratif | Jawaban + sitasi + action item |
| Reflection/self-correction | Tidak ada | Tidak ada | Ya (loop koreksi jika confidence rendah) |

### A.2.2 Fungsi Produk (Ringkasan)
1. Mengunggah dan mengindeks dokumen perusahaan secara otomatis.
2. Menjawab pertanyaan pengguna dengan proses multi-agent (riset → verifikasi → sintesis → aksi).
3. Memberikan sitasi sumber yang dapat ditelusuri untuk setiap klaim dalam jawaban.
4. Menghasilkan rekomendasi tindakan (action items) berdasarkan hasil analisis.
5. Menyediakan dashboard observability untuk memantau akurasi, biaya, dan latensi sistem.

### A.2.3 Karakteristik Pengguna

| Kelas Pengguna | Deskripsi | Kebutuhan Utama |
|---|---|---|
| Admin/Knowledge Manager | Mengelola dokumen, memantau performa sistem | Upload dokumen massal, dashboard monitoring, kontrol akses dasar |
| End User (HR, Support, Manager) | Mengajukan pertanyaan dan menerima insight | Jawaban cepat, akurat, dengan sumber jelas |
| Developer/Evaluator (dalam konteks portfolio) | Menilai kualitas teknis sistem | Kode modular, dokumentasi arsitektur, metrik evaluasi transparan |

### A.2.4 Lingkungan Operasi
- **Backend:** Python 3.11+, FastAPI, dijalankan dalam container Docker.
- **LLM Provider:** Groq Cloud API (model open-weight, lihat A.3.2).
- **Frontend:** Browser modern (Chrome, Firefox, Edge terbaru), akses via web app berbasis **Next.js** (React) — dipilih untuk hasil visual yang lebih polished dibanding Streamlit, dengan konsekuensi waktu development UI yang lebih panjang (lihat penyesuaian roadmap di B.5).
- **Database:** Supabase (PostgreSQL managed + Auth + File Storage) untuk metadata; Chroma (di VPS) untuk vector embedding. Arsitektur hybrid: Supabase mengelola data terstruktur (metadata dokumen, user, log), Chroma mengelola pencarian semantik.
- **Deployment target demo:** VPS untuk backend (FastAPI + Chroma + opsional LangFuse self-hosted), Vercel untuk frontend Next.js — agar mudah diakses reviewer/recruiter tanpa setup lokal.

### A.2.5 Batasan (Constraints)
- Biaya API harus tetap dalam anggaran mahasiswa — strategi hybrid model (model kecil untuk task ringan, model besar untuk reasoning kritis) menjadi kebutuhan, bukan pilihan opsional.
- Tidak ada SLA formal karena ini bukan sistem produksi nyata — metrik reliability diukur secara simulasi/testing, bukan uptime produksi.
- Ketergantungan pada ketersediaan model Groq — **risiko nyata** mengingat riwayat deprecation yang sering; arsitektur harus memudahkan penggantian model (abstraksi lewat LangChain `ChatGroq` wrapper, bukan hardcode di banyak tempat).

### A.2.6 Asumsi dan Dependensi
- Tersedia akun Groq API dengan kuota memadai untuk development dan testing (termasuk kemungkinan biaya kecil di luar free tier).
- Dataset dokumen contoh (200–1000 dokumen) dapat diperoleh dari sumber publik atau dokumen sintetis yang dibuat sendiri (mengingat ini bukan proyek dengan data perusahaan riil).
- Pengembang memiliki familiaritas dengan Python, LangChain/LangGraph dasar (dapat dipelajari paralel selama Fase 1).

---

## A.3 Kebutuhan Spesifik

### A.3.1 Kebutuhan Fungsional (Functional Requirements)

**FR1 — Document Ingestion & Indexing**
- FR1.1: Sistem dapat menerima upload dokumen dalam format PDF, DOCX, dan TXT.
- FR1.2: Sistem melakukan ekstraksi teks menggunakan library `unstructured` atau setara.
- FR1.3: Sistem melakukan chunking dokumen dengan strategi semantic/hierarchical (bukan fixed-size naive split).
- FR1.4: Sistem menyimpan embedding hasil chunking ke vector database beserta metadata (nama dokumen, tanggal, kategori, sumber).
- FR1.5: Sistem memberi notifikasi status ingestion (berhasil/gagal) ke admin.

**FR2 — Multi-Agent Query Processing**
- FR2.1: Sistem menerima pertanyaan dalam bahasa natural dari pengguna melalui antarmuka chat.
- FR2.2: **Orchestrator Agent** menganalisis intent query dan menentukan agent mana yang perlu diaktifkan (routing).
- FR2.3: **Researcher Agent** melakukan retrieval hybrid (vector similarity + keyword search) terhadap dokumen relevan.
- FR2.4: **Verifier/Fact-Checker Agent** memeriksa konsistensi hasil retrieval terhadap klaim yang akan disampaikan, dan menandai tingkat keyakinan (confidence score).
- FR2.5: Jika confidence score di bawah ambang batas tertentu, sistem melakukan reflection loop (retrieval ulang dengan query yang direformulasi) maksimal 2 iterasi sebelum menyerahkan jawaban dengan disclaimer.
- FR2.6: **Summarizer/Analyzer Agent** menyusun jawaban akhir dalam bahasa natural, termasuk insight tambahan bila relevan.
- FR2.7: **Executor/Action Agent** menghasilkan action item (misal draft email, to-do list) ketika query bersifat permintaan tindakan.

**FR3 — Tool Calling**
- FR3.1: Sistem mendukung tool: web search (untuk informasi di luar knowledge base internal).
- FR3.2: Sistem mendukung tool kalkulasi/analisis numerik sederhana.
- FR3.3: Sistem mendukung tool query terhadap database metadata internal (misal "dokumen apa saja yang diupload bulan ini").
- FR3.4: Setiap pemanggilan tool dicatat dalam log (via LangFuse) untuk keperluan tracing/observability.

**FR4 — Memory & Conversation History**
- FR4.1: Sistem menyimpan riwayat percakapan dalam sesi aktif (short-term memory).
- FR4.2: Sistem dapat merujuk pada konteks percakapan sebelumnya dalam sesi yang sama.
- FR4.3 (Should Have): Sistem menyimpan preferensi/pola query pengguna untuk personalisasi jangka panjang (long-term memory).

**FR5 — Citation & Source Traceability**
- FR5.1: Setiap klaim faktual dalam jawaban sistem harus disertai sitasi yang merujuk ke dokumen sumber.
- FR5.2: Pengguna dapat mengklik sitasi untuk melihat cuplikan asli dari dokumen sumber.
- FR5.3: Jika sistem tidak menemukan sumber yang memadai, sistem secara eksplisit menyatakan ketidaktahuan alih-alih mengarang jawaban.

**FR6 — Admin Dashboard**
- FR6.1: Admin dapat melihat daftar dokumen yang telah diindeks beserta statusnya.
- FR6.2: Admin dapat menghapus atau memperbarui dokumen yang sudah usang.
- FR6.3: Dashboard menampilkan metrik performa: rata-rata latensi, faithfulness score, jumlah query per hari, estimasi biaya API.

**FR7 — Evaluation & Logging**
- FR7.1: Sistem mencatat setiap interaksi (query, retrieval result, jawaban, waktu respons) untuk keperluan evaluasi.
- FR7.2: Sistem menjalankan evaluasi otomatis menggunakan RAGAS (faithfulness, answer relevance, context precision) terhadap sampel query.
- FR7.3: Hasil evaluasi dapat diekspor sebagai laporan (untuk keperluan showcase portfolio).

**Detail Evaluation Plan (FR7 diperluas):**
- **Ukuran test set:** Minimal 50 pasang Q&A (ground truth) untuk evaluasi awal; ideal 100+ jika waktu memungkinkan, mencakup variasi kasus:
  - Query sederhana (jawaban ada eksplisit di satu dokumen)
  - Query yang butuh sintesis lintas dokumen (menguji Summarizer Agent)
  - Query dengan potensi informasi kontradiktif antar dokumen (menguji Verifier Agent)
  - Query di luar cakupan knowledge base (menguji apakah sistem jujur bilang "tidak tahu", bukan mengarang)
- **Cara membuat ground truth:** Karena tidak ada data enterprise riil, ground truth dibuat manual dengan langkah:
  1. Pilih 50+ chunk dokumen representatif dari dataset.
  2. Buat pertanyaan yang jawabannya ada di chunk tersebut, tulis jawaban "ideal" secara manual.
  3. Sisipkan minimal 5-10 query jebakan (informasi tidak ada / kontradiktif) untuk menguji reflection loop dan kejujuran sistem.
  4. (Opsional, jika waktu ada) Gunakan LLM untuk membantu generate kandidat Q&A dari dokumen, lalu direview manual — bukan sepenuhnya otomatis, karena kualitas ground truth menentukan validitas seluruh evaluasi.
- **Baseline pembanding:** Jalankan test set yang sama pada baseline Naive RAG (dari Fase 1) dan Agentic RAG (sistem utama), lalu bandingkan skor faithfulness dan answer relevance — ini jadi bukti kuantitatif nilai tambah arsitektur agentic untuk showcase.

### A.3.2 Kebutuhan Non-Fungsional (Non-Functional Requirements)

**Performance**
- NFR-P1: Query sederhana (single-agent, tanpa reflection loop) direspons dalam waktu ≤ 4 detik.
- NFR-P2: Query kompleks (melibatkan reflection loop dan multi-agent) direspons dalam waktu ≤ 12 detik. *(Direvisi dari target awal 8 detik — dengan rantai 4–5 agent call, 8 detik terlalu ketat kecuali menggunakan model kecil untuk semua tahap, yang mengorbankan kualitas. 12 detik lebih realistis dengan strategi hybrid model.)*
- NFR-P3: Sistem menerapkan model routing — task ringan (routing, ekstraksi sederhana) menggunakan `openai/gpt-oss-20b`, task berat (verifikasi, sintesis akhir) menggunakan `openai/gpt-oss-120b` — untuk menyeimbangkan kecepatan dan kualitas.

**Scalability**
- NFR-S1: Sistem mampu mengindeks minimal 1.000 dokumen tanpa penurunan performa signifikan pada waktu retrieval.
- NFR-S2: Untuk keperluan demo portfolio, target beban diuji melalui **simulasi load testing** (misal menggunakan Locust) hingga 20–30 concurrent sessions — bukan infrastruktur produksi nyata yang menampung 100 pengguna aktif. *(Direvisi dari target awal 100 concurrent users, yang tidak proporsional untuk skala MVP solo-developer tanpa infrastruktur enterprise.)*

**Reliability**
- NFR-R1: Target faithfulness score (dari evaluasi RAGAS) minimal 85% pada dataset uji — target 95% pada versi awal dianggap terlalu tinggi untuk sistem berbasis model open-weight ukuran menengah; 85% adalah target yang menantang namun realistis dan tetap kompetitif untuk showcase.
- NFR-R2: Sistem harus menangani kegagalan pemanggilan API Groq (timeout, rate limit) dengan mekanisme retry dan fallback model.

**Security**
- NFR-SEC1: Autentikasi dasar (login) untuk akses dashboard admin.
- NFR-SEC2: Data dokumen tidak dikirim ke pihak ketiga selain provider LLM yang digunakan untuk inference.
- NFR-SEC3: API key disimpan sebagai environment variable, tidak pernah di-hardcode atau dikomit ke repository publik.

**Usability**
- NFR-U1: Antarmuka chat harus intuitif tanpa memerlukan pelatihan (mengikuti pola UI chatbot yang familiar, misal seperti ChatGPT/Claude).
- NFR-U2: Sistem menampilkan indikator loading/progress saat agent sedang memproses (mengingat latensi multi-agent bisa terasa oleh pengguna).

**Maintainability**
- NFR-M1: Kode diorganisasi secara modular per agent (folder terpisah untuk masing-masing agent, tools, dan graph definition).
- NFR-M2: Konfigurasi model (nama model, parameter) disimpan terpusat dalam satu file config, agar mudah diganti ketika Groq melakukan deprecation model (risiko yang sudah terbukti terjadi berkali-kali).

### A.3.3 Kebutuhan Antarmuka Eksternal
- **Antarmuka pengguna:** Web chat interface berbasis Next.js (React), dirancang untuk pengalaman visual yang setara produk chat modern (mis. pola UI ChatGPT/Claude).
- **Antarmuka API:** RESTful API (FastAPI) yang mengekspos endpoint `/query`, `/upload`, `/documents`, `/metrics`.
- **Antarmuka LLM:** Groq API via LangChain `ChatGroq` wrapper.
- **Antarmuka observability:** LangFuse (self-hosted, open-source) untuk tracing, evaluasi, dan cost monitoring — dipilih di atas LangSmith karena tidak terikat kuota berbayar setelah free tier habis.

---

# BAGIAN B — PRODUCT REQUIREMENTS DOCUMENT (PRD)

## B.1 Ringkasan Produk

### B.1.1 Visi
Menjadi contoh implementasi *production-grade thinking* dari sebuah sistem Agentic RAG — menunjukkan bukan hanya kemampuan membangun chatbot, tetapi kemampuan merancang sistem multi-agent yang reliable, dapat diaudit, dan sadar biaya/latensi seperti sistem enterprise sungguhan.

### B.1.2 Tujuan (Goals)
1. Mendemonstrasikan penguasaan arsitektur agentic (LangGraph) melampaui level RAG dasar.
2. Menunjukkan praktik *evaluation-driven development* (RAGAS, faithfulness scoring) — hal yang jarang ditunjukkan kandidat entry-level Data/ML.
3. Menghasilkan portfolio piece yang dapat di-demo secara live, bukan sekadar notebook statis.
4. Menunjukkan kesadaran terhadap *trade-off* rekayasa nyata: biaya vs kualitas, latensi vs akurasi.

### B.1.3 Non-Tujuan (Explicitly Out of Scope untuk MVP)
- Bukan sistem multi-tenant untuk banyak organisasi berbeda.
- Bukan sistem dengan compliance formal (SOC2, HIPAA, dsb.) — hanya mendemonstrasikan *awareness* terhadap prinsip keamanan dasar.
- Bukan produk dengan monetisasi atau go-to-market — murni showcase teknikal.

---

## B.2 Target Audiens & User Stories

### B.2.1 Persona

**Persona 1 — Rina, HR Generalist**
Kebutuhan: Menjawab pertanyaan karyawan soal kebijakan cuti/benefit tanpa membuka ulang dokumen SOP setiap kali.

**Persona 2 — Budi, Support Team Lead**
Kebutuhan: Menganalisis pola keluhan pelanggan dari ratusan tiket untuk menentukan prioritas perbaikan.

**Persona 3 — Sarah, Manager**
Kebutuhan: Mendapat ringkasan insight lintas laporan kuartalan tanpa membaca semua dokumen satu per satu.

### B.2.2 User Stories dengan Acceptance Criteria

**US1 (Rina):** *Sebagai HR, saya ingin menanyakan kebijakan cuti agar mendapat jawaban yang merujuk pada dokumen kebijakan terbaru.*
- AC1: Jawaban menyertakan sitasi ke dokumen SOP yang relevan beserta tanggal dokumen.
- AC2: Jika ada revisi kebijakan yang lebih baru menggantikan dokumen lama, sistem memprioritaskan dokumen dengan tanggal terbaru.
- AC3: Jika tidak ditemukan kebijakan terkait, sistem menyatakan hal tersebut secara eksplisit, bukan mengarang jawaban.

**US2 (Budi):** *Sebagai Support Lead, saya ingin menganalisis kumpulan tiket customer agar mendapat ringkasan pola masalah dan rekomendasi tindakan.*
- AC1: Sistem dapat memproses input berupa beberapa dokumen/tiket sekaligus dalam satu query analisis.
- AC2: Output berupa ringkasan pola (misal top 3 kategori keluhan) disertai rekomendasi action item konkret.
- AC3: Action item dapat diekspor sebagai teks (draft to-do list atau draft email).

**US3 (Sarah):** *Sebagai Manager, saya ingin insight lintas laporan Q2 agar tidak perlu membaca semua laporan satu per satu.*
- AC1: Sistem dapat mensintesis informasi dari lebih dari satu dokumen sumber dalam satu jawaban.
- AC2: Jawaban membedakan secara jelas antara fakta yang didukung sumber vs. inferensi/analisis tambahan dari sistem.

---

## B.3 Fitur & Prioritisasi (MoSCoW)

### Must Have (MVP — wajib ada untuk demo)
| Fitur | Terkait FR |
|---|---|
| Upload & ingestion dokumen | FR1 |
| Multi-agent chat (Orchestrator, Researcher, Verifier, Summarizer) | FR2 |
| Citation & source traceability | FR5 |
| Tracing dasar via LangSmith/LangFuse | FR7 |
| Basic tool: web search | FR3.1 |

### Should Have (nilai tambah signifikan, dikerjakan jika waktu memungkinkan)
| Fitur | Terkait FR |
|---|---|
| Executor Agent (action item generation) | FR2.7 |
| Admin dashboard metrik | FR6 |
| Evaluation report otomatis (RAGAS) | FR7.2–FR7.3 |
| Reflection/self-correction loop | FR2.5 |

### Could Have (nice-to-have, roadmap lanjutan pasca-MVP)
- Role-based access control granular
- GraphRAG (knowledge graph antar dokumen)
- Voice input/output
- Integrasi native Slack/Teams

---

## B.4 Metrik Keberhasilan (Success Metrics)

| Kategori | Metrik | Target |
|---|---|---|
| Teknis | Faithfulness Score (RAGAS) | ≥ 85% |
| Teknis | Answer Relevance (RAGAS) | ≥ 80% |
| Teknis | Latensi query kompleks | ≤ 12 detik |
| Bisnis (simulasi) | Estimasi waktu pencarian info yang dihemat | > 60% dibanding pencarian manual |
| Portfolio | Kelengkapan dokumentasi (README, diagram arsitektur, demo video) | 100% deliverable terpenuhi |
| Portfolio | Kualitas kode (modularitas, testing dasar) | Code review checklist terpenuhi |

---

## B.5 Roadmap & Timeline Terperinci (4–8 Minggu, Full-Time)

Karena kamu memilih untuk mengalokasikan waktu penuh, berikut breakdown mingguan yang lebih actionable dibanding estimasi fase besar sebelumnya:

### Fase 1 — Data Preparation & Baseline (Minggu 1–2)
- **Minggu 1:** Kumpulkan/susun dataset dokumen contoh (200–1000 dokumen: bisa kombinasi dokumen publik + dokumen sintetis buatan sendiri). Setup environment (Python, Docker, akun Groq API). Eksplorasi `unstructured` untuk ekstraksi teks.
- **Minggu 2:** Bangun pipeline ingestion dasar (chunking + embedding + vector store menggunakan Chroma untuk development). Buat baseline Naive RAG (retrieve-then-generate sekali) sebagai *pembanding* nanti — ini penting untuk showcase "Naive RAG vs Agentic RAG".

### Fase 2 — Agentic Workflow Inti (Minggu 3–5)
- **Minggu 3:** Desain graph LangGraph: definisikan state, node (Orchestrator, Researcher), dan edge routing dasar.
- **Minggu 4:** Implementasi Verifier Agent dan mekanisme confidence scoring + reflection loop. Implementasi Summarizer Agent.
- **Minggu 5:** Implementasi tool calling (web search, kalkulasi, query metadata) dan integrasi memory (short-term).

### Fase 3 — UI, Observability, Deployment (Minggu 6–7.5)
- **Minggu 6:** Bangun antarmuka chat berbasis Next.js — mulai dari layout dasar, komponen chat bubble, streaming response, dan tampilan sitasi sumber. *(Dialokasikan penuh 1 minggu karena Next.js lebih memakan waktu dibanding Streamlit; jangan mulai fitur admin dashboard dulu di minggu ini.)*
- **Minggu 7 (awal):** Selesaikan admin dashboard dasar di Next.js. Setup dan deploy LangFuse (self-hosted via Docker, atau gunakan LangFuse Cloud free tier bila ingin skip setup server sendiri) untuk tracing.
- **Minggu 7 (akhir):** Setup evaluasi otomatis dengan RAGAS terhadap dataset uji. Deploy backend + frontend ke platform cloud gratis/murah (Railway/Render/Vercel untuk Next.js). Load testing simulasi dengan Locust.

*Catatan risiko baru: karena Next.js menggeser sebagian waktu dari buffer, jika di akhir Minggu 7 UI belum sepenuhnya polished, prioritaskan fungsi (chat + sitasi + dashboard metrik dasar) di atas estetika — polish visual bisa lanjut di Minggu 8 bila waktu tersisa.*

### Fase 4 — Polish & Dokumentasi Portfolio (Minggu 8)
- Rekam demo video interaktif.
- Susun diagram arsitektur (Excalidraw/draw.io).
- Tulis README/blog post lengkap termasuk perbandingan metrik Naive RAG vs Agentic RAG.
- Review akhir kode (clean-up, komentar, modularitas).

*Catatan: Jika waktu efektif ternyata kurang dari 8 minggu penuh, fitur pada kategori "Should Have" (B.3) adalah kandidat pertama yang bisa ditunda tanpa mengorbankan inti demo.*

---

## B.6 Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Model Groq di-deprecate di tengah development | Kode error mendadak, harus refactor mendesak | Sentralisasi konfigurasi model di satu file; cek `console.groq.com/docs/models` secara berkala; siapkan fallback ke provider lain (misal OpenRouter) |
| Biaya API membengkak saat testing intensif | Kuota habis, development terhambat | Gunakan model kecil (`gpt-oss-20b`) untuk sebagian besar iterasi development, baru switch ke model besar saat testing akhir |
| Dataset dokumen tidak representatif | Hasil evaluasi tidak meyakinkan untuk showcase | Kombinasikan dokumen publik nyata (misal kebijakan HR open-source, laporan tahunan publik) dengan data sintetis yang dirancang punya variasi kasus (info kontradiktif antar dokumen, dokumen usang, dsb.) untuk menguji Verifier Agent secara berarti |
| Reflection loop menyebabkan latensi melonjak | Melanggar NFR-P2 | Batasi maksimal 2 iterasi reflection dan terapkan timeout keras |
| Development UI Next.js molor dari alokasi 1-1.5 minggu | Menggeser waktu dari Fase 4 (dokumentasi/polish) | Utamakan fungsi inti (chat, sitasi, dashboard metrik dasar) dulu; styling lanjutan jadi task fleksibel di Minggu 8 jika waktu tersisa |
| Supabase free tier limits (500MB DB, 1GB storage) | Data dokumen/metadata melebihi kapasitas gratis saat skala naik | Untuk MVP cukup; file dokumen asli bisa disimpan di VPS jika storage Supabase penuh; migrasi ke Supabase Pro hanya jika benar-benar dibutuhkan |

---

## B.7 Asumsi & Dependensi
- Ketersediaan akun Groq API dengan kuota yang cukup (termasuk kemungkinan biaya minor di luar free tier untuk model besar).
- Pengembang bersedia mempelajari LangGraph secara paralel di Minggu 1 jika belum familiar (dokumentasi resmi LangGraph cukup untuk level ini).
- Dataset uji untuk evaluasi RAGAS disiapkan secara manual (sebagai Q&A pairs) karena tidak ada data enterprise riil yang tersedia.

## B.8 Success Criteria untuk Demo Video

Demo video adalah deliverable portfolio yang paling banyak dilihat recruiter/reviewer, jadi harus menunjukkan *value* secara visual, bukan sekadar "chatbot yang jalan". Struktur demo yang direkomendasikan (durasi target 3-5 menit):

1. **Pembuka (30 detik):** Konteks masalah — knowledge worker menghabiskan waktu mencari info tersebar.
2. **Perbandingan Naive RAG vs Agentic RAG (1-1.5 menit):** Tunjukkan side-by-side query yang sama dijawab oleh baseline Naive RAG (jawaban tanpa verifikasi, berpotensi kurang akurat) vs EnterpriseMind AI (jawaban dengan sitasi + confidence score).
3. **Reflection Loop dalam Aksi (1 menit):** Tunjukkan satu contoh query yang awalnya punya confidence rendah, sistem melakukan reformulasi query, lalu berhasil menemukan jawaban yang lebih baik. Ini bagian paling *impressive* karena menunjukkan reasoning, bukan sekadar retrieval.
4. **Action Item Generation (30-45 detik):** Contoh query yang menghasilkan draft action (misal to-do list dari analisis tiket).
5. **Dashboard Observability (30 detik):** Tampilkan LangFuse trace dan metrik RAGAS sebagai bukti *production-readiness thinking*.
6. **Penutup (15 detik):** Ringkasan metrik hasil evaluasi (faithfulness score, latensi rata-rata) sebagai closing statement kuantitatif.

**Kriteria sukses demo:** Video harus bisa menjawab pertanyaan "kenapa ini lebih baik dari sekadar RAG biasa?" dalam 5 menit pertama tanpa penjelasan verbal tambahan dari kandidat.

---

*Dokumen ini adalah dokumen hidup — disarankan untuk memvalidasi ulang bagian Tech Stack (terutama nama model Groq) setiap kali akan memulai sesi development baru, mengingat frekuensi perubahan model provider ini cukup tinggi.*
