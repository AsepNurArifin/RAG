"""
Query Rewriter — EnterpriseMind AI.

Decision tree untuk query expansion:
1. Dictionary (abbreviation + synonym) — 0ms, $0
2. LLM expansion (hanya untuk comprehensive/ambiguous) — ~0.3s, $0.0001

Target: Mengurangi latency expansion 70% dibanding semua pakai LLM.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Dictionaries (singleton)
_abbreviations = None
_synonyms = None


def _load_abbreviations() -> dict:
    global _abbreviations
    if _abbreviations is None:
        path = Path(__file__).parent.parent.parent / "data" / "abbreviations_id.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _abbreviations = json.load(f)
            logger.info("Abbreviation dictionary loaded: %d entries", len(_abbreviations))
        else:
            _abbreviations = {}
            logger.warning("Abbreviation dictionary not found at %s", path)
    return _abbreviations


def _load_synonyms() -> dict:
    global _synonyms
    if _synonyms is None:
        path = Path(__file__).parent.parent.parent / "data" / "synonyms_id.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _synonyms = json.load(f)
            logger.info("Synonym dictionary loaded: %d entries", len(_synonyms))
        else:
            _synonyms = {}
            logger.warning("Synonym dictionary not found at %s", path)
    return _synonyms


def need_query_expansion(
    query: str,
    intent_type: str,
    intent_confidence: float,
    retriever_confidence: float = 0.0,
) -> bool:
    """
    Multi-signal decision: perlu expansion atau tidak.

    Signals:
    - intent_type: comprehensive → selalu expand
    - intent_confidence: confidence rendah → expand
    - retriever_confidence: hasil retrieval kurang → expand
    - query_length: query pendek → kemungkinan OOV tinggi
    """
    query_lower = query.lower().strip()
    query_words = query_lower.split()
    abbreviations = _load_abbreviations()
    synonyms = _load_synonyms()

    # Faktor 1: Ada singkatan?
    if any(w in abbreviations for w in query_words):
        logger.info("[Expansion] Need: abbreviation detected")
        return True

    # Faktor 2: Ada sinonim?
    if any(w in synonyms for w in query_words):
        logger.info("[Expansion] Need: synonym detected")
        return True

    # Faktor 3: Intent comprehensive
    if intent_type == "comprehensive":
        logger.info("[Expansion] Need: comprehensive intent")
        return True

    # Faktor 4: Intent confidence rendah
    if intent_confidence < 0.5:
        logger.info("[Expansion] Need: low intent confidence (%.2f)", intent_confidence)
        return True

    # Faktor 5: Retriever confidence rendah (jika tersedia)
    if retriever_confidence > 0 and retriever_confidence < 0.4:
        logger.info("[Expansion] Need: low retriever confidence (%.2f)", retriever_confidence)
        return True

    logger.info("[Expansion] Not needed")
    return False


def expand_query_dictionary(query: str) -> str:
    """
    Dictionary-based expansion (0ms, $0).
    Expand query dengan abbreviation dan synonym dari dictionary.
    """
    query_lower = query.lower().strip()
    query_words = query_lower.split()
    abbreviations = _load_abbreviations()
    synonyms = _load_synonyms()

    expanded = set()
    for word in query_words:
        expanded.add(word)
        if word in abbreviations:
            expanded.update(abbreviations[word])
        if word in synonyms:
            expanded.update(synonyms[word])

    result = ", ".join(sorted(expanded))
    logger.info("[Expansion] Dictionary: '%s' → '%s'", query[:50], result[:100])
    return result


def expand_query_llm(query: str, intent_type: str) -> str:
    """
    LLM-based expansion (~0.3s, $0.0001).
    Hanya dipanggil untuk comprehensive/ambiguous queries.
    """
    from app.core.llm_provider import get_llm

    llm = get_llm("fast", temperature=0.3, max_tokens=512)

    prompt = f"""Expand query berikut dengan sinonim dan istilah terkait dalam bahasa Indonesia.
Berikan 5-10 kata/frasa terkait yang akan membantu menemukan dokumen relevan.
Pisahkan dengan koma.

Query: {query}
Intent: {intent_type}

Expanded terms:"""

    try:
        response = llm.invoke(prompt)
        terms = [t.strip() for t in response.content.split(",") if t.strip()]
        result = ", ".join(terms)
        logger.info("[Expansion] LLM: '%s' → '%s'", query[:50], result[:100])
        return result
    except Exception as e:
        logger.warning("[Expansion] LLM failed: %s", e)
        return query


def expand_query(
    query: str,
    intent_type: str,
    intent_confidence: float,
    retriever_confidence: float = 0.0,
) -> str:
    """
    Main entry point: Decision tree expansion.

    1. Dictionary (abbreviation + synonym) — 0ms, $0
    2. LLM (hanya untuk comprehensive/ambiguous) — ~0.3s, $0.0001

    Returns: Expanded query string.
    """
    # Step 1: Check if expansion needed
    if not need_query_expansion(query, intent_type, intent_confidence, retriever_confidence):
        return query

    # Step 2: Dictionary expansion (always first, instant)
    dict_expanded = expand_query_dictionary(query)

    # Step 3: LLM expansion (only for comprehensive/ambiguous)
    if intent_type in ("comprehensive", "ambiguous"):
        llm_expanded = expand_query_llm(query, intent_type)
        # Combine dictionary + LLM
        all_terms = set(dict_expanded.split(", ")) | set(llm_expanded.split(", "))
        result = ", ".join(sorted(all_terms))
        logger.info("[Expansion] Combined: '%s' → '%s'", query[:50], result[:100])
        return result

    return dict_expanded
