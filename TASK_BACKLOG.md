# TASK_BACKLOG.md — EnterpriseMind AI

> Breakdown task-level dari roadmap mingguan di `SRS_PRD.md` (Bagian B.5). Update status task di sini seiring progress. Setiap task selesai harus lolos `DEFINITION_OF_DONE.md`.

Status: `TODO` / `IN PROGRESS` / `DONE` / `BLOCKED`

## Minggu 1 — Data Preparation & Setup
- [ ] TODO — Setup repo (struktur folder sesuai `ARCHITECTURE.md`), `.gitignore`, `.env.example`
- [ ] TODO — Setup akun Groq API, cek model aktif terbaru di console.groq.com/docs/models
- [ ] TODO — Kumpulkan dataset dokumen (target 200-1000 dokumen, kombinasi publik + sintetis)
- [ ] TODO — Setup Supabase project (buat tabel metadata, setup Auth, setup Storage bucket)
- [ ] TODO — Eksplorasi `unstructured` untuk ekstraksi teks dari sample dokumen

## Minggu 2 — Ingestion Pipeline & Baseline
- [ ] TODO — Implementasi `ingestion/extractor.py`
- [ ] TODO — Implementasi `ingestion/chunker.py` (strategi semantic/hierarchical)
- [ ] TODO — Implementasi `ingestion/embedder.py` + setup Chroma vector store
- [ ] TODO — Bangun baseline Naive RAG (single retrieve-then-generate) sebagai pembanding
- [ ] TODO — Jalankan baseline Naive RAG terhadap beberapa sample query untuk sanity check

## Minggu 3 — Graph & Agent Dasar
- [ ] TODO — Definisikan `graph/state.py` (State schema untuk LangGraph)
- [ ] TODO — Implementasi Orchestrator Agent (routing/intent classification)
- [ ] TODO — Implementasi Researcher Agent (hybrid retrieval)
- [ ] TODO — Rakit graph dasar: Orchestrator → Researcher → output sementara (belum ada verifikasi)
- [ ] TODO — Tulis system prompt awal untuk kedua agent di `PROMPT_LIBRARY.md`

## Minggu 4 — Verifier & Summarizer
- [ ] TODO — Implementasi Verifier Agent + confidence scoring
- [ ] TODO — Implementasi reflection loop (maks. 2 iterasi, dengan timeout)
- [ ] TODO — Implementasi Summarizer Agent (jawaban akhir + sitasi)
- [ ] TODO — Unit test untuk Verifier & Summarizer

## Minggu 5 — Tools & Memory
- [ ] TODO — Implementasi `tools/web_search_tool.py`
- [ ] TODO — Implementasi `tools/calculator_tool.py`
- [ ] TODO — Implementasi `tools/metadata_query_tool.py` (read-only, sesuai `SECURITY.md`)
- [ ] TODO — Implementasi Executor Agent (action item generation)
- [ ] TODO — Implementasi `memory/conversation_memory.py` (short-term)

## Minggu 6 — Frontend (Next.js)
- [ ] TODO — Setup project Next.js + struktur folder sesuai `ARCHITECTURE.md`
- [ ] TODO — Implementasi `ChatWindow.tsx`, `MessageBubble.tsx`, streaming response
- [ ] TODO — Implementasi `CitationCard.tsx` untuk menampilkan sitasi sumber
- [ ] TODO — Integrasi `lib/api.ts` dengan endpoint `/query` backend

## Minggu 7 — Dashboard, Observability, Deploy
- [ ] TODO — Implementasi admin dashboard (`DocumentTable.tsx`, `MetricsPanel.tsx`)
- [ ] TODO — Setup LangFuse (self-hosted via Docker di VPS, atau cloud free tier)
- [ ] TODO — Buat ground truth Q&A test set (≥50 pasang, sesuai Evaluation Plan di `SRS_PRD.md`)
- [ ] TODO — Jalankan evaluasi RAGAS, bandingkan Naive RAG vs Agentic RAG
- [ ] TODO — Deploy backend ke VPS (Docker Compose: FastAPI + Chroma) + frontend ke Vercel
- [ ] TODO — Load testing simulasi dengan Locust

## Minggu 8 — Polish & Dokumentasi
- [ ] TODO — Rekam demo video (struktur sesuai `SRS_PRD.md` Bagian B.8)
- [ ] TODO — Finalisasi diagram arsitektur (Excalidraw/draw.io)
- [ ] TODO — Tulis README lengkap + blog post (jika ada waktu)
- [ ] TODO — Review akhir kode: clean-up, komentar, cek `DEFINITION_OF_DONE.md` penuh
- [ ] TODO — Review `SECURITY.md` checklist sebelum publikasi/demo publik

## Backlog Should-Have (dikerjakan jika waktu tersisa, urutan prioritas sesuai kesepakatan)
1. Executor Agent enhancement (format action item lebih variatif)
2. Admin dashboard fitur tambahan (filter, search dokumen)
3. Evaluation report otomatis yang bisa diekspor PDF
4. Reflection loop enhancement (reformulasi query lebih pintar)
