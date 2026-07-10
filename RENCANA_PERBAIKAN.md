# RENCANA PERBAIKAN — EnterpriseMind AI

> **Tanggal Audit**: 06 Juli 2026
> **Total Issue Terbuka**: 54 (8 Critical, 14 High, 21 Medium, 11 Low)
> **Dari Total Sebelumnya**: 95 issue diidentifikasi, 16 sudah diperbaiki

---

## FASE 0 — EMERGENCY (Perbaiki SEKARANG — Blokir Fungsionalitas / Keamanan)

### ⚡ #1: Upload, Documents, Metrics — Tambah Authentication

**Issue**: `/api/upload`, `/api/documents`, `/api/metrics` tidak ada `Depends(get_current_user)` sama sekali. Siapa pun bisa upload file, lihat dokumen, hapus dokumen, dan lihat metrics system-wide.

**File**:
| File | Perubahan |
|------|-----------|
| `backend/app/api/upload.py` | Tambah `user: dict = Depends(get_current_user)` di `upload_document()` |
| `backend/app/api/documents.py` | Tambah `user: dict = Depends(get_current_user)` di `list_documents()` dan `remove_document()` |
| `backend/app/api/metrics.py` | Tambah `admin: dict = Depends(require_admin)` di `get_dashboard_metrics()` |

**Verifikasi**: `curl -X POST http://localhost:8000/api/upload` harus return `401 Unauthorized`

---

### ⚡ #2: JWT Secret Hardcoded — Ganti ke Required Env

**Issue**: `config.py` baris 141-145 masih punya fallback `"enterprisemind-dev-secret-change-in-production"`. Jika env var tidak ada, siapapun bisa forge JWT.

**File**: `backend/app/core/config.py`

**Perubahan**:
```python
# SEBELUM:
JWT_SECRET_KEY: str = field(
    default_factory=lambda: os.getenv(
        "JWT_SECRET_KEY", "enterprisemind-dev-secret-change-in-production"
    )
)

# SESUDAH:
JWT_SECRET_KEY: str = field(
    default_factory=lambda: os.getenv("JWT_SECRET_KEY", "")
)

def __post_init__(self):
    if self.APP_ENV != "development" and not self.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY wajib di-set di environment production!")
```

**File**: `backend/.env.example` — tambah:
```
JWT_SECRET_KEY=generate-dengan-openssl-rand-hex-32
JWT_EXPIRE_MINUTES=480
```

**Verifikasi**: Jalankan tanpa `JWT_SECRET_KEY` → harus crash dengan error jelas

---

### ⚡ #3: Supabase Client — Gunakan Anon Key, Bukan Service Role

**Issue**: `get_supabase_client()` selalu pakai `SUPABASE_SERVICE_ROLE_KEY`, bypass semua RLS. Anon key cukup untuk operasi publik. Service role hanya untuk admin (create_admin.py).

**File**: `backend/app/core/supabase_client.py`

**Perubahan**:
```python
# Baris 48-55:
# SEBELUM:
if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
    ...
_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

# SESUDAH:
if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_URL dan SUPABASE_ANON_KEY wajib di-set")
_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
```

Buat fungsi baru `get_supabase_admin_client()` yang pakai service role key, dan hanya dipanggil di `create_admin.py`.

**Verifikasi**: Semua query normal harus jalan dengan anon key + RLS

---

### ⚡ #4: Schema SQL vs Python — Sinkronisasi

**Issue**: Tabel `conversations` di SQL tidak punya kolom `user_id` dan `title`, tapi Python code insert kedua kolom itu. `metadata_query_tool.py` query `upload_date` padahal kolom asli `created_at`.

**File**: `backend/supabase_migration.sql`

**Perubahan**: Tambah ke tabel `conversations`:
```sql
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS title TEXT;
```

**File**: `backend/app/tools/metadata_query_tool.py` baris 32:
```python
# SEBELUM:
query = client.table("documents").select("filename, category, upload_date")

# SESUDAH:
query = client.table("documents").select("filename, category, created_at")
```

**File**: `backend/app/db/__init__.py` — pastikan definisi SQL di docstring match dengan migration SQL

**Verifikasi**: Jalankan query insert → tidak boleh ada error kolom tidak ditemukan

---

### ⚡ #5: ChromaDB — Tutup Port atau Tambah Auth

**Issue**: `docker-compose.yml` expose port 8001 ke semua interface tanpa auth. Vector DB bisa dibaca/ditulis siapa pun.

**File**: `backend/docker-compose.yml`

**Opsi A (Rekomendasi)**: Tutup port:
```yaml
# SEBELUM:
chroma:
  ports:
    - "8001:8000"

# SESUDAH:
chroma:
  # Tidak ada ports expose — hanya internal network
```

**Opsi B (Jika butuh akses eksternal)**: Tambah auth:
```yaml
chroma:
  environment:
    - CHROMA_SERVER_AUTHN_CREDENTIALS=admin:${CHROMA_ADMIN_PASSWORD}
    - CHROMA_SERVER_AUTHN_PROVIDER=chromadb.auth.token_authn.TokenAuthClientProvider
```

**Verifikasi**: `curl http://localhost:8001/api/v1/heartbeat` harus connection refused

---

### ⚡ #6: Verifier — Feed Draft Answer untuk Verifikasi

**Issue**: Verifier diminta verifikasi konsistensi antara "draft jawaban dengan dokumen sumber", tapi Summarizer (yang bikin draft answer) berjalan SETELAH Verifier. Confidence score purely hallucinated.

**File**: `backend/app/graph/build_graph.py`

**Perubahan**: Ubah urutan graph:
```
SEBELUM:  orchestrator → researcher → verifier → (summarizer | reflection)
SESUDAH:  orchestrator → researcher → summarizer(draft) → verifier → (final_summarizer | reflection)
```

Atau alternatif: jalankan summarizer dulu untuk bikin draft, lalu verifier periksa draft tersebut.

**File**: `backend/app/agents/verifier.py` baris 74-80:
```python
# Tambah draft_answer di human message:
human_message = human_template.format(
    query=query,
    documents=formatted_docs,
    draft_answer=draft_answer,  # ← TAMBAH INI
)
```

**Verifikasi**: Verifier harus menerima `draft_answer` dari state graph

---

### ⚡ #7: Researcher — Jadikan LLM Agent atau Hapus Prompt

**Issue**: `RESEARCHER_PROMPT` di `__init__.py` tidak pernah dipakai. Researcher hanyalah wrapper `hybrid_search()`. Ini bukan "agent" — hanya retrieval node.

**Opsi A (Rekomendasi)**: Tambah LLM call untuk filter/re-rank hasil retrieval:
```python
# researcher.py
from app.agents import RESEARCHER_PROMPT
from langchain_core.prompts import ChatPromptTemplate

chain = ChatPromptTemplate.from_messages([
    ("system", RESEARCHER_PROMPT),
    ("human", "{query}\n\nHasil pencarian:\n{search_results}")
]) | llm

response = chain.invoke({"query": query, "search_results": formatted_results})
filtered_docs = _parse_researcher_output(response.content, all_documents)
```

**Opsi B**: Hapus `RESEARCHER_PROMPT` dari `__init__.py` dan rename file jadi `retriever.py`

**Verifikasi**: Researcher harus memanggil LLM untuk filter/rerank

---

### ⚡ #8: Frontend — Fix CSP + Env URLs

**Issue**: CSP memblokir Google Fonts dan hardcode `localhost:8000` untuk production. `.env.example` dan `.env.production` missing `/api`.

**File**: `frontend/next.config.ts`:
```typescript
// Tambah ke CSP:
"font-src 'self' https://fonts.gstatic.com;"
"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"

// Ganti localhost hardcoded:
"connect-src 'self' https://*.domain-anda.com wss://*.domain-anda.com;"

// Hapus unsafe-inline jika memungkinkan: generate nonce untuk inline style
```

**File**: `frontend/.env.example`:
```
# SEBELUM:
NEXT_PUBLIC_API_URL=http://localhost:8000

# SESUDAH:
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

**File**: `frontend/.env.production`:
```
# SEBELUM:
NEXT_PUBLIC_API_URL=https://api-enterprisemind.domain-anda.com

# SESUDAH:
NEXT_PUBLIC_API_URL=https://api-enterprisemind.domain-anda.com/api
```

**Verifikasi**: Buka frontend di browser → Google Fonts harus render. Console tidak boleh ada CSP error.

---

## FASE 1 — HIGH PRIORITY (Minggu Ini)

### #9: Token Revocation via JTI Blacklist

**File**: `backend/app/core/auth.py`
- Tambah kolom `token_version` di tabel `users`
- Saat create JWT, embed `token_version` di payload
- Saat decode, bandingkan `token_version` dengan nilai di DB
- Untuk revoke, increment `token_version` di DB

```python
# Di decode_access_token, setelah verifikasi:
user = client.table("users").select("token_version").eq("id", user_id).execute()
if user.data[0]["token_version"] != payload.get("token_version"):
    raise HTTPException(status_code=401, detail="Token telah dicabut")
```

---

### #10: File Upload — Tambah Validasi & Batas Ukuran

**File**: `backend/app/api/upload.py`

```python
# Tambah di config.py:
MAX_UPLOAD_SIZE_MB: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_MB", "50")))

# Tambah di upload.py:
MAX_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="uncategorized"),
    user: dict = Depends(get_current_user),  # FIX dari Fase 0 #1
) -> dict:
    # Validasi content-type
    ALLOWED_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Tipe file tidak didukung")
    
    # Baca dengan batas ukuran
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f"Ukuran file maksimal {settings.MAX_UPLOAD_SIZE_MB}MB")
    
    # Sanitasi filename
    safe_filename = os.path.basename(file.filename or "unknown")
```

---

### #11: Tambah Timeout di Document Extraction

**File**: `backend/app/ingestion/pipeline.py`

```python
# Tambah di config.py:
EXTRACTION_TIMEOUT_SECONDS: int = field(default_factory=lambda: int(os.getenv("EXTRACTION_TIMEOUT_SECONDS", "120")))

# Di pipeline.py:
text = await asyncio.wait_for(
    asyncio.to_thread(extract_text, file_path, file_type),
    timeout=settings.EXTRACTION_TIMEOUT_SECONDS,
)
```

**File**: `backend/app/ingestion/extractor.py` — tambah `doc.close()` di finally block:
```python
def _extract_pdf(path: Path) -> str:
    doc = fitz.open(str(path))
    try:
        # ... extraction logic ...
    finally:
        doc.close()
```

---

### #12: Web Search Tool — Sanitasi Hasil

**File**: `backend/app/tools/web_search_tool.py`

```python
import re

def _sanitize_content(content: str, max_length: int = 1000) -> str:
    content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<[^>]+>", "", content)
    content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)
    return content[:max_length]

# Di fungsi search:
"content": _sanitize_content(res.get("content", "")),
"url": res.get("url", "") if res.get("url", "").startswith(("http://", "https://")) else "",
```

---

### #13: LLM Provider — Validasi API Key Kosong

**File**: `backend/app/core/llm_provider.py`

```python
def get_llm(mode: str = "fast", **kwargs) -> ChatGroq:
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_"):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY tidak boleh kosong")
    # ... rest of function
```

---

### #14: Observability — Perbaiki Handler Caching

**File**: `backend/app/core/observability.py`

```python
_handler: CallbackHandler | None = None

def get_langfuse_handler() -> CallbackHandler | None:
    global _handler
    if _handler is not None:
        return _handler
    try:
        from langfuse.callback import CallbackHandler
        _handler = CallbackHandler(...)
        return _handler
    except ImportError:
        logger.warning("Langfuse tidak tersedia")
        return None
```

---

### #15: Summarizer — Tambah Error Handling

**File**: `backend/app/agents/summarizer.py` baris 121-132

```python
# Wrap chain.invoke() dengan try/except seperti agent lain:
try:
    response = chain.invoke({...})
except Exception as e:
    logger.exception("Summarizer gagal")
    return {
        **state,
        "final_answer": "Maaf, terjadi kesalahan saat menyusun jawaban.",
        "error": str(e),
    }
```

---

### #16: Database — Tambah LIMIT di Semua Query

**File**: `backend/app/db/__init__.py` — `get_all_documents()`:
```python
.select("*").order("created_at", desc=True).limit(100).execute()
```

**File**: `backend/app/api/metrics.py` baris 33:
```python
client.table("query_logs").select("*").order("created_at", desc=True).limit(1000).execute()
```

**File**: `backend/app/tools/metadata_query_tool.py` baris 32:
```python
client.table("documents").select("filename, category, created_at").limit(50).execute()
```

**File**: `backend/app/api/users.py` baris 57 — tambah pagination:
```python
.limit(limit).range(offset, offset + limit - 1).execute()
```

---

### #17: Frontend — Tambah AbortController

**File**: `frontend/hooks/useChatStream.ts`

```typescript
useEffect(() => {
    const controller = new AbortController();
    // ... fetch logic dengan signal: controller.signal ...
    return () => controller.abort();
}, [dependencies]);
```

**File**: `frontend/lib/api.ts` — semua fungsi fetch tambah parameter signal:
```typescript
export async function query(body: QueryRequest, signal?: AbortSignal): Promise<QueryResponse> {
    const res = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
        credentials: "include",
    });
    // ...
}
```

---

## FASE 2 — MEDIUM PRIORITY (Minggu Depan)

### #18: Dependency Pinning

**File**: `backend/requirements.txt`

```txt
# Ganti >= dengan == untuk production:
langchain==0.3.13
langchain-groq==0.2.1
langchain-community==0.3.13
chromadb==0.5.20
supabase==2.7.4
langfuse==2.52.0
# ... dst
```

Tambah file `requirements-dev.txt`:
```txt
-r requirements.txt
pytest==8.3.3
pytest-asyncio==0.24.0
locust==2.31.8
ragas==0.2.6
pandas==2.2.3
datasets==3.0.1
```

---

### #19: Docker Multi-Stage Build

**File**: `backend/Dockerfile`

```dockerfile
# === STAGE 1: Builder ===
FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# === STAGE 2: Runtime ===
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 poppler-utils tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*
RUN useradd -m -r appuser
COPY --from=builder /root/.local /home/appuser/.local
WORKDIR /app
COPY --chown=appuser:appuser . .
ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### #20: Docker Compose — Pin Versi + Resource Limits

**File**: `backend/docker-compose.yml`

```yaml
services:
  chroma:
    image: chromadb/chroma:0.5.20  # Pin versi
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
    # Hapus ports jika tidak perlu akses eksternal

  backend:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Hapus**: `version: '3.8'` (baris 1) — deprecated

---

### #21: Model Embedding Pre-Download di Docker

**File**: `backend/Dockerfile`

```dockerfile
# Setelah COPY requirements.txt dan pip install, sebelum COPY . .:
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

Atau gunakan `HUGGINGFACE_HUB_CACHE` env var dengan volume persistent.

---

### #22: Summarizer — Tambah Conversation History

**File**: `backend/app/agents/summarizer.py` baris 43-49

```python
conversation_history = state.get("conversation_history", [])
# Format history ke dalam prompt:
history_text = _format_conversation_history(conversation_history)
# Pass ke human_template
```

**File**: `backend/app/api/query.py` — load history dari Supabase sebelum graph:
```python
prev_messages = client.table("messages").select("*").eq("conversation_id", conv_id).order("created_at").execute()
initial_state["conversation_history"] = prev_messages.data
```

---

### #23: Citation — Connect ke Answer Content

**File**: `backend/app/agents/summarizer.py` baris 163-200

Ganti citation generation dari "semua source_documents[:5]" jadi "hanya yang benar-benar dikutip LLM":

```python
def _parse_summarizer_response(response_text: str, source_documents: list[dict]) -> dict:
    # Ekstrak citation reference dari teks jawaban LLM
    # (misal: regex cari "[Sumber: ...]" di dalam answer)
    cited_sources = _extract_cited_sources(response_text, source_documents)
    return {
        "final_answer": answer,
        "citations": cited_sources,  # Hanya yang dikutip
    }
```

---

### #24: Frontend — Tipe API Responses

**File**: `frontend/types/index.ts`

```typescript
export interface Document {
  id: string;
  filename: string;
  category: string;
  file_size_bytes: number;
  status: string;
  created_at: string;
}

export interface Session {
  id: string;
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Metrics {
  total_queries: number;
  avg_latency_ms: number;
  avg_confidence_score: number;
  total_estimated_cost_usd: number;
  intent_distribution: Record<string, number>;
  recent_logs: QueryLog[];
}

export interface UserData {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}
```

**File**: `frontend/lib/api.ts` — ganti `any` dengan tipe konkrit.

---

### #25: Chunk Size ke Config

**File**: `backend/app/core/config.py`

```python
CHUNK_SIZE: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000")))
CHUNK_OVERLAP: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200")))
```

**File**: `backend/app/ingestion/pipeline.py` baris 99:
```python
chunks = await asyncio.to_thread(
    chunk_document, text, metadata,
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
)
```

---

### #26: DRY — Format Documents Bersama

**File**: `backend/app/agents/utils.py` (baru)

```python
def format_documents_for_prompt(documents: list[dict], max_chars: int = 500, include_date: bool = True) -> str:
    parts = []
    for i, doc in enumerate(documents, 1):
        content = doc.get("content", "")[:max_chars]
        source = doc.get("source", "unknown")
        if include_date:
            date = doc.get("date", "tidak diketahui")
            parts.append(f"[{i}] Sumber: {source} (tanggal: {date})\n{content}")
        else:
            parts.append(f"[{i}] Sumber: {source}\n{content}")
    return "\n\n".join(parts)
```

Hapus duplikasi di `verifier.py:136-148` dan `summarizer.py:150-160`.

---

### #27: ConversationMemory — Opsional Persistensi (Redis/Supabase)

**File**: `backend/app/memory/conversation_memory.py`

Tambah backend opsional:
```python
class ConversationMemory:
    def __init__(self, backend: str = "memory"):
        if backend == "supabase":
            self._backend = SupabaseMemoryBackend()
        elif backend == "redis":
            self._backend = RedisMemoryBackend()
        else:
            self._backend = InMemoryBackend()
```

---

### #28: Buat pytest.ini

**File**: `backend/pytest.ini`
```ini
[pytest]
pythonpath = .
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
markers =
    slow: tests that take a long time
    integration: tests that require external services
```

---

## FASE 3 — LOW PRIORITY (Sprint Berikutnya)

### #29: load_dotenv() Return Check
### #30: CORS_ORIGINS Strip Whitespace
### #31: CHROMA_PORT ke int
### #32: Config unsafe int() cast → validasi dengan try/except
### #33: QUERY_TIMEOUT_SECONDS → enforce di graph node
### #34: reflection_count default di TypedDict
### #35: bcrypt gensalt() explicit rounds
### #36: Logging Supabase URL → mask atau turunkan ke DEBUG
### #37: Calculator tambah batas depth & string length
### #38: Hybrid search → upgrade ke BM25 atau tambah stemming
### #39: Reflection loop wall-clock timeout
### #40: Hapus `fix_db.py` (dead code)
### #41: Hapus `supabase = get_supabase_client` (line 60, dead code)
### #42: Frontend CitationCard — tambah onClick, date, url field
### #43: Frontend DocumentUploader — progress bar dengan XMLHttpRequest
### #44: Frontend scrollbar-thin → ganti ke Tailwind v4 utility
### #45: Frontend duplicate API_BASE_URL → pindah ke lib/config.ts
### #46: Frontend Inactive ProcessRail icons → uniform colors
### #47: Hapus 40% CSS tokens yang tidak terpakai di globals.css
### #48: Tambah test: web_search, metadata_query, calculator operators
### #49: Tambah test: async tests dengan pytest-asyncio
### #50: Tambah test: integration test dengan FastAPI TestClient
### #51: Tambah pre-commit hooks (linting, secret scanning)
### #52: Tambah backup/restore docs
### #53: Tambah rollback strategy di DEPLOYMENT.md
### #54: Samakan DEPLOYMENT.md SQL dengan supabase_migration.sql

---

## CHECKLIST PENGERJAAN

| Fase | # Issue | Status |
|------|---------|--------|
| **FASE 0 — EMERGENCY** | 8 | ⬜ |
| &nbsp;&nbsp; #1 Auth tambah di upload/documents/metrics | | ⬜ |
| &nbsp;&nbsp; #2 JWT secret required env | | ⬜ |
| &nbsp;&nbsp; #3 Supabase anon key default | | ⬜ |
| &nbsp;&nbsp; #4 Schema sync | | ⬜ |
| &nbsp;&nbsp; #5 ChromaDB tutup port | | ⬜ |
| &nbsp;&nbsp; #6 Verifier draft answer | | ⬜ |
| &nbsp;&nbsp; #7 Researcher LLM agent | | ⬜ |
| &nbsp;&nbsp; #8 CSP + env URLs fix | | ⬜ |
| **FASE 1 — HIGH** | 9 | ⬜ |
| &nbsp;&nbsp; #9 Token revocation | | ⬜ |
| &nbsp;&nbsp; #10 Upload validation & size limit | | ⬜ |
| &nbsp;&nbsp; #11 Extraction timeout | | ⬜ |
| &nbsp;&nbsp; #12 Web search sanitization | | ⬜ |
| &nbsp;&nbsp; #13 API key empty validation | | ⬜ |
| &nbsp;&nbsp; #14 Observability handler caching | | ⬜ |
| &nbsp;&nbsp; #15 Summarizer error handling | | ⬜ |
| &nbsp;&nbsp; #16 Database limits + pagination | | ⬜ |
| &nbsp;&nbsp; #17 Frontend AbortController | | ⬜ |
| **FASE 2 — MEDIUM** | 11 | ⬜ |
| &nbsp;&nbsp; #18 Dependency pinning | | ⬜ |
| &nbsp;&nbsp; #19 Docker multi-stage | | ⬜ |
| &nbsp;&nbsp; #20 Docker compose limits + pin | | ⬜ |
| &nbsp;&nbsp; #21 Model pre-download | | ⬜ |
| &nbsp;&nbsp; #22 Summarizer conversation history | | ⬜ |
| &nbsp;&nbsp; #23 Citation connect to answer | | ⬜ |
| &nbsp;&nbsp; #24 API types | | ⬜ |
| &nbsp;&nbsp; #25 Chunk size config | | ⬜ |
| &nbsp;&nbsp; #26 DRY format_documents | | ⬜ |
| &nbsp;&nbsp; #27 ConversationMemory persistence | | ⬜ |
| &nbsp;&nbsp; #28 pytest.ini | | ⬜ |
| **FASE 3 — LOW** | 26 | ⬜ |

---

## VERIFIKASI AKHIR

Setelah semua fase selesai, jalankan:

```bash
# Backend
cd backend
pytest tests/ -v
python -m scripts.run_evaluation

# Frontend
cd frontend
npm run build
npm run lint

# Docker
docker compose build
docker compose up -d
curl http://localhost:8000/health
curl http://localhost:8000/api/metrics  # Harus return 401
```

---

> **Dibuat**: 06 Juli 2026 | **Total Issue**: 54 | **Target Selesai**: 2-3 sprint
