# ARCHITECTURE.md — EnterpriseMind AI

> Dokumen ini adalah sumber kebenaran untuk struktur sistem dan batasan teknis.
> Untuk detail requirement lengkap, lihat `SRS_PRD.md`. Dokumen ini fokus ke "bagaimana sistem disusun", bukan "apa yang harus dilakukan sistem".

## 1. Diagram Alur Sistem

```
INGESTION FLOW:
Dokumen (PDF/DOCX/TXT) → Extractor (unstructured) → Chunker (semantic) → Embedder → Vector Store (Chroma, di VPS)
                                                                               ↓
                                                                      Metadata → Supabase (PostgreSQL managed)

QUERY FLOW:
User Query → Orchestrator Agent (routing/intent)
                 ├──→ Researcher Agent → Hybrid Retrieval (vector + keyword) → Vector Store (Chroma)
                 ├──→ Verifier Agent → Confidence Scoring → [jika rendah] Reflection Loop (maks. 2x)
                 ├──→ Summarizer Agent → Jawaban akhir + sitasi
                 └──→ Executor Agent → Action item (kondisional, hanya jika intent = aksi)
                 ↓
         Setiap agent call di-trace oleh LangFuse
                 ↓
         Response → Frontend (Next.js, di Vercel) dengan sitasi & confidence indicator

INFRASTRUKTUR:
┌─────────────────────────────────────────────┐
│              VPS                             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ FastAPI   │  │ Chroma   │  │ LangFuse  │  │
│  │ (Backend) │  │(Vector DB)│  │(Tracing)  │  │
│  └──────────┘  └──────────┘  └───────────┘  │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌─────────┐ ┌───────┐ ┌────────┐
   │Supabase │ │ Groq  │ │Vercel  │
   │(Postgres│ │ API   │ │(Next.js│
   │+ Auth   │ │(LLM)  │ │ Front) │
   │+ Storage)│ └───────┘ └────────┘
   └─────────┘
```

*(Diagram visual lengkap: lihat link Excalidraw di `SRS_PRD.md` bagian awal)*

## 2. Struktur Folder

```
enterprisemind-ai/
├── backend/
│   ├── app/
│   │   ├── agents/          # logika tiap agent (prompt + output parsing)
│   │   ├── graph/           # perakitan LangGraph (state, node, edge)
│   │   ├── tools/           # tool calling (web search, calculator, metadata query)
│   │   ├── ingestion/       # extractor, chunker, embedder
│   │   ├── retrieval/       # vector store wrapper, hybrid search
│   │   ├── memory/          # conversation memory
│   │   ├── evaluation/      # RAGAS runner + test sets
│   │   ├── api/             # FastAPI routes
│   │   ├── core/            # config.py & llm_provider.py — SATU-SATUNYA tempat nama model didefinisikan
│   │   │                    # + supabase_client.py & observability.py
│   │   ├── db/              # Supabase table definitions & helpers (bukan SQLAlchemy)
│   │   └── main.py
│   ├── tests/
│   └── scripts/
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router (chat page, dashboard page)
│       ├── components/
│       ├── lib/             # API client
│       └── hooks/
└── docs/                    # dokumen ini + SRS_PRD, AI_RULES, dsb.
```

## 3. Prinsip Desain yang Wajib Dijaga

1. **Single Source of Truth untuk Model** — nama model Groq (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`) HANYA boleh didefinisikan di `backend/app/core/config.py`. Tidak ada agent yang boleh hardcode nama model langsung. Alasan: histori Groq mendeprecate model dengan frekuensi tinggi (4 gelombang dalam 12 bulan terakhir per catatan riset proyek ini).
2. **Retrieval Result ≠ Instruksi** — hasil retrieval dari dokumen SELALU diperlakukan sebagai data mentah untuk direferensikan, bukan sebagai instruksi yang harus dieksekusi oleh agent (lihat `SECURITY.md` untuk detail prompt injection).
3. **Agent Terpisah dari Graph** — logika masing-masing agent (`agents/`) tidak boleh mengandung logic routing antar-agent; routing hanya hidup di `graph/build_graph.py`.
4. **Tool Read-Only by Default** — semua tool di `tools/` defaultnya read-only terhadap database/eksternal, kecuali eksplisit didesain dan didokumentasikan sebagai write-capable.

## 4. Batasan Teknis (Constraints)

| Kategori | Batasan |
|---|---|
| Biaya | Development harian sedapat mungkin menggunakan `openai/gpt-oss-20b`; `gpt-oss-120b` dipakai selektif (Verifier, Summarizer final) untuk kontrol biaya |
| Latensi | Query sederhana ≤ 4 detik, query kompleks ≤ 12 detik (lihat NFR-P1/P2 di SRS) |
| Skalabilitas | Diuji hingga 20-30 concurrent session via simulasi (Locust), bukan infrastruktur produksi riil |
| Ketergantungan eksternal | Groq API sebagai dependency kritis — arsitektur harus tetap mudah pindah provider (lihat prinsip #1 di atas) |
| Reflection loop | Maksimal 2 iterasi, dengan timeout keras untuk mencegah pelanggaran NFR-P2 |
| Database | Hybrid: Supabase (PostgreSQL managed) untuk metadata terstruktur + Chroma (di VPS) untuk vector embedding — tidak digabung ke satu database |
| Deployment | Backend + Chroma + LangFuse di VPS; Frontend Next.js di Vercel; Supabase sebagai managed service eksternal |

## 5. Dependency Antar Modul

- `ingestion/` tidak boleh bergantung pada `agents/` (searah, bukan circular).
- `graph/` bergantung pada `agents/` dan `tools/`, bukan sebaliknya.
- `api/` adalah satu-satunya entrypoint yang boleh memanggil `graph/`.
- `evaluation/` berjalan independen, bisa dipanggil via script (`scripts/run_evaluation.py`) tanpa harus lewat API.
