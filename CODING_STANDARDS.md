# CODING_STANDARDS.md — EnterpriseMind AI

## Backend (Python)

**Style & Formatting**
- Ikuti PEP 8. Gunakan `black` untuk auto-formatting dan `ruff` untuk linting.
- Maksimal panjang baris: 100 karakter.
- Type hints wajib untuk semua fungsi publik (parameter dan return type).

**Naming Convention**
- File & folder: `snake_case` (mis. `web_search_tool.py`).
- Class: `PascalCase` (mis. `ResearcherAgent`).
- Fungsi & variabel: `snake_case`.
- Konstanta: `UPPER_SNAKE_CASE`, didefinisikan di `core/config.py`.

**Struktur Fungsi Agent**
Setiap agent di `agents/` mengikuti pola konsisten:
```python
def run_researcher_agent(state: GraphState) -> GraphState:
    """
    Menjalankan Researcher Agent: retrieval hybrid terhadap query.

    Args:
        state: State LangGraph saat ini, berisi query dan history.

    Returns:
        State yang diperbarui dengan hasil retrieval.

    Side effects:
        Memanggil vector store (I/O) dan LangFuse trace.
    """
    ...
```

**Error Handling**
- Semua pemanggilan API eksternal (Groq, web search) dibungkus try/except dengan retry logic (mis. `tenacity`), bukan dibiarkan crash tanpa penanganan.
- Gunakan custom exception class (mis. `ModelUnavailableError`, `RetrievalTimeoutError`) daripada exception generik, agar mudah ditangani berbeda di level API.
- Jangan pernah `except Exception: pass` tanpa logging — minimal log error ke LangFuse/console sebelum melanjutkan atau fallback.

**Logging**
- Gunakan `logging` module standar Python, bukan `print()`, untuk semua log production-path.
- Setiap agent call dan tool call WAJIB ter-trace di LangFuse (lihat `core/observability.py`).

## Frontend (Next.js/TypeScript)

**Style & Formatting**
- ESLint + Prettier dengan konfigurasi default Next.js.
- Komponen React: `PascalCase` (mis. `ChatWindow.tsx`).
- Hooks custom: prefix `use` (mis. `useChatStream.ts`).

**Struktur Komponen**
- Komponen presentational (murni tampilan) dipisah dari komponen yang mengandung logic fetching data.
- Semua pemanggilan ke backend API lewat `lib/api.ts`, jangan `fetch()` langsung tersebar di banyak komponen.

**State Management**
- Gunakan React state/hooks bawaan untuk state lokal; hindari menambah library state management (Redux, Zustand) kecuali kompleksitas benar-benar membutuhkannya — untuk skala MVP ini kemungkinan besar tidak perlu.

## Umum (Berlaku Backend & Frontend)

- Commit message mengikuti format: `[area] deskripsi singkat` (mis. `[backend/agents] tambah confidence scoring di verifier`).
- Tidak ada kode yang di-commit dengan API key/secret di dalamnya — cek `.env` sudah di `.gitignore` sebelum commit pertama.
- Setiap Pull Request (meskipun proyek solo, tetap gunakan PR ke branch `main` untuk kebiasaan baik) menyertakan deskripsi singkat perubahan dan referensi ke task di `TASK_BACKLOG.md`.
