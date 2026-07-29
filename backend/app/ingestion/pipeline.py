"""
Ingestion Pipeline — EnterpriseMind AI.

End-to-end: Upload → Extract → Parent-Child Chunk → Embed → Store.
"""
import logging
import time
import asyncio

from app.core.config import settings
from app.db import create_document, update_document_status
from app.db.graph import save_graph_draft
from app.ingestion.chunker import chunk_document_parent_child, chunk_pages
from app.ingestion.embedder import embed_and_store_parent_child
from app.ingestion.extractor import detect_file_type, extract_text, extract_text_with_pages, flatten_pages
from app.ingestion.graph_extractor import extract_graph_from_text

logger = logging.getLogger(__name__)


async def run_ingestion_pipeline(
    file_path: str,
    filename: str,
    file_type: str | None = None,
    category: str = "uncategorized",
    file_size_bytes: int = 0,
) -> dict:
    """
    Run full ingestion pipeline with parent-child chunking.

    Returns dict with document_id, status, chunk_count, processing_time_ms, error.
    Status: "indexed" or "failed".
    """
    start_time = time.time()

    if file_type is None:
        file_type = detect_file_type(filename)

    doc_record = await create_document(
        filename=filename,
        file_type=file_type,
        category=category,
        storage_object_name=file_path,
        file_size_bytes=file_size_bytes,
    )
    document_id = doc_record["id"]

    try:
        await update_document_status(document_id, "processing")

        logger.info("[Pipeline] Step 1/3: Extracting text — %s", filename)
        extraction_result = await asyncio.wait_for(
            asyncio.to_thread(extract_text_with_pages, file_path, file_type),
            timeout=settings.EXTRACTION_TIMEOUT_SECONDS,
        )

        if isinstance(extraction_result, list):
            pages = extraction_result
            if not pages or all(not p.get("text", "").strip() for p in pages):
                raise ValueError(f"Dokumen '{filename}' kosong setelah ekstraksi.")
            logger.info("[Pipeline] Step 2/3: Page-aware chunking — %s", filename)
            metadata = {
                "filename": filename,
                "file_type": file_type,
                "category": category,
                "document_id": document_id,
            }
            parent_chunks, child_chunks = await asyncio.to_thread(
                chunk_pages, pages, metadata,
            )
        else:
            text = extraction_result
            if not text.strip():
                raise ValueError(f"Dokumen '{filename}' kosong setelah ekstraksi.")
            logger.info("[Pipeline] Step 2/3: Parent-Child Chunking — %s", filename)
            metadata = {
                "filename": filename,
                "file_type": file_type,
                "category": category,
                "document_id": document_id,
            }
            parent_chunks, child_chunks = await asyncio.to_thread(
                chunk_document_parent_child, text, metadata,
            )

        logger.info(
            "[Pipeline] Step 3/3: Embedding & storing — %s (parents=%d, children=%d)",
            filename, len(parent_chunks), len(child_chunks),
        )
        parent_count, child_count = await asyncio.to_thread(
            embed_and_store_parent_child, parent_chunks, child_chunks,
        )

        # Step 4: Graph extraction (LLM-based, conditional)
        if settings.NEO4J_ENABLED:
            try:
                logger.info("[Pipeline] Step 4/4: Graph extraction — %s", filename)
                text_for_graph = (
                    flatten_pages(pages) if isinstance(extraction_result, list)
                    else str(extraction_result)
                )
                await run_graph_extraction(
                    text=text_for_graph,
                    filename=filename,
                    document_id=document_id,
                )
            except Exception as e:
                logger.warning("[Pipeline] Graph extraction skipped: %s", e)

        await update_document_status(document_id, "indexed", chunk_count=child_count)

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "[Pipeline] Selesai: %s — %d parents, %d children, %dms",
            filename, parent_count, child_count, elapsed_ms,
        )

        return {
            "document_id": document_id,
            "filename": filename,
            "status": "indexed",
            "parent_count": parent_count,
            "chunk_count": child_count,
            "processing_time_ms": elapsed_ms,
            "error": None,
        }

    except Exception as e:
        logger.exception("[Pipeline] Gagal memproses: %s", filename)
        await update_document_status(document_id, "failed")
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "document_id": document_id,
            "filename": filename,
            "status": "failed",
            "chunk_count": 0,
            "processing_time_ms": elapsed_ms,
            "error": str(e),
        }


async def run_graph_extraction(text: str, filename: str, document_id: str) -> dict | None:
    """
    Extract entities and relationships for Knowledge Graph.
    In DRAFT mode: save to PostgreSQL for review.
    In LIVE mode: insert directly to Neo4j.

    Ref: GRAPH_PLAN.md §6 (Draft-then-Review Mechanism)
    """
    result = await asyncio.to_thread(
        extract_graph_from_text, text, filename, document_id
    )

    if not result["entities"]:
        logger.info("[GraphExtract] Tidak ada entity ditemukan untuk '%s'", filename)
        return result

    if settings.NEO4J_DRAFT_MODE:
        await save_graph_draft(document_id, filename, result)
        logger.info(
            "[GraphExtract] DRAFT saved: %d entities, %d relationships untuk '%s'",
            len(result["entities"]), len(result["relationships"]), filename,
        )
    else:
        from app.core.neo4j_client import get_neo4j, init_neo4j_schema
        try:
            init_neo4j_schema()
            driver = get_neo4j()
            with driver.session() as session:
                for ent in result["entities"]:
                    session.run(
                        "MERGE (e:Entity {name: $name}) SET e.type = $type",
                        name=ent["name"], type=ent["type"],
                    )
                for rel in result["relationships"]:
                    if rel["type"] == "MENTIONED_IN":
                        session.run(
                            "MATCH (e:Entity {name: $source}) "
                            "MERGE (d:Document {id: $target}) "
                            "MERGE (e)-[:MENTIONED_IN {context: $context}]->(d)",
                            source=rel["source"], target=rel["target"],
                            context=rel.get("context", ""),
                        )
                    else:
                        session.run(
                            f"MATCH (a:Entity {{name: $source}}) "
                            f"MATCH (b:Entity {{name: $target}}) "
                            f"MERGE (a)-[:{rel['type']} {{context: $context}}]->(b)",
                            source=rel["source"], target=rel["target"],
                            context=rel.get("context", ""),
                        )
            logger.info(
                "[GraphExtract] COMMITTED to Neo4j: %d entities, %d relationships untuk '%s'",
                len(result["entities"]), len(result["relationships"]), filename,
            )
        except Exception as e:
            logger.warning("[GraphExtract] Gagal commit ke Neo4j: %s. Data aman di draft.", e)
            await save_graph_draft(document_id, filename, result)

    return result
