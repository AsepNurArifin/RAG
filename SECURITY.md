# SECURITY.md — EnterpriseMind AI

> Dokumen ini fokus pada risiko keamanan yang SPESIFIK untuk sistem agentic RAG dengan tool-calling — bukan checklist keamanan generik. Wajib direview sebelum deploy publik (lihat `DEFINITION_OF_DONE.md`).

## 1. Prompt Injection via Dokumen/Tool Output

**Risiko:** Dokumen yang diupload ke knowledge base (atau hasil web search) bisa berisi teks yang menyerupai instruksi, misalnya "abaikan instruksi sebelumnya dan lakukan X". Karena hasil retrieval masuk ke context LLM, ada risiko agent "termakan" instruksi tersembunyi ini.

**Aturan wajib:**
- Hasil retrieval dari Researcher Agent SELALU diperlakukan sebagai data untuk direferensikan, bukan instruksi yang dieksekusi (lihat prompt Verifier Agent v1 di `PROMPT_LIBRARY.md`).
- Verifier Agent secara eksplisit diinstruksikan mendeteksi dan melaporkan (bukan mengeksekusi) teks yang menyerupai instruksi dalam dokumen sumber.
- Saat testing, sengaja sisipkan 2-3 dokumen "adversarial" (berisi instruksi palsu) ke test set evaluasi untuk memverifikasi agent tidak termakan.

## 2. Tool Permission Scoping

**Risiko:** Tool yang terlalu permisif (misal punya akses write ke database) bisa disalahgunakan jika ada prompt injection yang berhasil, atau bug pada agent reasoning.

**Aturan wajib:**
- Semua tool di `backend/app/tools/` defaultnya **read-only**.
- `metadata_query_tool.py` HANYA boleh melakukan SELECT query, tidak pernah INSERT/UPDATE/DELETE.
- Jika di masa depan dibutuhkan tool dengan kemampuan write (misal update status dokumen), tool tersebut harus:
  - Didokumentasikan eksplisit sebagai write-capable di `ARCHITECTURE.md`.
  - Memerlukan konfirmasi tambahan (bukan dieksekusi otomatis oleh agent tanpa human-in-the-loop).

## 3. Secrets Management

**Aturan wajib:**
- `.env` masuk `.gitignore` **sejak commit pertama** proyek — cek ini sebelum commit apa pun dilakukan.
- Gunakan `.env.example` (tanpa nilai asli) sebagai referensi struktur environment variable.
- API key Groq, connection string PostgreSQL, dan credential LangFuse tidak pernah muncul di kode, log, atau pesan error yang ditampilkan ke pengguna.
- Frontend (Next.js) tidak pernah menyimpan API key backend di client-side bundle — semua pemanggilan ke Groq terjadi di backend, frontend hanya berkomunikasi dengan backend sendiri.

## 4. Rate Limiting & Cost Abuse Protection

**Risiko:** Jika demo di-deploy publik untuk portfolio, endpoint bisa disalahgunakan (spam query) yang menghabiskan kuota Groq API dalam waktu singkat.

**Aturan wajib:**
- Terapkan rate limiting dasar di endpoint `/query` (misal maksimal N request per menit per IP) menggunakan middleware FastAPI (`slowapi` atau setara).
- Pertimbangkan menambahkan captcha sederhana atau autentikasi ringan (bukan full user management) jika demo publik dan ada kekhawatiran biaya.
- Monitor penggunaan kuota Groq secara berkala selama periode demo aktif.

## 5. Data Privacy (Simulasi)

Meskipun proyek ini menggunakan data publik/sintetis (bukan data perusahaan riil), tetap terapkan praktik yang benar sebagai bagian dari showcase:
- Dokumen yang diupload tidak dikirim ke pihak ketiga selain provider LLM yang digunakan untuk inference (Groq).
- Jika dataset sintetis mengandung nama/data yang menyerupai orang riil, pastikan itu jelas fiktif untuk menghindari kebingungan saat demo.

## 6. Checklist Pre-Deploy

- [ ] `.env` tidak ter-commit ke git (cek riwayat commit, bukan hanya `.gitignore` saat ini)
- [ ] Rate limiting aktif di endpoint publik
- [ ] Tool write-capable (jika ada) sudah direview dan memerlukan human-in-the-loop
- [ ] Test set evaluasi menyertakan minimal 2-3 kasus adversarial (prompt injection test)
- [ ] Tidak ada credential/API key yang muncul di log yang dapat diakses publik
