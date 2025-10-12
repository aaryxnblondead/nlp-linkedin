"""
Build a lightweight SFT dataset from RAG contexts (ChromaDB) and fine-tune a small Gemma-like model using LoRA.

Usage (Windows cmd):
    set USE_GENERATOR=true
    set GEMMA_MODEL_ID=google/gemma-2-2b-it
    python backend\\scripts\\train_rag_lora.py --out models\\gemma-rag-lora
"""
import os
import json
import argparse
from typing import List

from app.services.embeddings import retrieve_corpus_texts

def build_examples(questions: List[str], k: int = 6):
    data = []
    for q in questions:
        ctxs = retrieve_corpus_texts(q, k=k)
        if not ctxs:
            continue
        prompt = (
            "You are a recruiter assistant. Answer using only the provided context. Be concise.\n\n"
            + "Context:\n" + "\n".join(f"- {c}" for c in ctxs) + f"\n\nQuestion: {q}\nAnswer:"
        )
        # For SFT we need a target; since we don't have gold answers, we can bootstrap with the question itself or empty.
        # In practice, provide curated Q/A. Here we leave empty to teach format.
        data.append({"prompt": prompt, "response": ""})
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Output dir for LoRA adapter and dataset")
    ap.add_argument("--questions", nargs="*", default=[
        "What are core skills for a data scientist?",
        "Summarize a candidate with 5 years of backend experience in Python.",
        "What are typical responsibilities of a frontend engineer?",
        "List common cloud skills across resumes.",
        "How to assess experience with Kubernetes?",
    ])
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    ds = build_examples(args.questions)
    ds_path = os.path.join(args.out, "sft_dataset.jsonl")
    with open(ds_path, "w", encoding="utf-8") as f:
        for row in ds:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote dataset with {len(ds)} examples to {ds_path}")

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
        from peft import LoraConfig, get_peft_model
        from trl.trainer.sft_trainer import SFTTrainer
        from datasets import Dataset
        import torch
    except Exception as e:
        print("Training deps missing; install transformers peft trl accelerate datasets. Skipping train.", e)
        return

    model_id = os.getenv("GEMMA_MODEL_ID", "google/gemma-2-2b-it")
    tok = AutoTokenizer.from_pretrained(model_id, use_fast=True)
    tok.model_max_length = 2048
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto", device_map="auto")

    peft_cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, task_type="CAUSAL_LM")
    model = get_peft_model(model, peft_cfg)

    def formatting(example):
        return example["prompt"] + (example.get("response") or "")

    train_args = TrainingArguments(
        output_dir=args.out,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        logging_steps=10,
        num_train_epochs=1,
        learning_rate=2e-4,
        fp16=torch.cuda.is_available(),
        bf16=False,
        save_steps=100,
        save_total_limit=2,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        report_to=[],
    )
    train_ds = Dataset.from_list(ds)

    trainer = SFTTrainer(
        model=model,
        args=train_args,
        train_dataset=train_ds,
        processing_class=tok,
        formatting_func=formatting,
    )
    trainer.train()
    trainer.save_model(args.out)
    print("LoRA adapter saved to", args.out)

if __name__ == "__main__":
    main()
    main()
