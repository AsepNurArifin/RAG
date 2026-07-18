# EnterpriseMind AI — Implementation Plan v3.1

> **Target**: Enterprise-grade AI Search Production  
> **Last Updated**: 2026-07-16  
> **Status**: Ready for Implementation  
> **Methodology**: One experiment, one evaluation. Setiap sprint = 1 komponen + 1 evaluasi.  
> **LLM**: Google Gemini 2.5 Flash  
> **Embedding**: BAAI/bge-m3  
> **Reranker**: BAAI/bge-reranker-v2-m3

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Analysis](#2-current-architecture-analysis)
3. [Target Pipeline Architecture](#3-target-pipeline-architecture)
4. [Phase 0: Offline Evaluation Framework](#phase-0-offline-evaluation-framework)
5. [Phase 1: Core Retrieval Improvements](#phase-1-core-retrieval-improvements)
6. [Phase 2: Advanced Retrieval](#phase-2-advanced-retrieval)
7. [Phase 3: Generation & Prompt Engineering](#phase-3-generation--prompt-engineering)
8. [Phase 4: Infrastructure & Backend](#phase-4-infrastructure--backend)
9. [Phase 5: Frontend UI Redesign](#phase-5-frontend-ui-redesign)
10. [Tech Stack Reference](#tech-stack-reference)
11. [Success Criteria](#success-criteria)

---

## 1. Executive Summary

EnterpriseMind AI adalah Agentic RAG system untuk enterprise knowledge search. Setelah analisis mendalam terhadap pipeline saat ini dan benchmark terhadap Google NotebookLM, ditemukan bahwa **quality gap terbesar** berasal dari:

1. Query handling yang lemah (tanpa expansion/rewrite)
2. Embedding model yang tidak optimal untuk bahasa Indonesia
3. Retrieval yang terlalu sederhana (k=5, single-pass, BM25 basic)
4. Context window yang terlalu kecil (~4.000 chars vs NotebookLM ~100.000 chars)

**Tujuan**: Mencapai kualitas jawaban yang **sebanding dengan NotebookLM** untuk dokumen internal perusahaan, dengan pipeline yang scalable dan terukur.

---

## 2. Current Architecture Analysis

### Pipeline Saat Ini

```
User Query
    → Orchestrator (Llama-3.1-8b, intent classification)
    → Researcher (hybrid_search, k=5, vector+BM25)
    → Verifier (Llama-3.3-70b, confidence scoring)
    → [Reflection Loop max 2x]
    → Summarizer (Llama-3.3-70b, answer synthesis)
    → [Executor if action_request]
    → Response
```

### Masalah yang Ditemukan

| Komponen | Saat Ini | Masalah | Impact |
|----------|----------|---------|--------|
| Embedding | `all-MiniLM-L6-v2` (22M, English) | Bahasa Indonesia buruk | Retrieval meleset |
| Chunking | Recursive, 1000 chars | Terlalu kecil, kehilangan konteks | Context hilang |
| Retrieval | top-5, single pass | Terlalu sedikit untuk listing queries | Jawaban tidak lengkap |
| BM25 | Simple stemming, 22 stopwords | Tidak akurat untuk bahasa Indonesia | Keyword matching buruk |
| Query Handling | Tidak ada expansion/rewrite | "aturan pensiun" ≠ "purna tugas" | Recall rendah |
| Intent | Semua pakai LLM (0.3s) | Lambat, tidak perlu untuk query sederhana | Latency tinggi |
| Top-k | Fixed k=5 | Tidak adaptive terhadap query type | Over/under-fetch |
| Prompt | "JANGAN PERNAH copy" | Terlalu restriktif untuk factual queries | Jawaban terlalu generik |
| Evaluation | Tidak ada | Tidak bisa ukur kualitas | Tidak bisa iterasi |

---

## 3. Target Pipeline Architecture

### Pipeline Final (Disetujui)

```
User Query
    │
    ▼
┌──────────────────────────────────┐
│ 1. Lightweight Intent Classifier │ ← Tiered: Rule → Classifier → LLM
│    factual/comprehensive/action  │    (hanya LLM jika ambiguous)
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 2. Need Query Rewrite?           │ ← Multi-signal: intent + confidence +
│    (rule + confidence)           │    ambiguity + length + OOV
└──────────────┬───────────────────┘
               │
          ┌────┴─────┐
          │ No       │ Yes
          │          ▼
          │    ┌──────────────────┐
          │    │ 3. Query Rewrite │
          │    │    (LLM expand)  │
          │    └──────────────────┘
          └────┬────┘
               │
               ▼
┌──────────────────────────────────┐
│ 4. Adaptive top-k                │ ← Multi-signal: intent + length +
│    (k=3..20)                     │    confidence + candidate count
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 5. Hybrid Search                 │ ← Vector (multilingual-e5-large) +
│    (Vector + BM25 Indonesia)     │    BM25 (Sastrawi, 100+ stopwords, synonym)
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 6. Retrieve Child Chunks         │ ← Embed child, retrieve child
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 7. Resolve Parents               │ ← Ambil parent, deduplicate
│    (deduplicate)                 │    (20 children → ~7 unique parents)
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 8. Cross-Encoder Reranker        │ ← Rerank parents → top 5 terbaik
│    (top 5)                       │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 9. Summarizer (LLM)              │ ← Conditional prompt:
│    + Citations                   │    listing → boleh kutip langsung
│                                  │    analysis → sintesis + parafrase
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 10. Verifier (optional)          │ ← Confidence check
│     Faithfulness scoring         │
└──────────────────────────────────┘
               │
               ▼
          Response
```

---

## Phase 0: Offline Evaluation Framework

> **WAJIB diimplementasikan SEBELUM perubahan apapun. Tanpa evaluasi, kita hanya berasumsi.**

### 0.1 Buat Test Set

| Task | Detail | File |
|------|--------|------|
| Buat 100 pertanyaan dengan expected answers | Komposisi eksplisit per kategori (lihat di bawah) | `evaluation/test_set.json` |
| Setiap pertanyaan punya `expected_answer`, `expected_sources`, `query_type` | Format JSON yang terstruktur | `evaluation/test_set.json` |
| Pastikan test set mencakup edge cases | Query pendek, query panjang, istilah teknis, sinonim | `evaluation/test_set.json` |

**Test Set Composition (100 pertanyaan):**

```
├── 30 Factual (definisi, entitas, angka, lokasi)
│   ├── Definisi: "Apa itu SOP?", "Apa itu kearifan lokal?"
│   ├── Entitas: "Siapa direktur PT?", "Kapan perusahaan berdiri?"
│   ├── Angka: "Berapa hari cuti tahunan?", "Berapa gaji minimum?"
│   └── Lokasi: "Di mana kantor pusat?", "Di mana cabang terdekat?"
│
├── 20 Listing (exhaustive, category, enumeration)
│   ├── Exhaustive: "Sebutkan semua jenis cuti"
│   ├── Category: "Apa saja yang termasuk kearifan lokal?"
│   └── Enumeration: "Daftar seluruh SOP yang berlaku"
│
├── 20 Comparison (direct, pros/cons, difference)
│   ├── Direct: "Bandingkan SOP A dan SOP B"
│   ├── Pros/Cons: "Kelebihan dan kekurangan WFH"
│   └── Difference: "Perbedaan cuti tahunan dan cuti sakit"
│
├── 20 Procedural (how-to, steps, SOP)
│   ├── How-to: "Bagaimana cara mengajukan cuti?"
│   ├── Steps: "Langkah-langkah pengajuan WFH"
│   └── SOP: "Prosedur pengaduan karyawan"
│
└── 10 Analytical (analysis, impact, relationship)
    ├── Analysis: "Analisis kebijakan WFH perusahaan"
    ├── Impact: "Dampak kearifan lokal terhadap lingkungan"
    └── Relationship: "Hubungan antara SOP dan kearifan lokal"
```

**Kenapa komposisi ini penting:**

```
Contoh hasil evaluasi per kategori:

                | Baseline | After Query Expansion |
|---------------|----------|----------------------|
| Factual       | 0.85     | 0.86 (+0.01)        |
| Listing       | 0.52     | 0.71 (+0.19) ★★★    |
| Comparison    | 0.68     | 0.73 (+0.05)        |
| Procedural    | 0.74     | 0.76 (+0.02)        |
| Analytical    | 0.61     | 0.65 (+0.04)        |

→ Query Expansion PALING BERPENGARUH untuk listing queries
→ Untuk factual queries, hampir tidak ada perbedaan
→ Insight ini hilang jika hanya melihat rata-rata keseluruhan
```

**Format test_set.json:**
```json
[
  {
    "id": 1,
    "query": "Apa itu kearifan lokal?",
    "query_type": "factual",
    "subcategory": "definition",
    "expected_answer_contains": ["pengetahuan tradisional", "adat istiadat", "sistem nilai"],
    "expected_sources": ["564974-kearifan-lokal-local-wisdom-indonesia-4ca2930e.pdf"],
    "difficulty": "easy"
  },
  {
    "id": 2,
    "query": "Sebutkan semua contoh kearifan lokal di Indonesia",
    "query_type": "comprehensive",
    "subcategory": "exhaustive",
    "expected_answer_contains": ["Subak", "Sasi", "Tumpang Sari", "Sedekah Bumi"],
    "expected_sources": ["564974-kearifan-lokal-local-wisdom-indonesia-4ca2930e.pdf"],
    "difficulty": "hard"
  }
]
```

### 0.2 Buat Evaluation Script

| Task | Detail | File |
|------|--------|------|
| Buat script evaluasi otomatis | Hitung semua metrics di bawah | `evaluation/evaluate.py` |
| Buat baseline evaluation | Jalankan evaluasi pada pipeline saat ini, simpan skor | `evaluation/results/baseline.json` |
| Buat comparison script | Bandingkan baseline vs perubahan | `evaluation/compare.py` |

**Metrics yang WAJIB diukur:**

| Metrik | Kategori | Formula | Target Enterprise |
|--------|----------|---------|-------------------|
| Recall@20 | Kualitas | # relevant chunks in top-20 / total relevant | > 0.80 |
| Context Precision | Kualitas | # relevant in retrieved / total retrieved | > 0.70 |
| Answer Relevancy | Kualitas | Cosine(answer, query) | > 0.75 |
| Faithfulness | Kualitas | # claims supported by context / total claims | > 0.85 |
| Hallucination Rate | Kualitas | # unsupported claims / total claims | < 5% |
| **Latency P50** | **Operasional** | Median response time | **< 3s** |
| **Latency P95** | **Operasional** | 95th percentile response time | **< 8s** |
| **Cost per Query** | **Operasional** | Total API cost per query | **< $0.01** |

**Trade-off Matrix Template:**

```
Perubahan              | Accuracy | Latency | Cost    | Worth it?
-----------------------|----------|---------|---------|----------
[baseline]             | --       | --      | --      | --
Query Expansion        | ?%      | +?s     | +$?     | ?/??
Reranker               | ?%      | +?s     | +$?     | ?/??
Parent-Child           | ?%      | +?s     | +$?     | ?/??
dst.
```

### 0.3 CI/CD Evaluation Gate

| Task | Detail | File |
|------|--------|------|
| Setiap perubahan di P0/P1 WAJIB di-evaluasi dulu | CI pipeline: run evaluation → compare with baseline → pass/fail | `.github/workflows/eval.yml` |
| Threshold: tidak boleh turun lebih dari 2% di metrik apapun | Regression detection | `evaluation/config.json` |

---

## Phase 1: Core Retrieval Improvements

> **Target**: Meningkatkan kualitas retrieval secara signifikan.  
> **Setiap perubahan harus di-evaluasi dengan Phase 0 sebelum merge.**

### 1.0 Migrasi LLM ke Gemini 2.5 Flash

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Install `langchain-google-genai` | Package untuk Gemini API | `requirements.txt` | 5 min |
| Update config | Tambah `GOOGLE_API_KEY`, `GEMINI_MODEL`, hapus `GROQ_API_KEY` | `core/config.py` | 15 min |
| Rewrite LLM provider | `ChatGroq` → `ChatGoogleGenerativeAI` | `core/llm_provider.py` | 30 min |
| Update .env | `GROQ_API_KEY` → `GOOGLE_API_KEY` | `.env`, `.env.example` | 5 min |
| Testing | Pastikan semua agent berfungsi dengan Gemini | Manual testing | 30 min |
| Evaluasi: baseline (Groq) vs new (Gemini) | Bandingkan kualitas jawaban | `evaluation/evaluate.py` | 30 min |

**Config change:**
```python
# config.py
# HAPUS:
# REASONING_MODEL: str = "llama-3.3-70b-versatile"
# FAST_MODEL: str = "llama-3.1-8b-instant"
# GROQ_API_KEY: str = ...

# TAMBAH:
GOOGLE_API_KEY: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
GEMINI_MODEL: str = "gemini-2.5-flash"
```

**LLM Provider change:**
```python
# core/llm_provider.py

from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

def get_llm(
    task_type: str = "fast",
    temperature: float = 0.1,
    max_tokens: int | None = 4096,
) -> ChatGoogleGenerativeAI:
    """
    Get Gemini 2.5 Flash instance.
    - task_type="fast" → temperature=0.1 (routing, intent, query expansion)
    - task_type="reasoning" → temperature=0.4 (summarizer, verifier)
    """
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY tidak boleh kosong")

    temp = temperature
    if task_type == "reasoning":
        temp = max(temperature, 0.4)

    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temp,
        max_output_tokens=max_tokens,
    )
```

**Keuntungan Gemini 2.5 Flash:**
- Context window: 1M tokens (vs Groq Llama ~128K)
- Multilingual lebih baik (bahasa Indonesia lebih bagus)
- Lebih murah: ~$0.15/1M input tokens
- Lebih konsisten dalam mengikuti instruksi prompt

**Trade-off:**
- Latency: Gemini ~1-3s (sedikit lebih lambat dari Groq ~0.5-1s)
- Tapi: Groq sering rate-limit, Gemini lebih stabil

### 1.1 Ganti Embedding Model

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Ganti dari `all-MiniLM-L6-v2` ke `BAAI/bge-m3` | Model multilingual 568M params, 1024 dim, bahasa Indonesia sangat bagus | `config.py`, `embedder.py` | 2 jam |
| Re-index semua dokumen | Embedding lama tidak kompatibel dengan model baru | `scripts/reindex.py` | 1 jam |
| Evaluasi: Recall@20 baseline vs baru | Target: Recall@20 naik minimal 5% | `evaluation/evaluate.py` | 30 min |

**Config change:**
```python
# config.py
EMBEDDING_MODEL: str = "BAAI/bge-m3"  # dari all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS: int = 1024  # dari 384
```
EMBEDDING_DIMENSIONS: int = 1024  # dari 384
```

**Embedder change:**
```python
# embedder.py
def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model

# Untuk E5, tambah prefix saat embed
def embed_query(query: str) -> str:
    """E5 models need 'query:' prefix for queries."""
    if "e5" in settings.EMBEDDING_MODEL:
        return f"query: {query}"
    return query

def embed_passage(text: str) -> str:
    """E5 models need 'passage:' prefix for documents."""
    if "e5" in settings.EMBEDDING_MODEL:
        return f"passage: {text}"
    return text
```

### 1.2 Lightweight Intent Classifier (Tiered)

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Implement tiered intent detection | Tier 1: Regex/Rule, Tier 2: Keyword, Tier 3: LLM | `agents/intent_classifier.py` (baru) | 1 hari |
| Buat regex patterns untuk greeting, action | Pattern matching untuk query sederhana | `agents/intent_classifier.py` | 2 jam |
| Buat keyword rules untuk factual, comprehensive | Keyword-based classification | `agents/intent_classifier.py` | 2 jam |
| LLM fallback hanya untuk ambiguous queries | Hanya 15% query yang perlu LLM | `agents/intent_classifier.py` | 1 jam |
| Integrasi ke pipeline | Ganti orchestrator LLM call dengan tiered classifier | `agents/orchestrator.py` | 2 jam |
| Evaluasi: classification accuracy + latency | Target: 60% query tanpa LLM, 0ms latency | `evaluation/evaluate.py` | 30 min |

**Implementasi:**
```python
# agents/intent_classifier.py

import re

# Tier 1: Regex/Rule (0ms, $0)
GREETING_PATTERN = re.compile(
    r"^(halo|hai|hi|hello|hey|selamat\s+(pagi|siang|sore|malam)|good\s+(morning|afternoon))",
    re.IGNORECASE
)
ACTION_PATTERN = re.compile(
    r"(buatkan|buat|draft|tulis|kirim|email|surat|laporan|rekomendasikan|saran)",
    re.IGNORECASE
)

# Tier 2: Keyword-based (0ms, $0)
COMPREHENSIVE_KEYWORDS = {
    "semua", "seluruh", "daftar", "list", "semua jenis", "macam-macam",
    "sebutkan semua", "tuliskan semua", "apa saja", "apa-apa saja",
}
ANALYTICAL_KEYWORDS = {
    "bandingkan", "analisis", "evaluasi", "kelebihan", "kekurangan",
    "perbedaan", "persamaan", "hubungan", "dampak", "pengaruh",
}

def classify_intent(query: str) -> tuple[str, float]:
    """
    Tiered intent classification.
    Returns: (intent, confidence)
    - confidence 1.0 = rule-based, tidak perlu LLM
    - confidence 0.0 = ambiguous, perlu LLM
    """
    query_lower = query.strip().lower()
    query_words = query_lower.split()

    # Tier 1: Greeting
    if GREETING_PATTERN.match(query_lower):
        return ("greeting", 1.0)

    # Tier 1: Action request
    if ACTION_PATTERN.search(query_lower):
        return ("action_request", 1.0)

    # Tier 2: Comprehensive
    for keyword in COMPREHENSIVE_KEYWORDS:
        if keyword in query_lower:
            return ("comprehensive", 0.9)

    # Tier 2: Analytical
    for keyword in ANALYTICAL_KEYWORDS:
        if keyword in query_lower:
            return ("analytical", 0.9)

    # Tier 2: Factual (query pendek, question words)
    question_words = {"apa", "siapa", "kapan", "di mana", "dimana", "berapa", "mengapa", "kenapa", "bagaimana"}
    if any(qw in query_lower for qw in question_words) and len(query_words) <= 10:
        return ("factual", 0.8)

    # Tier 3: Ambiguous → perlu LLM
    return ("ambiguous", 0.0)
```

### 1.3 Adaptive top-k

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Implement adaptive top-k berdasarkan multi-signal | intent + query_length + confidence + candidate_count | `retrieval/hybrid_search.py` | 4 jam |
| Buat fungsi `adaptive_top_k()` | Logika penentuan k berdasarkan konteks | `retrieval/hybrid_search.py` | 2 jam |
| Integrasi ke retriever | Ganti hardcoded `k=5` dengan adaptive | `agents/retriever.py` | 1 jam |
| Evaluasi: recall per query type | Target: factual k=3-5, comprehensive k=15-20 | `evaluation/evaluate.py` | 30 min |

**Implementasi:**
```python
# retrieval/hybrid_search.py

def adaptive_top_k(
    intent: str,
    query_length: int,
    retriever_confidence: float,
    candidate_count: int,
) -> int:
    """Tentukan top-k berdasarkan multi-signal."""

    # Base k per intent
    base_k = {
        "factual": 5,
        "comprehensive": 20,
        "analytical": 15,
        "action_request": 5,
        "greeting": 0,
        "ambiguous": 10,
    }.get(intent, 10)

    # Adjust berdasarkan retriever confidence
    if retriever_confidence < 0.4:
        base_k = min(base_k * 2, 30)  # Naikkan jika confidence rendah

    # Adjust berdasarkan panjang query
    if query_length < 4:
        base_k = max(base_k - 2, 3)  # Turunkan untuk query pendek
    elif query_length > 15:
        base_k = min(base_k + 5, 30)  # Naikkan untuk query panjang

    # Adjust berdasarkan jumlah kandidat
    base_k = min(base_k, candidate_count)

    return max(base_k, 3)  # Minimum 3
```

### 1.4 Query Expansion / Rewrite

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Implement decision tree untuk query expansion | Dictionary → LLM hybrid approach | `agents/query_rewriter.py` (baru) | 1 hari |
| Buat synonym dictionary untuk domain spesifik | Kata-kata yang sering berbeda antara query dan dokumen | `data/synonyms_id.json` | 4 jam |
| Buat abbreviation dictionary | Singkatan umum di enterprise (SOP, HRD, dll) | `data/abbreviations_id.json` | 2 jam |
| Implement LLM fallback untuk ambiguous queries | Hanya dipanggil jika dictionary tidak cukup | `agents/query_rewriter.py` | 4 jam |
| Integrasi ke pipeline | Expansion hanya jika `need_expansion()` = True | `agents/retriever.py` | 2 jam |
| Evaluasi: recall sebelum vs sesudah expansion | Target: recall listing queries naik minimal 10% | `evaluation/evaluate.py` | 30 min |

**Decision Tree (PENTING):**

```
Query masuk
    │
    ▼
┌──────────────────────┐
│ Ada singkatan?       │ ── Ya → Dictionary (0ms, $0)
│ (SOP, HRD, WFH, dll)│        Contoh: SOP → "Standar Operasional Prosedur, procedure"
└──────────┬───────────┘
           │ Tidak
           ▼
┌──────────────────────┐
│ Ada sinonim umum?    │ ── Ya → Dictionary (0ms, $0)
│ (pensiun, cuti, dll) │        Contoh: cuti → "izin, libur, leave, day off"
└──────────┬───────────┘
           │ Tidak
           ▼
┌──────────────────────┐
│ Comprehensive intent?│ ── Ya → LLM expand (0.3s, $0.0001)
│ (sebutkan semua, dll)│        Tambah semua sinonim terkait
└──────────┬───────────┘
           │ Tidak
           ▼
┌──────────────────────┐
│ Confidence < 0.5?    │ ── Ya → LLM expand (0.3s, $0.0001)
│ (ambiguous query)    │        Reformulasi query
└──────────┬───────────┘
           │ Tidak
           ▼
      Tidak perlu expansion
```

**Kenapa Decision Tree:**

```
Distribusi query enterprise (estimasi):
├── 40% punya singkatan/sinonim → Dictionary (0ms, $0)
├── 25% tidak perlu expansion → Skip (0ms, $0)
├── 20% comprehensive → LLM (0.3s, $0.0001)
└── 15% ambiguous → LLM (0.3s, $0.0001)

Rata-rata latency expansion: 0.09s
(vs semua pakai LLM: 0.3s → penghematan 70%)
```

**Implementasi:**
```python
# agents/query_rewriter.py

import json
from app.core.llm_provider import get_llm

# Load dictionaries (singleton)
_abbreviations = None
_synonyms = None

def _load_abbreviations() -> dict:
    global _abbreviations
    if _abbreviations is None:
        with open("data/abbreviations_id.json", "r") as f:
            _abbreviations = json.load(f)
    return _abbreviations

def _load_synonyms() -> dict:
    global _synonyms
    if _synonyms is None:
        with open("data/synonyms_id.json", "r") as f:
            _synonyms = json.load(f)
    return _synonyms


def need_query_expansion(
    query: str,
    intent: str,
    retriever_confidence: float,
) -> bool:
    """Multi-signal decision: perlu expansion atau tidak."""

    # Faktor 1: Ada singkatan?
    abbreviations = _load_abbreviations()
    query_words = query.lower().split()
    if any(w in abbreviations for w in query_words):
        return True

    # Faktor 2: Ada sinonim?
    synonyms = _load_synonyms()
    if any(w in synonyms for w in query_words):
        return True

    # Faktor 3: Intent comprehensive
    if intent == "comprehensive":
        return True

    # Faktor 4: Retriever confidence rendah (ambiguous)
    if retriever_confidence < 0.5:
        return True

    return False


def expand_query(query: str, intent: str, retriever_confidence: float) -> str:
    """
    Expand query berdasarkan decision tree:
    1. Dictionary (abbreviation + synonym) — instant, no cost
    2. LLM (hanya untuk comprehensive/ambiguous) — 0.3s, $0.0001
    """
    expanded_terms = set()
    query_words = query.lower().split()

    # Step 1: Dictionary expansion (0ms)
    abbreviations = _load_abbreviations()
    synonyms = _load_synonyms()

    for word in query_words:
        expanded_terms.add(word)
        if word in abbreviations:
            expanded_terms.update(abbreviations[word])
        if word in synonyms:
            expanded_terms.update(synonyms[word])

    # Step 2: LLM expansion (hanya jika perlu)
    if intent == "comprehensive" or retriever_confidence < 0.5:
        llm_result = _llm_expand_query(query)
        expanded_terms.update(llm_result)

    return ", ".join(expanded_terms)


def _llm_expand_query(query: str) -> list[str]:
    """LLM-based query expansion untuk kasus ambiguous."""
    llm = get_llm("fast", temperature=0.3)
    prompt = f"""Expand query berikut dengan sinonim dan istilah terkait dalam bahasa Indonesia.
Berikan 5-10 kata/frasa terkait, pisahkan dengan koma.

Query: {query}

Expanded terms:"""

    response = llm.invoke(prompt)
    terms = [t.strip() for t in response.content.split(",") if t.strip()]
    return terms

# Contoh data/abbreviations_id.json:
# {
#   "sop": ["standar operasional prosedur", "standard operating procedure", "prosedur"],
#   "hrd": ["human resource development", "sumber daya manusia", "sdm"],
#   "wfh": ["work from home", "bekerja dari rumah", "kerja remote"],
#   "kpi": ["key performance indicator", "indikator kinerja"]
# }

# Contoh data/synonyms_id.json:
# {
#   "pensiun": ["purna tugas", "retirement", "pensiun dini", "berhenti bekerja"],
#   "cuti": ["izin", "libur", "leave", "day off", "absen"],
#   "kearifan": ["kebijaksanaan", "wisdom", "kearifan lokal", "local wisdom"],
#   "sanksi": ["hukuman", "peringatan", "punishment", "sanksi disiplin"]
# }
```

### 1.5 Perbaiki Hybrid Search (BM25 Indonesia)

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Ganti stemming ke Sastrawi | Stemming bahasa Indonesia yang lebih akurat | `retrieval/hybrid_search.py` | 2 jam |
| Tambah 100+ stop words bahasa Indonesia | Stop words yang lebih lengkap | `retrieval/stopwords_id.py` (baru) | 1 jam |
| Tambah synonym expansion di BM25 | Expand query tokens dengan sinonim sebelum matching | `retrieval/hybrid_search.py` | 2 jam |
| Tambah bigram matching | Match kata majemuk (misal: "hukum adat") | `retrieval/hybrid_search.py` | 2 jam |
| Evaluasi: BM25 recall sebelum vs sesudah | Target: peningkatan keyword matching | `evaluation/evaluate.py` | 30 min |

**Implementasi:**
```python
# retrieval/hybrid_search.py

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# Inisialisasi Sastrawi stemmer (singleton)
_stemmer = None

def get_stemmer():
    global _stemmer
    if _stemmer is None:
        factory = StemmerFactory()
        _stemmer = factory.create_stemmer()
    return _stemmer

# 100+ stop words bahasa Indonesia
STOP_WORDS_ID = {
    "dan", "di", "ke", "dari", "yang", "ini", "itu", "dengan", "untuk",
    "pada", "adalah", "atau", "juga", "telah", "sudah", "akan", "dapat",
    "bisa", "tidak", "bukan", "belum", "ada", "tidak", "oleh", "dalam",
    "secara", "seperti", "antara", "lain", "serta", "hal", "masih",
    "harus", "merupakan", "pernah", "setelah", "sebelum", "ketika",
    "jika", "apabila", "maka", "namun", "tetapi", "sehingga",
    "karena", "yaitu", "yakni", "ialah", "adapun", "bahwa",
    "the", "is", "in", "of", "to", "and", "a", "an", "for", "on",
    "with", "by", "at", "from", "or", "as", "be", "this", "that",
    # ... tambahkan sesuai kebutuhan
}

def _tokenize_improved(text: str) -> set[str]:
    """Tokenisasi dengan Sastrawi stemming, stop word removal, dan bigram."""
    import re
    stemmer = get_stemmer()
    words = re.findall(r"\w+", text.lower())

    # Stemming dan stop word removal
    tokens = set()
    for w in words:
        if w not in STOP_WORDS_ID and len(w) > 1:
            stemmed = stemmer.stem(w)
            tokens.add(stemmed)

    # Tambah bigram
    filtered = [w for w in words if w not in STOP_WORDS_ID and len(w) > 1]
    for i in range(len(filtered) - 1):
        bigram = f"{filtered[i]}_{filtered[i+1]}"
        tokens.add(bigram)

    return tokens
```

---

## Phase 2: Advanced Retrieval

> **Target**: Implementasi Parent-Child retrieval dan Cross-Encoder Reranker.

### 2.1 Parent-Child Chunking

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Implement parent-child chunking strategy | Parent: 2000 chars, Child: 500 chars | `ingestion/chunker.py` | 1 hari |
| Tambah `parent_id` ke child metadata | Link child ke parent | `ingestion/chunker.py` | 2 jam |
| Implement storage decision (Hybrid) | Chroma metadata (dev) / PostgreSQL (prod) | `ingestion/embedder.py`, `db/parent_chunks.py` | 4 jam |
| Implement `resolve_parents()` + deduplication | Ambil parent dari child, deduplicate | `retrieval/parent_resolver.py` (baru) | 4 jam |
| Re-index semua dokumen dengan parent-child | Backfill existing documents | `scripts/reindex.py` | 2 jam |
| Evaluasi: Faithfulness sebelum vs sesudah | Target: Faithfulness naik minimal 5% | `evaluation/evaluate.py` | 30 min |

**Storage Decision (PENTING):**

```
┌─────────────────────────────────────────────────────────────────┐
│ Parent-Child Storage Decision                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Development:                                                      │
│ ├── Parent chunks: Chroma metadata field                         │
│ ├── Simpel, tidak perlu DB tambahan                              │
│ └── Cukup untuk <10.000 documents                                │
│                                                                   │
│ Production:                                                       │
│ ├── Parent chunks: PostgreSQL table                              │
│ ├── Tabel: parent_chunks (id, document_id, content, metadata)   │
│ ├── Index: parent_id (untuk fast lookup dari child)              │
│ └── Scalable untuk >100.000 documents                            │
│                                                                   │
│ Flow:                                                             │
│ 1. Saat ingestion: Simpan parent di PostgreSQL                   │
│    → Simpan child di Chroma (dengan parent_id di metadata)       │
│ 2. Saat retrieval: Retrieve child dari Chroma                    │
│    → Lookup parent dari PostgreSQL (batch query)                 │
│    → Deduplicate → Rerank → LLM                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Deduplication (PENTING):**

```
20 child chunks retrieved:
├── Child A → Parent 1
├── Child B → Parent 1
├── Child C → Parent 1
├── Child D → Parent 2
├── Child E → Parent 2
└── ...

Setelah deduplication:
├── Parent 1 (3 children)
├── Parent 2 (2 children)
└── ... = 7 unique parents

→ 7 unique parents × 2000 chars = 14.000 chars (100% unik)
→ vs 20 parents tanpa dedup = banyak duplikat, wasted context
```

**Implementasi chunking:**
```python
# ingestion/chunker.py

PARENT_CHUNK_SIZE = 2000
PARENT_CHUNK_OVERLAP = 400
CHILD_CHUNK_SIZE = 500
CHILD_CHUNK_OVERLAP = 100

def chunk_document_parent_child(
    text: str,
    metadata: dict,
) -> tuple[list[DocumentChunk], list[DocumentChunk]]:
    """
    Split dokumen jadi parent-child chunks.
    Parent = konteks besar untuk LLM.
    Child = unit kecil untuk embedding dan retrieval.

    Returns: (parent_chunks, child_chunks)
    """
    # Step 1: Split jadi parent chunks
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=PARENT_CHUNK_SIZE,
        chunk_overlap=PARENT_CHUNK_OVERLAP,
        separators=SEPARATORS,
    )
    parent_texts = parent_splitter.split_text(text)

    parent_chunks = []
    child_chunks = []

    for parent_idx, parent_text in enumerate(parent_texts):
        parent_id = f"{metadata['filename']}__parent_{parent_idx}"

        # Buat parent chunk
        parent_metadata = {
            **metadata,
            "chunk_type": "parent",
            "parent_id": parent_id,
            "chunk_index": parent_idx,
            "total_chunks": len(parent_texts),
        }
        parent_chunks.append(DocumentChunk(
            content=parent_text,
            metadata=parent_metadata,
            chunk_index=parent_idx,
        ))

        # Step 2: Split parent jadi child chunks
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHILD_CHUNK_SIZE,
            chunk_overlap=CHILD_CHUNK_OVERLAP,
            separators=SEPARATORS,
        )
        child_texts = child_splitter.split_text(parent_text)

        for child_idx, child_text in enumerate(child_texts):
            child_id = f"{parent_id}__child_{child_idx}"
            child_metadata = {
                **metadata,
                "chunk_type": "child",
                "parent_id": parent_id,
                "child_id": child_id,
                "chunk_index": child_idx,
                "total_chunks": len(child_texts),
            }
            child_chunks.append(DocumentChunk(
                content=child_text,
                metadata=child_metadata,
                chunk_index=child_idx,
            ))

    return parent_chunks, child_chunks
```

**Implementasi parent resolver:**
```python
# retrieval/parent_resolver.py

def resolve_and_deduplicate_parents(
    child_chunks: list[dict],
    parent_store,
) -> list[dict]:
    """
    Ambil parent chunks dari child chunks, deduplicate.

    Contoh:
    - 20 child chunks retrieved
    - Child A, B, C → Parent 1
    - Child D, E → Parent 2
    - ...
    - Result: 7 unique parents
    """
    seen_parent_ids = set()
    unique_parents = []

    for child in child_chunks:
        parent_id = child["metadata"]["parent_id"]
        if parent_id not in seen_parent_ids:
            seen_parent_ids.add(parent_id)
            parent = parent_store.get(parent_id)
            if parent:
                unique_parents.append(parent)

    return unique_parents
```

### 2.2 Cross-Encoder Reranker

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Implement cross-encoder reranker | Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` atau `BAAI/bge-reranker-v2-m3` | `retrieval/reranker.py` (baru) | 1 hari |
| Integrasi ke pipeline | Setelah parent resolution, rerank parents → top 5 | `agents/retriever.py` | 2 jam |
| Lazy load reranker model | Singleton pattern seperti embedding model | `retrieval/reranker.py` | 1 jam |
| Evaluasi: Context Precision sebelum vs sesudah | Target: chunk yang di-retrieve lebih relevan | `evaluation/evaluate.py` | 30 min |

**Implementasi:**
```python
# retrieval/reranker.py

from sentence_transformers import CrossEncoder
from app.core.config import settings

_reranker = None

def get_reranker() -> CrossEncoder:
    """Singleton reranker model."""
    global _reranker
    if _reranker is None:
        model_name = getattr(settings, "RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        _reranker = CrossEncoder(model_name, max_length=512)
    return _reranker


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """Rerank chunks berdasarkan relevansi ke query. Returns top-k."""
    if not chunks:
        return []

    reranker = get_reranker()

    # Buat pairs (query, chunk_content)
    pairs = [(query, chunk["content"]) for chunk in chunks]

    # Hitung scores
    scores = reranker.predict(pairs)

    # Sort berdasarkan score descending
    scored_chunks = list(zip(scores, chunks))
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    return [chunk for _, chunk in scored_chunks[:top_k]]
```

---

## Phase 3: Generation & Prompt Engineering

> **Target**: Memperbaiki kualitas jawaban dari Summarizer.

### 3.1 Perbaiki Summarizer Prompt

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Buat conditional prompt berdasarkan query type | Listing → boleh kutip langsung, Analysis → sintesis | `agents/__init__.py` (SUMMARIZER_PROMPT) | 2 jam |
| Hapus restriksi "JANGAN PERNAH copy" untuk factual queries | Ganti dengan conditional instruction | `agents/__init__.py` | 1 jam |
| Tambah structured output format | JSON mode untuk jawaban yang lebih konsisten | `agents/summarizer.py` | 2 jam |
| Evaluasi: Answer Relevancy sebelum vs sesudah | Target: jawaban lebih relevan dan lengkap | `evaluation/evaluate.py` | 30 min |

**Implementasi conditional prompt:**
```python
# agents/__init__.py

SUMMARIZER_PROMPT = """Kamu adalah Summarizer/Analyzer Agent yang ahli menyusun jawaban berkualitas tinggi.

ATURAN UTAMA:
Untuk pertanyaan TIPE LISTING/ENUMERASI (misalnya "sebutkan semua", "daftar", "apa saja"):
- Kamu BOLEH langsung kutip dari sumber dengan sitasi [Sumber: nama_dokumen]
- Format sebagai numbered list yang rapi
- Jangan parafrase jika user meminta daftar dari sumber

Untuk pertanyaan TIPE ANALISIS/EKSPLANASI (misalnya "jelaskan", "analisis", "bagaimana"):
- Sintesis dan parafrase informasi dari dokumen sumber
- Format sebagai paragraf naratif yang mengalir
- Minimal 3 paragraf: definisi, detail, analisis

Untuk pertanyaan TIPE FAKTA SEDERHANA (misalnya "apa itu", "siapa"):
- Jawab langsung dan singkat dengan sitasi

ATURAN SITASI:
- Setiap klaim yang berasal dari dokumen sumber HARUS disertai sitasi [Sumber: nama_dokumen]

LARANGAN:
- JANGAN menyebutkan hal teknis internal (confidence score, dll)
- JANGAN membuat informasi yang tidak ada di dokumen sumber

Output format: teks jawaban naratif + daftar sitasi terpisah."""
```

### 3.2 Naikkan Context Window

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Naikkan `max_chars` dari 800 ke 1500 | LLM lihat lebih banyak per chunk | `agents/utils.py` | 5 min |
| Naikkan `max_tokens` dari 4096 ke 8192 | LLM bisa generate jawaban lebih panjang | `core/config.py` | 5 min |
| Evaluasi: jawaban lebih lengkap? | Manual review + Answer Relevancy | `evaluation/evaluate.py` | 30 min |

---

## Phase 4: Infrastructure & Backend

### 4.1 PostgreSQL Migration

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Buat PostgreSQL client | async connection pool dengan asyncpg | `core/postgres_client.py` (baru) | 2 jam |
| Rewrite CRUD operations | Ganti Supabase calls ke asyncpg | `db/documents.py`, `db/messages.py`, `db/queries.py` | 3 jam |
| Update config | Tambah DATABASE_URL | `core/config.py` | 30 min |
| Update Docker Compose | Tambah PostgreSQL service | `docker-compose.yml` | 1 jam |
| Migration script | Buat tabel-tabel yang dibutuhkan | `scripts/migrate.sql` | 1 jam |
| Testing | Pastikan semua endpoint berfungsi | Manual testing | 2 jam |

### 4.2 RBAC Implementation

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Tambah `department`, `clearance_level` ke JWT | Update payload saat login | `core/auth.py` | 1 jam |
| Buat `user_profiles` table | Tabel untuk RBAC metadata | `scripts/migrate.sql` | 30 min |
| Tambah RBAC metadata ke chunks | department, clearance_level, effective_date | `ingestion/chunker.py` | 2 jam |
| Buat `filter_metadata` mandatory | Wajib filter berdasarkan user profile | `retrieval/hybrid_search.py` | 1 jam |
| Inject filter dari user profile | Ambil profile dari JWT, pass ke retriever | `agents/retriever.py` | 2 jam |

### 4.3 Temporal.io Integration

| Task | Detail | File | Effort |
|------|--------|------|--------|
| Buat Temporal workflows dan activities | Ingestion workflow dengan activities | `temporal/workflows.py`, `temporal/activities.py` | 3 hari |
| Buat Temporal worker | Worker process untuk menjalankan activities | `temporal/worker.py` | 1 hari |
| Update upload endpoint | Return 202 + workflow_id | `api/upload.py` | 2 jam |
| Update Docker Compose | Tambah Temporal server + worker | `docker-compose.yml` | 2 jam |

---

## Phase 5: Frontend UI Redesign

> **Status**: Sudah selesai diimplementasikan. Lihat file-file berikut:
> - `frontend/app/(chat)/layout.tsx` — 2-column layout, `#f8fafc` bg
> - `frontend/components/layout/ProcessRail.tsx` — Floating + collapsible
> - `frontend/components/ChatWindow.tsx` — Header bar + improved empty state
> - `frontend/components/MessageBubble.tsx` — Confidence ring dengan warna dinamis
> - `frontend/components/layout/UserSideNavBar.tsx` — Deep blue `#004790`
> - `frontend/components/layout/SideNavBar.tsx` — Admin sidebar konsisten
> - `frontend/app/login/page.tsx` — Clean brand colors
> - `frontend/app/admin/page.tsx` — White surface

---

## Tech Stack Reference

### Backend

| Komponen | Saat Ini | Target |
|----------|----------|--------|
| Framework | FastAPI | FastAPI (tetap) |
| Database | Supabase (PostgreSQL managed) | PostgreSQL async (asyncpg) |
| Vector Store | ChromaDB | ChromaDB (tetap) |
| Embedding | `all-MiniLM-L6-v2` (22M) | `BAAI/bge-m3` (568M) |
| Reranker | Tidak ada | `BAAI/bge-reranker-v2-m3` |
| LLM Provider | Groq (`langchain-groq`) | Google Gemini (`langchain-google-genai`) |
| LLM Model | `llama-3.3-70b-versatile` + `llama-3.1-8b-instant` | `gemini-2.5-flash` (satu model, beda temperature) |
| Orchestration | LangGraph | LangGraph (tetap) |
| Ingestion | Sync pipeline | Temporal.io (async) |
| BM25 | Custom simple stemming | Sastrawi stemming + 100+ stopwords |

### Frontend

| Komponen | Saat Ini | Target |
|----------|----------|--------|
| Framework | Next.js 16 + React 19 | Next.js 16 (tetap) |
| Styling | Tailwind CSS v4 + shadcn | Tailwind CSS v4 (tetap) |
| Animations | framer-motion | framer-motion (tetap) |
| State | useChatStream + Context | useChatStream + Context (tetap) |

### Infrastructure

| Komponen | Saat Ini | Target |
|----------|----------|--------|
| Container | Docker Compose | Docker Compose (tetap) |
| Queue | Tidak ada | Temporal.io |
| Cache | Tidak ada | Redis (Phase 2) |
| Monitoring | Tidak ada | LangFuse (Phase 3) |
| Evaluation | Tidak ada | RAGAS + custom metrics |

---

## Success Criteria

### Kualitas Jawaban (Per Kategori Query)

| Metrik | Baseline | Target Overall | Target Listing | Target Factual |
|--------|----------|---------------|----------------|----------------|
| Recall@20 | TBD | > 0.80 | > 0.75 | > 0.85 |
| Context Precision | TBD | > 0.70 | > 0.65 | > 0.75 |
| Answer Relevancy | TBD | > 0.75 | > 0.70 | > 0.80 |
| Faithfulness | TBD | > 0.85 | > 0.80 | > 0.90 |
| Hallucination Rate | TBD | < 5% | < 8% | < 3% |

### Operasional

| Metrik | Target | Batas Maksimal |
|--------|--------|----------------|
| Latency P50 | < 2s | < 3s |
| Latency P95 | < 5s | < 8s |
| Cost per Query | < $0.005 | < $0.01 |
| Intent Detection (tanpa LLM) | > 70% query | > 60% query |

### Acceptance Criteria Global

```
Setiap sprint harus menghasilkan:
1. Tabel Before/After dengan semua metrik di atas
2. Per-kategori breakdown (factual, listing, comparison, procedural, analytical)
3. Trade-off analysis (accuracy vs latency vs cost)
4. PASS/FAIL decision berdasarkan acceptance criteria per sprint

Jika FAIL:
- Tidak boleh lanjut ke sprint berikutnya
- Harus investigasi penyebab kegagalan
- Harus buat rencana perbaikan sebelum retry
```

### Fungsional

| Fitur | Status |
|-------|--------|
| Pertanyaan listing komprehensif | ✅ Harus bekerja |
| Pertanyaan factual sederhana | ✅ Harus bekerja |
| Pertanyaan analisis/eksplanasi | ✅ Harus bekerja |
| Pertanyaan comparison | ✅ Harus bekerja |
| Pertanyaan procedural (SOP) | ✅ Harus bekerja |
| Action request (draft email, dll) | ✅ Harus bekerja |
| Multi-turn conversation | ✅ Harus bekerja |
| RBAC (department + clearance) | ✅ Harus bekerja |
| Async ingestion (100GB+) | ✅ Harus bekerja |
| Mobile responsive UI | ✅ Harus bekerja |

---

## Implementation Sequence

> **Prinsip: SATU eksperimen, SATU evaluasi.** Setiap sprint menghasilkan tabel Before/After. Jika tidak ada peningkatan yang jelas, sprint berikutnya JANGAN dilanjutkan sebelum dipahami penyebabnya.

```
Sprint 1: Evaluation Dataset + LLM Migration + Embedding Upgrade
├── Buat 100 test questions (30 factual, 20 listing, 20 comparison, 20 procedural, 10 analytical)
├── Jalankan baseline evaluation (dengan Groq + old embedding, simpan skor sebagai perbandingan)
├── Migrasi LLM: Groq (Llama) → Google Gemini 2.5 Flash
│   ├── Install: pip install langchain-google-genai
│   ├── Update config: GOOGLE_API_KEY, GEMINI_MODEL
│   ├── Rewrite llm_provider.py: ChatGroq → ChatGoogleGenerativeAI
│   └── Update .env: GROQ_API_KEY → GOOGLE_API_KEY
├── Ganti embedding model: all-MiniLM-L6-v2 → BAAI/bge-m3
├── Re-index semua dokumen
├── Jalankan evaluasi
├── Bandingkan: baseline (Groq + old embedding) vs new (Gemini 2.5 Flash + bge-m3)
└── Output: Tabel Before/After

Sprint 2: Hybrid Search Improvement
├── Implement Sastrawi stemming + 100+ stopwords
├── Tambah synonym expansion + bigram matching
├── Jalankan evaluasi
├── Bandingkan dengan Sprint 1
└── Output: Tabel Before/After per kategori query

Sprint 3: Intent Detection + Adaptive top-k
├── Implement tiered intent classifier (Rule → Classifier → LLM)
├── Implement adaptive top-k (multi-signal)
├── Jalankan evaluasi per kategori
├── Bandingkan dengan Sprint 2
└── Output: Tabel Before/After per kategori query

Sprint 4: Query Expansion
├── Implement decision tree (Dictionary → LLM)
├── Buat synonym + abbreviation dictionaries
├── Jalankan evaluasi per kategori
├── Bandingkan dengan Sprint 3
└── Output: Tabel Before/After, terutama untuk listing queries

Sprint 5: Reranker
├── Implement cross-encoder reranker (BAAI/bge-reranker-v2-m3)
├── Jalankan evaluasi
├── Bandingkan dengan Sprint 4
└── Output: Tabel Before/After

Sprint 6: Parent-Child
├── Implement parent-child chunking
├── Implement storage: Chroma metadata (dev) / PostgreSQL (prod)
├── Implement parent resolver + deduplication
├── Re-index semua dokumen
├── Jalankan evaluasi
├── Bandingkan dengan Sprint 5
└── Output: Tabel Before/After

Sprint 7: Prompt Engineering
├── Implement conditional summarizer prompt
├── Naikkan context window (max_chars 800→1500, max_tokens 4096→8192)
├── Jalankan evaluasi manual (10 queries sample)
├── Bandingkan dengan Sprint 6
└── Output: Before/After comparison

Sprint 8: Infrastructure
├── PostgreSQL migration
├── RBAC implementation
├── Temporal.io integration
├── Final evaluation dengan test set lengkap
└── Output: All existing tests pass, deployment ready
```

**Acceptance Criteria per Sprint:**

```
┌─────────────────────────────────────────────────────────────────┐
│ Sprint 1: LLM Migration + Embedding Upgrade                      │
├─────────────────────────────────────────────────────────────────┤
│ LLM Migration (Groq → Gemini 2.5 Flash):                         │
│ ├── Semua agent berfungsi normal dengan Gemini                   │
│ ├── Answer Relevancy: tidak boleh turun > 5% dari baseline       │
│ └── Faithfulness: tidak boleh turun > 5% dari baseline           │
│                                                                   │
│ Embedding Upgrade (MiniLM → bge-m3):                             │
│ ├── Recall@20 (overall): minimal naik 5% dari baseline            │
│ ├── Recall@20 (listing): minimal naik 8%                         │
│ └── Context Precision: minimal naik 3%                           │
│                                                                   │
│ Operational:                                                      │
│ ├── Latency P95: maksimal naik 30% dari baseline                 │
│ └── Cost/query: maksimal naik 50% dari baseline                  │
│                                                                   │
│ PASS: Semua kriteria terpenuhi                                    │
│ FAIL: Kembalikan ke baseline, investigasi penyebab               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Sprint 2: Hybrid Search                                          │
├─────────────────────────────────────────────────────────────────┤
│ Quality:                                                          │
│ ├── Recall@20 (overall): minimal naik 3% dari Sprint 1           │
│ ├── Recall@20 (factual): tidak boleh turun > 2%                  │
│ └── Context Precision: minimal naik 2%                           │
│ Operational:                                                      │
│ ├── Latency P50: maksimal naik 0.2s                              │
│ └── Cost/query: tidak berubah                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Sprint 3: Intent + Adaptive k                                    │
├─────────────────────────────────────────────────────────────────┤
│ Quality:                                                          │
│ ├── Recall@20 (comprehensive): minimal naik 10%                  │
│ ├── Recall@20 (factual): tidak boleh turun > 2%                  │
│ └── Answer Relevancy: minimal naik 3%                            │
│ Operational:                                                      │
│ ├── Latency P50 (overall): turun minimal 10% (lebih efisien)     │
│ └── Intent detection tanpa LLM: > 60% query                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Sprint 4: Query Expansion                                        │
├─────────────────────────────────────────────────────────────────┤
│ Quality:                                                          │
│ ├── Recall@20 (listing): minimal naik 10% dari Sprint 3          │
│ ├── Recall@20 (factual): tidak boleh turun > 2%                  │
│ └── Answer Relevancy (listing): minimal naik 5%                  │
│ Operational:                                                      │
│ ├── Latency P50: maksimal naik 0.3s                              │
│ └── Cost/query: maksimal naik $0.0002                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Sprint 5: Reranker                                               │
├─────────────────────────────────────────────────────────────────┤
│ Quality:                                                          │
│ ├── Context Precision: minimal naik 5% dari Sprint 4             │
│ ├── Answer Relevancy: minimal naik 3%                            │
│ └── Faithfulness: minimal naik 3%                                │
│ Operational:                                                      │
│ ├── Latency P50: maksimal naik 0.5s                              │
│ └── Cost/query: maksimal naik $0.0003                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Sprint 6: Parent-Child                                           │
├─────────────────────────────────────────────────────────────────┤
│ Quality:                                                          │
│ ├── Faithfulness: minimal naik 5% dari Sprint 5                  │
│ ├── Answer Relevancy: minimal naik 3%                            │
│ └── Hallucination Rate: turun minimal 2%                         │
│ Operational:                                                      │
│ ├── Latency P50: maksimal naik 0.3s                              │
│ └── Storage: tidak naik signifikan                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Sprint 7: Prompt Engineering                                     │
├─────────────────────────────────────────────────────────────────┤
│ Quality:                                                          │
│ ├── Answer Relevancy (listing): minimal naik 5%                  │
│ ├── Faithfulness: tidak boleh turun > 2%                         │
│ └── Manual review: 10 queries sample → kualitas membaik          │
│ Operational:                                                      │
│ ├── Latency P50: tidak berubah signifikan                        │
│ └── Cost/query: tidak berubah signifikan                         │
└─────────────────────────────────────────────────────────────────┘
```

**Trade-off Matrix Template (per Sprint):**

```
┌──────────────────────────────────────────────────────────────────┐
│ Sprint N: [Nama Komponen]                                         │
├──────────────────────────────────────────────────────────────────┤
│ Metric                │ Baseline  │ After     │ Delta   │ Pass? │
├───────────────────────┼───────────┼───────────┼─────────┼───────┤
│ Recall@20 (overall)   │ 0.71      │ 0.78      │ +0.07   │ ✅    │
│ Recall@20 (listing)   │ 0.52      │ 0.65      │ +0.13   │ ✅    │
│ Recall@20 (factual)   │ 0.85      │ 0.84      │ -0.01   │ ✅    │
│ Context Precision     │ 0.55      │ 0.62      │ +0.07   │ ✅    │
│ Answer Relevancy      │ 0.68      │ 0.73      │ +0.05   │ ✅    │
│ Faithfulness          │ 0.79      │ 0.84      │ +0.05   │ ✅    │
│ Hallucination Rate    │ 8%        │ 5%        │ -3%     │ ✅    │
│ Latency P50           │ 1.2s      │ 1.4s      │ +0.2s   │ ✅    │
│ Latency P95           │ 2.8s      │ 3.1s      │ +0.3s   │ ✅    │
│ Cost/query            │ $0.001    │ $0.0012   │ +$0.0002│ ✅    │
├───────────────────────┴───────────┴───────────┴─────────┴───────┤
│ RESULT: PASS — Semua kriteria terpenuhi                          │
│ ACTION: Lanjut ke Sprint berikutnya                               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Appendix: File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `backend/evaluation/test_set.json` | Test set 50-100 pertanyaan |
| `backend/evaluation/evaluate.py` | Script evaluasi otomatis |
| `backend/evaluation/compare.py` | Script perbandingan baseline vs perubahan |
| `backend/evaluation/results/baseline.json` | Skor baseline |
| `backend/agents/intent_classifier.py` | Tiered intent classifier |
| `backend/agents/query_rewriter.py` | Query expansion logic |
| `backend/data/synonyms_id.json` | Synonym dictionary bahasa Indonesia |
| `backend/data/abbreviations_id.json` | Abbreviation dictionary (SOP, HRD, WFH, dll) |
| `backend/retrieval/stopwords_id.py` | 100+ stop words bahasa Indonesia |
| `backend/retrieval/reranker.py` | Cross-encoder reranker |
| `backend/retrieval/parent_resolver.py` | Parent resolution + deduplication |
| `backend/temporal/workflows.py` | Temporal workflow definitions |
| `backend/temporal/activities.py` | Temporal activity definitions |
| `backend/temporal/worker.py` | Temporal worker process |
| `backend/temporal/client.py` | Temporal client helper |
| `backend/core/postgres_client.py` | PostgreSQL async client |
| `backend/scripts/reindex.py` | Re-index all documents |
| `backend/scripts/migrate.sql` | Database migration script |

### Modified Files

| File | Changes |
|------|---------|
| `backend/core/config.py` | Tambah EMBEDDING_DIMENSIONS, RERANKER_MODEL, DATABASE_URL |
| `backend/ingestion/chunker.py` | Parent-child chunking strategy |
| `backend/ingestion/embedder.py` | E5 prefix, parent-child storage |
| `backend/ingestion/pipeline.py` | Parent-child pipeline |
| `backend/retrieval/hybrid_search.py` | Sastrawi stemming, adaptive k, synonym, bigram |
| `backend/retrieval/vector_store.py` | E5 prefix support |
| `backend/agents/__init__.py` | Conditional summarizer prompt |
| `backend/agents/orchestrator.py` | Integrasi tiered classifier |
| `backend/agents/retriever.py` | Query expansion, adaptive k, parent resolution |
| `backend/agents/summarizer.py` | Structured output, larger context |
| `backend/agents/verifier.py` | Adjusted threshold |
| `backend/graph/build_graph.py` | Updated routing logic |
| `backend/graph/state.py` | Tambah user_profile, expanded_query fields |
| `backend/db/__init__.py` | PostgreSQL CRUD |
| `backend/core/auth.py` | RBAC fields di JWT |
| `backend/api/upload.py` | Async 202 + Temporal |
| `backend/api/query.py` | RBAC filter injection |
| `backend/requirements.txt` | +asyncpg, +temporalio, +Sastrawi, +sentence-transformers |
