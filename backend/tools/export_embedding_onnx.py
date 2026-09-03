"""
Export Embedding ke ONNX INT8 — EnterpriseMind AI.

Mengonversi BAAI/bge-m3 (WAJIB model yang sama — non-negotiable plan_optimasi.md)
menjadi ONNX dynamic-quantized INT8 sehingga runtime produksi cukup memakai
onnxruntime + tokenizers (tanpa torch / sentence-transformers / transformers).

Pooling dilakukan DI RUNTIME (bukan di dalam graph ONNX): last_hidden_state
→ CLS token → L2 normalize. Ini identik dengan backend torch fallback sehingga
parity konsisten dan mudah diverifikasi.

Artifact yang dihasilkan (satu direktori):
    model.onnx            — encoder XLM-R (output: last_hidden_state)
    tokenizer.json        — fast tokenizer untuk runtime (tokenizers)
    tokenizer_config.json — metadata pad token
    parity_report.txt     — hasil cek kesetaraan torch vs onnx

Penggunaan (jalankan di mesin dengan torch + HF):
    uv run --extra torch python tools/export_embedding_onnx.py
    uv run --extra torch python tools/export_embedding_onnx.py --no-quantize

⚠️ Setelah berganti embedding representation, WAJIB reindex:
    python -m scripts.reindex --clear     # hapus vector lama lalu rebuild
    (lakukan saat window maintenance; lihat plan_optimasi.md Fase 3B.5)
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-m3"
SAMPLE_TEXTS = [
    "EnterpriseMind adalah platform knowledge management dengan agentic RAG.",
    "Bagaimana cara reset password user di aplikasi?",
    "Vector database menyimpan representasi numerik dari teks untuk pencarian semantik.",
    "Sistem memakai hybrid retrieval: BM25 untuk keyword dan vector similarity untuk semantik.",
]


def default_output_dir() -> Path:
    """<repo>/backend/model_cache/onnx/embedding-<model-slug> (sama dgn runtime)."""
    hf_home = os.getenv("HF_HOME", "").strip()
    base = Path(hf_home) if hf_home else Path(__file__).resolve().parents[1] / "model_cache"
    return base / "onnx" / f"embedding-{DEFAULT_MODEL.rstrip('/').split('/')[-1]}"


def export_onnx(
    model_name: str,
    output_dir: Path,
    max_length: int = 8192,
    quantize: bool = True,
    opset: int = 17,
) -> Path:
    import torch
    from transformers import AutoModel, AutoTokenizer

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Memuat model & tokenizer: %s", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
    model.eval()

    enc = tokenizer(
        SAMPLE_TEXTS[:2],
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )

    fp32_path = output_dir / "model_fp32.onnx"
    onnx_path = output_dir / "model.onnx"

    logger.info("Export ke ONNX (opset %d)...", opset)
    torch.onnx.export(
        model,
        (enc["input_ids"], enc["attention_mask"]),
        str(fp32_path),
        input_names=["input_ids", "attention_mask"],
        output_names=["last_hidden_state"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "seq"},
            "attention_mask": {0: "batch", 1: "seq"},
            "last_hidden_state": {0: "batch", 1: "seq"},
        },
        opset_version=opset,
        do_constant_folding=True,
    )

    if quantize:
        from onnxruntime.quantization import QuantType, quantize_dynamic

        logger.info("Quantisasi dynamic INT8...")
        tmp_path = output_dir / "model_quantized.onnx"
        quantize_dynamic(
            str(fp32_path),
            str(tmp_path),
            weight_type=QuantType.QUInt8,
        )
        tmp_path.replace(onnx_path)
        fp32_path.unlink(missing_ok=True)
    else:
        fp32_path.replace(onnx_path)

    tokenizer.save_pretrained(str(output_dir))
    logger.info("Tokenizer disimpan di %s", output_dir)

    size_mb = onnx_path.stat().st_size / (1024 * 1024)
    logger.info("ONNX selesai: %s (%.1f MB)", onnx_path, size_mb)

    parity = run_parity_check(model, tokenizer, onnx_path, max_length)
    (output_dir / "parity_report.txt").write_text(
        json.dumps(parity, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Parity report: %s/parity_report.txt", output_dir)
    return onnx_path


def _cls_l2(hidden):
    """CLS pooling + L2 normalize (identik dengan runtime embedder)."""
    import numpy as np
    cls = np.asarray(hidden)[:, 0, :]
    norm = np.linalg.norm(cls, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return cls / norm


def run_parity_check(model, tokenizer, onnx_path: Path, max_length: int) -> dict:
    """Bandingkan embedding torch vs onnx (cosine similarity)."""
    import numpy as np
    import onnxruntime as ort
    import torch

    texts = SAMPLE_TEXTS
    enc = tokenizer(texts, padding=True, truncation=True, max_length=max_length, return_tensors="pt")

    with torch.no_grad():
        hidden_torch = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"]).last_hidden_state
    emb_torch = _cls_l2(hidden_torch.numpy())

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    feed = {"input_ids": enc["input_ids"].numpy(), "attention_mask": enc["attention_mask"].numpy()}
    hidden_onnx = session.run(["last_hidden_state"], feed)[0]
    emb_onnx = _cls_l2(hidden_onnx)

    sims = (emb_torch * emb_onnx).sum(axis=1)
    min_cos = float(sims.min())
    logger.info("Parity: cosine torch-vs-onnx min=%.5f (per-vektor)", min_cos)
    return {
        "model": str(onnx_path.parent),
        "min_cosine_similarity": round(min_cos, 6),
        "sample_texts": texts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export embedding ke ONNX INT8")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="HF model id (wajib BAAI/bge-m3 di produksi)")
    parser.add_argument("--output", type=Path, default=None, help="Output dir (default: <HF_HOME|backend/model_cache>/onnx/embedding-<slug>)")
    parser.add_argument("--max-length", type=int, default=8192)
    parser.add_argument("--no-quantize", action="store_true", help="Simpan FP32 (tanpa INT8)")
    parser.add_argument("--opset", type=int, default=17)
    args = parser.parse_args()

    output_dir = args.output or default_output_dir()
    export_onnx(
        model_name=args.model,
        output_dir=output_dir,
        max_length=args.max_length,
        quantize=not args.no_quantize,
        opset=args.opset,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
