# EnterpriseMind AI

**Intelligent Multi-Agent Knowledge Assistant** — Sistem Agentic RAG dengan arsitektur LangGraph multi-agent: Orchestrator, Researcher, Verifier, Summarizer, Executor. Dilengkapi fact verification, reflection loop, hybrid retrieval, dan full observability.

## Fitur Utama

| Fitur | Deskripsi |
|---|---|
| **Multi-Agent Orchestration** | 5 agent dikendalikan LangGraph state machine dengan conditional routing |
| **Hybrid Retrieval** | Vector similarity (70%) + keyword matching (30%) via Chroma |
| **Fact Verification** | Verifier Agent + Confidence Scoring + Reflection Loop (max 2 iterasi) |
| **Citation & Source Tracing** | Setiap klaim disertai sitasi ke dokumen sumber yang dapat ditelusuri |
| **Action Generation** | Executor Agent menghasilkan draft action items dari query |
| **Enterprise UI** | Next.js + Tailwind v4 + Process Rail + Confidence Indicator |
| **Observability** | LangFuse tracing per-agent, latency monitoring, token cost tracking |
| **RAGAS Evaluation** | Evaluasi otomatis: Faithfulness, Answer Relevance, Context Precision, Recall |
| **Security-Aware** | Prompt injection mitigation, tool read-only scoping, rate limiting |

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
                       │ REST API
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   VPS — Docker Compose                    │
│  ┌──────────────────┐  ┌─────────────────┐               │
│  │  FastAPI Backend  │  │  Chroma Vector DB│              │
│  │  ┌─────────────┐  │  │   (port 8001)    │              │
│  │  │ LangGraph    │  │  └─────────────────┘              │
│  │  │ ┌─────────┐ │  │                                    │
│  │  │ │Orchstrtr│ │  │                                    │
│  │  │ │  ↓      │ │  │                                    │
│  │  │ │Resrchr  │ │  │                                    │
│  │  │ │  ↓      │ │  │                                    │
│  │  │ │Verifier │ │  │                                    │
│  │  │ │  ↓      │ │  │                                    │
│  │  │ │Summrzr  │ │  │                                    │
│  │  │ │  ↓      │ │  │                                    │
│  │  │ │Executor │ │  │                                    │
│  │  │ └─────────┘ │  │                                    │
│  │  └─────────────┘  │                                    │
│  └────────┬─────────┘                                    │
└───────────┼──────────────────────────────────────────────┘
            │
   ┌────────┼────────┬────────────┐
   ▼        ▼        ▼            ▼
┌──────┐ ┌────┐ ┌──────────┐ ┌──────────┐
│Supabase│ │Groq│ │LangFuse  │ │ LangChain │
│(PG+Auth)│ │API │ │ Cloud    │ │ Framework │
└──────┘ └────┘ └──────────┘ └──────────┘
```

### Alur Query Multi-Agent

```
User Query
    │
    ▼
Orchestrator ──→ Intent Classification
    │              (informational / analytical / action_request / out_of_scope)
    ▼
Researcher ──→ Hybrid Search (Vector + Keyword)
    │              └→ Chroma Vector DB
    ▼
Verifier ──→ Confidence Scoring + Fact Check
    │            ├─ Score ≥ 0.6 → Summarizer
    │            └─ Score < 0.6 → Reflection (reformulasi query)
    │                              └→ Researcher (ulang, max 2x)
    ▼
Summarizer ──→ Jawaban Akhir + Sitasi Sumber
    │              └─ Jika intent=action_request → Executor
    ▼
Executor ──→ Action Items (draft email / to-do list)
    │              └─ Requires Human Review ✓
    ▼
Response ke User (confidence score, citations, latency, action items)
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
| Self-Correction | Tidak ada | Reflection loop (max 2x) |
| Action Generation | Tidak ada | Executor Agent |
| Retrieval | Vector only | Hybrid (vector + keyword) |
| Observability | Tidak ada | LangFuse per-agent tracing |
| Keamanan | Tidak ada | Prompt injection detection + tool scoping |

## Tech Stack

| Layer | Teknologi |
|---|---|
| LLM Provider | Groq Cloud API (`gpt-oss-120b` + `gpt-oss-20b`) |
| Orchestration | LangGraph + LangChain |
| Vector DB | Chroma (VPS, Docker) |
| Metadata DB | Supabase (PostgreSQL managed) |
| Backend | FastAPI (Python 3.11) |
| Frontend | Next.js 15 + React 19 + Tailwind v4 |
| Observability | LangFuse Cloud |
| Evaluation | RAGAS (4 metrik) |
| Deployment | Docker Compose (VPS) + Vercel (Frontend) |

## Cara Menjalankan

### Development

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env    # Isi dengan credential Anda
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Evaluasi RAGAS
```bash
cd backend
python -m scripts.run_evaluation
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

Ringkasan:
```bash
# VPS — Backend + Chroma
cd backend
docker compose up -d --build

# Vercel — Frontend
cd frontend
vercel --prod
```

## Struktur Repositori

```text
Mind/
├── backend/
│   ├── app/
│   │   ├── agents/        # Orch., Researcher, Verifier, Summarizer, Executor
│   │   ├── api/           # FastAPI routes (/query, /upload, /documents, /metrics)
│   │   ├── core/          # config.py, llm_provider.py, observability.py
│   │   ├── db/            # Supabase client
│   │   ├── evaluation/    # RAGAS runner + test set (50+ Q&A)
│   │   ├── graph/         # LangGraph state + build_graph
│   │   ├── ingestion/     # extractor, chunker, embedder, pipeline
│   │   ├── memory/        # conversation_memory
│   │   ├── retrieval/     # hybrid_search, vector_store
│   │   └── tools/         # web_search, calculator, metadata_query
│   ├── scripts/           # run_evaluation, build_naive_rag, load_test
│   ├── tests/             # Unit tests
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   ├── app/               # (chat), admin, admin/metrics
│   ├── components/        # ChatWindow, MessageBubble, CitationCard, ProcessRail
│   ├── context/           # ActiveAgentContext
│   ├── hooks/             # useChatStream
│   └── lib/               # api.ts, utils.ts
├── ARCHITECTURE.md         # Arsitektur detail + constraints
├── AI_RULES.md             # Aturan untuk AI coding agent
├── CODING_STANDARDS.md     # Konvensi kode
├── DECISION_LOG.md         # ADR (10+ keputusan teknis)
├── DEFINITION_OF_DONE.md   # Checklist selesai task
├── DEPLOYMENT.md           # Panduan deploy production
├── PROMPT_LIBRARY.md       # System prompt tiap agent
├── SECURITY.md             # Keamanan agentic RAG
├── SRS_PRD.md              # Full requirements specification
└── TASK_BACKLOG.md         # Task breakdown
```

## Lisensi

Proyek portfolio pribadi. Tidak untuk produksi komersial.
