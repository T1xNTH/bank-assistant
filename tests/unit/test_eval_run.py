"""eval/run.py: departments, metrics, judge wiring, report and CLI with fake retrieval, LLM and judge (CI)."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from app.contracts import REFUSAL, Hit, User
from tests.fakes import FakeLLM

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("eval_run", ROOT / "eval/run.py")
run = importlib.util.module_from_spec(spec)
sys.modules["eval_run"] = run  # dataclasses look the module up while the class is created
spec.loader.exec_module(run)

DEPARTMENTS = {"luong.pdf": "hr", "the.pdf": "credit", "phi.pdf": "public", "cu.pdf": "hr"}


def row(question, sources, category="fact", in_scope=True):
    return {
        "user_input": question,
        "reference": "x",
        "sources": sources,
        "category": category,
        "difficulty": "easy",
        "in_scope": in_scope,
    }


def hit(source, page, text="nội dung", score=0.9):
    return Hit(f"{source}-{page}", source, page, text, score, DEPARTMENTS.get(source, "public"))


ROWS = [
    row("Lương vùng I?", [{"file": "luong.pdf", "page": 2}]),
    row("Phí thẻ và lãi?", [{"file": "the.pdf", "page": 5}, {"file": "phi.pdf", "page": 1}], "cross_department"),
    row("Giá vàng?", [], "out_of_scope", in_scope=False),
]


class Retrieve:
    """Answers by question; records the user and mode it was asked with."""

    def __init__(self, table):
        self.table, self.calls = table, []

    def __call__(self, question, user, k, mode):
        self.calls.append((question, user, k, mode))
        return self.table.get(question, [])[:k]


TABLE = {
    "Lương vùng I?": [hit("luong.pdf", 2, "5.310.000 đồng")],
    "Phí thẻ và lãi?": [hit("phi.pdf", 9), hit("the.pdf", 7)],  # right files, wrong pages: a miss
}


# Departments and loading


def test_department_is_the_non_public_source_or_public():
    assert run.department_for(ROWS[0], DEPARTMENTS) == "hr"
    assert run.department_for(ROWS[1], DEPARTMENTS) == "credit"
    assert run.department_for(ROWS[2], DEPARTMENTS) == "public"


def test_question_needing_two_departments_is_an_error():
    bad = row("x", [{"file": "luong.pdf", "page": 1}, {"file": "the.pdf", "page": 1}])
    with pytest.raises(ValueError, match="several departments"):
        run.department_for(bad, DEPARTMENTS)


def test_manifest_gives_departments_and_superseded_files(tmp_path):
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "doc_id,file,department,classification,effective_date,superseded_by,source_url\n"
        "a,luong.pdf,hr,public,2025-01-01,,u\n"
        "b,cu.pdf,hr,public,2024-01-01,a,u\n"
    )
    assert run.load_manifest(manifest) == ({"luong.pdf": "hr", "cu.pdf": "hr"}, {"cu.pdf"})


def test_every_golden_question_has_one_department():
    departments, _ = run.load_manifest(ROOT / "data/manifest.csv")
    rows = run.load_golden(ROOT / "eval/golden.jsonl")
    assert len(rows) == 50
    assert {run.department_for(r, departments) for r in rows} <= {"public", "credit", "hr"}


# Answering


def test_answer_all_asks_as_the_needed_department_and_keeps_contexts():
    retrieve = Retrieve(TABLE)
    records = run.answer_all(ROWS, "hybrid", DEPARTMENTS, retrieve, FakeLLM("Đáp [1]."))
    assert [c[1] for c in retrieve.calls] == [User("eval", "hr"), User("eval", "credit"), User("eval", "public")]
    assert {c[2] for c in retrieve.calls} == {5} and {c[3] for c in retrieve.calls} == {"hybrid"}
    first, second, third = records
    assert first.found and first.citations == [{"n": 1, "source": "luong.pdf", "page": 2, "score": 0.9}]
    assert first.contexts == [{"source": "luong.pdf", "page": 2, "score": 0.9, "text": "5.310.000 đồng"}]
    assert first.hit and not second.hit
    assert (third.found, third.answer, third.contexts) == (False, REFUSAL, [])


def test_one_failing_question_is_recorded_not_fatal():
    def broken(question, user, k, mode):
        raise RuntimeError("boom")

    [record] = run.answer_all(ROWS[:1], "dense", DEPARTMENTS, broken, FakeLLM())
    assert record.error == "RuntimeError: boom" and not record.found


def test_transient_unavailable_is_retried(monkeypatch):
    from app.llm import LLMError

    monkeypatch.setattr(run, "RETRY_DELAY_S", 0)

    class Flaky(FakeLLM):
        def __init__(self, failures):
            super().__init__("Đáp [1].")
            self.failures = failures

        def chat(self, messages, alias, temperature=0.0):
            if self.failures:
                self.failures -= 1
                raise LLMError("LLM gateway returned HTTP 502")
            return super().chat(messages, alias, temperature)

    [ok] = run.answer_all(ROWS[:1], "dense", DEPARTMENTS, Retrieve(TABLE), Flaky(2))
    assert (ok.found, ok.error, ok.retries) == (True, None, 2)
    [failed] = run.answer_all(ROWS[:1], "dense", DEPARTMENTS, Retrieve(TABLE), Flaky(3))
    assert not failed.found and failed.retries == 2
    assert failed.error == "AnswerUnavailable: LLM gateway unavailable (LLMError: LLM gateway returned HTTP 502)"
    summary = run.metrics([ok, failed], set())
    assert (summary["errors"], summary["retries"]) == (1, 4)


def test_bugs_are_not_retried():
    calls = []

    def broken(question, user, k, mode):
        calls.append(1)
        raise KeyError("payload")

    [record] = run.answer_all(ROWS[:1], "dense", DEPARTMENTS, broken, FakeLLM())
    assert len(calls) == 1 and record.retries == 0 and record.error == "KeyError: 'payload'"


def test_tokens_are_counted_per_question():
    class Tokens(FakeLLM):
        def chat(self, messages, alias, temperature=0.0):
            result = super().chat(messages, alias, temperature)
            return type(result)(result.text, result.model, 100, 7)

    records = run.answer_all(ROWS, "hybrid", DEPARTMENTS, Retrieve(TABLE), Tokens("Đáp [1]."))
    assert [(r.input_tokens, r.output_tokens) for r in records] == [(100, 7), (100, 7), (0, 0)]


# Judge and metrics


def test_judge_scores_only_answered_in_scope_questions_with_their_contexts():
    records = run.answer_all(ROWS, "hybrid", DEPARTMENTS, Retrieve(TABLE), FakeLLM("Đáp [1]."))
    seen = []

    def judge(samples):
        seen.extend(samples)
        return [0.5, None]

    run.judge_records(records, judge)
    assert seen[0] == {"user_input": "Lương vùng I?", "response": "Đáp [1].", "contexts": ["5.310.000 đồng"]}
    assert len(seen) == 2
    assert [r.faithfulness for r in records] == [0.5, None, None]


def test_metrics():
    records = run.answer_all(ROWS, "hybrid", DEPARTMENTS, Retrieve(TABLE), FakeLLM("Đáp [1]."))
    run.judge_records(records, lambda samples: [1.0, 0.5])
    summary = run.metrics(records, superseded={"luong.pdf"})
    assert summary["questions"] == 3 and summary["in_scope"] == 2 and summary["out_of_scope"] == 1
    assert summary["hit_at_5"] == 0.5
    assert summary["refusal_accuracy"] == 1.0
    assert summary["citation_rate"] == 1.0
    assert summary["answer_rate"] == 1.0
    assert summary["faithfulness"] == 0.75 and summary["faithfulness_scored"] == 2
    assert summary["superseded_cited"] == 1
    assert summary["errors"] == 0


def test_out_of_scope_answer_lowers_refusal_accuracy():
    table = {**TABLE, "Giá vàng?": [hit("phi.pdf", 1)]}
    records = run.answer_all(ROWS, "hybrid", DEPARTMENTS, Retrieve(table), FakeLLM("Đáp [1]."))
    assert run.metrics(records, set())["refusal_accuracy"] == 0.0


def test_missing_metric_counts_as_a_failure():
    summary = {"faithfulness": None, "hit_at_5": 0.8, "refusal_accuracy": 0.85, "citation_rate": 1.0}
    thresholds = {"faithfulness": 0.8, "hit_at_5": 0.75, "refusal_accuracy": 0.9, "citation_rate": 1.0}
    assert run.failures(summary, thresholds) == ["faithfulness", "refusal_accuracy"]


def test_percentile():
    assert run._percentile([], 0.95) is None
    assert run._percentile([5, 1, 3], 0.5) == 3
    assert run._percentile(list(range(1, 101)), 0.95) == 95


# CLI and report


def cli(tmp_path, argv, judge=None, table=TABLE):
    golden = tmp_path / "golden.jsonl"
    golden.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in ROWS) + "\n")
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "doc_id,file,department,classification,effective_date,superseded_by,source_url\n"
        + "".join(f"{f},{f},{d},public,2025-01-01,,u\n" for f, d in DEPARTMENTS.items())
    )
    out, results = tmp_path / "report.md", tmp_path / "results"
    code = run.main(
        [*argv, "--golden", str(golden), "--manifest", str(manifest), "--out", str(out), "--results", str(results)],
        judge=judge,
        retrieve=Retrieve(table),
        llm=FakeLLM("Đáp [1]."),
    )
    return code, out, results


def test_all_modes_write_report_and_results(tmp_path, monkeypatch):
    monkeypatch.delenv("REFUSAL_THRESHOLD", raising=False)
    monkeypatch.delenv("RERANK_CANDIDATES", raising=False)
    code, out, results = cli(tmp_path, ["--all"], judge=lambda s: [0.9] * len(s))
    assert code == 0
    report = out.read_text()
    for mode in ("dense", "hybrid", "hybrid_rerank"):
        assert f"`{mode}`" in report
        lines = (results / f"{mode}.jsonl").read_text().splitlines()
        assert len(lines) == 3 and json.loads(lines[0])["hit"] is True
    assert "| Faithfulness (NFR-01) | ≥ 0.8 | 0.90 ✅ | 0.90 ✅ | 0.90 ✅ |" in report
    assert "| Hit@5 (NFR-02) | ≥ 0.75 | 0.50 ❌ | 0.50 ❌ | 0.50 ❌ |" in report
    assert "- [cross_department, credit] Phí thẻ và lãi? — không trúng trang" in report
    assert "RERANK_CANDIDATES**: `5`" in report


def test_check_exits_1_when_a_threshold_is_missed(tmp_path):
    code, _, _ = cli(tmp_path, ["--mode", "dense", "--check"], judge=lambda s: [0.9] * len(s))
    assert code == 1  # hit@5 is 0.5


def test_check_exits_0_when_every_threshold_is_met(tmp_path):
    table = {**TABLE, "Phí thẻ và lãi?": [hit("the.pdf", 5)]}
    code, _, _ = cli(tmp_path, ["--mode", "dense", "--check"], judge=lambda s: [0.9] * len(s), table=table)
    assert code == 0


def test_no_judge_leaves_faithfulness_empty_and_failing(tmp_path):
    code, out, _ = cli(tmp_path, ["--mode", "hybrid", "--no-judge", "--check"])
    assert code == 1
    assert "| Faithfulness (NFR-01) | ≥ 0.8 | — ❌ |" in out.read_text()
    assert "không chạy (--no-judge)" in out.read_text()


def test_limit_and_repeated_mode(tmp_path):
    code, out, results = cli(tmp_path, ["--mode", "dense", "--mode", "dense", "--limit", "1", "--no-judge"])
    assert len((results / "dense.jsonl").read_text().splitlines()) == 1
    assert "(1 câu)" in out.read_text()


def test_mode_and_all_are_exclusive(tmp_path):
    with pytest.raises(SystemExit):
        cli(tmp_path, ["--all", "--mode", "dense"])
