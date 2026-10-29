"""Check smoke verdicts and avoid leaking credentials/provider error bodies."""

import importlib.util
import io
import json
import urllib.error
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "smoke_llm", Path(__file__).resolve().parents[2] / "scripts/smoke_llm.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def test_checks_both_aliases_with_auth(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["smoke_llm"])
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-test-secret")
    seen = []

    def respond(request, timeout):
        assert request.full_url == "http://127.0.0.1:4000/v1/chat/completions"
        assert request.get_header("Authorization") == "Bearer sk-test-secret"
        seen.append(json.loads(request.data)["model"])
        return io.BytesIO(b'{"choices":[{"message":{"content":"pong"}}]}')

    monkeypatch.setattr(smoke.urllib.request, "urlopen", respond)
    assert smoke.main() == 0
    assert seen == ["cloud-chat", "local-chat"]
    assert "sk-test-secret" not in capsys.readouterr().out


@pytest.mark.parametrize("payload", [b'{}', b'{"choices":[]}',
    b'{"choices":[{"message":{"content":" "}}]}'])
def test_rejects_missing_or_empty_completion(monkeypatch, payload):
    monkeypatch.setattr("sys.argv", ["smoke_llm", "--models", "local-chat"])
    monkeypatch.setattr(smoke.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(payload))
    assert smoke.main() == 1


def test_provider_error_is_redacted_and_other_alias_still_checked(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["smoke_llm"])
    seen = []

    def respond(request, timeout):
        model = json.loads(request.data)["model"]
        seen.append(model)
        if model == "cloud-chat":
            raise urllib.error.HTTPError(request.full_url, 401, "secret-detail", {},
                                         io.BytesIO(b'secret-provider-body'))
        return io.BytesIO(b'{"choices":[{"message":{"content":"pong"}}]}')

    monkeypatch.setattr(smoke.urllib.request, "urlopen", respond)
    assert smoke.main() == 1
    assert seen == ["cloud-chat", "local-chat"]
    output = capsys.readouterr()
    assert "401" in output.err
    assert "secret" not in output.err + output.out


def test_connection_reset_is_a_failed_smoke_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["smoke_llm", "--models", "local-chat"])

    def reset(*args, **kwargs):
        raise ConnectionResetError("private network detail")

    monkeypatch.setattr(smoke.urllib.request, "urlopen", reset)
    assert smoke.main() == 1
    assert "private network detail" not in capsys.readouterr().err
