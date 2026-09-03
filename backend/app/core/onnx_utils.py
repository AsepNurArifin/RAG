"""
ONNX runtime helpers — EnterpriseMind AI.

Utilitas bersama untuk backend ONNX (embedding & reranker, plan_optimasi.md
Fase 3A/3B): membuat InferenceSession onnxruntime + memuat fast tokenizer
(format `tokenizers`) dengan padding/truncation yang konsisten.

Hanya import library ringan (onnxruntime, tokenizers) — TIDAK memuat torch.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _resolve_pad_token(tok, model_dir: Path) -> str:
    """Pad token: baca tokenizer_config.json, fallback ke token umum."""
    try:
        cfg = json.loads((model_dir / "tokenizer_config.json").read_text(encoding="utf-8"))
        pad = cfg.get("pad_token")
        if pad and tok.token_to_id(pad) is not None:
            return pad
    except Exception:
        pass
    for candidate in ("<pad>", "[PAD]", "<s>", "<unk>"):
        if tok.token_to_id(candidate) is not None:
            return candidate
    raise RuntimeError("Tidak dapat menentukan pad token untuk tokenizer ONNX.")


def load_onnx_tokenizer(model_dir: Path, max_length: int):
    """
    Load fast tokenizer (tokenizers) dengan truncation+padding.

    Returns:
        tokenizer dengan enable_truncation(max_length) & enable_padding
        (pad token diselesaikan otomatis).
    """
    from tokenizers import Tokenizer

    tokenizer_json = model_dir / "tokenizer.json"
    if not tokenizer_json.exists():
        raise FileNotFoundError(f"tokenizer.json tidak ditemukan di {model_dir}")

    tok = Tokenizer.from_file(str(tokenizer_json))
    tok.enable_truncation(max_length=max_length)
    pad_token = _resolve_pad_token(tok, model_dir)
    tok.enable_padding(pad_id=tok.token_to_id(pad_token), pad_token=pad_token)
    return tok


def new_cpu_session(model_path: Path, threads: int = 0):
    """
    InferenceSession onnxruntime (CPU) dengan optimasi graph + thread opsional.

    threads=0 → biarkan onnxruntime memilih (intra_op default).
    """
    import onnxruntime as ort

    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    if threads and threads > 0:
        so.intra_op_num_threads = threads
        so.inter_op_num_threads = 1

    return ort.InferenceSession(
        str(model_path), sess_options=so, providers=["CPUExecutionProvider"]
    )
