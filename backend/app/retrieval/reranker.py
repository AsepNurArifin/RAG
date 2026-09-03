"""
Cross-Encoder Reranker — EnterpriseMind AI.

Rerank retrieved documents menggunakan cross-encoder untuk meningkatkan
Context Precision. Model: BAAI/bge-reranker-v2-m3 (self-hosted, NON-NEGOTIABLE).

Runtime (plan_optimasi.md Fase 3A):
- Backend default "onnx": model INT8-quantized dijalankan via onnxruntime +
  tokenizers (ringan, tanpa torch / sentence-transformers).
- Fallback "pytorch": sentence-transformers CrossEncoder — hanya dipakai saat
  berkas ONNX belum tersedia (pasca-clone / dev / ekspor ulang).
- Backend & perilaku lama (rerank_chunks signature, reranker_score) TIDAK berubah.

Rerank model BAAI/bge-reranker-v2-m3 adalah cross-encoder multilingual
(berbasis XLM-R/bge-m3); pasangan input [query, dokumen] diproses bersama
sehingga skor relevansi lebih akurat daripada bi-encoder.

Singleton pattern untuk lazy loading model (tidak import torch/onnx di modul
top-level → startup cepat & aman saat dependency torch tidak terpasang).
"""
import logging
import os
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_reranker = None
_reranker_backend: str | None = None  # backend yang berhasil di-load ("onnx"/"pytorch")


# --------------------------------------------------------------------------- #
# Lokasi artifact ONNX
# --------------------------------------------------------------------------- #
def _hf_cache_base() -> Path:
    """Direktori cache model. HF_HOME di set di compose (VPS: /app/model_cache)."""
    hf_home = os.getenv("HF_HOME", "").strip()
    if hf_home:
        return Path(hf_home)
    # Dev default: <repo>/backend/model_cache
    return Path(__file__).resolve().parents[2] / "model_cache"


def reranker_onnx_dir() -> Path:
    """Direktori artifact ONNX untuk model reranker (export_reranker_onnx.py)."""
    if settings.RERANKER_ONNX_DIR:
        return Path(settings.RERANKER_ONNX_DIR)
    slug = settings.RERANKER_MODEL.rstrip("/").split("/")[-1]
    return _hf_cache_base() / "onnx" / f"reranker-{slug}"


# --------------------------------------------------------------------------- #
# Backend ONNX (produksi — default)
# --------------------------------------------------------------------------- #
class OnnxReranker:
    """Cross-encoder reranker via onnxruntime (INT8 quantized) + tokenizers.

    Artifact yang dibutuhkan di reranker_onnx_dir() (dibuat oleh
    tools/export_reranker_onnx.py):
        model.onnx          — model INT8 dynamic-quantized
        tokenizer.json      — fast tokenizer (format tokenizers)
    """

    def __init__(self, model_path: Path, max_length: int = 256, threads: int = 0):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        if not model_path.exists():
            raise FileNotFoundError(f"ONNX reranker tidak ditemukan: {model_path}")

        tokenizer_json = model_path.parent / "tokenizer.json"
        if not tokenizer_json.exists():
            raise FileNotFoundError(f"tokenizer.json tidak ditemukan di {model_path.parent}")

        # --- Session options: thread + optimasi (CPU only) ---
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        if threads and threads > 0:
            so.intra_op_num_threads = threads
            so.inter_op_num_threads = 1

        self._session = ort.InferenceSession(
            str(model_path), sess_options=so, providers=["CPUExecutionProvider"]
        )

        # --- Tokenizer (pair encoding: [CLS] q [SEP] d [SEP]) ---
        self._tok = Tokenizer.from_file(str(tokenizer_json))
        self._tok.enable_truncation(max_length=max_length)
        pad_token = _resolve_pad_token(self._tok, model_path.parent)
        pad_id = self._tok.token_to_id(pad_token)
        self._tok.enable_padding(pad_id=pad_id, pad_token=pad_token)

        self._input_names = [i.name for i in self._session.get_inputs()]
        self._output_name = self._session.get_outputs()[0].name
        logger.info(
            "ONNX reranker loaded: %s (inputs=%s, threads=%s)",
            model_path, self._input_names, threads or "auto",
        )

    def predict(self, pairs: list[tuple[str, str]]):
        """Skor relevansi untuk pasangan (query, dokumen). Mengembalikan list float."""
        if not pairs:
            return []
        encoded = self._tok.encode_batch([(q, d) for (q, d) in pairs])
        feed = {
            "input_ids": [e.ids for e in encoded],
            "attention_mask": [e.attention_mask for e in encoded],
        }
        if "token_type_ids" in self._input_names:
            feed["token_type_ids"] = [e.type_ids for e in encoded]

        import numpy as np
        logits = self._session.run([self._output_name], feed)[0]  # (n, 1)
        scores = np.asarray(logits).reshape(-1).astype(float)
        # Model dilatih dengan BCE — terapkan sigmoid agar setara predict()
        # sentence-transformers (CrossEncoder klasifikasi biner).
        scores = 1.0 / (1.0 + np.exp(-scores))
        return scores.tolist()


def _resolve_pad_token(tok, model_dir: Path) -> str:
    """Pad token: cek tokenizer_config.json, lalu fallback token umum."""
    try:
        import json
        cfg = json.loads((model_dir / "tokenizer_config.json").read_text(encoding="utf-8"))
        pad = cfg.get("pad_token")
        if pad and tok.token_to_id(pad) is not None:
            return pad
    except Exception:
        pass
    for candidate in ("<pad>", "[PAD]", "<s>", "<unk>"):
        if tok.token_to_id(candidate) is not None:
            return candidate
    raise RuntimeError("Tidak dapat menentukan pad token untuk tokenizer reranker.")


# --------------------------------------------------------------------------- #
# Backend PyTorch (dev/fallback — hanya saat ONNX belum tersedia)
# --------------------------------------------------------------------------- #
class TorchReranker:
    """Wrapper sentence-transformers CrossEncoder — perilaku runtime lama."""

    def __init__(self, model_name: str, max_length: int = 256):
        from sentence_transformers import CrossEncoder
        logger.info("Initializing torch reranker model: %s...", model_name)
        self._model = CrossEncoder(model_name, max_length=max_length)
        logger.info("Torch reranker loaded.")

    def predict(self, pairs: list[tuple[str, str]]):
        return self._model.predict(pairs)


# --------------------------------------------------------------------------- #
# Singleton
# --------------------------------------------------------------------------- #
def _load_onnx():
    model_dir = reranker_onnx_dir()
    model_path = model_dir / "model.onnx"
    if not model_path.exists():
        return None
    return OnnxReranker(
        model_path,
        max_length=settings.RERANKER_MAX_LENGTH,
        threads=settings.ORT_THREADS,
    )


def get_reranker():
    """Get cross-encoder reranker instance (singleton, lazy load).

    Prioritas backend:
      1. "onnx"    (default) — artifact ONNX; bila tidak ada & torch tersedia,
         fallback sementara ke torch + warning (agar dev tidak patah).
      2. "pytorch" — sentence-transformers (eksplisit, dev/ekspor).
    Mengembalikan None bila kedua backend gagal (pemanggil fallback ke
    chunks tanpa rerank + warning).
    """
    global _reranker, _reranker_backend

    if _reranker is not None:
        return _reranker

    backend = (settings.RERANKER_BACKEND or "onnx").lower()
    model_name = settings.RERANKER_MODEL
    max_length = settings.RERANKER_MAX_LENGTH

    if backend in ("onnx", "auto", ""):
        try:
            _reranker = _load_onnx()
            if _reranker is not None:
                _reranker_backend = "onnx"
                return _reranker
            logger.warning(
                "ONNX reranker artifact tidak ditemukan di %s — mencoba fallback "
                "torch. Jalankan tools/export_reranker_onnx.py untuk produksi.",
                reranker_onnx_dir(),
            )
        except Exception as e:
            logger.error("Gagal load ONNX reranker: %s — fallback ke torch.", e)
            _reranker = None

    # Fallback: torch (hanya bila dependency tersedia)
    try:
        _reranker = TorchReranker(model_name, max_length=max_length)
        _reranker_backend = "pytorch"
        logger.warning("RERANKER_BACKEND efektif = pytorch (fallback). Produksi gunakan ONNX.")
        return _reranker
    except Exception as e:
        logger.error(
            "Gagal load reranker (onnx & torch): %s. Fallback: chunks tanpa rerank.", e
        )
        _reranker = None
        _reranker_backend = None
        return None


def get_reranker_backend() -> str | None:
    """Backend yang sedang aktif ('onnx'/'pytorch'/None) — untuk observability."""
    get_reranker()
    return _reranker_backend


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """
    Rerank chunks berdasarkan relevansi ke query.

    Args:
        query: User query
        chunks: List of chunk dicts with 'content' key
        top_k: Number of top chunks to return

    Returns:
        Top-k chunks sorted by reranker score (descending)
    """
    if not chunks:
        return []

    reranker = get_reranker()
    if reranker is None:
        logger.warning("Reranker not available, returning original chunks")
        return chunks[:top_k]

    try:
        # Buat pairs (query, chunk_content)
        pairs = [(query, chunk.get("content", "")) for chunk in chunks]

        # Hitung scores
        scores = reranker.predict(pairs)

        # Attach scores to chunks
        scored_chunks = []
        for i, (score, chunk) in enumerate(zip(scores, chunks)):
            chunk_copy = chunk.copy()
            chunk_copy["reranker_score"] = float(score)
            scored_chunks.append(chunk_copy)

        # Sort berdasarkan reranker score descending
        scored_chunks.sort(key=lambda x: x["reranker_score"], reverse=True)

        result = scored_chunks[:top_k]
        logger.info(
            "Reranked %d chunks → top %d. Best score: %.4f, Worst: %.4f",
            len(chunks), top_k,
            result[0]["reranker_score"] if result else 0,
            result[-1]["reranker_score"] if len(result) > 1 else 0,
        )
        return result

    except Exception as e:
        logger.error("Reranking failed: %s, returning original chunks", e)
        return chunks[:top_k]
