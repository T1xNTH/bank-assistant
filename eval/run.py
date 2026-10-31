"""Evaluate the RAG pipeline on eval/golden.jsonl and write docs/12-ai/rag-eval-report.md.

Usage: python eval/run.py --all | --mode dense [--mode hybrid ...]
       [--limit N] [--no-judge] [--check] [--golden ...] [--manifest ...] [--out ...] [--results ...]

For each mode every golden question goes through ``RagAnswerer`` in process, as a user of the department
the question needs (its non-public source, else ``public``), against Qdrant and the LiteLLM gateway
(``LLM_BACKEND=litellm``). Metrics, with their NFR thresholds from eval/thresholds.json:

- ``hit_at_5`` (NFR-02): in-scope questions whose retrieved chunks (up to 5, the ones sent to the LLM)
  include a golden (file, page).
- ``refusal_accuracy`` (NFR-03): out-of-scope questions answered with ``found: false``.
- ``citation_rate`` (NFR-04): in-scope answers with ``found: true`` that carry at least one citation.
- ``faithfulness`` (NFR-01): RAGAS faithfulness of in-scope answers against their retrieved chunks,
  judged by ``JUDGE_MODEL`` (default the gateway alias ``cloud-chat``). ``--no-judge`` skips it.

Also reported: in-scope answer rate, citations of superseded documents (must be 0), latency, tokens.
Per-question rows go to eval/results/<mode>.jsonl. ``--check`` exits 1 when a threshold is missed.
Needs the eval venv (requirements-eval.txt) for the judge; docs/12-ai/rag-eval-report.md explains it.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.contracts import Hit, RetrievalMode, User  # noqa: E402

MODES: tuple[RetrievalMode, ...] = ("dense", "hybrid", "hybrid_rerank")
K = 5
RETRIES = 2  # AnswerUnavailable is transient (gateway 5xx/timeout, Qdrant restart); latency is the last attempt's
RETRY_DELAY_S = 2.0

# (question, answer, contexts) for each answered in-scope question -> one score per sample, None if unscored.
Judge = Callable[[list[dict]], list[float | None]]


@dataclass
class Record:
    user_input: str
    category: str
    in_scope: bool
    department: str
    sources: list[dict]
    mode: str
    answer: str = ""
    found: bool = False
    citations: list[dict] = field(default_factory=list)
    contexts: list[dict] = field(default_factory=list)
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    faithfulness: float | None = None
    error: str | None = None
    retries: int = 0

    @property
    def hit(self) -> bool:
        gold = {(s["file"], s["page"]) for s in self.sources}
        return any((c["source"], c["page"]) in gold for c in self.contexts[:K])


def load_golden(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_manifest(path: Path) -> tuple[dict[str, str], set[str]]:
    """File -> department, and the files of superseded documents."""
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {r["file"]: r["department"] for r in rows}, {r["file"] for r in rows if r["superseded_by"]}


def department_for(row: dict, departments: dict[str, str]) -> str:
    """The department that may read every source: golden questions never mix credit and hr."""
    needed = {departments[s["file"]] for s in row["sources"]} - {"public"}
    if len(needed) > 1:
        raise ValueError(f"question needs several departments {sorted(needed)}: {row['user_input']}")
    return needed.pop() if needed else "public"


class _CountingLLM:
    def __init__(self, llm) -> None:
        self.llm = llm
        self.input_tokens = self.output_tokens = 0

    def chat(self, messages, alias, temperature=0.0):
        result = self.llm.chat(messages, alias, temperature)
        self.input_tokens += result.input_tokens
        self.output_tokens += result.output_tokens
        return result


def _describe(exc: Exception) -> str:
    cause = f" ({type(exc.__cause__).__name__}: {exc.__cause__})" if exc.__cause__ else ""
    return f"{type(exc).__name__}: {exc}{cause}"


def answer_all(
    rows: list[dict], mode: RetrievalMode, departments: dict[str, str], retrieve=None, llm=None
) -> list[Record]:
    """Ask every row through RagAnswerer, keeping the hits that were sent to the LLM as contexts."""
    from app.rag.answer import AnswerUnavailable, RagAnswerer

    if retrieve is None:
        from app.rag.retrieve import retrieve
    if llm is None:
        from app import llm
    records = []
    for row in rows:
        department = department_for(row, departments)
        record = Record(row["user_input"], row["category"], row["in_scope"], department, row["sources"], mode)
        seen: list[Hit] = []

        def capture(question, user, k, m, _seen=seen):
            hits = retrieve(question, user, k, m)
            _seen[:] = hits
            return hits

        counter = _CountingLLM(llm)
        for attempt in range(RETRIES + 1):
            started = time.monotonic()
            try:
                result = RagAnswerer(capture, counter, k=K).answer(row["user_input"], User("eval", department), mode)
            except AnswerUnavailable as exc:  # a transient gateway or Qdrant failure: try again
                record.error = _describe(exc)
                if attempt < RETRIES:
                    record.retries += 1
                    time.sleep(RETRY_DELAY_S * (attempt + 1))
                    continue
            except Exception as exc:  # one failed question must not lose the whole run
                record.error = _describe(exc)
            else:
                record.error = None
                record.answer, record.found = result.answer, result.found
                record.citations = [asdict(c) for c in result.citations]
            break
        record.latency_ms = round((time.monotonic() - started) * 1000)
        record.contexts = [{"source": h.source, "page": h.page, "score": h.score, "text": h.text} for h in seen]
        record.input_tokens, record.output_tokens = counter.input_tokens, counter.output_tokens
        records.append(record)
        print(f"  [{mode}] {len(records)}/{len(rows)} {record.category} found={record.found}", file=sys.stderr)
    return records


def judge_records(records: list[Record], judge: Judge) -> None:
    answered = [r for r in records if r.in_scope and r.found]
    samples = [
        {"user_input": r.user_input, "response": r.answer, "contexts": [c["text"] for c in r.contexts]}
        for r in answered
    ]
    for record, score in zip(answered, judge(samples) if samples else [], strict=True):
        record.faithfulness = score


def _mean(values: list) -> float | None:
    return round(statistics.fmean(values), 4) if values else None


def _percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))]


def metrics(records: list[Record], superseded: set[str]) -> dict:
    in_scope = [r for r in records if r.in_scope]
    out_scope = [r for r in records if not r.in_scope]
    answered = [r for r in in_scope if r.found]
    scored = [r.faithfulness for r in answered if r.faithfulness is not None]
    latencies = [r.latency_ms for r in records if r.error is None]
    return {
        "questions": len(records),
        "in_scope": len(in_scope),
        "out_of_scope": len(out_scope),
        "errors": sum(r.error is not None for r in records),
        "retries": sum(r.retries for r in records),
        "faithfulness": _mean(scored),
        "faithfulness_scored": len(scored),
        "hit_at_5": _mean([r.hit for r in in_scope]),
        "refusal_accuracy": _mean([not r.found for r in out_scope]),
        "citation_rate": _mean([bool(r.citations) for r in answered]),
        "answer_rate": _mean([r.found for r in in_scope]),
        "superseded_cited": sum(c["source"] in superseded for r in records for c in r.citations),
        "latency_p50_ms": _percentile(latencies, 0.5),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "input_tokens": sum(r.input_tokens for r in records),
        "output_tokens": sum(r.output_tokens for r in records),
    }


def failures(summary: dict, thresholds: dict) -> list[str]:
    """Threshold names missed; a metric that could not be computed counts as missed."""
    return [name for name, minimum in thresholds.items() if summary.get(name) is None or summary[name] < minimum]


def by_category(records: list[Record]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for category in sorted({r.category for r in records}):
        rows = [r for r in records if r.category == category]
        out[category] = {
            "n": len(rows),
            "found": sum(r.found for r in rows),
            "hit": sum(r.hit for r in rows) if rows[0].in_scope else None,
        }
    return out


def _fmt(value) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def render_report(results: dict[str, list[Record]], summaries: dict[str, dict], thresholds: dict, config: dict) -> str:
    modes = list(results)
    lines = [
        "---",
        "id: rag-eval-report",
        "title: RAG Evaluation Report",
        "type: report",
        "domain: ai",
        "module: eval",
        "tags: [eval, ragas, e-008, t-023]",
        "priority: 1",
        "---",
        "# Báo cáo đánh giá RAG",
        "",
        "Sinh tự động bởi `python eval/run.py`; không sửa tay (chạy lại để cập nhật). Phần nhận xét viết tay nằm ở "
        "`docs/12-ai/rag-eval-notes.md`.",
        "",
        "## Cấu hình",
        "",
        *(f"- **{k}**: `{v}`" for k, v in config.items()),
        "",
        "## Kết quả theo mode",
        "",
        "| Chỉ số | Ngưỡng | " + " | ".join(f"`{m}`" for m in modes) + " |",
        "|---|---|" + "---|" * len(modes),
    ]
    labels = {
        "faithfulness": "Faithfulness (NFR-01)",
        "hit_at_5": "Hit@5 (NFR-02)",
        "refusal_accuracy": "Từ chối đúng câu ngoài phạm vi (NFR-03)",
        "citation_rate": "Câu trả lời có trích dẫn (NFR-04)",
    }
    for name, label in labels.items():
        cells = []
        for m in modes:
            value = summaries[m].get(name)
            ok = value is not None and value >= thresholds.get(name, float("-inf"))
            cells.append(f"{_fmt(value)} {'✅' if ok else '❌'}")
        lines.append(f"| {label} | ≥ {thresholds.get(name, '—')} | " + " | ".join(cells) + " |")
    extra = {
        "answer_rate": "Câu trong phạm vi được trả lời",
        "faithfulness_scored": "Số câu được chấm faithfulness",
        "superseded_cited": "Trích văn bản bị thay thế (phải 0)",
        "errors": "Lỗi khi chạy (sau khi thử lại)",
        "retries": "Số lần thử lại do dependency lỗi tạm thời",
        "latency_p50_ms": "Độ trễ p50 (ms)",
        "latency_p95_ms": "Độ trễ p95 (ms)",
        "input_tokens": "Token vào (LLM trả lời)",
        "output_tokens": "Token ra (LLM trả lời)",
    }
    for name, label in extra.items():
        lines.append(f"| {label} | | " + " | ".join(_fmt(summaries[m].get(name)) for m in modes) + " |")
    lines += [
        "",
        "## Theo loại câu hỏi",
        "",
        "Số câu được trả lời (`found`) và số câu retrieval trúng trang vàng (hit@5).",
        "",
    ]
    lines.append("| Loại | Số câu | " + " | ".join(f"`{m}` found / hit" for m in modes) + " |")
    lines.append("|---|---|" + "---|" * len(modes))
    categories = {m: by_category(results[m]) for m in modes}
    for category, info in categories[modes[0]].items():
        cells = []
        for m in modes:
            c = categories[m][category]
            cells.append(f"{c['found']} / {_fmt(c['hit'])}")
        lines.append(f"| `{category}` | {info['n']} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Câu trượt",
        "",
        "Câu trong phạm vi bị từ chối hoặc retrieval không trúng trang vàng, và câu ngoài phạm vi vẫn được trả lời.",
        "",
    ]
    for m in modes:
        misses = [
            r
            for r in results[m]
            if (r.in_scope and (not r.found or not r.hit)) or (not r.in_scope and r.found) or r.error
        ]
        lines.append(f"### `{m}` ({len(misses)})")
        lines.append("")
        for r in misses:
            what = (
                "lỗi: " + r.error
                if r.error
                else (
                    "trả lời câu ngoài phạm vi"
                    if not r.in_scope
                    else ("từ chối" if not r.found else "không trúng trang")
                )
            )
            lines.append(f"- [{r.category}, {r.department}] {r.user_input} — {what}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _display(path: Path) -> Path:
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


JUDGE_CONCURRENCY = 4


def ragas_judge(model: str, base_url: str, api_key: str) -> Judge:  # pragma: no cover - needs the eval venv
    """RAGAS faithfulness through the LiteLLM gateway (OpenAI-compatible) with the JUDGE_MODEL alias.

    ``reasoning_effort="none"``: RAGAS sends ``top_p``, which gpt-6-luna accepts only without reasoning
    (the gateway answers 400 otherwise), as ``app.llm`` does for ``cloud-chat``. A sample the judge
    cannot score (gateway error, unparsable output) is ``None`` and reported as unscored.
    """
    import asyncio

    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.metrics.collections import Faithfulness

    if not api_key:
        raise SystemExit("LITELLM_MASTER_KEY is required for the judge (or pass --no-judge)")
    client = AsyncOpenAI(base_url=f"{base_url}/v1", api_key=api_key)
    metric = Faithfulness(llm=llm_factory(model, client=client, reasoning_effort="none"))

    async def score_all(samples: list[dict]) -> list[float | None]:
        gate = asyncio.Semaphore(JUDGE_CONCURRENCY)

        async def score(sample: dict) -> float | None:
            async with gate:
                try:
                    result = await metric.ascore(
                        user_input=sample["user_input"],
                        response=sample["response"],
                        retrieved_contexts=sample["contexts"],
                    )
                except Exception as exc:  # noqa: BLE001 - one unscored sample must not stop the run
                    print(f"  judge failed: {type(exc).__name__}", file=sys.stderr)
                    return None
                return float(result.value)

        return await asyncio.gather(*(score(s) for s in samples))

    return lambda samples: asyncio.run(score_all(samples))


def main(argv: list[str] | None = None, judge: Judge | None = None, retrieve=None, llm=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="dense, hybrid and hybrid_rerank")
    group.add_argument("--mode", action="append", choices=MODES)
    parser.add_argument("--limit", type=int, help="first N questions only (a cheap smoke run)")
    parser.add_argument("--no-judge", action="store_true", help="skip RAGAS faithfulness (no judge calls)")
    parser.add_argument("--check", action="store_true", help="exit 1 when a threshold is missed")
    parser.add_argument("--golden", type=Path, default=ROOT / "eval/golden.jsonl")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.csv")
    parser.add_argument("--thresholds", type=Path, default=ROOT / "eval/thresholds.json")
    parser.add_argument("--out", type=Path, default=ROOT / "docs/12-ai/rag-eval-report.md")
    parser.add_argument("--results", type=Path, default=ROOT / "eval/results")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    modes = list(MODES) if args.all else list(dict.fromkeys(args.mode))
    rows = load_golden(args.golden)[: args.limit]
    departments, superseded = load_manifest(args.manifest)
    thresholds = json.loads(args.thresholds.read_text())
    judge_model = os.getenv("JUDGE_MODEL", "cloud-chat")
    if judge is None and not args.no_judge:
        base = os.getenv("LLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
        judge = ragas_judge(judge_model, base, os.getenv("LITELLM_MASTER_KEY", ""))

    from app import prompts
    from app.rag import rerank
    from app.rag import retrieve as retrieval

    results, summaries = {}, {}
    args.results.mkdir(parents=True, exist_ok=True)
    for mode in modes:
        records = answer_all(rows, mode, departments, retrieve, llm)
        if judge is not None:
            judge_records(records, judge)
        results[mode], summaries[mode] = records, metrics(records, superseded)
        with (args.results / f"{mode}.jsonl").open("w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps({**asdict(r), "hit": r.hit}, ensure_ascii=False) + "\n")
    config = {
        "Ngày chạy": time.strftime("%Y-%m-%d %H:%M"),
        "Bộ câu hỏi": f"{_display(args.golden)} ({len(rows)} câu)",
        "Model trả lời": "alias cloud-chat qua LiteLLM",
        "Judge (faithfulness)": "không chạy (--no-judge)" if judge is None else f"RAGAS faithfulness, {judge_model}",
        "PROMPT_VERSION": prompts.PROMPT_VERSION,
        "k": K,
        "REFUSAL_THRESHOLD": rerank.refusal_threshold(),
        "RERANK_CANDIDATES": retrieval.rerank_candidates(),
        "QDRANT_COLLECTION": os.getenv("QDRANT_COLLECTION", "bank_docs"),
    }
    args.out.write_text(render_report(results, summaries, thresholds, config), encoding="utf-8")
    missed = {m: failures(summaries[m], thresholds) for m in modes}
    for m in modes:
        print(f"{m}: {json.dumps(summaries[m], ensure_ascii=False)} missed={missed[m]}")
    return 1 if args.check and any(missed.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
