"""Generate review candidates locally with the Apache-2.0 Qwen model.

The generated files are candidates, not a finished or manually reviewed dataset.
Run on a CUDA machine: python generate_ticket_candidates.py
"""
import csv
import json
import random
import re
from pathlib import Path

import torch
from huggingface_hub import model_info
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
OUT = Path("ticket_candidates")
LABELS = {
    "complaint": ["damaged product", "late delivery", "missing item", "wrong size", "faulty device", "poor packaging", "incorrect colour", "delivery marked complete but missing", "rude service", "broken seal", "product different from listing", "item stopped working"],
    "order": ["place a new order", "change size before dispatch", "cancel an unshipped order", "change delivery slot", "add an item before shipping", "update delivery instructions", "order another quantity", "replace an item in an unshipped order", "apply a coupon before purchase", "confirm a new purchase", "reschedule an unshipped delivery", "order a gift wrap"],
    "question": ["delivery charges", "available sizes", "warranty length", "payment options", "return policy", "product material", "stock availability", "shipping timeframe", "cash on delivery availability", "care instructions", "delivery coverage", "whether batteries are included"],
    "refund": ["request refund for a returned item", "refund not received", "refund status after cancellation", "refund to original payment method", "partial refund for missing item", "refund for duplicate payment", "refund amount is wrong", "refund delayed after pickup", "refund after damaged item return", "refund timeline after rejection", "refund receipt", "refund for unavailable item"],
    "other": ["thank the support team", "share a suggestion for the website", "compliment helpful staff", "ask to unsubscribe from marketing", "report an accessibility suggestion", "give general product feedback", "thank delivery staff", "suggest a new product colour", "compliment packaging", "suggest better size chart", "give general feedback on app design", "ask to change notification preferences"],
}

def main():
    if not torch.cuda.is_available():
        raise SystemExit("A CUDA GPU is required for this candidate generation run.")
    OUT.mkdir(exist_ok=True)
    revision = model_info(MODEL).sha
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=revision)
    model = AutoModelForCausalLM.from_pretrained(MODEL, revision=revision, torch_dtype=torch.float16, device_map="auto")
    random.seed(20261116)
    torch.manual_seed(20261116)
    seen = set()
    rows = {"train": [], "test": []}
    for label, scenarios in LABELS.items():
        for index, scenario in enumerate(scenarios):
            split = "train" if index < 10 else "test"
            script = "a mix of Devanagari Hindi and English" if index % 4 == 0 else "Roman-script Hinglish"
            collected = []
            for attempt in range(8):
                remaining = 10 - len(collected)
                if remaining <= 0:
                    break
                prompt = (f"Write {remaining + 3} distinct short customer support messages in {script} about {scenario}. "
                          f"Each must have the main intent '{label}'. No names, phone numbers, emails, real companies, "
                          "addresses, order numbers or other personal information. One message per line, numbered. "
                          "Output messages only. Vary wording and sentence structure.")
                inputs = tokenizer.apply_chat_template([{"role": "user", "content": prompt}], tokenize=True,
                           add_generation_prompt=True, return_tensors="pt").to(model.device)
                output = model.generate(inputs, max_new_tokens=650, do_sample=True, temperature=0.8, top_p=0.9,
                                        pad_token_id=tokenizer.eos_token_id)
                text = tokenizer.decode(output[0][inputs.shape[1]:], skip_special_tokens=True)
                for line in text.splitlines():
                    line = re.sub(r"^\s*(?:\d+[.)\-:]\s*|[-*]\s*)", "", line).strip(' \t\"\'')
                    key = " ".join(line.lower().split())
                    if 12 <= len(line) <= 250 and key not in seen:
                        seen.add(key)
                        collected.append(line)
                        if len(collected) == 10:
                            break
            if len(collected) != 10:
                raise RuntimeError(f"Insufficient candidates: {label}, {scenario}: {len(collected)}")
            rows[split].extend({"text": text, "label": label} for text in collected)
            print(f"{split}: {label}: {scenario}: {len(collected)}", flush=True)
    for split, items in rows.items():
        random.shuffle(items)
        with (OUT / f"{split}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["text", "label"])
            writer.writeheader()
            writer.writerows(items)
    (OUT / "provenance.json").write_text(json.dumps({"model": MODEL, "revision": revision, "seed": 20261116,
        "temperature": 0.8, "top_p": 0.9, "max_new_tokens": 650, "status": "unreviewed candidates"}, indent=2), encoding="utf-8")
    print(f"Candidates saved to {OUT.resolve()}; manual review is still required.")

if __name__ == "__main__":
    main()
