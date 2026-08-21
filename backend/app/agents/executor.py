"""
Executor / Action Agent — EnterpriseMind AI.

Menghasilkan action items (to-do list, draft email, rekomendasi tindakan)
ketika intent dari Orchestrator = action_request.

Ref: FR2.7 di SRS_PRD.md, PROMPT_LIBRARY.md Executor v1
Model: FAST (gpt-oss-20b) — task standar

PENTING: Agent ini TIDAK pernah mengeksekusi tindakan nyata.
Hanya menghasilkan draft untuk direview manusia.

Usage:
    Dipanggil oleh graph/build_graph.py, BUKAN langsung.
    Hanya aktif jika intent == "action_request".
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.agents import EXECUTOR_PROMPT
from app.core.llm_provider import get_llm, invoke_llm_instrumented
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def run_executor_agent(state: GraphState) -> GraphState:
    """
    Generate action items untuk review manusia.

    Args:
        state: State LangGraph, berisi query, final_answer, dan
               retrieved_documents.

    Returns:
        State yang diperbarui dengan action_items.

    Side effects:
        - API call ke Groq (model fast) via LangChain.
    """
    query = state.get("query", "")
    final_answer = state.get("final_answer", "")
    documents = state.get("retrieved_documents", [])
    session_id = state.get("session_id", "")

    logger.info("[Executor] Generating action items untuk: '%s...'", query[:80])

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", EXECUTOR_PROMPT),
            (
                "human",
                "Query pengguna (permintaan tindakan): {query}\n\n"
                "Konteks dari analisis sebelumnya:\n{context}\n\n"
                "Buat action items yang konkret dan actionable. "
                "Respond dalam format JSON.",
            ),
        ]
    )

    llm = get_llm("fast")

    chain = prompt | llm
    response, _ = invoke_llm_instrumented(
        chain=chain,
        input_data={
            "query": query,
            "context": final_answer[:1000],
        },
        agent_name="executor",
        task_type="fast",
        max_retries=2,
    )

    # Parse response
    try:
        action_items = _parse_executor_response(response.content)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(
            "[Executor] Gagal parse response, fallback: %s", e
        )
        action_items = [
            {
                "action_type": "recommendation",
                "draft_content": response.content,
                "requires_human_review": True,
            }
        ]

    logger.info(
        "[Executor] Generated %d action items", len(action_items)
    )

    return {
        **state,
        "action_items": action_items,
    }


def _parse_executor_response(response_text: str) -> list[dict]:
    """Parse JSON response dari Executor LLM."""
    text = response_text.strip()

    # Extract JSON
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    result = json.loads(text)

    # Pastikan selalu ada requires_human_review = True
    if isinstance(result, dict):
        result["requires_human_review"] = True
        return [result]
    elif isinstance(result, list):
        for item in result:
            item["requires_human_review"] = True
        return result

    return [
        {
            "action_type": "unknown",
            "draft_content": str(result),
            "requires_human_review": True,
        }
    ]
