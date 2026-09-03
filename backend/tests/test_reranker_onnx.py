"""
Parity & sanity tests — ONNX Reranker (plan_optimasi.md Fase 3A).

Strategi:
1. Tes struktur (tanpa dependency berat): modul bisa di-import dan rerank_chunks
   berperilaku sama (fallback aman) — jalan di CI ringan.
2. Tes parity (skip bila artifact/onnxruntime belum ada): skor & urutan ONNX
   konsisten; dijalankan manual setelah tools/export_reranker_onnx.py.

Jalankan tes parity eksplisit:
    uv run --group torch pytest tests/test_reranker_onnx.py -v
"""

import importlib.util
import os
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# 1. Struktur / import safety (selalu dijalankan)
# --------------------------------------------------------------------------- #
def test_module_import_safe_without_heavy_deps():
    """Import app.retrieval.reranker TIDAK boleh memicu torch/onnx/sentence-transformers."""
    import sys

    # Pastikan tidak ada dependency berat yang ter-import saat modul dimuat
    for heavy in ("torch", "onnxruntime", "sentence_transformers", "transformers"):
        sys.modules.pop(heavy, None)

    module = importlib.import_module("app.retrieval.reranker")
    assert hasattr(module, "rerank_chunks")
    assert hasattr(module, "OnnxReranker")
    assert hasattr(module, "TorchReranker")

    assert module._reranker is None  # lazy: belum di-load


def test_rerank_chunks_empty():
    from app.retrieval.reranker import rerank_chunks

    assert rerank_chunks("query", []) == []


# --------------------------------------------------------------------------- #
# 2. Parity ONNX vs torch (skip bila artifact belum ada)
# --------------------------------------------------------------------------- #
def _onnx_artifact_available() -> bool:
    if os.getenv("RERANKER_ONNX_DIR"):
        p = Path(os.getenv("RERANKER_ONNX_DIR"))
    else:
        hf_home = os.getenv("HF_HOME", "").strip()
        base = Path(hf_home) if hf_home else BACKEND_DIR / "model_cache"
        p = base / "onnx" / "reranker-bge-reranker-v2-m3"
    return (p / "model.onnx").exists() and (p / "tokenizer.json").exists()


ARTIFACT_REASON = "ONNX artifact belum ada — jalankan tools/export_reranker_onnx.py dulu"

@pytest.mark.skipif(importlib.util.find_spec("onnxruntime") is None, reason="onnxruntime tidak terpasang")
@pytest.mark.skipif(not _onnx_artifact_available(), reason=ARTIFACT_REASON)
def test_onnx_reranker_predict_shape_and_range():
    from app.retrieval.reranker import OnnxReranker, reranker_onnx_dir

    reranker = OnnxReranker(reranker_onnx_dir() / "model.onnx", max_length=256)
    scores = reranker.predict([
        ("apa itu vector database", "vector database menyimpan embedding teks"),
        ("apa itu vector database", "resep masakan rendang sapi"),
    ])
    assert len(scores) == 2
    assert all(0.0 <= s <= 1.0 for s in scores)
    # Dokumen relevan harus diskor lebih tinggi daripada yang tidak relevan
    assert scores[0] > scores[1]


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch tidak terpasang")
@pytest.mark.skipif(not _onnx_artifact_available(), reason=ARTIFACT_REASON)
def test_rerank_ordering_torch_vs_onnx():
    """Urutan top-k via ONNX harus sama dengan torch (regresi kualitas)."""
    from app.retrieval.reranker import OnnxReranker, TorchReranker, reranker_onnx_dir

    query = "Bagaimana cara reset password user?"
    docs = [
        "Panduan reset password: Pengaturan > Keamanan > Reset Password.",
        "Laporan keuangan kuartal III tumbuh 12 persen.",
        "Cara mengganti email notifikasi di profil pengguna.",
        "Vector database untuk semantic search di Milvus.",
        "Reset password otomatis dikirim via email setiap 90 hari.",
    ]
    pairs = [(query, d) for d in docs]

    onnx = OnnxReranker(reranker_onnx_dir() / "model.onnx", max_length=256)
    torch_r = TorchReranker("BAAI/bge-reranker-v2-m3", max_length=256)

    scores_onnx = onnx.predict(pairs)
    scores_torch = torch_r.predict(pairs)

    order_onnx = [i for i, _ in sorted(enumerate(scores_onnx), key=lambda x: -x[1])]
    order_torch = [i for i, _ in sorted(enumerate(scores_torch), key=lambda x: -x[1])]
    assert order_onnx == order_torch, f"Urutan beda: onnx={order_onnx}, torch={order_torch}"
