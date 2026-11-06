"""CI subset integrity: ten real golden rows, public-only and both scope classes."""

import json
from pathlib import Path

import pytest

from scripts.select_ci_golden import select

ROOT = Path(__file__).resolve().parents[2]


def test_committed_subset_is_ten_original_public_rows():
    rows = select(ROOT / "eval/golden.jsonl", ROOT / "eval/ci-questions.json", ROOT / "data/manifest.csv")
    golden = [json.loads(line) for line in (ROOT / "eval/golden.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 10 and all(row in golden for row in rows)
    assert sum(row["in_scope"] for row in rows) == 8
    assert {row["category"] for row in rows} >= {"fact", "table", "multi_hop", "out_of_scope"}


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "short", "private", "no_refusals"])
def test_invalid_subset_fails_before_model_calls(tmp_path, mutation):
    golden = [json.loads(line) for line in (ROOT / "eval/golden.jsonl").read_text(encoding="utf-8").splitlines()]
    questions = json.loads((ROOT / "eval/ci-questions.json").read_text(encoding="utf-8"))
    if mutation == "duplicate":
        questions[-1] = questions[0]
    elif mutation == "missing":
        questions[0] = "not in the golden set"
    elif mutation == "short":
        questions.pop()
    elif mutation == "private":
        questions[0] = golden[0]["user_input"]  # credit/confidential document
    else:
        questions[-1] = golden[3]["user_input"]
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        select(ROOT / "eval/golden.jsonl", selection, ROOT / "data/manifest.csv")
