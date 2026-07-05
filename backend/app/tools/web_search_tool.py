"""
Web Search Tool — EnterpriseMind AI.

Digunakan oleh agent untuk mencari informasi terkini dari internet
jika informasi tidak ditemukan di internal knowledge base.

Sifat: READ-ONLY.
"""

import logging

from langchain_community.tools.tavily_search import TavilySearchResults

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 3) -> list[dict]:
    """
    Cari informasi di web menggunakan Tavily API.

    Args:
        query: Pertanyaan atau kata kunci pencarian.
        max_results: Maksimal hasil yang dikembalikan.

    Returns:
        List dict berisi `url` dan `content` (snippet).
    """
    logger.info("Mencari di web untuk query: '%s'", query)
    
    try:
        # Memerlukan TAVILY_API_KEY di .env
        search = TavilySearchResults(max_results=max_results)
        results = search.invoke({"query": query})
        
        # Format ke bentuk standar
        formatted_results = []
        for res in results:
            formatted_results.append({
                "url": res.get("url", ""),
                "content": res.get("content", ""),
            })
            
        return formatted_results
    except Exception as e:
        logger.warning("Web search gagal: %s", e)
        return [{"url": "error", "content": "Gagal melakukan pencarian web."}]
