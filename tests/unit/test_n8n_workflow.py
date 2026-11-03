"""Exercise exported workflow code, including fail-closed approval and polling paths."""

import json
import re
import shutil
import subprocess
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = json.loads((ROOT / "infrastructure/n8n/workflows/intake-to-reply.json").read_text(encoding="utf-8"))
NODES = {n["name"]: n for n in WORKFLOW["nodes"]}


def run_js(code, payload, *, classification=None, run_index=0, intake=None):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required to execute n8n expressions")
    script = """
const [code, payload, classification, runIndex, intake] = JSON.parse(process.argv[1]);
const input = {all: () => [{json: payload}]};
const lookup = name => ({first: () => ({json: name === 'Validate intake' ? intake : classification})});
try {
  const result = new Function('$json', '$input', '$', '$runIndex', code)(payload, input, lookup, runIndex);
  console.log(JSON.stringify({result}));
} catch (e) { console.log(JSON.stringify({error: e.message})); }
"""
    result = subprocess.run(
        [node, "-e", script, json.dumps([code, payload, classification, run_index, intake])],
        capture_output=True, text=True, check=True, encoding="utf-8",
    )
    return json.loads(result.stdout)


def execute(name, payload, **kwargs):
    return run_js(NODES[name]["parameters"]["jsCode"], payload, **kwargs)


@pytest.mark.parametrize("email", ["a@example.test,b@example.test", "a@example.test\r\nBcc: b@example.test", "bad"])
def test_intake_rejects_multiple_or_invalid_recipients(email):
    assert "error" in execute("Validate intake", {"Email": email, "Message": "Question?"})


def test_intake_bounds_and_normalizes():
    assert execute("Validate intake", {"Email": " a@example.test ", "Message": " Question? "}) == {
        "result": [{"json": {"email": "a@example.test", "message": "Question?"}}],
    }
    assert "error" in execute("Validate intake", {"Email": "a@example.test", "Message": "x" * 2001})


def test_poll_budget_and_unknown_status_fail_closed():
    assert "result" in execute("Poll budget", {}, run_index=59)
    assert "error" in execute("Poll budget", {}, run_index=60)
    assert "error" in execute("Validate job", {"status": "unknown"})


def test_draft_preserves_citations_and_refuses_unsourced_answer():
    payload = {"status": "done", "result": {
        "found": True, "answer": "Annual fee [1]", "citations": [{"n": 1, "source": "fees.pdf", "page": 2}],
    }}
    classification = {"intent": "question", "needs_human": False}
    result = execute("Prepare draft", payload, classification=classification)
    assert "Annual fee [1]" in result["result"][0]["json"]["text"]
    assert "fees.pdf" in result["result"][0]["json"]["text"]
    assert "2" in result["result"][0]["json"]["text"]
    payload["result"]["citations"] = []
    assert "error" in execute("Prepare draft", payload, classification=classification)


def test_missing_answer_uses_refusal_without_relaying_model_text():
    result = execute(
        "Prepare draft", {"status": "done", "result": {"found": False, "answer": "UNSUPPORTED"}},
        classification={"intent": "question", "needs_human": False},
    )
    assert "UNSUPPORTED" not in result["result"][0]["json"]["text"]


@pytest.mark.parametrize("classification", [{"intent": "unknown", "needs_human": False},
                                          {"intent": "question", "needs_human": "false"}])
def test_malformed_classification_stops(classification):
    assert "error" in execute("Validate classification", classification)


@pytest.mark.parametrize("intent,human", [("complaint", True), ("request", True), ("question", True), ("other", False)])
def test_handoff_does_not_relay_classifier_answer(intent, human):
    result = execute("Prepare draft", {}, classification={"intent": intent, "needs_human": human, "answer": "UNSAFE"})
    assert "UNSAFE" not in result["result"][0]["json"]["text"]


@pytest.mark.parametrize("data", [{"approved": False}, {}, {"approved": "true"}, {"approved": True}])
def test_only_explicit_boolean_approval_sends_reply(data):
    expression = NODES["Approved"]["parameters"]["conditions"]["conditions"][0]["leftValue"]
    expression = expression.removeprefix("={{ ").removesuffix(" }}")
    assert run_js("return " + expression, {"data": data})["result"] is (data.get("approved") is True)
    assert WORKFLOW["connections"]["Approved"]["main"][1][0]["node"] == "No reply"


@pytest.mark.parametrize("email,question", [
    ("first@example.test", "Annual fee?"),
    ("second@example.test", "<script>unsafe</script> & 'quoted' question?"),
])
def test_review_message_includes_recipient_question_and_draft(email, question):
    expression = NODES["Review draft"]["parameters"]["message"].removeprefix("={{ ").removesuffix(" }}")
    payload = {"intent": "question", "needs_human": False, "text": "Answer [1]\nfees.pdf page 3 <i>policy</i> & fees"}
    result = run_js("return " + expression, payload, intake={"email": email, "message": question})["result"]
    # Pinned n8n 2.45.7 decodes these named entities before inserting into HTML.
    # Model that external boundary so ordinary named-entity escaping cannot regress unnoticed.
    html_message = re.sub(r"&amp;|&lt;|&gt;|&#39;|&quot;", lambda m: unescape(m[0]), result)
    text = unescape(html_message)
    assert email in text
    assert question in text
    assert payload["text"] in text
    assert text.index(email) < text.index(question) < text.index(payload["text"])
    tags = []
    parser = HTMLParser()
    parser.handle_starttag = lambda tag, attrs: tags.append(tag)
    parser.feed(html_message)
    assert tags == []


def test_execution_cap_covers_approval_plus_poll_and_delivery():
    compose = yaml.safe_load((ROOT / "infrastructure/compose.yaml").read_text())
    maximum = int(compose["services"]["n8n"]["environment"]["EXECUTIONS_TIMEOUT_MAX"])
    budget = WORKFLOW["settings"]["executionTimeout"]
    approval = NODES["Review draft"]["parameters"]["options"]["limitWaitTime"]["values"]
    assert approval["resumeUnit"] == "hours"
    # 60 worst-case polls (5s Wait + 15s HTTP) plus classification, enqueue and delivery margin.
    assert approval["resumeAmount"] * 3600 + 60 * (5 + 15) + 60 <= budget <= maximum


def test_profile_ports_and_credential_references():
    compose = yaml.safe_load((ROOT / "infrastructure/compose.yaml").read_text())
    for service in ("n8n", "mailpit"):
        assert compose["services"][service]["profiles"] == ["automation"]
        assert all(port.startswith("127.0.0.1:") for port in compose["services"][service]["ports"])
    for name in ("Classify", "Enqueue", "Poll job"):
        assert NODES[name]["credentials"]["httpHeaderAuth"]["id"] == "bank-public-service"
    assert WORKFLOW["active"] is False
    assert WORKFLOW["pinData"] == {}
    assert NODES["Review draft"]["parameters"]["operation"] == "sendAndWait"
    assert NODES["Intake form"]["parameters"]["options"]["path"] == "bank-intake"
    assert WORKFLOW["connections"]["Job failed"]["main"][1][0]["node"] == "Poll budget"
