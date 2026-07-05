# DEFINITION_OF_DONE.md — EnterpriseMind AI

> Checklist ini direferensikan setiap menyelesaikan task di `TASK_BACKLOG.md`. Sebuah task TIDAK dianggap selesai sampai semua poin relevan tercentang.

## Checklist Umum (semua task)

- [ ] Kode mengikuti `CODING_STANDARDS.md`
- [ ] Tidak ada nama model, API key, atau credential yang di-hardcode
- [ ] Fungsi baru punya docstring/type hint sesuai standar
- [ ] Perubahan arsitektur (jika ada) sudah dicatat di `ARCHITECTURE.md` dan `DECISION_LOG.md`
- [ ] Tidak ada `print()` debug yang tertinggal di kode final

## Checklist Tambahan — Fitur Agent/Retrieval

- [ ] Minimal 1 unit test ditambahkan untuk logic baru
- [ ] Agent call/tool call baru ter-trace di LangFuse
- [ ] Prompt agent (jika baru/berubah) sudah dicatat di `PROMPT_LIBRARY.md`
- [ ] Diverifikasi terhadap acceptance criteria terkait di `SRS_PRD.md` (bukan cuma "kode jalan")

## Checklist Tambahan — Fitur UI (Frontend)

- [ ] Responsif minimal di ukuran desktop standar (tidak wajib mobile-first untuk MVP)
- [ ] Loading state ditampilkan untuk operasi yang memakan waktu >1 detik (sesuai NFR-U2)
- [ ] Error dari backend ditampilkan secara user-friendly, bukan raw error/stack trace

## Checklist Tambahan — Sebelum Deploy/Demo

- [ ] Evaluasi RAGAS terbaru dijalankan dan hasilnya konsisten dengan target di SRS (faithfulness ≥ 85%)
- [ ] Load testing simulasi (Locust) sudah dijalankan minimal sekali sebelum demo final
- [ ] Checklist `SECURITY.md` sudah direview penuh (khususnya `.env`, rate limiting endpoint publik)
- [ ] README di root repo mencerminkan kondisi terbaru proyek (bukan versi lama)
