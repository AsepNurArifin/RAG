"""
Evaluation module — EnterpriseMind AI.

Offline evaluation framework + RAGAS integration.

Modules:
- evaluate.py: Custom offline evaluation (Recall@20, Context Precision, latency, cost)
- ragas_runner.py: RAGAS evaluation (faithfulness, answer relevancy)
- test_set.py: Test set untuk evaluasi teknis sistem (50 pertanyaan)
- test_set.json: Test set untuk evaluasi domain knowledge (100 pertanyaan)

Usage:
    # Custom offline evaluation
    python -m app.evaluation.evaluate --baseline
    python -m app.evaluation.evaluate --compare baseline.json --current eval.json
    
    # RAGAS evaluation
    from app.evaluation.ragas_runner import run_evaluation
"""
