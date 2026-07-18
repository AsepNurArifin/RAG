"""
Parent Resolver — EnterpriseMind AI.

Resolve parent chunks from child chunks, with deduplication.

Flow:
1. Retrieve child chunks dari Chroma
2. Ambil parent_id dari metadata setiap child
3. Lookup parent chunks dari storage (Chroma metadata / PostgreSQL)
4. Deduplicate parents (20 children → ~7 unique parents)
5. Return unique parents untuk LLM context

Storage Strategy:
- Development: Parent chunks di Chroma metadata field
- Production: Parent chunks di PostgreSQL table
"""
import logging

logger = logging.getLogger(__name__)


def resolve_and_deduplicate_parents(
    child_chunks: list[dict],
    parent_store: dict[str, dict] | None = None,
) -> list[dict]:
    """
    Ambil parent chunks dari child chunks, deduplicate.

    Args:
        child_chunks: List child chunk dicts dengan parent_id di metadata
        parent_store: Dict mapping parent_id → parent chunk data
                     (untuk development, bisa dari Chroma metadata)

    Returns:
        List unique parent chunk dicts, tanpa duplikat.

    Contoh:
        20 child chunks retrieved:
        ├── Child A → Parent 1
        ├── Child B → Parent 1
        ├── Child C → Parent 1
        ├── Child D → Parent 2
        ├── Child E → Parent 2
        └── ...
        → Deduplicate → 7 unique parents
    """
    if not child_chunks:
        return []

    seen_parent_ids: set[str] = set()
    unique_parents: list[dict] = []

    for child in child_chunks:
        parent_id = child.get("metadata", {}).get("parent_id") or child.get("parent_id")

        if not parent_id:
            # Child tanpa parent_id → treat sebagai standalone
            unique_parents.append(child)
            continue

        if parent_id in seen_parent_ids:
            continue

        seen_parent_ids.add(parent_id)

        # Cari parent dari store
        if parent_store and parent_id in parent_store:
            parent = parent_store[parent_id].copy()
            parent["resolved_from_children"] = _count_children(child_chunks, parent_id)
            unique_parents.append(parent)
        else:
            # Fallback: gunakan child sebagai proxy parent
            child_copy = child.copy()
            child_copy["is_child_proxy"] = True
            unique_parents.append(child_copy)

    logger.info(
        "Parent resolution: %d children → %d unique parents",
        len(child_chunks),
        len(unique_parents),
    )

    return unique_parents


def _count_children(child_chunks: list[dict], parent_id: str) -> int:
    """Hitung berapa child yang merujuk ke parent_id yang sama."""
    count = 0
    for child in child_chunks:
        child_parent_id = child.get("metadata", {}).get("parent_id") or child.get("parent_id")
        if child_parent_id == parent_id:
            count += 1
    return count


def build_parent_store_from_chroma(milvus_store, parent_ids: list[str]) -> dict[str, dict]:
    """
    Build parent store dari Milvus berdasarkan parent_ids.

    Args:
        milvus_store: Milvus vector store instance
        parent_ids: List parent_id yang perlu diambil

    Returns:
        Dict mapping parent_id → parent chunk data
    """
    if not parent_ids:
        return {}

    parent_store = {}

    try:
        # Query Milvus untuk parent chunks
        ids_str = ", ".join(f'"{pid}"' for pid in parent_ids)
        expr = f"parent_id in [{ids_str}]"
        
        milvus_store.col.load()
        results = milvus_store.col.query(
            expr=expr,
            output_fields=["text", "metadata", "parent_id"]
        )

        for doc in results:
            parent_id = doc.get("parent_id") or doc.get("metadata", {}).get("parent_id")
            if parent_id:
                parent_store[parent_id] = {
                    "content": doc.get("text", ""),
                    "metadata": doc.get("metadata", {}),
                    "parent_id": parent_id,
                }

        logger.info("Built parent store: %d parents from Milvus", len(parent_store))

    except Exception as e:
        logger.warning("Failed to build parent store from Milvus: %s", e)

    return parent_store
