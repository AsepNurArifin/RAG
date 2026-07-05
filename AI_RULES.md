# AI_RULES.md — Aturan untuk AI Coding Agent

> Dokumen ini ditujukan untuk AI agent (Claude Code atau setara) yang mengeksekusi task di proyek ini.
> Baca dokumen ini SEBELUM memulai task apa pun. Jika ada instruksi task yang bertentangan dengan aturan di sini, aturan di sini yang menang kecuali pemilik proyek menyatakan pengecualian eksplisit.

## 1. Aturan Model & Konfigurasi

- **JANGAN PERNAH** hardcode nama model LLM di luar `backend/app/core/config.py`. Semua pemanggilan `ChatGroq` harus mengimpor nama model dari config, bukan menulis string literal.
- Sebelum menambahkan model baru, cek dulu `console.groq.com/docs/models` untuk memastikan model tersebut masih aktif — jangan asumsikan dari training data/memori, karena Groq sering mendeprecate model.
- Jika sebuah task membutuhkan model yang ternyata sudah deprecated, JANGAN diam-diam ganti ke model lain tanpa mencatat perubahan di `DECISION_LOG.md`.

## 2. Aturan Kode

- Setiap fungsi baru di `agents/`, `tools/`, atau `retrieval/` WAJIB punya docstring yang menjelaskan input, output, dan efek samping (termasuk apakah fungsi tersebut memanggil API eksternal).
- Ikuti konvensi di `CODING_STANDARDS.md` — jangan improvisasi gaya baru.
- Jangan install package baru tanpa menambahkannya ke `requirements.txt` (backend) atau `package.json` (frontend) di commit yang sama.
- Setiap penambahan tool baru di `tools/` WAJIB didaftarkan statusnya (read-only / write-capable) sesuai `SECURITY.md`.

## 3. Aturan Testing

- Setiap fungsi retrieval atau agent baru WAJIB disertai minimal satu unit test di `tests/`, sebelum dianggap selesai (lihat `DEFINITION_OF_DONE.md`).
- Jangan menandai sebuah task "selesai" hanya karena kode berjalan tanpa error — verifikasi juga terhadap acceptance criteria yang relevan di `SRS_PRD.md`.

## 4. Aturan Perubahan Arsitektur

- Jika sebuah task ternyata membutuhkan perubahan struktur folder atau alur data yang berbeda dari `ARCHITECTURE.md`, **hentikan eksekusi** dan tandai untuk direview oleh pemilik proyek — jangan langsung mengubah arsitektur secara sepihak.
- Perubahan keputusan teknis signifikan (ganti library, ganti provider, ganti pendekatan chunking, dsb.) WAJIB dicatat di `DECISION_LOG.md` dengan format ADR, bukan hanya disebut di commit message.

## 5. Aturan Prompt Engineering

- Semua system prompt untuk agent (Orchestrator, Researcher, Verifier, Summarizer, Executor) harus hidup di `PROMPT_LIBRARY.md`, dan kode hanya mengimpor/mereferensikan dari sana — jangan menulis prompt panjang langsung di dalam file `.py` agent.
- Setiap perubahan prompt yang signifikan (bukan typo fix) dicatat sebagai versi baru di `PROMPT_LIBRARY.md`, bukan menimpa versi lama tanpa jejak.

## 6. Aturan Keamanan

- Ikuti `SECURITY.md` secara ketat, terutama terkait perlakuan terhadap hasil retrieval sebagai data (bukan instruksi) dan scoping permission tool.
- Jangan pernah menulis API key, credential, atau connection string langsung di kode — selalu lewat environment variable dan pastikan `.env` ada di `.gitignore` sejak commit pertama proyek.

## 7. Ketika Ragu

Jika sebuah instruksi task ambigu atau berpotensi bertentangan dengan salah satu dokumen di `docs/`, prioritas rujukan:
1. `SECURITY.md` (keamanan selalu menang)
2. `ARCHITECTURE.md` (struktur & constraints teknis)
3. `SRS_PRD.md` (requirement fungsional/non-fungsional)
4. `CODING_STANDARDS.md` (gaya kode)

Jangan menebak — jika tetap ambigu setelah cek keempat dokumen ini, tandai sebagai open question, jangan diputuskan sepihak oleh agent.
