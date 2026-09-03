"""
Parity & sanity tests — ONNX Embedding (plan_optimasi.md Fase 3B).

Strategi:
1. Tes struktur (tanpa dependency berat): modul bisa di-import tanpa
   torch/transformers/sentence-transformers (import safety Fase 3C).
2. Tes parity (skip bila artifact/onnxruntime belum ada): cosine similarity
   tinggi antara embedding ONNX dan torch, konsisten dgn re-index.

Jalankan tes parity eksplisit (setelah tools/export_embedding_onnx.py):
    uv run --extra torch pytest tests/test_embedding_onnx.py -v
"""
import importlib.util
import os
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# 1. Struktur / import safety (selalu dijalankan)
# --------------------------------------------------------------------------- #
def test_embedder_import_safe_without_heavy_deps():
    """Import app.ingestion.embedder TIDAK memicu torch/transformers/langchain-huggingface."""
    import sys

    for heavy in ("torch", "transformers", "sentence_transformers", "langchain_huggingface"):
        sys.modules.pop(heavy, None)

    module = importlib.import_module("app.ingestion.embedder")
    assert hasattr(module, "OnnxEmbedding")
    assert hasattr(module, "get_embedding_model")
    assert hasattr(module, "get_vector_store")
    assert module._embedding_model is None  # lazy


def test_onnx_embedding_duck_type_contract():
    """Objek OnnxEmbedding menyediakan kontrak LangChain Embeddings.

    Tanpa artifact, konstruktor OnnxEmbedding harus gagal dgn pesan jelas —
    bukan import error (struktur tetap teruji).
    """
    from app.ingestion.embedder import OnnxEmbedding

    # Method ada pada class (tanpa instantiate model)
    assert callable(OnnxEmbedding.embed_documents)
    assert callable(OnnxEmbedding.embed_query)


# --------------------------------------------------------------------------- #
# 2. Parity ONNX vs torch (skip bila artifact belum ada)
# --------------------------------------------------------------------------- #
def _onnx_artifact_available() -> bool:
    if os.getenv("EMBEDDING_ONNX_DIR"):
        p = Path(os.getenv("EMBEDDING_ONNX_DIR"))
    else:
        hf_home = os.getenv("HF_HOME", "").strip()
        base = Path(hf_home) if hf_home else BACKEND_DIR / "model_cache"
        p = base / "onnx" / "embedding-bge-m3"
    return (p / "model.onnx").exists() and (p / "tokenizer.json").exists()


ARTIFACT_REASON = "ONNX artifact belum ada — jalankan tools/export_embedding_onnx.py dulu"


@pytest.mark.skipif(importlib.util.find_spec("onnxruntime") is None, reason="onnxruntime tidak terpasang")
@pytest.mark.skipif(not _onnx_artifact_available(), reason=ARTIFACT_REASON)
def test_onnx_embedding_dim_norm_and_query():
    from app.ingestion.embedder import OnnxEmbedding, embedding_onnx_dir

    emb = OnnxEmbedding(embedding_onnx_dir() / "model.onnx", threads=2)
    texts = ["apa itu vector database", "cara reset password user"]
    vectors = emb.embed_documents(texts)
    assert len(vectors) == 2
    for v in vectors:
        assert len(v) == 1024  # BGE-M3 dimension
        norm = sum(x * x for x in v) ** 0.5
        assert abs(norm - 1.0) < 1e-3  # L2 normalized

    q = emb.embed_query("apa itu vector database")
    assert len(q) == 1024
    sim = sum(a * b for a, b in zip(q, vectors[0]))
    assert sim > 0.9  # pertanyaan identik → kosinus tinggi


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch tidak terpasang")
@pytest.mark.skipif(not _onnx_artifact_available(), reason=ARTIFACT_REASON)
def test_embedding_parity_torch_vs_onnx():
    """Embedding ONNX ≈ torch (CLS+L2) — regresi kualitas saat re-index."""
    from app.ingestion.embedder import OnnxEmbedding, TorchEmbedding, embedding_onnx_dir

    texts = [
        "EnterpriseMind adalah knowledge management dengan agentic RAG.",
        "Bagaimana cara reset password user?",
        "Laporan keuangan kuartal ketiga tumbuh 12 persen.",
    ]

    onnx = OnnxEmbedding(embedding_onnx_dir() / "model.onnx", threads=2)
    torch_e = TorchEmbedding("BAAI/bge-m3")

    vec_onnx = onnx.embed_documents(texts)
    vec_torch = torch_e.embed_documents(texts)

    for a, b in zip(vec_onnx, vec_torch):
        sim = sum(x * y for x, y in zip(a, b))
        assert sim > 0.99, f"Cosinus torch-vs-onnx terlalu rendah: {sim:.5f}"
