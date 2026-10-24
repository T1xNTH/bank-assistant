"""Tests for scripts/agent (lifecycle CLI). Run against a temporary copy of the repo."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENT = REPO / "scripts" / "agent"
IGNORE = shutil.ignore_patterns(".git", ".venv", "data", "__pycache__", "node_modules", ".pytest_cache", ".ruff_cache")

EPIC = "E-901"
EPIC_ROW = f"| `{EPIC}` | `M-901` | `Test epic` | `owner-a` | `{{status}}` | `none` | `pending` | `none` |"


def run_validator(root: Path) -> tuple[bool, set[str]]:
    proc = subprocess.run(
        [sys.executable, "scripts/validate-framework.py"], cwd=root, capture_output=True, text=True
    )
    findings = {line for line in proc.stdout.splitlines() if line.startswith("ERROR")}
    return "FRAMEWORK_VALIDATION_PASS" in proc.stdout, findings


class AgentCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="agent-cli-"))
        self.root = self.tmp / "repo"
        shutil.copytree(REPO, self.root, ignore=IGNORE)
        self.seed_epic("EPIC_READY")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    # ------------------------------------------------------------------ helpers

    def path(self, relative: str) -> Path:
        return self.root / relative

    def read(self, relative: str) -> str:
        return self.path(relative).read_text(encoding="utf-8")

    def seed_epic(self, status: str) -> None:
        epics = self.path(".agent/planning/epics.md")
        lines = epics.read_text(encoding="utf-8").split("\n")
        lines = [ln for ln in lines if ln.strip() != "No epic records are registered." and f"`{EPIC}`" not in ln]
        header = next(i for i, ln in enumerate(lines) if ln.startswith("| Epic ID |"))
        separator = header + 1
        last = separator
        while last + 1 < len(lines) and lines[last + 1].startswith("| `E-"):
            last += 1
        lines.insert(last + 1, EPIC_ROW.format(status=status))
        epics.write_text("\n".join(lines), encoding="utf-8")

    def agent(self, *args: str, expect: int | None = 0) -> subprocess.CompletedProcess:
        env = dict(os.environ, AGENT_ROOT=str(self.root))
        proc = subprocess.run(
            [sys.executable, str(AGENT), *args], capture_output=True, text=True, env=env, cwd=self.root
        )
        if expect is not None:
            self.assertEqual(proc.returncode, expect, f"agent {' '.join(args)}\n{proc.stdout}\n{proc.stderr}")
        return proc

    def task_row(self, task_id: str) -> list[str]:
        for line in self.read(".agent/execution/task-board.md").splitlines():
            if line.startswith(f"| `{task_id}`"):
                return [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        self.fail(f"{task_id} not on task board")

    def epic_row(self) -> list[str]:
        for line in self.read(".agent/planning/epics.md").splitlines():
            if line.startswith(f"| `{EPIC}`"):
                return [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        self.fail("epic row missing")

    def write_record(self, relative: str, status: str) -> None:
        self.path(relative).write_text(
            "---\nid: x\ntitle: x\ntype: governance\ndomain: d\nmodule: m\ntags: [x]\npriority: 2\n---\n"
            f"# x\n\n- **Status**: `{status}`\n",
            encoding="utf-8",
        )

    def started_task(self, task_id: str = "T-901") -> None:
        self.agent("task", "add", task_id, "--epic", EPIC, "--title", "Do it", "--owner", "owner-a")
        if self.epic_row()[4] == "EPIC_READY":
            self.agent("epic", "status", EPIC, "EPIC_IN_PROGRESS")
        self.agent("task", "start", task_id)

    def task_in_review(self, task_id: str = "T-901") -> None:
        self.started_task(task_id)
        self.agent("task", "report", task_id, "--executor", "claude-exec")
        self.agent("task", "verify", task_id, "--cmd", "true")
        self.agent("task", "report", task_id, "--executor", "claude-exec", "--complete")
        self.agent("review", "request", task_id, "--reviewer", "claude-review")

    # ------------------------------------------------------------------ happy path

    def test_full_lifecycle_keeps_framework_valid(self) -> None:
        passed_before, before = run_validator(self.root)
        board_before = self.read(".agent/execution/task-board.md")

        self.task_in_review()
        self.agent("review", "start", "T-901", "--reviewer", "claude-review")
        self.agent("review", "approve", "T-901", "--reviewer", "claude-review")
        self.agent("task", "done", "T-901")
        self.agent("qa", "start", EPIC, "--qa", "qa-bot")
        self.agent("qa", "pass", EPIC, "--qa", "qa-bot")
        self.agent("epic", "status", EPIC, "EPIC_DONE")

        self.assertEqual(self.task_row("T-901")[4], "done")
        self.assertEqual(self.epic_row()[4], "EPIC_DONE")
        self.assertEqual(self.epic_row()[5], "T-901")
        self.assertNotIn("No task records are registered.", self.read(".agent/execution/task-board.md"))
        self.assertNotIn("No session records are registered.", self.read(".agent/execution/sessions-history.md"))
        for rel in (
            ".agent/reports/implementation/T-901.md",
            ".agent/reports/review/T-901.md",
            f".agent/reports/qa/{EPIC}.md",
        ):
            self.assertNotIn("<required", self.read(rel))
        # non-target content of the board survives byte-for-byte
        header = board_before.split("| Task ID |")[0]
        self.assertTrue(self.read(".agent/execution/task-board.md").startswith(header))

        passed_after, after = run_validator(self.root)
        self.assertLessEqual(after, before, f"new validator findings: {after - before}")
        if passed_before:
            self.assertTrue(passed_after)

    def test_status_lists_tasks_by_epic(self) -> None:
        self.agent("task", "add", "T-901", "--epic", EPIC, "--title", "Do it", "--owner", "owner-a")
        out = self.agent("status").stdout
        self.assertIn(f"{EPIC} [EPIC_READY]", out)
        self.assertIn("T-901 [pending] owner-a: Do it", out)

    # ------------------------------------------------------------------ epic rules

    def test_epic_ready_requires_owner(self) -> None:
        self.seed_epic("EPIC_PROPOSED")
        epics = self.path(".agent/planning/epics.md")
        epics.write_text(epics.read_text().replace("`owner-a`", "`unassigned`"))
        self.agent("epic", "status", EPIC, "EPIC_READY", expect=2)
        epics.write_text(epics.read_text().replace("`unassigned`", "`owner-a`"))
        self.agent("epic", "status", EPIC, "EPIC_READY")

    def test_epic_in_progress_requires_a_task(self) -> None:
        self.agent("epic", "status", EPIC, "EPIC_IN_PROGRESS", expect=2)
        self.agent("task", "add", "T-901", "--epic", EPIC, "--title", "t", "--owner", "owner-a")
        self.agent("epic", "status", EPIC, "EPIC_IN_PROGRESS")

    def test_epic_blocked_requires_existing_blocker(self) -> None:
        self.started_task()
        self.agent("epic", "status", EPIC, "EPIC_BLOCKED", expect=2)
        self.agent("epic", "status", EPIC, "EPIC_BLOCKED", "--blocker", "BLOCKER-901", expect=2)
        self.write_record(".agent/governance/blockers/BLOCKER-901.md", "open")
        self.agent("epic", "status", EPIC, "EPIC_BLOCKED", "--blocker", "BLOCKER-901")
        self.assertIn("BLOCKER-901", self.epic_row()[7])
        self.agent("epic", "status", EPIC, "EPIC_IN_PROGRESS", expect=2)
        self.write_record(".agent/governance/blockers/BLOCKER-901.md", "resolved")
        self.agent("epic", "status", EPIC, "EPIC_IN_PROGRESS")

    def test_epic_done_requires_tasks_and_passed_qa(self) -> None:
        self.task_in_review()
        self.agent("epic", "status", EPIC, "EPIC_DONE", expect=2)  # task still in review
        self.agent("review", "start", "T-901", "--reviewer", "claude-review")
        self.agent("review", "approve", "T-901", "--reviewer", "claude-review")
        self.agent("task", "done", "T-901")
        self.agent("epic", "status", EPIC, "EPIC_DONE", expect=2)  # no QA report
        self.agent("qa", "start", EPIC, "--qa", "qa-bot")
        self.agent("qa", "fail", EPIC, "--qa", "qa-bot")
        self.agent("epic", "status", EPIC, "EPIC_DONE", expect=2)  # QA failed
        self.agent("qa", "start", EPIC, "--qa", "qa-bot")
        self.agent("qa", "pass", EPIC, "--qa", "qa-bot")
        self.agent("epic", "status", EPIC, "EPIC_DONE")

    def test_epic_illegal_transition(self) -> None:
        self.agent("epic", "status", EPIC, "EPIC_DONE", expect=2)

    # ------------------------------------------------------------------ task rules

    def test_task_add_only_while_epic_ready(self) -> None:
        self.seed_epic("EPIC_PROPOSED")
        self.agent("task", "add", "T-901", "--epic", EPIC, "--title", "t", "--owner", "o", expect=2)
        self.seed_epic("EPIC_READY")
        self.agent("task", "add", "T-901", "--epic", EPIC, "--title", "t", "--owner", "o")
        self.assertEqual(self.task_row("T-901")[4], "pending")
        self.agent("task", "add", "T-901", "--epic", EPIC, "--title", "t", "--owner", "o", expect=2)

    def test_task_add_rejects_unknown_deps_and_bad_values(self) -> None:
        self.agent("task", "add", "T-902", "--epic", EPIC, "--title", "t", "--owner", "o", "--deps", "T-999", expect=2)
        self.agent("task", "add", "T-902", "--epic", EPIC, "--title", "a|b", "--owner", "o", expect=2)

    def test_task_start_requires_epic_in_progress(self) -> None:
        self.agent("task", "add", "T-901", "--epic", EPIC, "--title", "t", "--owner", "o")
        self.agent("task", "start", "T-901", expect=2)
        self.agent("epic", "status", EPIC, "EPIC_IN_PROGRESS")
        self.agent("task", "start", "T-901")
        self.agent("task", "start", "T-901", expect=2)  # already in progress

    def test_task_start_requires_deps_done(self) -> None:
        self.agent("task", "add", "T-901", "--epic", EPIC, "--title", "t", "--owner", "o")
        self.agent("task", "add", "T-902", "--epic", EPIC, "--title", "t", "--owner", "o", "--deps", "T-901")
        self.agent("epic", "status", EPIC, "EPIC_IN_PROGRESS")
        self.agent("task", "start", "T-902", expect=2)
        self.agent("task", "cancel", "T-901", "--reason", "dropped")
        self.agent("task", "start", "T-902", expect=2)  # cancelled is not done
        self.agent("task", "start", "T-901", expect=2)  # terminal

    def test_task_block_and_unblock(self) -> None:
        self.started_task()
        self.agent("task", "block", "T-901", "--blocker", "BLOCKER-901", expect=2)
        self.write_record(".agent/governance/blockers/BLOCKER-901.md", "open")
        self.agent("task", "block", "T-901", "--blocker", "BLOCKER-901")
        self.assertEqual(self.task_row("T-901")[4], "blocked")
        self.agent("task", "start", "T-901", expect=2)
        self.write_record(".agent/governance/blockers/BLOCKER-901.md", "resolved")
        self.agent("task", "start", "T-901")

    def test_verify_records_failure_and_exit_code(self) -> None:
        self.started_task()
        proc = self.agent("task", "verify", "T-901", "--cmd", "echo boom; false", expect=1)
        self.assertIn("boom", proc.stdout)
        report = self.read(".agent/reports/implementation/T-901.md")
        self.assertIn("`failed`", report)
        self.agent("task", "report", "T-901", "--executor", "claude-exec", "--complete", expect=2)

    def test_report_complete_requires_passed_verify(self) -> None:
        self.started_task()
        self.agent("task", "report", "T-901", "--executor", "claude-exec", "--complete", expect=2)
        self.assertFalse(self.path(".agent/reports/implementation/T-901.md").exists())  # nothing written
        self.agent("task", "report", "T-901", "--executor", "claude-exec")
        self.agent("task", "verify", "T-901", "--cmd", "true")
        self.agent("task", "report", "T-901", "--executor", "claude-exec", "--complete")
        self.assertIn("- **Status**: `complete`", self.read(".agent/reports/implementation/T-901.md"))

    def test_done_requires_approved_review(self) -> None:
        self.task_in_review()
        self.agent("task", "done", "T-901", expect=2)
        self.agent("review", "start", "T-901", "--reviewer", "claude-review")
        self.agent("task", "done", "T-901", expect=2)  # draft review

    # ------------------------------------------------------------------ review rules

    def test_review_request_requires_complete_report(self) -> None:
        self.started_task()
        self.agent("task", "report", "T-901", "--executor", "claude-exec")
        self.agent("review", "request", "T-901", "--reviewer", "claude-review", expect=2)

    def test_reviewer_must_differ_from_executor(self) -> None:
        self.started_task()
        self.agent("task", "report", "T-901", "--executor", "claude-exec")
        self.agent("task", "verify", "T-901", "--cmd", "true")
        self.agent("task", "report", "T-901", "--executor", "claude-exec", "--complete")
        self.agent("review", "request", "T-901", "--reviewer", "claude-exec", expect=2)
        self.agent("review", "request", "T-901", "--reviewer", "claude-review")
        self.agent("review", "start", "T-901", "--reviewer", "claude-exec", expect=2)
        self.agent("review", "start", "T-901", "--reviewer", "claude-review")
        self.agent("review", "approve", "T-901", "--reviewer", "claude-exec", expect=2)

    def test_request_changes_returns_task_to_in_progress(self) -> None:
        self.task_in_review()
        self.agent("review", "start", "T-901", "--reviewer", "claude-review")
        self.agent("review", "request-changes", "T-901", "--reviewer", "claude-review")
        self.assertEqual(self.task_row("T-901")[4], "in-progress")
        self.assertIn("- **Status**: `changes-required`", self.read(".agent/reports/review/T-901.md"))
        self.assertIn("- **Status**: `draft`", self.read(".agent/reports/implementation/T-901.md"))
        # second round
        self.agent("task", "verify", "T-901", "--cmd", "true")
        self.agent("task", "report", "T-901", "--executor", "claude-exec", "--complete")
        self.agent("review", "request", "T-901", "--reviewer", "claude-review")
        self.agent("review", "start", "T-901", "--reviewer", "claude-review")
        self.agent("review", "approve", "T-901", "--reviewer", "claude-review")
        self.agent("task", "done", "T-901")

    # ------------------------------------------------------------------ qa rules

    def test_qa_start_requires_all_tasks_terminal(self) -> None:
        self.started_task()
        self.agent("qa", "start", EPIC, "--qa", "qa-bot", expect=2)
        self.agent("qa", "pass", EPIC, "--qa", "qa-bot", expect=2)  # no report yet

    def test_sessions_history_appended_per_mutation(self) -> None:
        def session_rows() -> list[str]:
            text = self.read(".agent/execution/sessions-history.md")
            return [ln for ln in text.splitlines() if ln.startswith("| `S-")]

        before = len(session_rows())
        self.started_task()
        rows = session_rows()[before:]
        self.assertEqual(len(rows), 3)  # add, epic status, start
        ids = [r.split("|")[1].strip() for r in rows]
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(all(re.fullmatch(r"`S-\d{8}-\d{6}(-\d+)?`", i) for i in ids))
        self.assertTrue(all("`completed`" in r for r in rows))


if __name__ == "__main__":
    unittest.main()
