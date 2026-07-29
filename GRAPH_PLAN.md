# GRAPH_PLAN.md — Neo4j Knowledge Graph Integration

> **EnterpriseMind AI**
> Dokumen ini adalah **rencana implementasi** penambahan Knowledge Graph layer
> menggunakan Neo4j untuk memungkinkan multi-hop reasoning dan learning path
> traversal pada dokumen HR training.
>
> **Status**: Direncanakan
> **Terakhir diupdate**: 2026-07-26

---

## Daftar Isi

1. [Tujuan & Motivasi](#1-tujuan--motivasi)
2. [Arsitektur Final](#2-arsitektur-final)
3. [Entity & Relationship Model](#3-entity--relationship-model)
4. [Struktur File](#4-struktur-file)
5. [Detail Implementasi](#5-detail-implementasi)
6. [Draft-then-Review Mechanism](#6-draft-then-review-mechanism)
7. [Conditional Graph Traversal](#7-conditional-graph-traversal)
8. [Query Pipeline (Flow)](#8-query-pipeline-flow)
9. [Resource Impact](#9-resource-impact)
10. [Trade-off & Risiko](#10-trade-off--risiko)
11. [Rollback Plan](#11-rollback-plan)
12. [Urutan Eksekusi](#12-urutan-eksekusi)

---

## 1. Tujuan & Motivasi

### Kemampuan Baru

| Kemampuan | Tanpa Graph | Dengan Graph |
|---|---|---|
| "Apa learning path menjadi HRBP?" | ❌ Hanya kembalikan dokumen dengan kata "HRBP" | ✅ Traverse: Skill → Training → Certification → HRBP |
| "Hubungan Leadership dan Performance Review?" | ❌ Kembalikan dokumen terpisah | ✅ Path: Leadership → (terkait via Training X) → Performance Review |
| "Apa prerequisite sebelum belajar Forecasting?" | ❌ Cuma dokumen Forecasting | ✅ Python → Data Analysis → ML → Forecasting |
| "Siapa yang bertanggung jawab atas SOP ini?" | ❌ Tidak tahu relasi | ✅ Policy → GOVERNS → Department/Position |

### Kenapa Neo4j, Bukan PostgreSQL untuk Graph?

| Aspek | PostgreSQL | Neo4j |
|---|---|---|
| **Multi-hop traversal** (depth 3+) | JOIN berulang, lambat | Traversal native, milidetik |
| **Path finding** (shortest path) | Tidak ada, harus rekursif manual | `SHORTEST_PATH` bawaan |
| **Variable-length relationship** | Tidak support | `[*1..5]` native |
| **Query readability** | SQL recursive CTE (rumit) | `MATCH path = (a)-[:PREREQ*]->(b)` (intuitif) |

Untuk 300-500 entity, PostgreSQL masih OK. Tapi query multi-hop di SQL jadi **30-50 baris recursive CTE** vs **3 baris Cypher**. Neo4j adalah pilihan arsitektur yang tepat untuk graph traversal.

---

## 2. Arsitektur Final

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                        INGESTION PIPELINE                        │
 │                                                                   │
 │  Upload ──► MinIO ──► Download ──► Extract ──► Chunk             │
 │                                                   │               │
 │                                           ┌───────┴────────┐     │
 │                                           ▼                ▼      │
 │                                       Embedding      LLM Extract  │
 │                                           │            Entities   │
 │                                           ▼              │        │
 │                                        Milvus           Draft     │
 │                                                      (PostgreSQL) │
 │                                                           │        │
 │                                                   [REVIEW]        │
 │                                                           │        │
 │                                                      Commit        │
 │                                                           ▼        │
 │                                                       Neo4j        │
 └──────────────────────────────────────────────────────────────────┘



 ┌──────────────────────────────────────────────────────────────────┐
 │                         QUERY PIPELINE                           │
 │                                                                   │
 │  User Query                                                       │
 │       │                                                           │
 │       ▼                                                           │
 │  Orchestrator ──► Intent Classification                           │
 │       │                                                           │
 │       │              ┌──────────────────────┐                     │
 │       │              │   factual/greeting    │                     │
 │       │              │   /action_request     │                     │
 │       │              └──────────┬───────────┘                     │
 │       │                         ▼                                 │
 │       │                 Hybrid Search Only                        │
 │       │                   (Milvus)                                │
 │       │                                                           │
 │       │              ┌──────────────────────┐                     │
 │       │              │  analytical/comparison                     │
 │       │              │  /comprehensive       │                     │
 │       │              │  /ambiguous           │                     │
 │       │              └──────────┬───────────┘                     │
 │       │                         ▼                                 │
 │       │              ┌──────────────────┐                         │
 │       │              │  Extract Entities │ ← LLM 8B atau rule    │
 │       │              │  dari Query       │                         │
 │       │              └──────────┬───────┘                         │
 │       │                         ▼                                 │
 │       │              ┌──────────────────┐                         │
 │       │              │  Graph Traversal  │ ← Neo4j Cypher         │
 │       │              │  (max depth 3)    │                         │
 │       │              └──────────┬───────┘                         │
 │       │                         │                                 │
 │       └──────────────┬──────────┘                                 │
 │                      ▼                                            │
 │               Context Fusion                                      │
 │          (vector docs + graph path)                               │
 │                      │                                            │
 │                      ▼                                            │
 │                  Reranker                                          │
 │                      │                                            │
 │                      ▼                                            │
 │             Parent Resolution                                      │
 │                      │                                            │
 │                      ▼                                            │
 │            LLM (Verifier + Summarizer)                            │
 │                      │                                            │
 │                      ▼                                            │
 │                  Response                                          │
 └──────────────────────────────────────────────────────────────────┘
```

### Alur Data Lengkap

```
INGESTION:
Dokumen → chunk → [embed → Milvus] + [LLM extract → Draft → Review → Neo4j]
                      │                      │
                vector search           graph traversal
                      │                      │
                      └── Context Fusion ───┘
                               │
                          Response lebih kaya
```

---

## 3. Entity & Relationship Model

### 3.1 Entity Types (HANYA 7 tipe — selektif)

| Tipe | Label Neo4j | Contoh | Kriteria |
|---|---|---|---|
| **Skill** | `Skill` | Python, Leadership, Data Analysis, Active Listening | Kompetensi yang bisa dipelajari/dikuasai |
| **Training** | `Training` | TNA, DNA, LVC, Lean ISD, Training Evaluation | Judul modul, pelatihan, course |
| **SOP** | `SOP` | SOP Cuti Tahunan, SOP SP1, SOP WFH | Prosedur operasional standar |
| **Department** | `Department` | HR, Finance, Operations, Learning & Development | Divisi, unit kerja |
| **Position** | `Position` | HRBP, Manager, Training Analyst, Supervisor | Jabatan, peran dalam organisasi |
| **Certificate** | `Certificate` | Certified Trainer, BNSP Assessor, HR Certification | Sertifikat resmi |
| **Policy** | `Policy` | WFH Policy, Overtime Policy, Leave Policy | Aturan, kebijakan perusahaan |

**Larangan**: JANGAN extract entity untuk:
- Kata kerja umum: "mengikuti", "melaksanakan", "membuat"
- Pelaku generik: "peserta", "karyawan", "perusahaan", "tim"
- Kata bantu: "dapat", "bisa", "harus", "akan"
- Waktu: "hari", "bulan", "tahun" (kecuali bagian dari kebijakan spesifik)

### 3.2 Relationship Types (HANYA 5 tipe)

| Relasi | Label Neo4j | Contoh Cypher | Makna |
|---|---|---|---|
| **Prerequisite** | `PREREQUISITE_FOR` | `(AnalisisData)-[:PREREQUISITE_FOR]->(MachineLearning)` | A harus dikuasai SEBELUM B |
| **Requires** | `REQUIRES` | `(Training:TNA)-[:REQUIRES]->(Skill:AnalisisData)` | Training membutuhkan skill tertentu |
| **Part Of** | `PART_OF` | `(DNA)-[:PART_OF]->(CLT_Module)` | A adalah komponen/sub-bagian dari B |
| **Governs** | `GOVERNS` | `(SOP_Cuti)-[:GOVERNS]->(Department:HR)` | Kebijakan berlaku untuk departemen/posisi |
| **Mentioned In** | `MENTIONED_IN` | `(Leadership)-[:MENTIONED_IN]->(docId:"123")` | Entity muncul di dokumen (otomatis) |

### 3.3 Neo4j Schema

```cypher
// Constraints — mencegah duplikat
CREATE CONSTRAINT entity_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;
CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type);

// Entity labels bersifat multiple — setiap entity punya :Entity + tipe spesifik
// CREATE (s:Entity:Skill {name: "Python", type: "Skill", doc_id: "doc-uuid"})
```

---

## 4. Struktur File

### 4.1 File Baru

| # | File | Deskripsi | Estimasi Baris |
|---|---|---|---|
| 1 | `backend/app/core/neo4j_client.py` | Neo4j connection singleton + lifecycle | ~60 |
| 2 | `backend/app/ingestion/graph_extractor.py` | LLM-based entity & relationship extraction | ~130 |
| 3 | `backend/app/retrieval/graph_traversal.py` | Cypher queries: lookup, traversal, path | ~110 |

### 4.2 File Diubah

| # | File | Perubahan | Baris Berubah |
|---|---|---|---|
| 4 | `backend/docker-compose.yml` | Tambah service `neo4j` | ~25 |
| 5 | `backend/app/core/config.py` | Tambah `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DRAFT_MODE` | ~6 |
| 6 | `backend/app/ingestion/pipeline.py` | Tambah step: `run_graph_extraction()` setelah embed | ~10 |
| 7 | `backend/app/temporal/activities.py` | Tambah activity `extract_graph_activity` | ~12 |
| 8 | `backend/app/temporal/workflows.py` | Tambah step graph di workflow | ~8 |
| 9 | `backend/app/agents/retriever.py` | Integrasi conditional graph traversal + context fusion | ~45 |
| 10 | `backend/pyproject.toml` | Tambah dependency `neo4j` | ~1 |

### 4.3 Total Perubahan

| Kategori | Baris |
|---|---|
| File baru | ~300 |
| File diubah | ~107 |
| **Total** | **~407 baris** |

---

## 5. Detail Implementasi

### 5.1 — Neo4j Container (`docker-compose.yml`)

Tambahkan setelah service `docling`:

```yaml
  neo4j:
    image: neo4j:5-community
    container_name: enterprisemind_neo4j
    environment:
      - NEO4J_AUTH=neo4j/enterprisemind
      - NEO4J_server_memory_heap_max__size=512M
      - NEO4J_server_memory_pagecache_size=256M
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "enterprisemind", "RETURN 1"]
      interval: 15s
      timeout: 10s
      retries: 10
      start_period: 30s
    restart: unless-stopped
    networks:
      - enterprisemind_net

volumes:
  # ... existing volumes ...
  neo4j_data:
    driver: local
  neo4j_logs:
    driver: local
```

**Catatan**: Heap 512MB + pagecache 256MB = ~768MB total. Ini minimum yang disarankan Neo4j. Jika laptop mulai swap, turunkan ke `256M` + `128M` (~384MB), tapi performa traversal akan turun.

---

### 5.2 — Neo4j Client (`core/neo4j_client.py`)

```python
"""
Neo4j Client — EnterpriseMind AI.

Singleton connection ke Neo4j graph database.
Lifecycle: connect pada first use, close saat shutdown.

Usage:
    from app.core.neo4j_client import get_neo4j
    driver = get_neo4j()
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS count")
"""

import logging
from neo4j import GraphDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

_driver = None

def get_neo4j() -> GraphDatabase.driver:
    global _driver
    if _driver is None:
        uri = settings.NEO4J_URI
        user = settings.NEO4J_USER
        password = settings.NEO4J_PASSWORD
        logger.info("Connecting to Neo4j: %s", uri)
        _driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_lifetime=3600,
            connection_timeout=10,
            max_connection_pool_size=5,
        )
        # Verify connection
        with _driver.session() as session:
            session.run("RETURN 1")
        logger.info("Neo4j connected successfully.")
    return _driver

async def close_neo4j():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
        logger.info("Neo4j connection closed.")

def verify_neo4j_health() -> bool:
    try:
        driver = get_neo4j()
        with driver.session() as session:
            result = session.run("MATCH (n:Entity) RETURN count(n) AS count")
            record = result.single()
            logger.info("Neo4j health OK: %d entities", record["count"] if record else 0)
        return True
    except Exception as e:
        logger.warning("Neo4j health check failed: %s", e)
        return False
```

---

### 5.3 — Graph Extractor (`ingestion/graph_extractor.py`)

```python
"""
Graph Entity Extractor — EnterpriseMind AI.

LLM-based extraction of entities and relationships from document chunks.
Output disimpan sebagai DRAFT terlebih dahulu, sebelum direview dan di-commit ke Neo4j.

Entity Types (HANYA 7): Skill, Training, SOP, Department, Position, Certificate, Policy
Relationship Types (HANYA 5): PREREQUISITE_FOR, REQUIRES, PART_OF, GOVERNS, MENTIONED_IN

Ref: GRAPH_PLAN.md §3
"""

import json
import logging
from typing import TypedDict

from app.core.llm_provider import get_llm

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES = {"Skill", "Training", "SOP", "Department", "Position", "Certificate", "Policy"}
VALID_RELATIONSHIP_TYPES = {"PREREQUISITE_FOR", "REQUIRES", "PART_OF", "GOVERNS", "MENTIONED_IN"}

EXTRACTION_PROMPT = """You are an entity extractor for HR training documents.

Extract ONLY entities and relationships that are EXPLICITLY stated in the text.

ENTITY TYPES (only these 7):
- Skill: competencies, abilities (e.g., Python, Leadership, Data Analysis, Active Listening)
- Training: module titles, courses (e.g., TNA, DNA, LVC, Lean ISD)
- SOP: procedures, standard operating procedures (e.g., SOP Cuti Tahunan, SOP SP1)
- Department: divisions, units (e.g., HR, Finance, Operations)
- Position: roles, job titles (e.g., HRBP, Manager, Training Analyst)
- Certificate: official certifications (e.g., Certified Trainer, BNSP Assessor)
- Policy: rules, company policies (e.g., WFH Policy, Leave Policy)

RELATIONSHIP TYPES (only these 5):
- PREREQUISITE_FOR: A must be learned/acquired before B (Skill → Skill, Training → Training)
- REQUIRES: Training needs Skill OR Policy requires Compliance (Training → Skill, Policy → Department)
- PART_OF: A is a component/sub-module of B (Training → Training)
- GOVERNS: Policy applies to Department/Position (Policy → Department, Policy → Position)
- MENTIONED_IN: Entity appears in this document (auto for all entities)

STRICT RULES:
- ONLY extract entities EXPLICITLY named in the text. Do NOT infer or guess.
- ONLY extract relationships EXPLICITLY stated. Do NOT assume connections.
- Do NOT extract: generic actors ("participant", "employee", "company"), helper verbs ("must", "should"), time units.
- If text mentions a Skill being needed for a Training → use REQUIRES.
- If text says "before learning X, you need Y" → use PREREQUISITE_FOR.

TEXT TO ANALYZE:
{text}

Respond ONLY with valid JSON:
{{
  "entities": [
    {{"name": "...", "type": "Skill"}}
  ],
  "relationships": [
    {{"source": "...", "target": "...", "type": "PREREQUISITE_FOR", "context": "..."}}
  ]
}}

If no entities found, return: {{"entities": [], "relationships": []}}"""


class ExtractedEntity(TypedDict):
    name: str
    type: str

class ExtractedRelationship(TypedDict):
    source: str
    target: str
    type: str
    context: str

class ExtractionResult(TypedDict):
    entities: list[ExtractedEntity]
    relationships: list[ExtractedRelationship]


def extract_graph_from_text(text: str, filename: str, document_id: str) -> ExtractionResult:
    """
    Extract entities and relationships from document text using LLM.

    Args:
        text: Extracted text from document (first 4000 chars for efficiency)
        filename: Source filename (for logging)
        document_id: UUID of the document (for MENTIONED_IN relationships)

    Returns:
        ExtractionResult with validated entities and relationships.

    Notes:
        - Uses GROQ_MODEL_FAST (8B) for speed and low cost
        - Only processes first 4000 chars to limit token usage
        - Output is validated against allowed types before returning
    """
    logger.info("[GraphExtract] Extracting from '%s' (%d chars)...", filename, len(text))

    truncated = text[:4000]

    llm = get_llm("fast", temperature=0.1, max_tokens=2048)
    prompt = EXTRACTION_PROMPT.format(text=truncated)

    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]

        result: ExtractionResult = json.loads(raw)

        # Validate and filter entities
        valid_entities = [
            {"name": e["name"].strip(), "type": e["type"]}
            for e in result.get("entities", [])
            if e.get("type") in VALID_ENTITY_TYPES and e.get("name", "").strip()
        ]

        # Validate and filter relationships
        valid_relationships = [
            {
                "source": r["source"].strip(),
                "target": r["target"].strip(),
                "type": r["type"],
                "context": r.get("context", "")[:200],
            }
            for r in result.get("relationships", [])
            if r.get("type") in VALID_RELATIONSHIP_TYPES
            and r.get("source", "").strip()
            and r.get("target", "").strip()
        ]

        # Auto-add MENTIONED_IN for all entities
        for entity in valid_entities:
            valid_relationships.append({
                "source": entity["name"],
                "target": document_id,
                "type": "MENTIONED_IN",
                "context": f"Document: {filename}",
            })

        logger.info(
            "[GraphExtract] '%s': %d entities, %d relationships",
            filename, len(valid_entities), len(valid_relationships),
        )

        return {
            "entities": valid_entities,
            "relationships": valid_relationships,
        }

    except Exception as e:
        logger.warning("[GraphExtract] Gagal extract '%s': %s", filename, e)
        return {"entities": [], "relationships": []}
```

---

### 5.4 — Graph Traversal (`retrieval/graph_traversal.py`)

```python
"""
Graph Traversal — EnterpriseMind AI.

Cypher queries untuk entity lookup, path traversal, dan multi-hop reasoning.

Hanya diaktifkan untuk intent: analytical, comparison, comprehensive, ambiguous.
Ref: GRAPH_PLAN.md §7
"""

import logging
from typing import Optional

from app.core.neo4j_client import get_neo4j

logger = logging.getLogger(__name__)

MAX_TRAVERSAL_DEPTH = 3


def extract_entities_from_query(query: str) -> list[str]:
    """
    Extract entity names from user query using LLM.

    Uses LLM 8B (fast, cheap) to identify which entities in Neo4j
    the user is asking about.

    Args:
        query: User's natural language query

    Returns:
        List of entity name strings found in the query.
        Empty list if no entities detected.

    Notes:
        - Cost: ~200ms, ~$0.00002 per query
        - Only called for analytical/comparison/comprehensive/ambiguous intents
        - Entity names must match EXACTLY with Neo4j (case-insensitive matching in Cypher)
    """
    from app.core.llm_provider import get_llm

    prompt = f"""Extract entity names from this query that match our knowledge base.

Our entity types: Skill, Training, SOP, Department, Position, Certificate, Policy

Query: {query}

Identify ALL entities mentioned. Return ONLY valid JSON array of strings.
Examples:
- "Apa hubungan Leadership dan Performance?" → ["Leadership", "Performance"]
- "Learning path menjadi HRBP" → ["HRBP"]
- "Berapa hari cuti tahunan?" → []

Respond: {{"entities": [...]}}"""

    try:
        llm = get_llm("fast", temperature=0.1, max_tokens=512)
        response = llm.invoke(prompt)
        raw = response.content.strip()

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]

        result = json.loads(raw)
        entities = result.get("entities", [])
        logger.info("[GraphQuery] Entities dari query '%s': %s", query[:50], entities)
        return entities

    except Exception as e:
        logger.warning("[GraphQuery] Gagal extract entities dari query: %s", e)
        return []


def find_entity_paths(entity_names: list[str], max_depth: int = MAX_TRAVERSAL_DEPTH) -> list[dict]:
    """
    Find paths between entities in the graph.

    For multiple entities: find connections between them.
    For single entity: find all related entities up to max_depth.

    Args:
        entity_names: List of entity name strings
        max_depth: Maximum traversal depth (default 3)

    Returns:
        List of path dicts with nodes, relationships, and depth.
        Empty list if no paths found or Neo4j unavailable.
    """
    if not entity_names:
        return []

    try:
        driver = get_neo4j()
    except Exception as e:
        logger.warning("[GraphTraversal] Neo4j tidak tersedia: %s", e)
        return []

    paths = []

    with driver.session() as session:
        if len(entity_names) >= 2:
            # Multi-entity: find paths between them
            paths.extend(_find_paths_between_entities(session, entity_names, max_depth))
        else:
            # Single entity: find all related paths
            paths.extend(_find_paths_from_entity(session, entity_names[0], max_depth))

    logger.info("[GraphTraversal] %d paths ditemukan untuk %s", len(paths), entity_names)
    return paths


def _find_paths_between_entities(session, entity_names: list[str], max_depth: int) -> list[dict]:
    """Find shortest paths connecting any pair of entities."""
    query = """
        MATCH path = (start:Entity)-[:PREREQUISITE_FOR|REQUIRES|PART_OF|GOVERNS*1..$max_depth]-(end:Entity)
        WHERE start.name IN $entities AND end.name IN $entities AND start.name < end.name
        RETURN 
            [node IN nodes(path) | node.name] AS node_names,
            [rel IN relationships(path) | type(rel)] AS rel_types,
            length(path) AS depth
        ORDER BY depth ASC
        LIMIT 10
    """

    result = session.run(query, entities=entity_names, max_depth=max_depth)
    return [
        {
            "path": record["node_names"],
            "relationships": record["rel_types"],
            "depth": record["depth"],
        }
        for record in result
    ]


def _find_paths_from_entity(session, entity_name: str, max_depth: int) -> list[dict]:
    """Find all paths radiating from a single entity."""
    query = """
        MATCH path = (start:Entity {name: $entity})-[rels:PREREQUISITE_FOR|REQUIRES|PART_OF|GOVERNS*1..$max_depth]-(end:Entity)
        RETURN 
            [node IN nodes(path) | node.name] AS node_names,
            [rel IN relationships(path) | type(rel)] AS rel_types,
            length(path) AS depth
        ORDER BY depth ASC
        LIMIT 20
    """

    result = session.run(query, entity=entity_name, max_depth=max_depth)
    return [
        {
            "path": record["node_names"],
            "relationships": record["rel_types"],
            "depth": record["depth"],
        }
        for record in result
    ]


def format_paths_for_context(paths: list[dict]) -> str:
    """
    Format graph paths menjadi konteks untuk LLM.

    Output contoh:
    [GRAPH RELATIONS]
    Python --[PREREQUISITE_FOR]--> Data Analysis --[PREREQUISITE_FOR]--> Machine Learning
    Leadership --[MENTIONED_IN]--> LVC_Module
    """
    if not paths:
        return ""

    lines = ["[GRAPH RELATIONS]"]
    seen = set()

    for p in paths:
        path_names = p.get("path", [])
        rel_types = p.get("relationships", [])
        if len(path_names) < 2:
            continue

        # Format: A --[REL]--> B --[REL]--> C
        parts = []
        for i in range(len(path_names) - 1):
            rel = rel_types[i] if i < len(rel_types) else "RELATES_TO"
            parts.append(f"{path_names[i]} --[{rel}]--> {path_names[i+1]}")

        line = " | ".join(parts)
        if line not in seen:
            seen.add(line)
            lines.append(f"  {line}")

    if len(lines) == 1:
        return ""

    return "\n".join(lines)
```

---

### 5.5 — Integrasi Pipeline Ingestion (`ingestion/pipeline.py`)

Tambahkan setelah step embedding:

```python
# Step 4: Graph extraction (LLM-based, synchronous)
graph_result = None
if extraction_result:
    text_to_extract = extraction_result[0]["text"] if isinstance(extraction_result, list) and extraction_result else str(extraction_result)
    graph_result = await run_graph_extraction(
        text=text_to_extract,
        filename=filename,
        document_id=document_id,
    )
```

```python
async def run_graph_extraction(text: str, filename: str, document_id: str) -> dict | None:
    """
    Extract entities and relationships for Knowledge Graph.
    In DRAFT mode: save to PostgreSQL for review.
    In LIVE mode: insert directly to Neo4j.
    """
    if not settings.NEO4J_ENABLED:
        logger.info("[GraphExtract] Neo4j disabled, skipping graph extraction.")
        return None

    from app.ingestion.graph_extractor import extract_graph_from_text

    result = await asyncio.to_thread(
        extract_graph_from_text, text, filename, document_id
    )

    if not result["entities"]:
        logger.info("[GraphExtract] Tidak ada entity ditemukan untuk '%s'", filename)
        return result

    if settings.NEO4J_DRAFT_MODE:
        # Save to PostgreSQL draft table (review before commit)
        await _save_graph_draft(document_id, filename, result)
        logger.info(
            "[GraphExtract] DRAFT saved: %d entities, %d relationships untuk '%s'",
            len(result["entities"]), len(result["relationships"]), filename,
        )
    else:
        # Insert directly to Neo4j
        await _commit_graph_to_neo4j(result)
        logger.info(
            "[GraphExtract] COMMITTED to Neo4j: %d entities, %d relationships untuk '%s'",
            len(result["entities"]), len(result["relationships"]), filename,
        )

    return result
```

---

### 5.6 — Integrasi Retriever (`agents/retriever.py`)

Tambahkan di `run_retriever_agent()`, setelah Step 3 (hybrid search) dan SEBELUM Step 4 (reranker):

```python
# Step 3b: Graph traversal (kondisional, hanya untuk intent tertentu)
graph_context = None
if intent_type in ("analytical", "comparison", "comprehensive", "ambiguous"):
    try:
        from app.retrieval.graph_traversal import (
            extract_entities_from_query,
            find_entity_paths,
            format_paths_for_context,
        )
        query_entities = extract_entities_from_query(query)
        if query_entities:
            paths = find_entity_paths(query_entities, max_depth=3)
            graph_context = format_paths_for_context(paths)
            if graph_context:
                logger.info("[Retriever] Graph context ditambahkan: %d path", len(paths))
    except Exception as e:
        logger.warning("[Retriever] Graph traversal gagal (fallback): %s", e)
```

Tambahkan graph_context ke retrieved_documents atau ke state untuk digunakan oleh Verifier/Summarizer. Graph path bisa ditambahkan sebagai pseudo-document dengan relevance_score tinggi (1.0).

---

## 6. Draft-then-Review Mechanism

### 6.1 Alur

```
Extraction → Simpan ke PostgreSQL (table: graph_drafts)
                 ↓
          [Admin Review via API/Frontend]
                 ↓
          Approve/Reject/Edit per entity
                 ↓
          Commit ke Neo4j
                 ↓
          Hapus dari draft
```

### 6.2 PostgreSQL Schema

```sql
-- Draft entities (menunggu review)
CREATE TABLE graph_drafts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    draft_data JSONB NOT NULL,  -- {entities: [...], relationships: [...]}
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'committed')),
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.3 API Endpoint Baru

| Method | Endpoint | Fungsi |
|---|---|---|
| `GET` | `/api/graph/drafts` | List semua draft pending |
| `GET` | `/api/graph/drafts/{id}` | Detail draft (entities + relationships) |
| `PUT` | `/api/graph/drafts/{id}/approve` | Approve → commit ke Neo4j |
| `PUT` | `/api/graph/drafts/{id}/reject` | Reject → hapus draft |
| `PUT` | `/api/graph/drafts/{id}/edit` | Edit entities/relationships sebelum commit |

### 6.4 Config Mode

```python
# config.py
NEO4J_DRAFT_MODE: bool = True  # Default: draft dulu, jangan langsung commit
```

Selama development, `NEO4J_DRAFT_MODE=True`. Setelah entity extraction quality divalidasi, set ke `False`.

---

## 7. Conditional Graph Traversal

### 7.1 Decision Matrix

```python
GRAPH_INTENTS = {"analytical", "comparison", "comprehensive", "ambiguous"}
SKIP_GRAPH_INTENTS = {"factual", "greeting", "action_request"}
```

### 7.2 Flow

```
query → intent_classifier
           │
           ▼
    ┌──────────────┐
    │ intent ∈     │ YES → extract_entities_from_query(query)
    │ GRAPH_INTENTS│         → find_entity_paths(entities)
    └──────┬───────┘         → format_paths_for_context(paths)
           │ NO                      │
           ▼                         ▼
    [Skip Graph]              [Fuse ke context]
           │                         │
           └──────────┬──────────────┘
                      ▼
              [Reranker + Parent Resolution + LLM]
```

### 7.3 Impact per Intent

| Intent | % Traffic | Graph? | Latency Tambahan |
|---|---|---|---|
| factual | ~50% | ❌ | 0ms |
| greeting | ~5% | ❌ | 0ms |
| action_request | ~10% | ❌ | 0ms |
| analytical | ~15% | ✅ | +~200ms (entity) + ~50ms (traversal) |
| comparison | ~5% | ✅ | +~200ms + ~50ms |
| comprehensive | ~10% | ✅ | +~200ms + ~100ms (lebih banyak traversal) |
| ambiguous | ~5% | ✅ | +~200ms + ~50ms |

**Rata-rata tambahan latency per query**: ~15% × 250ms = **~37.5ms** average. Tidak terasa oleh user.

---

## 8. Query Pipeline (Flow)

### 8.1 Skenario: "Apa learning path menjadi HRBP?"

```
1. USER: "Apa learning path menjadi HRBP?"
2. ORCHESTRATOR: intent = "comprehensive" (Tier 2 keyword: "path")
3. RETRIEVER:
   a. Hybrid search → Milvus → top-20 chunks
   b. Intent = comprehensive → aktifkan graph
   c. extract_entities_from_query("Apa learning path menjadi HRBP?")
      → ["HRBP"]
   d. find_entity_paths(["HRBP"], max_depth=3)
      → [
          {path: ["Training:DNA", "PREREQUISITE_FOR", "Training:TNA",
                   "PREREQUISITE_FOR", "Position:HRBP"],
           depth: 2},
          {path: ["Skill:Leadership", "REQUIRES", "Training:DNA",
                   "PART_OF", "Curriculum:HRBP", "REQUIRES", "Position:HRBP"],
           depth: 3}
        ]
   e. format_paths_for_context(paths)
      → "[GRAPH RELATIONS]\n  DNA --[PREREQUISITE_FOR]--> TNA --[PREREQUISITE_FOR]--> HRBP\n  Leadership --[REQUIRES]--> DNA --[PART_OF]--> HRBP Curriculum"
   f. Fuse: vector chunks + graph context → context pool
4. RERANKER: rerank semua context
5. PARENT RESOLUTION: resolve parents
6. SUMMARIZER: syntesis jawaban + graph context
7. OUTPUT:
   "Untuk menjadi HRBP, Anda perlu mengikuti:
   1. Pelatihan DNA (dasar)
   2. Pelatihan TNA (lanjutan)
   3. Serta menguasai skill Leadership

   [GRAPH RELATIONS]
   DNA --[PREREQUISITE_FOR]--> TNA --[PREREQUISITE_FOR]--> HRBP
   Leadership --[REQUIRES]--> DNA"
```

### 8.2 Skenario: "Apa itu SOP Cuti?"

```
1. USER: "Apa itu SOP Cuti?"
2. ORCHESTRATOR: intent = "factual" (Tier 2: question word "apa")
3. RETRIEVER:
   a. Intent = factual → SKIP graph
   b. Hybrid search → Milvus → top-k chunks
4. Flow normal tanpa graph
5. OUTPUT (sama seperti sekarang, tidak ada tambahan latency)
```

---

## 9. Resource Impact

### 9.1 Memory & Storage

| Resource | Sebelum | Sesudah | Delta |
|---|---|---|---|
| RAM (containers + Python) | ~3.1 GB | ~3.9 GB | **+~768 MB** |
| RAM (Windows + browser) | ~4.9 GB sisa | ~4.1 GB sisa | **-768 MB** |
| Disk (Docker volumes) | ~2 GB | ~2.5 GB | **+~500 MB** |
| Docker containers | 7 | 8 | **+1** |

### 9.2 Latency

| Skenario | Sebelum | Sesudah | Delta |
|---|---|---|---|
| Query factual (60% traffic) | ~15-30 detik | ~15-30 detik | **0%** |
| Query analytical (30% traffic) | ~20-45 detik | ~20-45 detik + ~250ms | **+~1%** |
| Query comprehensive (10% traffic) | ~30-60 detik | ~30-60 detik + ~300ms | **+~1%** |
| Ingestion per dokumen | ~63 detik | ~68 detik | **+~8%** |

### 9.3 Cost (Groq API)

| Item | Jumlah | Biaya |
|---|---|---|
| Extraction per dokumen | 1 call (8B, ~3500 token) | ~$0.00007 |
| Extraction untuk 13 dokumen | 13 calls | **~$0.0009** |
| Entity detection per query | per query analytical | ~$0.00002 per query |
| **Total estimasi** | | **< $0.01** |

---

## 10. Trade-off & Risiko

### 10.1 Matriks Risiko

| Risiko | Probabilitas | Dampak | Mitigasi |
|---|---|---|---|
| **RAM tidak cukup → swap → sistem lambat** | 🟡 Sedang | 🔴 Tinggi | Heap minimum 512M. Jika swap terjadi: turunkan ke 256M atau nonaktifkan Neo4j via `NEO4J_ENABLED=false` |
| **LLM hallucinate entities → graph tercemar** | 🟡 Sedang | 🟡 Sedang | **Draft mode** — extract disimpan dulu, review sebelum commit. Jangan LIVE mode di awal |
| **Entity extraction tidak konsisten antar dokumen** | 🟡 Sedang | 🟡 Sedang | Prompt engineering iterative. Review hasil draft 13 dokumen, perbaiki prompt, re-extract |
| **Graph traversal lambat (deep path + banyak entity)** | 🟢 Rendah | 🟢 Rendah | `max_depth=3`, `LIMIT` di Cypher, index di `name` dan `type` |
| **Neo4j container crash** | 🟢 Rendah | 🟡 Sedang | Fallback: kalo Neo4j unreachable, query tetap jalan tanpa graph context |
| **Cypher injection** | 🟢 Rendah | 🔴 Tinggi | Parameterized queries (`$entities`, bukan f-string). Tidak ada拼接 langsung |

### 10.2 Trade-off Utama

| Keuntungan | Pengorbanan |
|---|---|
| Multi-hop reasoning (learning path) | +768MB RAM untuk Neo4j |
| Jawaban lintas dokumen yang eksplisit | +~5 detik ingestion per dokumen (LLM extraction) |
| LLM tahu relasi antar konsep | Risiko graph tercemar entity palsu (dim mitigasi oleh draft mode) |
| Portfolio/arsitektur modern | +1 container, +~400 baris kode, maintenance overhead |

### 10.3 Kapan Harus Rollback?

Segera nonaktifkan Neo4j jika:
1. **Laptop mulai swap** — semua container jadi lambat. Set `NEO4J_ENABLED=false` di `.env`.
2. **Entity extraction quality < 70%** — setelah review draft, jika terlalu banyak entity salah, perbaiki prompt dulu sebelum live.
3. **Query latency naik > 2 detik** (bukan 200ms) — ada yang salah di traversal query.

### 10.4 Rollback Steps

```bash
# 1. Nonaktifkan tanpa hapus container
echo "NEO4J_ENABLED=false" >> .env

# 2. Hapus container + volume (jika perlu)
docker compose stop neo4j
docker compose rm neo4j
docker volume rm backend_neo4j_data backend_neo4j_logs

# 3. Hapus service dari docker-compose.yml
# Hapus baris neo4j service

# 4. Revert code changes
git checkout -- backend/app/core/neo4j_client.py
git checkout -- backend/app/ingestion/graph_extractor.py
git checkout -- backend/app/retrieval/graph_traversal.py
git checkout -- backend/app/core/config.py
git checkout -- backend/app/ingestion/pipeline.py
git checkout -- backend/app/agents/retriever.py
git checkout -- backend/docker-compose.yml
```

---

## 11. Rollback Plan

### 11.1 Safe Rollback (tanpa hapus data)

```python
# .env
NEO4J_ENABLED=false
```

Semua kode graph akan di-skip:
- `pipeline.py` — skip graph extraction
- `retriever.py` — skip graph traversal
- Neo4j container tetap jalan, data aman

### 11.2 Hard Rollback (hapus semua)

```bash
docker compose down neo4j
docker volume rm backend_neo4j_data
# Hapus service dari docker-compose.yml
# Revert code via git
```

---

## 12. Urutan Eksekusi

### Fase 1: Infrastructure (30 menit)

| Step | Action | Durasi |
|---|---|---|
| 1.1 | `uv add neo4j` — install driver | 1 menit |
| 1.2 | Tambah Neo4j service di `docker-compose.yml` | 5 menit |
| 1.3 | `docker compose up -d neo4j` — start container | 5 menit |
| 1.4 | Verifikasi: `cypher-shell -u neo4j -p enterprisemind "RETURN 1"` | 1 menit |

### Fase 2: Backend Core (30 menit)

| Step | Action | Durasi |
|---|---|---|
| 2.1 | Tambah config di `config.py` (4 env vars) | 3 menit |
| 2.2 | Buat `core/neo4j_client.py` | 10 menit |
| 2.3 | Update `pyproject.toml` | 1 menit |
| 2.4 | Test: `python -c "from app.core.neo4j_client import get_neo4j; print('OK')"` | 5 menit |

### Fase 3: Ingestion Graph Extraction (40 menit)

| Step | Action | Durasi |
|---|---|---|
| 3.1 | Buat `ingestion/graph_extractor.py` | 20 menit |
| 3.2 | Update `ingestion/pipeline.py` + activities + workflows | 15 menit |
| 3.3 | Buat tabel `graph_drafts` di PostgreSQL | 5 menit |

### Fase 4: Query Graph Traversal (30 menit)

| Step | Action | Durasi |
|---|---|---|
| 4.1 | Buat `retrieval/graph_traversal.py` | 20 menit |
| 4.2 | Update `agents/retriever.py` — conditional integration | 10 menit |

### Fase 5: Testing & Review (30 menit)

| Step | Action | Durasi |
|---|---|---|
| 5.1 | Upload 1 dokumen → cek draft di PostgreSQL | 5 menit |
| 5.2 | Review entity quality → perbaiki prompt jika perlu | 15 menit |
| 5.3 | Approve draft → commit ke Neo4j | 5 menit |
| 5.4 | Test query analytical → verifikasi graph context masuk | 5 menit |

### Total Timeline: ~2.5 jam

```
Fase 1 (infra):      ██████████████░░░░░░░░░░ 30 menit
Fase 2 (core):       ██████████████████░░░░░░ 30 menit
Fase 3 (ingestion):  ██████████████████████░░ 40 menit
Fase 4 (query):      ████████████████████░░░░ 30 menit
Fase 5 (testing):    ████████████████████████ 30 menit
                    ─────────────────────────
TOTAL:              2 jam 40 menit
```
