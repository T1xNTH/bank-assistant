"""Measure the /chat classification (intent, needs_human) on eval/classify.jsonl.

Usage: LLM_BACKEND=litellm python eval/classify.py [--samples eval/classify.jsonl]
       [--per-intent 5] [--min-accuracy 0.85] [--results eval/results/classify.jsonl]

Each sample goes through ``app.chat.structured_chat`` (the exact prompt and validation /chat uses, alias
``cloud-chat``) via the LiteLLM gateway. A call that fails or returns invalid output is retried, then
counted as wrong for both labels. Prints intent accuracy, needs_human accuracy and the intent confusion,
writes per-sample rows to ``--results``, and exits 1 when intent accuracy is below ``--min-accuracy``
(T-032 acceptance: 0.85).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import HTTPException  # noqa: E402

from app.chat import structured_chat  # noqa: E402
from app.contracts import LLM  # noqa: E402

INTENTS = ("question", "complaint", "request", "other")
FIELDS = ["intent", "message", "needs_human"]


def load_samples(path: Path, per_intent: int | None = 5) -> list[dict]:
    samples: list[dict] = []
    seen: dict[str, int] = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        where = f"dòng {n}"
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{where}: JSON không hợp lệ ({e.msg})") from None
        if not isinstance(row, dict) or sorted(row) != FIELDS:
            raise ValueError(f"{where}: trường phải là message, intent, needs_human")
        if not isinstance(row["message"], str) or not row["message"].strip():
            raise ValueError(f"{where}: message phải là chuỗi không rỗng")
        if not isinstance(row["intent"], str) or row["intent"] not in INTENTS:
            raise ValueError(f"{where}: intent phải thuộc {list(INTENTS)}")
        if not isinstance(row["needs_human"], bool):
            raise ValueError(f"{where}: needs_human phải là true/false")
        key = " ".join(row["message"].lower().split())
        if key in seen:
            raise ValueError(f"{where}: message trùng với dòng {seen[key]}")
        seen[key] = n
        samples.append(row)
    if per_intent is not None:
        counts = Counter(s["intent"] for s in samples)
        for intent in INTENTS:
            if counts[intent] != per_intent:
                raise ValueError(f"cần {per_intent} mẫu intent {intent}, đang có {counts[intent]}")
    return samples


@dataclass
class Score:
    rows: list[dict] = field(default_factory=list)

    @property
    def intent_accuracy(self) -> float:
        return sum(r["predicted_intent"] == r["intent"] for r in self.rows) / len(self.rows)

    @property
    def needs_human_accuracy(self) -> float:
        return sum(r["predicted_needs_human"] == r["needs_human"] for r in self.rows) / len(self.rows)

    @property
    def confusion(self) -> Counter:
        return Counter((r["intent"], r["predicted_intent"]) for r in self.rows)


def score(samples: list[dict], llm: LLM, retries: int = 3, retry_delay: float = 2.0) -> Score:
    result = Score()
    for sample in samples:
        predicted, error = None, None
        for attempt in range(retries):
            try:
                predicted = structured_chat(sample["message"], llm)
                break
            except HTTPException as exc:  # gateway failure or output that fails the /chat schema
                error = str(exc.detail)
                if attempt < retries - 1:
                    time.sleep(retry_delay)
        result.rows.append({
            **sample,
            "predicted_intent": predicted.intent if predicted else None,
            "predicted_needs_human": predicted.needs_human if predicted else None,
            "error": None if predicted else error,
        })
    return result


def main(argv: list[str] | None = None, llm: LLM | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--samples", type=Path, default=ROOT / "eval/classify.jsonl")
    parser.add_argument("--per-intent", type=int, default=5, help="số mẫu mỗi intent; 0 để bỏ qua")
    parser.add_argument("--min-accuracy", type=float, default=0.85)
    parser.add_argument("--results", type=Path, default=ROOT / "eval/results/classify.jsonl")
    args = parser.parse_args(argv)
    if llm is None:
        backend = os.getenv("LLM_BACKEND", "fake")
        if backend != "litellm":
            # The fake backend always answers intent "question": the accuracy would be meaningless.
            parser.error(f"LLM_BACKEND=litellm is required (got {backend!r})")
        from app import llm as gateway

        llm = gateway

    try:
        samples = load_samples(args.samples, args.per_intent or None)
    except ValueError as e:
        parser.error(str(e))
    result = score(samples, llm)

    for r in result.rows:
        mark = "ok " if r["predicted_intent"] == r["intent"] else "SAI"
        human = "ok " if r["predicted_needs_human"] == r["needs_human"] else "SAI"
        print(f"{mark} {r['intent']:>9} -> {r['predicted_intent'] or r['error']!s:<16} "
              f"needs_human {human} {r['needs_human']!s:>5} -> {r['predicted_needs_human']!s:<5} {r['message']}")
    total = len(result.rows)
    intent_ok = round(result.intent_accuracy * total)
    human_ok = round(result.needs_human_accuracy * total)
    print(f"\nintent accuracy: {intent_ok}/{total} = {result.intent_accuracy:.2f}")
    print(f"needs_human accuracy: {human_ok}/{total} = {result.needs_human_accuracy:.2f}")
    misses = {k: v for k, v in result.confusion.items() if k[0] != k[1]}
    for (expected, predicted), count in sorted(misses.items(), key=str):
        print(f"  {expected} -> {predicted}: {count}")

    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result.rows),
                            encoding="utf-8")
    passed = result.intent_accuracy >= args.min_accuracy
    print(f"{'OK' if passed else 'FAIL'}  intent accuracy {result.intent_accuracy:.2f} "
          f"(ngưỡng {args.min_accuracy:.2f})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
