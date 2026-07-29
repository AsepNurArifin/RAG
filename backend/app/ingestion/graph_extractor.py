"""
Graph Entity Extractor — EnterpriseMind AI.

LLM-based extraction of entities and relationships from document chunks.
Output disimpan sebagai DRAFT terlebih dahulu, sebelum direview dan di-commit ke Neo4j.

Entity Types (HANYA 7): Skill, Training, SOP, Department, Position, Certificate, Policy
Relationship Types (HANYA 5): PREREQUISITE_FOR, REQUIRES, PART_OF, GOVERNS, MENTIONED_IN

Ref: GRAPH_PLAN.md §5.3
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
    logger.info("[GraphExtract] Extracting from '%s' (%d chars)...", filename, len(text))

    truncated = text[:4000]

    llm = get_llm("fast", temperature=0.1, max_tokens=2048)
    prompt = EXTRACTION_PROMPT.format(text=truncated)

    try:
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

        result: ExtractionResult = json.loads(raw)

        valid_entities = [
            {"name": e["name"].strip(), "type": e["type"]}
            for e in result.get("entities", [])
            if e.get("type") in VALID_ENTITY_TYPES and e.get("name", "").strip()
        ]

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

        doc_id_str = str(document_id)
        for entity in valid_entities:
            valid_relationships.append({
                "source": entity["name"],
                "target": doc_id_str,
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
