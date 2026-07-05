# SECURITY CHECKLIST — Pre-Deploy Review

> Checklist dari SECURITY.md baris 48-54.
> Centang setiap item sebelum deploy publik.

## Hasil Review — Juli 2026

### 1. .env tidak ter-commit ke git
- [x] Root `.gitignore` sudah dibuat dengan `**/.env`, `.env.*`, `!.env.example`
- [x] `backend/.gitignore` sudah ada dan meng-ignore `.env`
- [x] `frontend/.gitignore` sudah meng-ignore `.env*`
- [x] Semua credential di `.env` asli — **WAJIB di-rotate sebelum deploy publik**

### 2. Rate limiting aktif di endpoint publik
- [x] SlowAPI rate limiter terkonfigurasi di `main.py`
- [x] Default: 30 request/menit per IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- [x] Endpoint `/api/query` sudah dibungkus `@limiter.limit()`
- [x] Rate limit exceeded handler sudah terdaftar

### 3. Tool write-capable (jika ada) sudah direview
- [x] Semua tool di `tools/` bersifat **read-only**
- [x] `metadata_query_tool.py` hanya SELECT
- [x] `web_search_tool.py` hanya fetch eksternal (read)
- [x] `calculator_tool.py` pure computation (no side effect)
- [x] Tidak ada tool write-capable saat ini

### 4. Test set evaluasi menyertakan kasus adversarial
- [x] `test_set.py` berisi 5 pertanyaan adversarial:
  - Prompt injection ("abaikan instruksi sebelumnya")
  - System override impersonation
  - Role manipulation
  - XSS injection (`<script>` tags)
  - Instruction injection (hapus database, kirim email)
- [x] Verifier Agent prompt mencakup deteksi instruksi adversarial

### 5. Tidak ada credential/API key yang muncul di log
- [x] Global exception handler menyembunyikan detail di production
- [x] Log hanya mencatat query content, intent, latency — bukan credentials
- [x] Environment variables hanya diakses via `config.py`, tidak di-print

---

## Tindakan Wajib Sebelum Deploy Publik

1. **ROTATE API KEYS** — Regenerate semua key di:
   - Groq Console → API Keys
   - Supabase Dashboard → Project Settings → API
   - LangFuse → Project Settings → API Keys
   
   Update `.env` di VPS dengan key baru.

2. Pastikan `.env` TIDAK PERNAH masuk git commit:
   ```bash
   git status  # pastikan .env tidak ada di staged/tracked files
   ```

3. Set `APP_ENV=production` di `.env` VPS

4. Update `CORS_ORIGINS` di `.env` VPS dengan domain Vercel produksi

5. Pertimbangkan menambahkan autentikasi dasar untuk endpoint `/api/upload`
   dan `/api/admin` jika admin dashboard diakses publik

6. Monitor kuota Groq API secara berkala selama periode demo aktif
