# EnterpriseMind AI

**Intelligent Multi-Agent Knowledge Assistant** — Sistem Agentic RAG dengan arsitektur LangGraph multi-agent: Orchestrator, Researcher, Verifier, Summarizer, Executor. Dilengkapi fact verification, reflection loop, hybrid retrieval, **Knowledge Graph reasoning**, dan full observability.

## Fitur Utama

| Fitur | Deskripsi |
|---|---|
| **Multi-Agent Orchestration** | 5 agent dikendalikan LangGraph state machine dengan conditional routing |
| **Knowledge Graph (Neo4j)** | Entity extraction + relationship mapping untuk multi-hop reasoning & learning paths |
| **Hybrid Retrieval** | Vector similarity (70%) + keyword matching (30%) via Milvus + Sastrawi stemming |
| **Conditional Graph Traversal** | Graph reasoning hanya aktif untuk query analytical/comparison/comprehensive |
| **Fact Verification** | Verifier Agent + Confidence Scoring + Reflection Loop (max 1 iterasi, optimized) |
| **Citation & Source Tracing** | Setiap klaim disertai sitasi ke dokumen sumber yang dapat ditelusuri |
| **Action Generation** | Executor Agent menghasilkan draft action items dari query |
| **Enterprise UI** | Next.js 16 + React 19 + Tailwind v4 + Process Rail + Confidence Indicator |
| **Draft-then-Review** | Entity extraction disimpan di PostgreSQL dulu, review sebelum commit ke Neo4j |
| **Observability** | LangFuse tracing per-agent, latency monitoring, token cost tracking |
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
 │  │  │  │(Intent)  │    │(Hybrid+ │               │ │   │
 │  │  │  └──────────┘    │ Graph)  │               │ │   │
 │  │  │                  └────┬────┘               │ │   │
 │  │  │                       ▼                     │ │   │
 │  │  │                  ┌─────────┐               │ │   │
 │  │  │                  │Verifier │               │ │   │
 │  │  │                  │(70B LLM)│               │ │   │
 │  │  │                  └────┬────┘               │ │   │
 │  │  │                       ▼                     │ │   │
 │  │  │  ┌──────────┐    ┌──────────┐             │ │   │
 │  │  │  │Summrizr  │◄───│Reflection│             │ │   │
 │  │  │  │(70B LLM) │    │(max 1)   │             │ │   │
 │  │  │  └────┬─────┘    └──────────┘             │ │   │
 │  │  │       ▼                                    │ │   │
 │  │  │  ┌─────────┐                              │ │   │
 │  │  │  │Executor │                              │ │   │
 │  │  │  └─────────┘                              │ │   │
 │  │  └─────────────────────────────────────────────┘ │   │
 │  └──────────────────────────────────────────────────┘   │
 │                                                           │
 │  ┌───────────────┐  ┌────────────┐  ┌──────────────┐   │
 │  │ Milvus Vector │  │   Neo4j    │  │  PostgreSQL  │   │
 │  │ DB (embeddings│  │ (Knowledge │  │  (metadata + │   │
 │  │ + parent-child│  │   Graph)   │  │  graph_drafts│   │
 │  │   retrieval)  │  │            │  │   + users)   │   │
 │  └───────────────┘  └────────────┘  └──────────────┘   │
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
              (llama-3.1-8b-instant
              llama-3.3-70b-versatile)
```

## Knowledge Graph Integration (Neo4j)

### Entity Types (7 tipe selektif)
- **Skill**: Kompetensi (Python, Leadership, Data Analysis)
- **Training**: Modul pelatihan (TNA, DNA, LVC)
- **SOP**: Prosedur standar (SOP Cuti, SOP WFH)
- **Department**: Divisi (HR, Finance, Operations)
- **Position**: Jabatan (HRBP, Manager, Analyst)
- **Certificate**: Sertifikat (Certified Trainer, BNSP)
- **Policy**: Kebijakan (WFH Policy, Leave Policy)

### Relationship Types (5 tipe)
- **PREREQUISITE_FOR**: A harus dikuasai sebelum B
- **REQUIRES**: Training membutuhkan Skill
- **PART_OF**: A adalah sub-bagian dari B
- **GOVERNS**: Policy berlaku untuk Department/Position
- **MENTIONED_IN**: Entity muncul di dokumen

### Conditional Graph Traversal
Graph traversal **hanya aktif** untuk intent:
- `analytical` — "Apa hubungan TNA dan DNA?"
- `comparison` — "Bandingkan Leadership dan Performance Review"
- `comprehensive` — "Learning path menjadi HRBP"
- `ambiguous` — Query tidak jelas

Query `factual`, `greeting`, `action_request` → **skip graph** (0ms overhead).

### Draft-then-Review Mechanism
1. Entity extraction → simpan di PostgreSQL (`graph_drafts`)
2. Review via API: `GET /api/graph/drafts`
3. Approve → commit ke Neo4j: `PUT /api/graph/drafts/{id}/approve`
4. Neo4j Browser: http://localhost:7474 (user: `neo4j`, password: `enterprisemind`)

### Alur Query Multi-Agent

```
User Query
    │
    ▼
Orchestrator ──→ Intent Classification (Tiered: Regex → Keyword → LLM)
    │              (factual / analytical / comparison / comprehensive / action_request / greeting / ambiguous)
    ▼
Retriever ──→ Query Expansion (Dictionary-based atau LLM untuk comprehensive/ambiguous)
    │
    ├──→ Hybrid Search (Milvus Vector 70% + Sastrawi Keyword 30%)
    │     └─ Top-k adaptive berdasarkan intent (10-20 chunks)
    │
    ├──→ Graph Traversal (HANYA jika intent = analytical/comparison/comprehensive/ambiguous)
    │     └─ Neo4j: Extract entities → multi-hop path (max depth 3)
    │
    └──→ Context Fusion (vector docs + graph paths)
          │
          ▼
    Reranker ──→ Cross-Encoder (BGE-reranker-v2-m3)
          │       └─ Top-10 chunks
          ▼
    Parent Resolution ──→ Resolve parent chunks (2000 chars) dari child (500 chars)
          │
          ▼
Verifier ──→ Confidence Scoring + Fact Check (LLM 70B)
    │            ├─ Score ≥ 0.6 → Summarizer
    │            └─ Score < 0.6 → Reflection (max 1x, reformulasi query)
    │                              └→ Retriever (ulang)
    ▼
Summarizer ──→ Jawaban Akhir + Sitasi + Graph Context (LLM 70B)
    │              └─ Jika intent=action_request → Executor
    ▼
Executor ──→ Action Items (draft email / to-do list, LLM 8B)
    │              └─ Requires Human Review ✓
    ▼
Response ke User (final_answer, citations, graph_context, confidence_score, latency_ms, action_items)
```
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
| Arsitektur | Single-pass retrieve→generate | Multi-agent state graph + Knowledge Graph |
| Verifikasi Fakta | Tidak ada | Verifier Agent + Confidence Score |
| Self-Correction | Tidak ada | Reflection loop (max 1x, optimized) |
| Action Generation | Tidak ada | Executor Agent |
| Retrieval | Vector only | Hybrid (vector + keyword) + Graph traversal |
| Multi-hop Reasoning | Tidak ada | Neo4j graph dengan prerequisite chains |
| Observability | Tidak ada | LangFuse per-agent tracing |
| Keamanan | Tidak ada | Prompt injection detection + tool scoping |

## Tech Stack

| Layer | Teknologi | Versi |
|---|---|---|
| **LLM Provider** | Groq Cloud API | `llama-3.1-8b-instant` + `llama-3.3-70b-versatile` |
| **Orchestration** | LangGraph + LangChain | 0.2.61 + 0.3.13 |
| **Vector DB** | Milvus (standalone, Docker) | 2.5.6 |
| **Knowledge Graph** | Neo4j Community (Docker) | 5-community |
| **Metadata DB** | PostgreSQL (local) | 16.x |
| **Object Storage** | MinIO (Docker) | Latest |
| **Workflow Engine** | Temporal (Docker) | Latest |
| **Document Parser** | Docling + PyMuPDF4LLM + RapidOCR | Latest |
| **Backend** | FastAPI + Python | 0.115.0 + 3.11 |
| **Frontend** | Next.js + React + Tailwind | 16.1 + 19 + 4.0 |
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
# Edit .env: tambahkan GROQ_API_KEY, DATABASE_URL, dll.

# Start Docker services (Milvus, Neo4j, Temporal, MinIO, Docling)
docker compose up -d

# Verify Neo4j
docker compose exec neo4j cypher-shell -u neo4j -p enterprisemind "RETURN 1"

# Run database migrations
.venv\Scripts\python -c "
import asyncio, asyncpg
async def migrate():
    conn = await asyncpg.connect('postgresql://postgres:Password@localhost:5432/enterprisemind')
    with open('app/db/schema.sql', 'r') as f:
        await conn.execute(f.read())
    await conn.close()
asyncio.run(migrate())
"

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
- **Neo4j Browser**: http://localhost:7474 (neo4j / enterprisemind)
- **Temporal UI**: http://localhost:8233
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin)

### Neo4j Knowledge Graph

#### Review & Approve Drafts
```bash
# List pending drafts
curl http://localhost:8000/api/graph/drafts

# Approve draft
curl -X PUT http://localhost:8000/api/graph/drafts/{draft_id}/approve

# View graph via Neo4j Browser (http://localhost:7474)
MATCH (e:Entity)-[r]->(t) RETURN e, r, t LIMIT 50
```

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
| **Parent Embedding Skip** | Ingestion -30% waktu (parent chunks tidak di-embed) | `embedder.py:89` |
| **Sastrawi LRU Cache** | Query -50% untuk dokumen yang sering di-retrieve | `hybrid_search.py:63` |
| **Exponential Backoff Turun** | Rate limit recovery 2× lebih cepat (2s→1s base) | `llm_provider.py:101` |
| **Reflection Loop 2→1** | Worst case query -30 detik | `config.py:50` |
| **Conditional Graph Traversal** | Graph skip untuk 60% query (factual/greeting/action) | `retriever.py:168` |
| **Batch Embedding** | BGE-M3 default batch_size=32 (bukan 1-by-1) | `embedder.py` |

Detail lengkap: **[OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md)**

## Knowledge Graph Details

Lihat **[GRAPH_PLAN.md](GRAPH_PLAN.md)** untuk:
- Arsitektur lengkap Neo4j integration
- Entity & Relationship model (7 entity types, 5 relationship types)
- Draft-then-Review mechanism
- Conditional traversal logic
- Resource impact & trade-offs

## Struktur Repositori

```text
EnterpriseMind_AI/
├── backend/
│   ├── app/
│   │   ├── agents/        # Orchestrator, Retriever, Verifier, Summarizer, Executor
│   │   ├── api/           # FastAPI routes (/query, /upload, /graph, /documents, /metrics)
│   │   ├── core/          # config.py, llm_provider.py, neo4j_client.py, postgres_client.py
│   │   ├── db/            # CRUD functions (documents, messages, queries, graph drafts)
│   │   ├── evaluation/    # RAGAS runner + test set (50+ Q&A)
│   │   ├── graph/         # LangGraph state + build_graph
│   │   ├── ingestion/     # extractor, chunker, embedder, graph_extractor, pipeline
│   │   ├── retrieval/     # hybrid_search, reranker, parent_resolver, graph_traversal
│   │   ├── temporal/      # Temporal workflows + activities + worker
│   │   ├── memory/        # conversation_memory
│   │   └── tools/         # web_search, calculator, metadata_query
│   ├── scripts/           # run_evaluation, build_naive_rag, load_test
│   ├── tests/             # Unit tests
│   ├── Dockerfile
│   └── docker-compose.yml # 8 services: Milvus, Neo4j, Temporal, MinIO, Docling, etcd, PostgreSQL
├── frontend/
│   ├── app/               # (chat), admin, admin/metrics
│   ├── components/        # ChatWindow, MessageBubble, CitationCard, ProcessRail, DocumentUploader
│   ├── context/           # ActiveAgentContext
│   ├── hooks/             # useChatStream
│   └── lib/               # api.ts, utils.ts
├── docs/                  # 13 dokumen HR training (PDF/PPTX)
├── ARCHITECTURE.md        # Arsitektur detail + constraints
├── GRAPH_PLAN.md          # **BARU**: Neo4j Knowledge Graph implementation plan
├── OPTIMIZATION_PLAN.md   # **BARU**: Performance optimizations detail
├── AI_RULES.md            # Aturan untuk AI coding agent
├── CODING_STANDARDS.md    # Konvensi kode
├── DECISION_LOG.md        # ADR (15+ keputusan teknis)
├── DEFINITION_OF_DONE.md  # Checklist selesai task
├── DEPLOYMENT.md          # Panduan deploy production
├── PROMPT_LIBRARY.md      # System prompt tiap agent
├── SECURITY.md            # Keamanan agentic RAG
├── CHANGELOG.md           # Version history
└── EnterpriseMind_AI_SRS_PRD.md  # Full requirements specification
```

## Dokumentasi Lengkap

| File | Deskripsi |
|---|---|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Arsitektur sistem, constraints, trade-offs |
| **[GRAPH_PLAN.md](GRAPH_PLAN.md)** | Neo4j integration: entity model, draft-review, conditional traversal |
| **[OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md)** | 4 optimasi performa dengan analisis mendalam |
| **[CODING_STANDARDS.md](CODING_STANDARDS.md)** | Konvensi kode Python & TypeScript |
| **[DECISION_LOG.md](DECISION_LOG.md)** | Architecture Decision Records (ADR) |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Panduan deploy VPS + Vercel |
| **[SECURITY.md](SECURITY.md)** | Keamanan: prompt injection, RBAC, rate limiting |
| **[PROMPT_LIBRARY.md](PROMPT_LIBRARY.md)** | System prompts untuk 5 agents |
| **[EnterpriseMind_AI_SRS_PRD.md](EnterpriseMind_AI_SRS_PRD.md)** | Requirements lengkap |

## Kontributor

Developed by **Arifi** — Full-stack AI Engineer

## Lisensi

Proyek portfolio pribadi. Tidak untuk produksi komersial tanpa izin.
