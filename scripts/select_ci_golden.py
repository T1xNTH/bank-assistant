"""Materialize the CI smoke subset from the current golden rows, never saved eval results."""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def select(golden: Path, selection: Path, manifest: Path) -> list[dict]:
    rows = [json.loads(line) for line in golden.read_text(encoding="utf-8").splitlines() if line.strip()]
    questions = json.loads(selection.read_text(encoding="utf-8"))
    if not isinstance(questions, list) or any(not isinstance(q, str) for q in questions):
        raise ValueError("CI selection must be a list of question strings")
    if len(questions) != 10 or len(set(questions)) != 10:
        raise ValueError("CI selection must contain exactly ten distinct questions")
    by_question = {row["user_input"]: row for row in rows}
    if len(by_question) != len(rows):
        raise ValueError("Golden questions must be unique")
    if any(question not in by_question for question in questions):
        raise ValueError("CI question no longer matches the golden set; update the selection explicitly")
    chosen = [by_question[question] for question in questions]
    with manifest.open(encoding="utf-8", newline="") as source:
        departments = {row["file"]: row["department"] for row in csv.DictReader(source)}
    if any(departments.get(s["file"]) != "public" for row in chosen for s in row["sources"]):
        raise ValueError("Hosted CI only evaluates public-department questions; local-only evaluation stays local")
    if sum(row["in_scope"] is True for row in chosen) != 8:
        raise ValueError("CI selection must contain eight in-scope and two out-of-scope questions")
    if sum(row["in_scope"] is False for row in chosen) != 2:
        raise ValueError("CI selection must contain eight in-scope and two out-of-scope questions")
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = select(ROOT / "eval/golden.jsonl", ROOT / "eval/ci-questions.json", ROOT / "data/manifest.csv")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Invalid CI golden subset: {exc}\n")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print("Selected 10 original golden questions: 8 in scope, 2 out of scope, public department")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
