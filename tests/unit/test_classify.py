"""eval/classify.py: dataset checks, scoring and exit code, with a scripted LLM instead of the gateway."""

import json
from pathlib import Path

import pytest

from app.chat import CHAT_SYSTEM
from app.contracts import LLMResult
from app.llm import LLMError
from eval.classify import INTENTS, load_samples, main, score

ROOT = Path(__file__).resolve().parents[2]


class ScriptedLLM:
    """Replies with the given (intent, needs_human) per message; None makes the call fail."""

    def __init__(self, labels: dict[str, tuple[str, bool] | None], failures: int = 0) -> None:
        self.labels = labels
        self.failures = failures
        self.calls: list[str] = []

    def chat(self, messages: list[dict], alias: str, temperature: float = 0.0) -> LLMResult:
        assert messages[0] == {"role": "system", "content": CHAT_SYSTEM} and alias == "cloud-chat"
        message = messages[1]["content"]
        self.calls.append(message)
        if self.failures:
            self.failures -= 1
            raise LLMError("LLM gateway returned HTTP 503")
        label = self.labels[message]
        if label is None:
            return LLMResult(text="not json", model="scripted")
        intent, needs_human = label
        return LLMResult(text=json.dumps({"answer": "ok", "intent": intent, "needs_human": needs_human}),
                         model="scripted")


def sample(message, intent="question", needs_human=False):
    return {"message": message, "intent": intent, "needs_human": needs_human}


def write(tmp_path, rows):
    path = tmp_path / "classify.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path


def balanced(per_intent=1):
    return [sample(f"{intent} {n}", intent, intent in {"complaint", "request"})
            for intent in INTENTS for n in range(per_intent)]


def test_committed_set_has_five_valid_samples_per_intent():
    samples = load_samples(ROOT / "eval/classify.jsonl", per_intent=5)
    assert len(samples) == 20
    assert sorted({s["intent"] for s in samples}) == sorted(INTENTS)


@pytest.mark.parametrize("bad, fragment", [
    ({"extra": 1}, "trường"),
    ({"message": "  "}, "message"),
    ({"message": 3}, "message"),
    ({"intent": "praise"}, "intent"),
    ({"intent": ["question"]}, "intent"),
    ({"needs_human": "false"}, "needs_human"),
])
def test_bad_samples_are_rejected(tmp_path, bad, fragment):
    rows = balanced()
    rows[0] = {**rows[0], **bad}
    with pytest.raises(ValueError, match=f"dòng 1: .*{fragment}"):
        load_samples(write(tmp_path, rows), per_intent=1)


def test_duplicates_counts_and_broken_json_are_rejected(tmp_path):
    rows = balanced()
    with pytest.raises(ValueError, match="dòng 5: message trùng với dòng 1"):
        load_samples(write(tmp_path, [*rows, {**rows[0], "message": f" {rows[0]['message'].upper()} "}]),
                     per_intent=None)
    with pytest.raises(ValueError, match="cần 2 mẫu intent question, đang có 1"):
        load_samples(write(tmp_path, rows), per_intent=2)
    path = tmp_path / "broken.jsonl"
    path.write_text("{not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dòng 1: JSON"):
        load_samples(path, per_intent=None)


def test_score_counts_intent_and_needs_human_separately():
    samples = balanced()
    llm = ScriptedLLM({
        "question 0": ("question", False),
        "complaint 0": ("request", True),  # wrong intent, right needs_human
        "request 0": ("request", False),  # right intent, wrong needs_human
        "other 0": None,  # invalid output: both wrong
    })
    result = score(samples, llm, retry_delay=0)
    assert result.intent_accuracy == 0.5
    assert result.needs_human_accuracy == 0.5
    assert [r["predicted_intent"] for r in result.rows] == ["question", "request", "request", None]
    assert result.rows[3]["error"] == "Chat unavailable"
    assert result.confusion[("complaint", "request")] == 1


def test_transient_failures_are_retried():
    llm = ScriptedLLM({"question 0": ("question", False)}, failures=2)
    result = score([sample("question 0")], llm, retries=3, retry_delay=0)
    assert result.intent_accuracy == 1.0 and len(llm.calls) == 3


def test_main_exit_code_follows_the_threshold(tmp_path, capsys):
    rows = balanced()
    path = write(tmp_path, rows)
    perfect = ScriptedLLM({r["message"]: (r["intent"], r["needs_human"]) for r in rows})
    out = tmp_path / "out.jsonl"
    assert main(["--samples", str(path), "--per-intent", "1", "--results", str(out)], llm=perfect) == 0
    assert "intent accuracy: 4/4 = 1.00" in capsys.readouterr().out
    assert len(out.read_text(encoding="utf-8").splitlines()) == 4

    half = ScriptedLLM({r["message"]: ("other", False) for r in rows})
    assert main(["--samples", str(path), "--per-intent", "1", "--results", str(out)], llm=half) == 1
    assert "FAIL" in capsys.readouterr().out


def test_main_refuses_the_fake_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "fake")
    with pytest.raises(SystemExit):
        main(["--samples", str(write(tmp_path, balanced())), "--per-intent", "1"])


def test_committed_heldout_set_is_valid_and_covers_the_review_cases():
    samples = load_samples(ROOT / "eval/classify_heldout.jsonl", per_intent=None)
    assert len(samples) == 18
    assert {s["message"] for s in samples}.isdisjoint(
        s["message"] for s in load_samples(ROOT / "eval/classify.jsonl", per_intent=5))
    assert sum(s["intent"] == "complaint" for s in samples) == 5
    assert sum(s["intent"] == "question" and s["needs_human"] for s in samples) == 4
