"""Run the actual alert sanitizer against untrusted n8n error payloads."""

import json

import pytest

from tests.unit.test_n8n_workflow import NODES, ROOT, WORKFLOW, run_js

HANDLER = json.loads((ROOT / "infrastructure/n8n/workflows/error-handler.json").read_text(encoding="utf-8"))
ALERT_NODES = {node["name"]: node for node in HANDLER["nodes"]}


def alert(payload):
    return run_js(ALERT_NODES["Safe alert"]["parameters"]["jsCode"], payload)["result"][0]["json"]


@pytest.mark.parametrize("node,code,reason", [
    ("Classify", "429", "http_429"),
    ("Enqueue", 503, "http_503"),
    ("Poll job", "503", "http_503"),
    ("Poll job", None, "execution_error"),
    ("Stop failed job", None, "job_failed"),
    ("Poll budget", None, "poll_timeout"),
])
def test_alert_reports_safe_reason_and_local_execution(node, code, reason):
    result = alert({"execution": {"id": "123", "lastNodeExecuted": node, "error": {"httpCode": code}}})
    assert set(result) == {"text"}
    assert f"Reason: {reason}\n" in result["text"]
    assert f"Node: {node}\n" in result["text"]
    assert "http://127.0.0.1:5678/workflow/bankIntakeToReply/executions/123" in result["text"]


@pytest.mark.parametrize("execution_id", [
    "alice@example.test", "123\nBcc: alice@example.test", "9" * 21, {}, 123, None,
])
def test_alert_drops_all_free_text_and_injected_metadata(execution_id):
    private = "alice@example.test OTP=123456 account=0123456789 secret-key"
    result = alert({
        "Email": private, "Message": private,
        "workflow": {"id": private, "name": private},
        "execution": {"id": execution_id, "url": "https://evil.test/" + private,
                      "lastNodeExecuted": private, "retryOf": private,
                      "error": {"message": private, "stack": private, "description": private,
                                "httpCode": private, "context": {"body": private, "headers": private}}},
    })
    assert result == alert({})
    assert "Execution: unavailable" in result["text"]


def test_trigger_failure_without_execution_has_safe_fallback():
    private = "alice@example.test secret-key"
    result = alert({"trigger": {"error": {"message": private, "node": {"name": private}}}})
    assert "Reason: trigger_error" in result["text"]
    assert "Execution: unavailable" in result["text"]
    assert private not in result["text"]


def test_import_wiring_smtp_and_fail_closed_paths():
    assert WORKFLOW["settings"]["errorWorkflow"] == HANDLER["id"]
    assert ALERT_NODES["Error Trigger"]["type"] == "n8n-nodes-base.errorTrigger"
    assert HANDLER["connections"]["Error Trigger"]["main"][0][0]["node"] == "Safe alert"
    assert HANDLER["connections"]["Safe alert"]["main"][0][0]["node"] == "Notify operator"
    mail = ALERT_NODES["Notify operator"]
    assert mail["parameters"]["toEmail"] == "operator@example.test"
    assert mail["parameters"]["emailFormat"] == "text"
    assert mail["parameters"]["text"] == "={{ $json.text }}"
    assert mail["credentials"]["smtp"]["id"] == "mailpit-smtp"
    assert HANDLER["settings"]["saveDataErrorExecution"] == "none"
    assert not HANDLER["settings"].get("errorWorkflow")
    assert HANDLER["pinData"] == {}
    for name in ("Classify", "Enqueue", "Poll job"):
        node = NODES[name]
        assert not node.get("continueOnFail") and not node.get("retryOnFail")
        assert node.get("onError", "stopWorkflow") == "stopWorkflow"
        assert not node["parameters"]["options"].get("response", {}).get("response", {}).get("neverError")
    assert WORKFLOW["connections"]["Job failed"]["main"][0][0]["node"] == "Stop failed job"
    assert NODES["Stop failed job"]["type"] == "n8n-nodes-base.stopAndError"
    makefile = (ROOT / "Makefile").read_text()
    assert makefile.index("--input=/workflows/error-handler.json") < makefile.index(
        "--input=/workflows/intake-to-reply.json",
    )
