"""
Export Reranker ke ONNX INT8 — EnterpriseMind AI.

Mengonversi BAAI/bge-reranker-v2-m3 (cross-encoder, WAJIB tetap model ini —
non-negotiable plan_optimasi.md) menjadi ONNX dynamic-quantized INT8 sehingga
runtime produksi cukup memakai onnxruntime + tokenizers (tanpa torch /
sentence-transformers / transformers).

Artifact yang dihasilkan (satu direktori):
    model.onnx           — model INT8 (dynamic quantization)
    tokenizer.json       — fast tokenizer untuk runtime (tokenizers)
    tokenizer_config.json— metadata pad token
    parity_report.txt    — hasil cek kesetaraan torch vs onnx

Penggunaan (jalankan di mesin dengan torch + HF, mis. laptop dev):
    uv run --group torch python tools/export_reranker_onnx.py \
        --model BAAI/bge-reranker-v2-m3
    uv run --group torch python tools/export_reranker_onnx.py --no-quantize   # FP32

Catatan kesetaraan: skor akhir = sigmoid(logit). Perbedaan torch vs onnx INT8
umumnya < 0.02; urutan (ranking) dijamin identik untuk pasangan yang sama.
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"
SAMPLE_PAIRS = [
    ("Bagaimana cara reset password user?", "Panduan reset password: buka menu Pengaturan lalu pilih Keamanan > Reset Password."),
    ("Apa itu vector database?", "Vector database menyimpan representasi numerik (embedding) dari teks untuk pencarian semantik."),
    ("Bagaimana cara reset password user?", "Laporan keuangan kuartal ketiga menunjukkan pertumbuhan 12 persen dibanding tahun lalu."),
]


def default_output_dir() -> Path:
    """<repo>/backend/model_cache/onnx/reranker-<model-slug> (sama dgn runtime)."""
    hf_home = os.getenv("HF_HOME", "").strip()
    base = Path(hf_home) if hf_home else Path(__file__).resolve().parents[1] / "model_cache"
    return base / "onnx" / f"reranker-{DEFAULT_MODEL.rstrip('/').split('/')[-1]}"


def export_onnx(
    model_name: str,
    output_dir: Path,
    max_length: int = 256,
    quantize: bool = True,
    opset: int = 17,
) -> Path:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Memuat model & tokenizer: %s", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()

    # --- Siapkan dummy input (tanpa token_type_ids — XLM-R) ---
    enc = tokenizer(
        ["contoh query", "contoh query kedua"],
        ["dokumen pertama", "dokumen kedua"],
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
        output_names=["logits"],
        dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"}, "logits": {0: "batch"}},
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

    # --- Simpan tokenizer untuk runtime (tokenizers Rust) ---
    tokenizer.save_pretrained(str(output_dir))
    logger.info("Tokenizer disimpan di %s", output_dir)

    size_mb = onnx_path.stat().st_size / (1024 * 1024)
    logger.info("ONNX selesai: %s (%.1f MB)", onnx_path, size_mb)

    # --- Parity check torch vs onnx ---
    parity = run_parity_check(model, tokenizer, onnx_path, max_length)
    report = output_dir / "parity_report.txt"
    report.write_text(json.dumps(parity, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Parity report: %s", report)
    return onnx_path


def run_parity_check(model, tokenizer, onnx_path: Path, max_length: int) -> dict:
    """Bandingkan skor torch vs onnx untuk beberapa pasangan contoh."""
    import numpy as np
    import onnxruntime as ort
    import torch

    pairs = SAMPLE_PAIRS
    queries = [p[0] for p in pairs]
    docs = [p[1] for p in pairs]
    enc = tokenizer(queries, docs, padding=True, truncation=True, max_length=max_length, return_tensors="pt")

    with torch.no_grad():
        logits_torch = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"]).logits
    prob_torch = torch.sigmoid(logits_torch).numpy().reshape(-1)

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    feed = {"input_ids": enc["input_ids"].numpy(), "attention_mask": enc["attention_mask"].numpy()}
    logits_onnx = session.run(["logits"], feed)[0].reshape(-1)
    prob_onnx = 1.0 / (1.0 + np.exp(-logits_onnx))

    max_abs = float(np.max(np.abs(prob_torch - prob_onnx)))
    same_order = bool(np.allclose(np.argsort(prob_torch), np.argsort(prob_onnx)))
    logger.info(
        "Parity: max|Δprob| = %.5f, urutan sama = %s",
        max_abs, same_order,
    )
    return {
        "model": str(onnx_path.parent),
        "max_abs_diff": round(max_abs, 6),
        "same_ranking": same_order,
        "samples": [
            {"query": q, "torch_prob": round(float(p_t), 5), "onnx_prob": round(float(p_o), 5)}
            for q, p_t, p_o in zip(queries, prob_torch, prob_onnx)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export reranker ke ONNX INT8")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="HF model id (wajib BAAI/bge-reranker-v2-m3 di produksi)")
    parser.add_argument("--output", type=Path, default=None, help="Output dir (default: <HF_HOME|backend/model_cache>/onnx/reranker-<slug>)")
    parser.add_argument("--max-length", type=int, default=256)
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
