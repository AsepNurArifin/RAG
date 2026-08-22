# EnterpriseMind AI

**Intelligent Multi-Agent Knowledge Assistant** — Sistem Agentic RAG dengan arsitektur LangGraph multi-agent: Orchestrator, Researcher, Verifier, Summarizer, Executor. Dilengkapi fact verification, reflection loop, hybrid retrieval, dan full observability.

## Fitur Utama

| Fitur | Deskripsi |
|---|---|
| **Multi-Agent Orchestration** | 5 agent dikendalikan LangGraph state machine dengan conditional routing |
| **Hybrid Retrieval** | Vector similarity (70%) + keyword matching (30%) via Milvus + Sastrawi stemming |
| **Fact Verification** | Verifier Agent + Confidence Scoring + Reflection Loop (max 1 iterasi, optimized) |
| **Citation & Source Tracing** | Setiap klaim disertai sitasi ke dokumen sumber yang dapat ditelusuri |
| **Action Generation** | Executor Agent menghasilkan draft action items dari query |
| **Enterprise UI** | Next.js 16.2.10 + React 19.2.4 + Tailwind v4 + Process Rail + Confidence Indicator |
| **Observability** | LangFuse tracing per-agent (optional; enabled bila `LANGFUSE_ENABLED=true`), token usage & cost tracking di `query_logs` |
| **RAGAS Evaluation** | Evaluasi otomatis: Faithfulness, Answer Relevance, Context Precision, Recall |
| **Security-Aware** | Prompt injection mitigation, tool read-only scoping, rate limiting |
| **Performance Optimized** | Parent embedding skip, Sastrawi LRU cache, exponential backoff optimized |

## Arsitektur Sistem

```
 ┌─────────────────────────────────────────────────────────┐
 │                    USER (Browser)                        │
 └──────────────────────┬──────────────────────────────────┘
                        │
                        ▼
 ┌─────────────────────────────────────────────────────────┐
 │              VERCEL — Next.js Frontend                   │
 │  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌────────┐  │
 │  │ChatWindow│  │ProcessRail│  │CitationCard│  │Admin UI│  │
 │  └─────────┘  └──────────┘  └───────────┘  └────────┘  │
 └──────────────────────┬──────────────────────────────────┘
                        │ REST API + SSE
                        ▼
 ┌─────────────────────────────────────────────────────────┐
 │           VPS/Local — Docker Compose Stack              │
 │                                                           │
 │  ┌──────────────────────────────────────────────────┐   │
 │  │           FastAPI Backend (Python 3.11)           │   │
 │  │  ┌─────────────────────────────────────────────┐ │   │
 │  │  │         LangGraph Multi-Agent Graph         │ │   │
 │  │  │  ┌──────────┐    ┌─────────┐               │ │   │
 │  │  │  │Orchestrtr│───►│Retriever│               │ │   │
 │  │  │  │(Intent)  │    │(Hybrid) │               │ │   │
 │  │  │  └──────────┘    └────┬────┘               │ │   │
 │  │  │                       ▼                     │ │   │
 │  │  │                  ┌─────────┐               │ │   │
 │  │  │                  │Verifier │               │ │   │
 │  │  │                  │(120B)   │               │ │   │
 │  │  │                  └────┬────┘               │ │   │
 │  │  │                       ▼                     │ │   │
 │  │  │  ┌──────────┐    ┌──────────┐             │ │   │
 │  │  │  │Summrizr  │◄───│Reflection│             │ │   │
 │  │  │  │(120B)    │    │(max 1)   │             │ │   │
 │  │  │  └────┬─────┘    └──────────┘             │ │   │
 │  │  │       ▼                                    │ │   │
 │  │  │  ┌─────────┐                              │ │   │
 │  │  │  │Executor │                              │ │   │
 │  │  │  └─────────┘                              │ │   │
 │  │  └─────────────────────────────────────────────┘ │   │
 │  └──────────────────────────────────────────────────┘   │
 │                                                           │
 │  ┌───────────────┐                 ┌──────────────┐   │
 │  │ Milvus Vector │                 │  PostgreSQL  │   │
 │  │ DB (embeddings│                 │  (metadata + │   │
 │  │ + parent-child│                 │   users)     │   │
 │  │   retrieval)  │                 └──────────────┘   │
 │  └───────────────┘
 │                                                           │
 │  ┌───────────────┐  ┌────────────┐  ┌──────────────┐   │
 │  │    Docling    │  │  Temporal  │  │    MinIO     │   │
 │  │  (Layout +    │  │ (Ingestion │  │ (Document    │   │
 │  │ Table Extract)│  │  Workflow) │  │  Storage)    │   │
 │  └───────────────┘  └────────────┘  └──────────────┘   │
 └─────────────────────────────────────────────────────────┘
                        │
                        ▼
                   Groq API
              (openai/gpt-oss-20b
              openai/gpt-oss-120b)
```

### Alur Query Multi-Agent

```
User Query
    │
    ▼
Orchestrator ──→ Intent Classification (Tiered: Regex → Keyword → LLM)
    │              Raw: greeting / factual / comprehensive / analytical / procedural / comparison
    │                   / action_request / out_of_scope / ambiguous
    │              → Operational: informational / analytical / action_request / out_of_scope
    ▼
Retriever ──→ Query Expansion (Dictionary-based atau LLM untuk comprehensive/ambiguous)
    │
    └──→ Hybrid Search (Milvus Vector 70% + Sastrawi Keyword 30%)
          │     └─ Top-k adaptive berdasarkan intent (10-20 chunks)
          ▼
    Reranker ──→ Cross-Encoder (BGE-reranker-v2-m3)
          │       └─ Top-10 chunks
          ▼
    Parent Resolution ──→ Resolve parent chunks (2000 chars) dari child (500 chars)
          │
          ▼
Verifier ──→ Confidence Scoring + Fact Check (gpt-oss-120b)
    │            ├─ Score ≥ 0.6 → Summarizer
    │            └─ Score < 0.6 → Reflection (max 1x, reformulasi query)
    │                              └→ Retriever (ulang)
    ▼
Summarizer ──→ Jawaban Akhir + Sitasi (gpt-oss-120b)
    │              └─ Jika intent=action_request → Executor
    ▼
Executor ──→ Action Items (draft email / to-do list, gpt-oss-20b)
    │              └─ Requires Human Review ✓
    ▼
Response ke User (final_answer, citations, confidence_score, latency_ms, action_items)
```

### Metrik Evaluasi (RAGAS)

| Metrik | Target | Deskripsi |
|---|---|---|
| Faithfulness | ≥ 85% | Konsistensi jawaban terhadap dokumen sumber |
| Answer Relevance | ≥ 80% | Relevansi jawaban terhadap pertanyaan |
| Context Precision | ≥ 75% | Presisi konteks yang diambil |
| Context Recall | ≥ 75% | Kelengkapan konteks yang diambil |
| Latency (Simple) | ≤ 4 detik | Query single-agent tanpa reflection |
| Latency (Complex) | ≤ 12 detik | Query multi-agent dengan reflection loop |

### Perbandingan: Naive RAG vs Agentic RAG

| Aspek | Naive RAG | EnterpriseMind AI |
|---|---|---|
| Arsitektur | Single-pass retrieve→generate | Multi-agent state graph |
| Verifikasi Fakta | Tidak ada | Verifier Agent + Confidence Score |
| Self-Correction | Tidak ada | Reflection loop (max 1x, optimized) |
| Action Generation | Tidak ada | Executor Agent |
| Retrieval | Vector only | Hybrid (vector + keyword) |
| Observability | Tidak ada | LangFuse per-agent tracing |
| Keamanan | Tidak ada | Prompt injection detection + tool scoping |

## Tech Stack

| Layer | Teknologi | Versi |
|---|---|---|
| **LLM Provider** | Groq Cloud API | `openai/gpt-oss-20b` + `openai/gpt-oss-120b` |
| **Orchestration** | LangGraph + LangChain | 0.2.61 + 0.3.13 |
| **Vector DB** | Milvus (standalone, Docker) | 2.5.6 |
| **Metadata DB** | PostgreSQL (Docker) | 16.x |
| **Object Storage** | MinIO (Docker) | Latest |
| **Workflow Engine** | Temporal (Docker) | Latest |
| **Document Parser** | Docling + PyMuPDF4LLM + RapidOCR | Latest |
| **Backend** | FastAPI + Python | 0.115.0 + 3.11 |
| **Frontend** | Next.js + React + Tailwind | 16.2.10 + 19.2.4 + 4.0 |
| **Embedding Model** | BGE-M3 (HuggingFace) | BAAI/bge-m3 (1024-dim) |
| **Reranker** | BGE-Reranker-v2-m3 | BAAI/bge-reranker-v2-m3 |
| **Stemmer** | Sastrawi (Bahasa Indonesia) | 1.0.1+ |
| **Observability** | LangFuse (cloud/self-hosted) | Latest |
| **Deployment** | Docker Compose + Vercel | - |

## Cara Menjalankan

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker Desktop
- PostgreSQL 16+ (local)
- Groq API Key

### Backend Setup

```bash
cd backend

# Install uv (package manager)
pip install uv

# Install dependencies
uv sync

# Setup environment
cp .env.example .env
# Edit .env: tambahkan GROQ_API_KEY, DATABASE_URL, JWT_SECRET_KEY (wajib di
# semua environment), dll. JANGAN commit .env.

# Admin awal (fresh deployment) — buat lewat environment, BUKAN seed default:
# BOOTSTRAP_ADMIN_EMAIL=admin@company.com
# BOOTSTRAP_ADMIN_PASSWORD=<password-kuat-minimal-12-karakter>
# Admin dibuat otomatis saat backend pertama kali start.

# Start Docker services (Milvus, PostgreSQL, Temporal, MinIO, Docling)
docker compose up -d

# Jalankan migrasi database untuk deployment existing:
psql -U postgres -d enterprisemind -f app/db/migrations/001_security_storage_consistency.sql

# Database schema ter-init otomatis via /docker-entrypoint-initdb.d (fresh volume)

# Start Temporal Worker (background)
.venv\Scripts\python -m app.temporal.worker

# Start FastAPI server
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Setup environment
cp .env.example .env.local
# Edit .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000

# Run dev server
npm run dev
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Temporal UI**: http://localhost:8081
- **MinIO Console**: http://localhost:9001 (milvus-minio — dipakai Milvus untuk penyimpanan vektor & minio_client untuk document storage; endpoint app `localhost:9000`)

### Evaluasi RAGAS
```bash
cd backend
.venv\Scripts\python -m scripts.run_evaluation
# Hasil: ragas_agentic_results.csv + ragas_naive_results.csv
```

### Load Testing (Locust)
```bash
cd backend
locust -f scripts/load_test.py
# Buka http://localhost:8089
```

### Unit Tests
```bash
cd backend
pytest tests/ -v
```

## Deployment

Lihat **[DEPLOYMENT.md](DEPLOYMENT.md)** untuk panduan deploy lengkap ke VPS + Vercel.

## Performance Optimizations

Sistem telah dioptimasi untuk performa maksimal di laptop 8GB RAM:

| Optimasi | Dampak | File |
|---|---|---|
| **Parent Embedding Skip** | Parent chunk disimpan tanpa embed (hemat biaya embedding) | `embedder.py:89` |
| **Sastrawi LRU Cache** | Tokenisasi di-cache; tercatat <1s (sebelum ~35s) di `hybrid_search.py:66` | `hybrid_search.py:74` |
| **Exponential Backoff** | Retry dengan `base_delay * 2^attempt` | `llm_provider.py:77` |
| **Reflection Loop 2→1** | Worst-case query dipangkas 1 iterasi | `config.py:70` |
| **Batch Embedding** | BGE-M3 embedding dalam batch | `embedder.py` |

> Angka dampak persentase di README versi lama (‑30%, ‑50%, 2×) belum terukur ulang.
> Status `[UNMEASURED]` dan cara validasinya ada di **[OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md)**.

## Struktur Repositori

```text
EnterpriseMind_AI/
├── backend/
│   ├── app/
│   │   ├── agents/        # orchestrator, intent_classifier, query_rewriter, retriever, verifier, summarizer, executor, utils
│   │   ├── api/           # FastAPI routes: auth, query, upload, documents, metrics, sessions, users, workflows
│   │   ├── core/          # config, auth (JWT), llm_provider, postgres_client, minio_client, observability, health
│   │   ├── db/            # CRUD functions (documents, messages, queries, users) + migrations
│   │   ├── evaluation/    # RAGAS runner + test set (50+ Q&A)
│   │   ├── graph/         # LangGraph state + build_graph (satu-satunya tempat routing)
│   │   ├── ingestion/     # extractor, chunker (parent 2000/400 + child 500/100), embedder, pipeline
│   │   ├── retrieval/     # hybrid_search, reranker, parent_resolver, vector_store, stopwords_id
│   │   ├── temporal/      # Temporal workflows + activities + worker
│   │   ├── memory/        # conversation_memory
│   │   └── tools/         # calculator_tool, metadata_query_tool, tool_router (web search DILARANG)
│   ├── scripts/           # run_evaluation, build_naive_rag, load_test
│   ├── tests/             # Unit tests
│   ├── Dockerfile
│   ├── docker-compose.yml     # Infra: milvus-etcd, milvus-minio, milvus, temporal-db, temporal, postgres-app, temporal-ui, docling (8 service)
│   └── docker-compose.prod.yml# Prod: + service backend (FastAPI) & worker (Temporal)
├── frontend/
│   ├── app/               # (chat), admin, admin/users, login
│   ├── components/        # ChatWindow, MessageBubble, CitationCard, ErrorBoundary, LoadingIndicator
│   │   ├── layout/        # SideNavBar, UserSideNavBar, ProcessRail
│   │   ├── admin/         # DocumentTable, DocumentUploader, MetricsPanel
│   │   ├── auth/          # (kosong)
│   │   └── ui/            # shadcn/ui primitives (button, card, dialog, table, dsb.)
│   ├── context/           # ActiveAgentContext, AuthContext
│   ├── hooks/             # useChatStream
│   ├── lib/               # api.ts, utils.ts
│   └── types/             # index.ts
├── docs/                  # 13 dokumen HR training (PDF/PPTX) — knowledge base
├── ARCHITECTURE.md        # Arsitektur detail + constraints
├── OPTIMIZATION_PLAN.md   # Performance optimizations detail
├── AI_RULES.md            # Aturan untuk AI coding agent
├── CODING_STANDARDS.md    # Konvensi kode
├── DECISION_LOG.md        # ADR (keputusan teknis)
├── DEFINITION_OF_DONE.md  # Checklist selesai task
├── DEPLOYMENT.md          # Panduan deploy production
├── PROMPT_LIBRARY.md      # System prompt tiap agent
├── SECURITY.md            # Keamanan agentic RAG
└── EnterpriseMind_AI_SRS_PRD.md  # Full requirements specification
```

## Dokumentasi Lengkap

| File | Deskripsi |
|---|---|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Arsitektur sistem, constraints, trade-offs |
| **[CODING_STANDARDS.md](CODING_STANDARDS.md)** | Konvensi kode Python & TypeScript |
| **[DECISION_LOG.md](DECISION_LOG.md)** | Architecture Decision Records (ADR) |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Panduan deploy VPS + Vercel |
| **[SECURITY.md](SECURITY.md)** | Keamanan: prompt injection, RBAC, rate limiting |
| **[PROMPT_LIBRARY.md](PROMPT_LIBRARY.md)** | System prompts untuk tiap agent |
| **[EnterpriseMind_AI_SRS_PRD.md](EnterpriseMind_AI_SRS_PRD.md)** | Requirements lengkap |

## Kontributor

Developed by **Arifi** — Full-stack AI Engineer

## Lisensi

Proyek portfolio pribadi. Tidak untuk produksi komersial tanpa izin.
