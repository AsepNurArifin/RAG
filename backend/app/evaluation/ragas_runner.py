"""
RAGAS Runner — EnterpriseMind AI.

Mengeksekusi evaluasi dan menghitung metrik RAGAS menggunakan
Gemini 2.5 Flash sebagai evaluator.

Ref: SRS_PRD.md FR7.2, FR7.3 — evaluasi otomatis dengan RAGAS
"""
import logging

import pandas as pd
from datasets import Dataset
from langchain_groq import ChatGroq
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper

from app.core.config import settings

logger = logging.getLogger(__name__)

_METRICS_CACHE = None


def _get_metrics():
    global _METRICS_CACHE
    if _METRICS_CACHE is not None:
        return _METRICS_CACHE

    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    evaluator_llm = ChatGroq(
        model=settings.GROQ_MODEL_REASONING,
        api_key=settings.GROQ_API_KEY,
        temperature=0.0,
    )
    ragas_llm = LangchainLLMWrapper(evaluator_llm)

    _METRICS_CACHE = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]

    for m in _METRICS_CACHE:
        if hasattr(m, "llm"):
            m.llm = ragas_llm
        if hasattr(m, "embeddings"):
            from langchain_huggingface import HuggingFaceEmbeddings
            m.embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"trust_remote_code": True},
            )

    return _METRICS_CACHE


async def run_evaluation(graph_runner_func, test_set: list[dict]) -> dict | None:
    """
    Jalankan evaluasi RAGAS pada test set.

    Args:
        graph_runner_func: Fungsi async yang menerima (question: str)
            dan mengembalikan dict berisi 'answer' (str) dan
            'contexts' (list of str).
        test_set: List of dict dengan keys 'question' dan 'ground_truth'.

    Returns:
        Dict hasil evaluasi RAGAS, atau None jika gagal.
    """
    questions = []
    ground_truths = []
    answers = []
    contexts = []

    total = len(test_set)

    for i, item in enumerate(test_set):
        question = item["question"]
        gt = item["ground_truth"]

        logger.info("[%d/%d] Memproses: %s...", i + 1, total, question[:60])
        try:
            result = await graph_runner_func(question)

            ans = result.get("answer", "")
            ctxs = result.get("contexts", [])

            questions.append(question)
            ground_truths.append([gt])
            answers.append(ans)
            contexts.append(ctxs)
        except Exception as e:
            logger.error("Error pada '%s...': %s", question[:40], e)

    if not questions:
        logger.error("Tidak ada pertanyaan yang berhasil diproses")
        return None

    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truths": ground_truths,
    }

    dataset = Dataset.from_dict(data)
    metrics = _get_metrics()

    logger.info("Menghitung metrik RAGAS (%d samples)...", len(questions))
    try:
        result = evaluate(dataset=dataset, metrics=metrics)

        df = result.to_pandas()
        df.to_csv("ragas_evaluation_results.csv", index=False)
        logger.info("Hasil disimpan ke ragas_evaluation_results.csv")

        scores = dict(result)
        logger.info("=== Ringkasan Skor RAGAS ===")
        for k, v in scores.items():
            if isinstance(v, (int, float)):
                logger.info("  %s: %.4f", k, v)

        return {"scores": scores, "dataframe": df}

    except Exception as e:
        logger.exception("Evaluasi RAGAS gagal: %s", e)
        return None


async def run_comparison_evaluation(
    agentic_runner_func,
    naive_runner_func,
    test_set: list[dict],
) -> dict | None:
    """
    Jalankan evaluasi perbandingan Naive RAG vs Agentic RAG.

    Returns:
        Dict dengan key 'agentic' dan 'naive' masing-masing
        berisi hasil RAGAS evaluation.
    """
    logger.info("=== Evaluasi Agentic RAG ===")
    agentic_result = await run_evaluation(agentic_runner_func, test_set)

    logger.info("=== Evaluasi Naive RAG ===")
    naive_result = await run_evaluation(naive_runner_func, test_set)

    comparison = {
        "agentic": agentic_result["scores"] if agentic_result else None,
        "naive": naive_result["scores"] if naive_result else None,
    }

    agentic_df = agentic_result.get("dataframe") if agentic_result else None
    naive_df = naive_result.get("dataframe") if naive_result else None
    if agentic_df is not None:
        agentic_df.to_csv("ragas_agentic_results.csv", index=False)
    if naive_df is not None:
        naive_df.to_csv("ragas_naive_results.csv", index=False)

    logger.info("\n=== Perbandingan Skor ===")
    if comparison["agentic"] and comparison["naive"]:
        for key in comparison["agentic"]:
            a_val = comparison["agentic"].get(key, "N/A")
            n_val = comparison["naive"].get(key, "N/A")
            if isinstance(a_val, (int, float)) and isinstance(
                n_val, (int, float)
            ):
                delta = a_val - n_val
                logger.info(
                    "  %s: Agentic=%.4f | Naive=%.4f | Δ=%+.4f",
                    key,
                    a_val,
                    n_val,
                    delta,
                )

    return comparison
