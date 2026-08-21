"""
Lightweight Intent Classifier — EnterpriseMind AI.

Tiered approach untuk menghemat latency dan cost:
- Tier 1: Regex/Rule (0ms, $0)
- Tier 2: Keyword-based (0ms, $0)
- Tier 3: LLM fallback (hanya untuk ambiguous, ~0.3s, $0.0001)

Target: >60% query terklasifikasi tanpa LLM.
"""
import re
import logging

logger = logging.getLogger(__name__)


# ============================================================ #
# Tier 1: Regex Patterns (0ms, $0)
# ============================================================ #

GREETING_PATTERN = re.compile(
    r"^(halo|hai|hi|hello|hey|selamat\s+(pagi|siang|sore|malam)"
    r"|good\s+(morning|afternoon|evening)|apa\s+kabar|how\s+are\s+you)"
    r"[!?.\s]*$",
    re.IGNORECASE,
)

ACTION_PATTERN = re.compile(
    r"(buatkan|buat\s+draft|draft\s+email|tulis\s+surat|kirim\s+email"
    r"|kirim\s+laporan|rekomendasikan|berikan\s+saran|susun\s+laporan"
    r"|buat\s+laporan|draft\s+surat|buat\s+email|kirim\s+notifikasi)",
    re.IGNORECASE,
)


# ============================================================ #
# Tier 2: Keyword Sets (0ms, $0)
# ============================================================ #

COMPREHENSIVE_KEYWORDS = {
    "semua", "seluruh", "daftar", "list", "semua jenis", "macam-macam",
    "sebutkan semua", "tuliskan semua", "apa saja", "apa-apa saja",
    "sebutkan", "tuliskan", "cantumkan", "rinci", "detail semua",
}

ANALYTICAL_KEYWORDS = {
    "bandingkan", "analisis", "evaluasi", "kelebihan", "kekurangan",
    "perbedaan", "persamaan", "hubungan", "dampak", "pengaruh",
    "efektivitas", "efisiensi", "potensi", "risiko", "peluang",
    "tantangan", "solusi", "rekomendasi", "strategi",
}

PROCEDURAL_KEYWORDS = {
    "bagaimana cara", "langkah-langkah", "prosedur", "tata cara",
    "tutorial", "panduan", "cara", "steps", "mengapa begini",
    "bagaimana proses", "bagaimana alur", "mekanisme",
}

COMPARISON_KEYWORDS = {
    "bandingkan", "perbedaan", "persamaan", "vs", "versus",
    "dibanding", "lebih baik", "lebih buruk", "kelebihan", "kekurangan",
}


# ============================================================ #
# Intent Types
# ============================================================ #

VALID_INTENTS = {"greeting", "factual", "comprehensive", "analytical", "procedural", "comparison", "action_request", "out_of_scope"}


def classify_intent_tiered(query: str) -> tuple[str, float]:
    """
    Tiered intent classification.

    Returns:
        (intent, confidence)
        - confidence 1.0 = rule-based, tidak perlu LLM
        - confidence 0.0 = ambiguous, perlu LLM fallback
    """
    query_stripped = query.strip()
    query_lower = query_stripped.lower()
    query_words = query_lower.split()

    # ---- Tier 1: Greeting ----
    if GREETING_PATTERN.match(query_lower):
        logger.info("[Intent] Tier 1: greeting (confidence=1.0)")
        return ("greeting", 1.0)

    # ---- Tier 1: Action Request ----
    if ACTION_PATTERN.search(query_lower):
        logger.info("[Intent] Tier 1: action_request (confidence=1.0)")
        return ("action_request", 1.0)

    # ---- Tier 2: Comprehensive (listing/enumeration) ----
    for kw in COMPREHENSIVE_KEYWORDS:
        if kw in query_lower:
            logger.info("[Intent] Tier 2: comprehensive (keyword='%s', confidence=0.9)", kw)
            return ("comprehensive", 0.9)

    # ---- Tier 2: Analytical ----
    analytical_hits = sum(1 for kw in ANALYTICAL_KEYWORDS if kw in query_lower)
    if analytical_hits >= 2:
        logger.info("[Intent] Tier 2: analytical (%d keywords matched, confidence=0.85)", analytical_hits)
        return ("analytical", 0.85)

    # ---- Tier 2: Comparison ----
    comparison_hits = sum(1 for kw in COMPARISON_KEYWORDS if kw in query_lower)
    if comparison_hits >= 1:
        logger.info("[Intent] Tier 2: comparison (%d keywords matched, confidence=0.85)", comparison_hits)
        return ("comparison", 0.85)

    # ---- Tier 2: Procedural ----
    for kw in PROCEDURAL_KEYWORDS:
        if kw in query_lower:
            logger.info("[Intent] Tier 2: procedural (keyword='%s', confidence=0.85)", kw)
            return ("procedural", 0.85)

    # ---- Tier 2: Factual (question words + short query) ----
    question_words = {"apa", "siapa", "kapan", "di mana", "dimana", "berapa", "mengapa", "kenapa", "bagaimana"}
    has_question_word = any(qw in query_lower for qw in question_words)
    
    # Multi-entity definition query: "apa yang dimaksud X, Y, dan Z?"
    import re as _re
    uppercase_terms = _re.findall(r'\b[A-Z]{2,}\b', query)
    if has_question_word and len(uppercase_terms) >= 2:
        logger.info("[Intent] Tier 2: comprehensive (multi-entity: %s, confidence=0.85)", uppercase_terms)
        return ("comprehensive", 0.85)
    
    if has_question_word and len(query_words) <= 12:
        logger.info("[Intent] Tier 2: factual (confidence=0.8)")
        return ("factual", 0.8)

    # ---- Tier 3: Ambiguous → perlu LLM ----
    logger.info("[Intent] Tier 3: ambiguous (confidence=0.0, perlu LLM)")
    return ("ambiguous", 0.0)


def classify_intent_with_llm(query: str) -> tuple[str, float]:
    """
    LLM-based intent classification untuk query ambiguous.
    Hanya dipanggil jika tiered classifier confidence = 0.0.

    Returns:
        (intent, confidence)
    """
    from app.core.llm_provider import get_llm, invoke_llm_instrumented

    llm = get_llm("fast", temperature=0.1)

    prompt = f"""Klasifikasikan intent dari query berikut ke salah satu kategori:
- factual: pertanyaan fakta spesifik (apa, siapa, kapan, di mana, berapa)
- comprehensive: meminta daftar/list lengkap (sebutkan semua, apa saja)
- analytical: minta analisis/evaluasi/perbandingan
- procedural: minta cara/langkah/prosedur
- comparison: minta perbandingan antara 2+ hal
- action_request: minta draft/email/laporan
- out_of_scope: pertanyaan di luar konteks dokumen internal

Query: {query}

Respond HANYA dengan JSON: {{"intent": "...", "confidence": 0.0-1.0, "reasoning": "..."}}"""

    try:
        response, _ = invoke_llm_instrumented(
            chain=llm, input_data=prompt, agent_name="intent_classifier", task_type="fast", max_retries=2,
        )
        import json

        text = response.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        result = json.loads(text)
        intent = result.get("intent", "factual")
        confidence = float(result.get("confidence", 0.7))

        if intent not in VALID_INTENTS:
            intent = "factual"

        logger.info("[Intent] LLM: %s (confidence=%.2f, reasoning='%s')", intent, confidence, result.get("reasoning", "")[:60])
        return (intent, min(max(confidence, 0.0), 1.0))

    except Exception as e:
        logger.warning("[Intent] LLM fallback gagal: %s, default ke factual", e)
        return ("factual", 0.5)


def classify_intent(query: str) -> tuple[str, float]:
    """
    Main entry point: Tiered classification.

    Returns:
        (intent, confidence)
        - confidence 1.0/0.9/0.8 = rule/keyword-based, tidak perlu LLM
        - confidence < 0.8 = LLM-based
    """
    # Tier 1 + Tier 2
    intent, confidence = classify_intent_tiered(query)

    # Tier 3: LLM fallback jika ambiguous
    if confidence == 0.0:
        intent, confidence = classify_intent_with_llm(query)

    return (intent, confidence)
