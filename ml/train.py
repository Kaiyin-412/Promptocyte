"""GPU-aware local DistilBERT training for PromptSentinel (model architecture unchanged)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
from datasets import Dataset, load_from_disk
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)

from .inference import LABELS

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dataset"
OUTPUT = Path(__file__).resolve().parent / "model"
CACHE = ROOT / ".cache" / "tokenized_distilbert_v1"
MAX_LENGTH = 128


def load_csv(path: Path) -> Dataset:
    import pandas as pd
    frame = pd.read_csv(path)
    lookup = {label: index for index, label in enumerate(LABELS)}
    frame["labels"] = frame["label"].map(lookup)
    if frame["labels"].isna().any():
        raise ValueError("Dataset contains an unknown label")
    return Dataset.from_pandas(frame[["prompt", "labels"]], preserve_index=False)


def tokenized_datasets(tokenizer) -> tuple[Dataset, Dataset]:
    """Tokenize once and persist it; future runs avoid repeating CPU tokenization."""
    train_cache, test_cache = CACHE / "train", CACHE / "test"
    if train_cache.exists() and test_cache.exists():
        print(f"Loading pre-tokenized datasets from {CACHE}")
        return load_from_disk(str(train_cache)), load_from_disk(str(test_cache))

    print("Pre-tokenizing dataset once and saving it to disk cache...")
    train, test = load_csv(DATASET / "train.csv"), load_csv(DATASET / "test.csv")
    workers = max(1, min(4, (os.cpu_count() or 2) - 1))
    def tokenize(batch):
        # Deliberately omit padding here: collator dynamically pads each GPU batch.
        return tokenizer(batch["prompt"], truncation=True, max_length=MAX_LENGTH)
    train = train.map(tokenize, batched=True, num_proc=workers, remove_columns=["prompt"], desc="Tokenizing train")
    test = test.map(tokenize, batched=True, num_proc=workers, remove_columns=["prompt"], desc="Tokenizing test")
    CACHE.mkdir(parents=True, exist_ok=True)
    train.save_to_disk(str(train_cache)); test.save_to_disk(str(test_cache))
    return train, test


def gpu_utilization() -> str:
    command = shutil.which("nvidia-smi")
    if not command:
        return "unavailable"
    try:
        return subprocess.check_output(
            [command, "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


class RuntimeCallback(TrainerCallback):
    """Emit usable throughput and CUDA data at Hugging Face logging intervals."""
    def __init__(self, cuda: bool):
        self.cuda, self.started = cuda, time.perf_counter()

    def on_train_begin(self, args, state, control, **kwargs):
        device = kwargs["model"].device
        print(f"Training device: {device}")
        if self.cuda:
            print(f"GPU: {torch.cuda.get_device_name(0)} | allocated: {torch.cuda.memory_allocated() / 1024**2:.1f} MiB | nvidia-smi util/mem: {gpu_utilization()}")

    def on_log(self, args, state, control, logs=None, **kwargs):
        if not logs or state.global_step == 0:
            return
        elapsed = max(time.perf_counter() - self.started, 0.001)
        batches_per_second = state.global_step / elapsed
        detail = f"step={state.global_step} batches/s={batches_per_second:.2f}"
        if self.cuda:
            detail += f" allocated={torch.cuda.memory_allocated() / 1024**2:.0f}MiB reserved={torch.cuda.memory_reserved() / 1024**2:.0f}MiB gpu_util/mem={gpu_utilization()}"
        print(f"[runtime] {detail}")


def metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, predictions, average="weighted", zero_division=0)
    return {"accuracy": accuracy_score(labels, predictions), "precision": precision, "recall": recall, "f1": f1}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=32, help="Per-GPU batch size; lower to 16 if CUDA OOMs.")
    parser.add_argument("--gradient-accumulation", type=int, default=2, help="Effective batch size = batch size × this value.")
    parser.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1)))
    parser.add_argument("--require-gpu", action="store_true", help="Fail immediately instead of silently falling back to CPU.")
    args = parser.parse_args()

    cuda = torch.cuda.is_available()
    if args.require_gpu and not cuda:
        raise RuntimeError("CUDA is not available. Run `python tools/check_gpu.py` and install a CUDA-enabled PyTorch build.")
    device = torch.device("cuda:0" if cuda else "cpu")
    print(f"PyTorch: {torch.__version__} | CUDA available: {cuda} | selected device: {device}")
    if cuda:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.set_float32_matmul_precision("high")
        print(f"CUDA build: {torch.version.cuda} | GPU: {torch.cuda.get_device_name(0)} | BF16: {torch.cuda.is_bf16_supported()}")
    else:
        print("WARNING: CPU fallback is active. GPU utilization will remain at zero.")

    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    train, test = tokenized_datasets(tokenizer)
    # Dynamic padding reduces CPU transfer volume and GPU FLOPs versus padding every record to 128.
    collator = DataCollatorWithPadding(tokenizer=tokenizer, pad_to_multiple_of=8 if cuda else None)
    model = AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased", num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)), label2id={label: i for i, label in enumerate(LABELS)},
    )
    model.to(device)  # Explicit placement; Trainer/Accelerate retains this CUDA device.

    use_bf16 = cuda and torch.cuda.is_bf16_supported()
    training_args = TrainingArguments(
        output_dir=str(OUTPUT / "checkpoints"),
        eval_strategy="epoch", save_strategy="epoch", logging_strategy="steps", logging_steps=25,
        learning_rate=2e-5, per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size, gradient_accumulation_steps=args.gradient_accumulation,
        num_train_epochs=3, load_best_model_at_end=True, metric_for_best_model="f1",
        fp16=cuda and not use_bf16, bf16=use_bf16,
        dataloader_num_workers=args.workers, dataloader_pin_memory=cuda,
        dataloader_persistent_workers=args.workers > 0,
        optim="adamw_torch_fused" if cuda else "adamw_torch",
        report_to=[], seed=42,
    )
    trainer = Trainer(
        model=model, args=training_args, train_dataset=train, eval_dataset=test,
        processing_class=tokenizer, data_collator=collator, compute_metrics=metrics,
        callbacks=[RuntimeCallback(cuda)],
    )
    trainer.train()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(OUTPUT)); tokenizer.save_pretrained(str(OUTPUT))
    (OUTPUT / "metrics.json").write_text(json.dumps(trainer.evaluate(), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
