"""
Hybrid Search — EnterpriseMind AI.

Vector similarity + keyword search combined for higher recall.
Strategy: 0.7 semantic weight + 0.3 keyword weight.

Improvements (Sprint 2):
- Sastrawi stemming (bahasa Indonesia)
- 150+ stop words dari stopwords_id.py
- Synonym expansion
- Bigram matching
"""
import logging
import re
from functools import lru_cache

from app.retrieval.vector_store import similarity_search_with_scores
from app.retrieval.stopwords_id import STOP_WORDS_ID

logger = logging.getLogger(__name__)

# Sastrawi stemmer (singleton)
_stemmer = None


def _get_stemmer():
    """Get Sastrawi stemmer instance (singleton)."""
    global _stemmer
    if _stemmer is None:
        from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
        factory = StemmerFactory()
        _stemmer = factory.create_stemmer()
        logger.info("Sastrawi stemmer initialized.")
    return _stemmer


# Synonym dictionary — loaded once
_synonyms = None


def _load_synonyms() -> dict:
    """Load synonym dictionary from JSON file."""
    global _synonyms
    if _synonyms is None:
        import json
        from pathlib import Path
        synonym_path = Path(__file__).parent.parent.parent / "data" / "synonyms_id.json"
        if synonym_path.exists():
            with open(synonym_path, "r", encoding="utf-8") as f:
                _synonyms = json.load(f)
            logger.info("Synonym dictionary loaded: %d entries", len(_synonyms))
        else:
            _synonyms = {}
            logger.warning("Synonym dictionary not found at %s", synonym_path)
    return _synonyms


def _stem_word(word: str) -> str:
    """Stem a single word using Sastrawi."""
    stemmer = _get_stemmer()
    return stemmer.stem(word)


def _tokenize_improved(text: str) -> set[str]:
    """
    Tokenisasi DIOPTIMASI — stem per kalimat, bukan per kata.
    
    Sebelumnya: 4000+ panggilan stem() → 35s
    Sekarang: ~20 panggilan stem() (1 per dokumen) → <1s
    """
    return set(_cached_tokenize(text))


@lru_cache(maxsize=200)
def _cached_tokenize(text: str) -> frozenset:
    """
    Cached version of tokenization.
    LRU cache: 200 most recent unique texts.
    Dokumen yang sering di-retrieve tidak perlu di-stem ulang.
    Ref: OPTIMIZATION_PLAN.md P3
    """
    words = re.findall(r"\w+", text.lower())
    synonyms = _load_synonyms()

    # Filter stop words
    filtered = [w for w in words if w not in STOP_WORDS_ID and len(w) > 1]
    if not filtered:
        return frozenset()

    # Stem SELURUH text sekaligus (Sastrawi lebih efektif dengan konteks kalimat)
    stemmer = _get_stemmer()
    stemmed_text = stemmer.stem(" ".join(filtered))
    stemmed_words = set(stemmed_text.lower().split())

    # Collect original words for synonym expansion
    original_words = set(filtered)

    # Synonym expansion pada original words
    for w in original_words:
        if w in synonyms:
            for syn in synonyms[w]:
                syn_stemmed = stemmer.stem(syn)
                stemmed_words.add(syn_stemmed.lower())

    # Bigram matching (tetap pada original words untuk bigram yang bermakna)
    for i in range(len(filtered) - 1):
        bigram = f"{filtered[i]}_{filtered[i+1]}"
        stemmed_words.add(bigram)

    return frozenset(stemmed_words)


def hybrid_search(
    query: str,
    k: int = 5,
    filter_metadata: dict | None = None,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> list[dict]:
    """
    Hybrid retrieval: vector similarity + keyword matching.

    Returns sorted list of dicts with content, source, category, relevance_score, chunk_index.
    """
    logger.info("Hybrid search: query='%s...', k=%d", query[:50], k)

    vector_results = similarity_search_with_scores(
        query=query,
        k=k * 2,
        filter_metadata=filter_metadata,
    )

    query_tokens = _tokenize_improved(query)
    scored_results: dict[str, dict] = {}

    for doc, vector_distance in vector_results:
        vector_score = 1.0 / (1.0 + vector_distance)

        doc_tokens = _tokenize_improved(doc.page_content)
        keyword_score = len(query_tokens & doc_tokens) / max(len(query_tokens), 1) if doc_tokens else 0.0

        combined_score = vector_weight * vector_score + keyword_weight * keyword_score

        content_key = hash(doc.page_content[:200])
        if content_key not in scored_results or scored_results[content_key]["relevance_score"] < combined_score:
            scored_results[content_key] = {
                "content": doc.page_content,
                "source": doc.metadata.get("filename", "unknown"),
                "date": doc.metadata.get("upload_date", ""),
                "category": doc.metadata.get("category", "uncategorized"),
                "relevance_score": round(combined_score, 4),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "document_id": doc.metadata.get("document_id", ""),
                "parent_id": doc.metadata.get("parent_id", ""),
                "chunk_type": doc.metadata.get("chunk_type", ""),
                "page_number": doc.metadata.get("page_number", 0),
            }

    # Filter minimum relevance threshold
    min_relevance = 0.05
    filtered_results = {k: v for k, v in scored_results.items() if v["relevance_score"] >= min_relevance}

    sorted_results = sorted(
        filtered_results.values(),
        key=lambda x: x["relevance_score"],
        reverse=True,
    )[:k]

    logger.info("Hybrid search selesai: %d results (dari %d vector hits)", len(sorted_results), len(vector_results))
    return sorted_results
