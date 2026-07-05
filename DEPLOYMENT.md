# EnterpriseMind AI — Deployment Guide

## Prasyarat

- VPS dengan Docker & Docker Compose terinstall
- Akun Vercel (untuk frontend)
- Akun Supabase (managed database)
- Akun Groq API (LLM provider)
- Akun LangFuse Cloud (observability)

---

## 1. Deploy Backend ke VPS (Docker Compose)

### 1.1 Clone repo di VPS
```bash
git clone https://github.com/username/enterprisemind-ai.git
cd enterprisemind-ai/backend
```

### 1.2 Konfigurasi environment
```bash
cp .env.example .env
nano .env
```

Isi `.env`:
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=xxxxxxxxxxxx
SUPABASE_SERVICE_ROLE_KEY=xxxxxxxxxxxx
CHROMA_PERSIST_DIRECTORY=/app/chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxx
LANGFUSE_HOST=https://us.cloud.langfuse.com
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=https://enterprisemind-ai.vercel.app
RATE_LIMIT_PER_MINUTE=30
```

### 1.3 Jalankan Docker Compose
```bash
docker compose up -d --build
```

### 1.4 Verifikasi
```bash
curl http://localhost:8000/health
# Harus return: {"status":"healthy","app":"EnterpriseMind AI"...}
```

### 1.5 Setup Nginx Reverse Proxy (opsional, untuk HTTPS)
```nginx
server {
    listen 80;
    server_name api-enterprisemind.domain-anda.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 2. Deploy Frontend ke Vercel

### 2.1 Install Vercel CLI
```bash
npm i -g vercel
```

### 2.2 Deploy
```bash
cd frontend
vercel
```

### 2.3 Set Environment Variables di Vercel Dashboard
```
NEXT_PUBLIC_API_URL = https://api-enterprisemind.domain-anda.com
NEXT_PUBLIC_APP_NAME = EnterpriseMind AI
```

### 2.4 Redeploy setelah set env
```bash
vercel --prod
```

---

## 3. Supabase Setup

### 3.1 Buat project di supabase.com

### 3.2 Jalankan SQL berikut di Supabase SQL Editor:

```sql
-- Tabel metadata dokumen
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    category TEXT DEFAULT 'uncategorized',
    status TEXT DEFAULT 'pending',
    chunk_count INT DEFAULT 0,
    file_size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel log query
CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    intent TEXT,
    agents_activated TEXT[],
    latency_ms INT,
    confidence_score FLOAT,
    reflection_count INT DEFAULT 0,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel conversation messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index untuk performa
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
```

---

## 4. Post-Deploy Checklist

- [ ] Health check backend OK (`/health` returns 200)
- [ ] Frontend Vercel dapat diakses via URL publik
- [ ] Chat interface bisa mengirim query dan menerima respons
- [ ] Process Rail menampilkan indikator agent saat memproses
- [ ] Citation muncul di jawaban
- [ ] Document upload via Admin page berfungsi
- [ ] LangFuse dashboard menampilkan traces
- [ ] Rate limiting aktif (test >30 request per menit)
- [ ] CORS berfungsi (frontend Vercel bisa akses backend VPS)

---

## 5. Maintenance

### Update model Groq (jika deprecation)
Edit `backend/app/core/config.py` line 30 & 33:
```python
REASONING_MODEL: str = "model-baru-anda"
FAST_MODEL: str = "model-baru-anda"
```
Lalu rebuild:
```bash
docker compose up -d --build
```

### Monitoring logs
```bash
docker compose logs -f backend
```
