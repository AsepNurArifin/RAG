# CHANGELOG — EnterpriseMind AI

> **Tanggal**: 16 Juli 2026
> **Scope**: Full system overhaul — dari prototype ke production-grade AI Search
> **Metode**: 8 Sprint per-komponen + evaluasi setelah setiap sprint

---

## 0.1 Neo4j Graph Removal (2026-08-12)

Menghapus total Knowledge Graph (Neo4j) layer yang overengineering — extraction memakan biaya LLM per upload tapi `graph_context` tidak pernah dibaca agent mana pun (dead output).

### Dihapus
- `app/core/neo4j_client.py`, `app/ingestion/graph_extractor.py`, `app/retrieval/graph_traversal.py`, `app/api/graph.py`, `app/db/graph.py`
- Service `neo4j` + volume `neo4j_data`/`neo4j_logs` di `docker-compose.yml`
- Tabel `graph_drafts` dari `schema.sql` & `supabase_migration.sql`
- Dependency `neo4j` dari `pyproject.toml`/`uv.lock`
- `GRAPH_PLAN.md`

### Dimodifikasi
- `ingestion/pipeline.py`: hapus Step 4 (graph extraction) & `run_graph_extraction()`
- `temporal/workflows.py` & `activities.py` & `worker.py`: hapus `extract_graph_activity` & step-nya
- `agents/retriever.py`: hapus blok graph traversal & `graph_context` dari return
- `graph/state.py`: hapus field `graph_context` (LangGraph utuh)
- `api/query.py` & `scripts/run_evaluation.py`: hapus `graph_context` dari initial state
- `app/core/config.py`: hapus settings `NEO4J_*`
- PostgreSQL volume di-reset → schema fresh tanpa `graph_drafts`

### Hasil
- LangGraph (`app/graph/`) tidak disentuh — jantung multi-agent tetap utuh
- Ingestion lebih cepat (tanpa LLM extraction call tambahan)
- 1 service Docker berkurang (~768MB RAM hemat)

---

## 0. Production Readiness Fix (2026-08-05)

Perubahan untuk menghilangkan pemblokir produksi dan hardening keamanan.

### Keamanan & Auth
- **ADR-012**: Migrasi autentikasi frontend dari JWT di `localStorage` + header Bearer → **httpOnly cookie murni**. Semua fetch memakai `credentials: "include"`; token state dihapus dari `AuthContext` dan `api.ts`.
- Hapus sentinel mock `"cookie-session"` di `AuthContext`.
- Backend `delete_cookie` kini mengikuti `secure` sesuai environment (dev HTTP logout berfungsi).

### Database
- Tulis ulang `supabase_migration.sql` agar 100% sinkron dengan `app/db/schema.sql` (sumber kebenaran): kolom `password_hash`, role `('admin','analyst','viewer')`, `session_id`, tabel `chunk_hashes` & `graph_drafts`. Idempotent (`CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS`).
- `schema.sql`: tambah kolom `department` & `clearance_level` (dibaca oleh `core/auth.py`).

### Backend Fixes
- **Circular import** di `app/graph/__init__.py` (eager-import `build_graph`) dihapus — aplikasi kini bisa di-import tanpa error.
- `reload=True` di `main.py` → hanya aktif di `APP_ENV=development`.
- `TEMPORAL_HOST` dipindah dari `os.getenv` langsung ke `Settings` (`config.py`) — Single Source of Truth.
- Silent exception di `core/auth.py`, `temporal/workflows.py`, `api/sessions.py` kini di-log.
- Hapus dead code `app/ingestion/extractor_hybrid_backup.py` (563 baris) & jejak ChromaDB di `main.py`/`docker-compose.yml`.

### Tests
- `conftest.py`: hapus fixture `mock_supabase` yang rusak → `mock_db` (postgres_client).
- `test_auth.py`, `test_tools.py`, `test_orchestrator.py`, `test_verifier.py`, `test_ingestion.py` disinkronkan dengan kode aktual.
- Tambah `test_smoke.py` (4 test) & `test_orchestrator` case coverage.
- **Total: 50 test lulus** (sebelumnya import error).

### Config & Docs
- `.env.example`: ganti `GOOGLE_API_KEY` → `GROQ_API_KEY` (+ model fast/reasoning), tambah `NEO4J_*`, `CHUNK_*`, `MAX_UPLOAD_SIZE_MB`, `EXTRACTION_TIMEOUT_SECONDS`, peringatan ganti `JWT_SECRET_KEY`.
- `SECURITY.md` bagian 6 (Session Management) & `DECISION_LOG.md` ADR-012.

---

## Daftar Isi

1. [File Baru yang Dibuat](#1-file-baru-yang-dibuat)
2. [File yang Diedit/Diubah](#2-file-yang-dieditdiubah)
3. [File yang Dihapus](#3-file-yang-dihapus)
4. [Perubahan per Komponen](#4-perubahan-per-komponen)
5. [Dokumentasi yang Dibuat](#5-dokumentasi-yang-dibuat)

---

## 1. File Baru yang Dibuat

### Backend — Core & Config

| File | Deskripsi |
|------|-----------|
| `backend/app/core/postgres_client.py` | Async PostgreSQL client menggunakan asyncpg. Connection pool (min=2, max=20). Fungsi: `get_pool()`, `execute_query()`, `fetch_one()`, `fetch_all()`, `fetch_val()`. Menggantikan `supabase_client.py`. |

### Backend — Database

| File | Deskripsi |
|------|-----------|
| `backend/app/db/documents.py` | CRUD operasi untuk tabel `documents` di PostgreSQL. Fungsi: `create_document()`, `update_document_status()`, `get_all_documents()`, `delete_document()`. Dipindah dari `db/__init__.py`. |
| `backend/app/db/messages.py` | CRUD operasi untuk tabel `messages` di PostgreSQL. Fungsi: `save_message()`. Dipindah dari `db/__init__.py`. |
| `backend/app/db/queries.py` | CRUD operasi untuk tabel `query_logs` di PostgreSQL. Fungsi: `log_query()`. Dipindah dari `db/__init__.py`. |
| `backend/scripts/migrate.sql` | SQL migration script untuk membuat tabel: `users`, `documents`, `conversations`, `messages`, `query_logs`, `parent_chunks`. Termasuk indexes dan default admin user. |

### Backend — Agents (Intent & Query)

| File | Deskripsi |
|------|-----------|
| `backend/app/agents/intent_classifier.py` | **Tiered Intent Classifier** (3 tier). Tier 1: Regex/Rule (0ms, $0) — greeting, action_request. Tier 2: Keyword (0ms, $0) — comprehensive, analytical, comparison, procedural, factual. Tier 3: LLM fallback (~0.3s, $0.0001) — ambiguous queries. Target: >60% query terklasifikasi tanpa LLM. |
| `backend/app/agents/query_rewriter.py` | **Query Expansion Decision Tree**. 1) Dictionary abbreviation (0ms). 2) Dictionary synonym (0ms). 3) LLM expansion (hanya untuk comprehensive/ambiguous). Mengurangi latency expansion 70% dibanding semua pakai LLM. |

### Backend — Retrieval

| File | Deskripsi |
|------|-----------|
| `backend/app/retrieval/stopwords_id.py` | **211 stop words** bahasa Indonesia untuk BM25 tokenisasi. Mencakup: pronouns, prepositions, conjunctions, adverbs, interrogatives, auxiliary verbs, dan kata umum lainnya. |
| `backend/app/retrieval/reranker.py` | **Cross-Encoder Reranker** menggunakan model `BAAI/bge-reranker-v2-m3`. Singleton pattern (lazy load). Fungsi: `rerank_chunks(query, chunks, top_k=5)`. Meningkatkan Context Precision. |
| `backend/app/retrieval/parent_resolver.py` | **Parent Resolution + Deduplication**. Fungsi: `resolve_and_deduplicate_parents(child_chunks, parent_store)` — mengubah 20 child chunks menjadi ~7 unique parents. Menghilangkan duplikat konteks. |

### Backend — Temporal (Async Ingestion)

| File | Deskripsi |
|------|-----------|
| `backend/app/temporal/__init__.py` | Package marker. Re-export `start_ingestion_workflow`, `IngestionWorkflow`. |
| `backend/app/temporal/workflows.py` | **IngestionWorkflow** — Temporal workflow untuk fault-tolerant document ingestion. Jika server crash saat embedding, Temporal resume dari chunk terakhir yang sukses. |
| `backend/app/temporal/activities.py` | **6 Temporal Activities**: `detect_file_type_activity`, `extract_text_activity`, `chunk_document_activity`, `embed_and_store_activity`, `create_document_record_activity`, `update_document_status_activity`. Setiap activity bisa di-retry independently. |
| `backend/app/temporal/worker.py` | **Temporal Worker** — process yang menjalankan activities. Run dengan: `python -m app.temporal.worker`. |
| `backend/app/temporal/client.py` | **Temporal Client Helper** — Fungsi `start_ingestion_workflow()` untuk memulai workflow dari FastAPI. |

### Backend — Evaluation

| File | Deskripsi |
|------|-----------|
| `backend/app/evaluation/test_set.json` | **100 pertanyaan** untuk evaluasi domain knowledge. Komposisi: 30 factual, 20 listing, 20 comparison, 20 procedural, 10 analytical. Setiap pertanyaan punya `expected_answer_contains`, `expected_sources`, `difficulty`. |
| `backend/app/evaluation/evaluate.py` | **Custom Offline Evaluation Framework**. Metrics: Recall@20, Answer Contains, Context Precision, Latency P50/P95. Fungsi: `run_evaluation()`, `compare_results()`, `print_summary()`. Output: JSON dengan per-kategori breakdown. |
| `backend/app/evaluation/results/` | Directory untuk menyimpan hasil evaluasi (baseline.json, eval_*.json). |

### Backend — Data Dictionaries

| File | Deskripsi |
|------|-----------|
| `backend/data/synonyms_id.json` | **100+ sinonim** bahasa Indonesia untuk query expansion. Contoh: "pensiun" → ["purna tugas", "retirement"], "cuti" → ["izin", "libur", "leave"]. |
| `backend/data/abbreviations_id.json` | **50+ singkatan** enterprise untuk query expansion. Contoh: "SOP" → ["standar operasional prosedur"], "HRD" → ["human resource development", "sumber daya manusia"]. |

### Backend — Scripts

| File | Deskripsi |
|------|-----------|
| `backend/scripts/reindex.py` | **Re-index Script** — Re-embed semua dokumen dengan embedding model baru. Run: `python -m scripts.reindex --clear` |
| `backend/Makefile` | **Build Automation** — Commands: `setup`, `dev`, `backend`, `worker`, `frontend`, `start`, `stop`, `migrate`, `eval`, `reindex`, `test`, `lint`, `clean`. |

### Frontend — Flowcharts

| File | Deskripsi |
|------|-----------|
| `docs/flowcharts/01-rbac-retrieval.html` | Flowchart alur RBAC Retrieval (HTML + CSS) |
| `docs/flowcharts/02-ingestion-arq-redis.html` | Flowchart alur Ingestion ARQ+Redis (HTML + CSS) |
| `docs/flowcharts/03-auth-flow.html` | Flowchart alur Authentication (HTML + CSS) |
| `docs/flowcharts/04-multi-agent-pipeline.html` | Flowchart alur Multi-Agent Pipeline (HTML + CSS) |
| `docs/flowcharts/05-reflection-loop.html` | Flowchart alur Reflection Loop (HTML + CSS) |
| `docs/flowcharts/06-error-handling.html` | Flowchart alur Error Handling (HTML + CSS) |
| `docs/flowcharts/index.html` | Index page navigasi semua flowchart |

### Planning Documents

| File | Deskripsi |
|------|-----------|
| `IMPLEMENTATION_PLAN.md` | **v3.1** — Rencana implementasi lengkap dengan 8 sprint, acceptance criteria per sprint, trade-off matrix, test set composition, decision trees. |
| `CHANGELOG.md` | File ini — dokumentasi semua perubahan. |

---

## 2. File yang Diedit/Diubah

### Backend — Core

| File | Perubahan |
|------|-----------|
| `backend/app/core/config.py` | **Hapus**: `REASONING_MODEL`, `FAST_MODEL`, `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`. **Tambah**: `GEMINI_MODEL="gemini-2.5-flash"`, `GOOGLE_API_KEY`, `DATABASE_URL`, `EMBEDDING_DIMENSIONS=1024`. **Update**: `EMBEDDING_MODEL` dari `all-MiniLM-L6-v2` ke `BAAI/bge-m3`. |
| `backend/app/core/llm_provider.py` | **Rewrite**: `ChatGroq` → `ChatGoogleGenerativeAI`. Model: Gemini 2.5 Flash. Temperature: fast=0.1, reasoning=0.4. **Update**: `max_tokens` dari 4096 ke 8192. |
| `backend/app/core/auth.py` | **Rewrite**: Supabase → PostgreSQL. **Tambah**: RBAC fields (`department`, `clearance_level`) di JWT payload. **Tambah**: fungsi `get_user_rbac_filter(user)` untuk build filter metadata. |

### Backend — Database

| File | Perubahan |
|------|-----------|
| `backend/app/db/__init__.py` | **Rewrite**: Dari 297 baris (full CRUD) → 17 baris (re-export saja). CRUD dipindah ke `documents.py`, `messages.py`, `queries.py`. |

### Backend — Agents

| File | Perubahan |
|------|-----------|
| `backend/app/agents/__init__.py` | **Update**: `SUMMARIZER_PROMPT` — tambah conditional logic (listing vs analysis vs factual). Listing queries boleh kutip langsung dari sumber. |
| `backend/app/agents/orchestrator.py` | **Rewrite**: Integrasi tiered intent classifier. Hapus LLM call untuk routing. Sekarang: Rule → Keyword → LLM (hanya jika ambiguous). |
| `backend/app/agents/retriever.py` | **Rewrite**: Tambah query expansion (decision tree), adaptive top-k (multi-signal), cross-encoder reranker, parent resolution + deduplication. Pipeline: expand → adaptive k → hybrid search → rerank → resolve parents. |
| `backend/app/agents/utils.py` | **Update**: `max_chars` dari 800 ke 1500 (+87.5% context window). |

### Backend — Retrieval

| File | Perubahan |
|------|-----------|
| `backend/app/retrieval/hybrid_search.py` | **Rewrite**: Ganti stemming ke Sastrawi. Tambah 211 stop words dari `stopwords_id.py`. Tambah synonym expansion. Tambah bigram matching. Ganti `_simple_stem()` ke `_stem_word()` (Sastrawi). |

### Backend — Ingestion

| File | Perubahan |
|------|-----------|
| `backend/app/ingestion/chunker.py` | **Tambah**: `chunk_document_parent_child()` — Parent 2000 chars (overlap 400) + Child 500 chars (overlap 100). Parent untuk konteks LLM, Child untuk embedding. |
| `backend/app/ingestion/embedder.py` | **Tambah**: `embed_and_store_parent_child()` — Store parent chunks untuk lookup, embed child chunks untuk retrieval. **Update**: `trust_remote_code=True` untuk bge-m3. |
| `backend/app/ingestion/pipeline.py` | **Rewrite**: Gunakan parent-child chunking. Return `parent_count` dan `child_count`. |

### Backend — API

| File | Perubahan |
|------|-----------|
| `backend/app/api/upload.py` | **Rewrite**: Dari sync pipeline → async Temporal workflow. Return 202 Accepted + `workflow_id`. Require admin role. |
| `backend/app/api/query.py` | **Rewrite**: Supabase → PostgreSQL. **Tambah**: RBAC filter injection (`get_user_rbac_filter(user)`). **Tambah**: `intent_type`, `intent_confidence`, `rbac_filter` ke initial state. |
| `backend/app/api/auth.py` | **Rewrite**: Supabase → PostgreSQL. **Tambah**: RBAC fields (`department`, `clearance_level`) di JWT payload saat login. |

### Backend — Evaluation

| File | Perubahan |
|------|-----------|
| `backend/app/evaluation/ragas_runner.py` | **Update**: `ChatGroq` → `ChatGoogleGenerativeAI`. Model: Gemini 2.5 Flash. |

### Backend — Dependencies

| File | Perubahan |
|------|-----------|
| `backend/requirements.txt` | **Hapus**: `langchain-groq`, `supabase`. **Tambah**: `langchain-google-genai>=2.0.0`, `Sastrawi>=1.0.1`, `asyncpg>=0.29.0`, `temporalio>=1.8.0`. **Update**: `httpx` 0.27.2 → 0.28.1. |
| `backend/pyproject.toml` | **Hapus**: `langchain-groq`, `supabase`. **Tambah**: `langchain-google-genai`, `Sastrawi`, `asyncpg`, `temporalio`. **Update**: `httpx`, `description`. |
| `backend/docker-compose.yml` | **Rewrite**: Hapus PostgreSQL, Backend, Worker dari Docker. Simpan hanya ChromaDB + Temporal. Temporal connect ke PostgreSQL lokal via `host.docker.internal`. |
| `backend/.env` | **Hapus**: Supabase keys. **Tambah**: `DATABASE_URL`, `CHROMA_HOST`, `CHROMA_PORT`, `TEMPORAL_HOST`. **Update**: `EMBEDDING_MODEL=BAAI/bge-m3`, `GOOGLE_API_KEY`. |
| `backend/.env.example` | **Update**: Sama dengan .env (tanpa secrets). |

### Backend — Other Files

| File | Perubahan |
|------|-----------|
| `backend/app/main.py` | **Update**: Logging — hapus `FAST_MODEL`/`REASONING_MODEL`, ganti dengan `GEMINI_MODEL`. |
| `backend/scripts/build_naive_rag.py` | **Update**: `FAST_MODEL` → `GEMINI_MODEL`. |
| `backend/app/graph/state.py` | **Tambah**: `intent_type: str`, `intent_confidence: float` fields. |

### Frontend — UI Redesign

| File | Perubahan |
|------|-----------|
| `frontend/app/(chat)/layout.tsx` | **Update**: `bg-[#F2C300]` → `bg-[#f8fafc]`. Hapus `md:mr-[64px]`. ProcessRail sekarang floating di dalam main area. |
| `frontend/components/layout/ProcessRail.tsx` | **Rewrite**: Dari fixed sidebar (64px) → floating collapsible panel. Tombol toggle di top-right. Animated open/close. |
| `frontend/components/ChatWindow.tsx` | **Rewrite**: Tambah header bar (gradient biru + "System Active"). Surface: `bg-[#e6f0fa]` → `bg-white`. Input area gradient fix. |
| `frontend/components/MessageBubble.tsx` | **Update**: User bubble: `bg-slate-900` → `bg-[#004790]`. AI card: `bg-[#e6f0fa]` → `bg-white`. Confidence ring: dynamic color (green/amber/red). Action items: `bg-amber-50` → `bg-[#F2C300]/10`. |
| `frontend/components/CitationCard.tsx` | **Update**: Card bg: `bg-[#e6f0fa]` → `bg-white`. Match badge: `bg-[#e6f0fa] text-[#0077ff]`. |
| `frontend/components/LoadingIndicator.tsx` | **Update**: Bubble bg: `bg-[#e6f0fa]` → `bg-white`. Avatar: `Bot` icon. |
| `frontend/components/layout/UserSideNavBar.tsx` | **Rewrite**: Sidebar bg: `bg-[#0077ff]` → `bg-[#004790]`. Tambah `Sparkles` icon di header. Active nav: `bg-blue-800/80` → `bg-white/15`. Dialog bg: `bg-[#e6f0fa]` → `bg-white`. |
| `frontend/components/layout/SideNavBar.tsx` | **Rewrite**: Sidebar bg: `bg-[#0077ff]` → `bg-[#004790]`. Tambah `Sparkles` icon. Active nav: `bg-blue-800/80` → `bg-white/15`. |
| `frontend/app/login/page.tsx` | **Rewrite**: Hapus gradient multi-warna. Page bg: gradient → `bg-[#f8fafc]`. Logo: `ShieldCheck` → `Sparkles` di `bg-[#004790]`. Card: `bg-[#e6f0fa]/95` → `bg-white`. Button: `bg-[#0057A8]` → `bg-[#0077ff]`. |
| `frontend/app/admin/layout.tsx` | **Update**: `bg-[#F2C300]` → `bg-[#f8fafc]`. Hapus `md:mr-[64px]`. |
| `frontend/app/admin/page.tsx` | **Update**: Cards: `bg-[#e6f0fa]` → `bg-white`. Headers: `bg-[#e6f0fa]` → `bg-[#f8fafc]`. |
| `frontend/app/admin/metrics/page.tsx` | **Update**: Cards: `bg-[#e6f0fa]` → `bg-white`. Table: `bg-[#e6f0fa]` → `bg-white`. |
| `frontend/app/admin/users/page.tsx` | **Update**: Cards: `bg-[#e6f0fa]` → `bg-white`. Dialogs: `bg-[#e6f0fa]` → `bg-white`. |
| `frontend/components/admin/DocumentTable.tsx` | **Update**: Desktop table: `bg-[#e6f0fa]` → `bg-white`. |
| `frontend/components/admin/DocumentUploader.tsx` | **Update**: Select, dropzone, button: `bg-[#e6f0fa]` → `bg-white`/`bg-slate-100`. |
| `frontend/components/admin/MetricsPanel.tsx` | **Rewrite**: Dark theme (`bg-white/5`, `text-white/90`) → Light theme (`bg-white`, `text-slate-900`). Stats cards: `bg-black/40` → `bg-slate-100`. |

### Docstring Cleanup

| File | Perubahan |
|------|-----------|
| `backend/app/ingestion/extractor.py` | Hapus verbose docstrings. Simpan OCR fallback note. |
| `backend/app/ingestion/chunker.py` | Hapus verbose docstrings. Simpan separator hierarchy. |
| `backend/app/ingestion/embedder.py` | Hapus verbose docstrings. Simpan singleton pattern. |
| `backend/app/ingestion/pipeline.py` | Hapus verbose docstrings. Simpan status format. |
| `backend/app/retrieval/hybrid_search.py` | Hapus verbose docstrings. Simpan scoring formula. |
| `backend/app/retrieval/vector_store.py` | Hapus verbose docstrings. |
| `backend/app/agents/orchestrator.py` | Hapus verbose docstrings. |
| `backend/app/agents/retriever.py` | Hapus verbose docstrings. |
| `backend/app/agents/verifier.py` | Hapus verbose docstrings. Simpan confidence formula + security note. |
| `backend/app/agents/summarizer.py` | Hapus verbose docstrings. Simpan citation logic. |
| `backend/app/core/supabase_client.py` | Hapus verbose docstrings. |

---

## 3. File yang Dihapus

| File | Alasan |
|------|--------|
| `backend/evaluation/__init__.py` | Dipindah ke `app/evaluation/` |
| `backend/evaluation/test_set.json` | Dipindah ke `app/evaluation/test_set.json` |
| `backend/evaluation/evaluate.py` | Dipindah ke `app/evaluation/evaluate.py` |
| `backend/evaluation/results/` | Dipindah ke `app/evaluation/results/` |
| `backend/app/evaluation/__pycache__/` | Cleanup |

---

## 4. Perubahan per Komponen

### LLM Provider

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| Provider | Groq (`langchain-groq`) | Google Gemini (`langchain-google-genai`) |
| Model Reasoning | `llama-3.3-70b-versatile` | `gemini-2.5-flash` (temp=0.4) |
| Model Fast | `llama-3.1-8b-instant` | `gemini-2.5-flash` (temp=0.1) |
| Max Tokens | 4096 | 8192 |
| Context Window | ~128K tokens | ~1M tokens |

### Embedding

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| Model | `all-MiniLM-L6-v2` (22M params) | `BAAI/bge-m3` (568M params) |
| Dimensions | 384 | 1024 |
| Multilingual | English-dominant | Multilingual (bahasa Indonesia bagus) |
| Trust Remote Code | Tidak | Ya |

### Chunking

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| Strategi | Recursive (single level) | Parent-Child (2 level) |
| Chunk Size | 1000 chars | Parent: 2000 chars, Child: 500 chars |
| Overlap | 200 chars | Parent: 400 chars, Child: 100 chars |
| Storage | Semua di Chroma | Child di Chroma (embed), Parent di Chroma (lookup) |
| Context | 5 chunks × 800 chars = 4.000 chars | 5 parents × 1.500 chars = 7.500 chars |

### Retrieval

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| Top-k | Fixed k=5 | Adaptive k=3-25 (berdasarkan intent) |
| BM25 Stemming | Simple suffix removal | Sastrawi (bahasa Indonesia) |
| Stop Words | 22 kata | 211 kata |
| Synonym | Tidak ada | 100+ sinonim (dictionary) |
| Bigram | Tidak ada | Ya (match kata majemuk) |
| Reranker | Tidak ada | Cross-encoder `BAAI/bge-reranker-v2-m3` |
| Parent Resolution | Tidak ada | Deduplicate parents (20 children → ~7 parents) |
| Query Expansion | Tidak ada | Decision tree: Dictionary → LLM |

### Intent Classification

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| Metode | Semua pakai LLM (0.3s, $0.0001) | Tiered: Rule → Keyword → LLM |
| Latency | ~0.3s per query | ~0ms untuk 60%+ query |
| Cost | $0.0001 per query | $0 untuk 60%+ query |
| Intents | informational, analytical, action_request, out_of_scope | factual, comprehensive, analytical, comparison, procedural, action_request, greeting |

### Prompt Engineering

| Aspek | Sebelum | Sesudah |
|-------|---------|-------|
| Summarizer | "JANGAN PERNAH copy" (restriktif) | Conditional: listing boleh kutip, analysis sintesis |
| Format | Paragraf naratif saja | Markdown + bullet points + numbered list |
| Sitasi | Format tidak konsisten | [1], [2] + daftar sumber |

### Database

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| Backend | Supabase (managed) | PostgreSQL (local, asyncpg) |
| Client | `supabase_client.py` | `postgres_client.py` (async pool) |
| Tables | Supabase dashboard | SQL migration script |

### Authentication & RBAC

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| JWT Payload | `sub`, `role`, `token_version` | + `department`, `clearance_level` |
| User Profile | Tidak ada RBAC fields | `department`, `clearance_level` di users table |
| Document Filter | Tidak ada | `filter_metadata` mandatory (department + clearance_level) |
| Retriever | Tanpa filter | RBAC filter injected dari user profile |

### Ingestion Pipeline

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| Eksekusi | Sync (blocking di API thread) | Async (Temporal workflow) |
| Upload Response | 200 (tunggu selesai) | 202 Accepted + workflow_id |
| Fault Tolerance | Tidak ada (crash = gagal) | Temporal resume dari chunk terakhir |
| Retry | Tidak ada | Per-activity retry policy |
| Worker | Tidak ada | Temporal worker process |

### Infrastructure

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| Docker | Backend + Chroma di Docker | Chroma + Temporal di Docker (Backend local) |
| PostgreSQL | Supabase (managed) | Local (DBeaver) |
| Startup | Manual | `make setup`, `make dev` |
| Services | 1 Docker container | 2 Docker (Chroma) + 3 local (Backend, Worker, Frontend) |

---

## 5. Dokumentasi yang Dibuat

| File | Isi |
|------|-----|
| `IMPLEMENTATION_PLAN.md` | v3.1 — 8 sprint plan, acceptance criteria, trade-off matrix, decision trees, pipeline diagrams |
| `CHANGELOG.md` | File ini — dokumentasi lengkap semua perubahan |
| `docs/flowcharts/index.html` | Navigasi 6 flowcharts HTML |
| `backend/app/db/schema.sql` | SQL schema untuk semua tabel |
| `backend/.env.example` | Template environment variables |
| `backend/Makefile` | Build automation commands |

---

## Ringkasan Angka

| Metrik | Jumlah |
|--------|--------|
| File baru dibuat | ~30 |
| File diedit/diubah | ~35 |
| File dihapus | 4 |
| Baris kode baru | ~3.000+ |
| Dependencies ditambah | 4 (langchain-google-genai, Sastrawi, asyncpg, temporalio) |
| Dependencies dihapus | 2 (langchain-groq, supabase) |
| Sprint selesai | 8/8 |
| Test questions | 100 (domain) + 50 (teknis) |
| Stop words | 211 |
| Synonyms | 100+ |
| Abbreviations | 50+ |
