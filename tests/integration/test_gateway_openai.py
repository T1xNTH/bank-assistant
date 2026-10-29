"""Real pinned LiteLLM + local fake OpenAI: no credentials or paid API calls."""

import json
import os
import secrets
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
FAKE = '''import json
from http.server import BaseHTTPRequestHandler, HTTPServer
count = 0
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def send(self, code, payload):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())
    def do_GET(self):
        self.send(200, {"calls": count})
    def do_POST(self):
        global count
        count += 1
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if request["messages"][0]["content"] == "force-rate-limit":
            return self.send(429, {"error": {"message": "Synthetic rate limit",
                "type": "rate_limit_error", "code": "rate_limit_exceeded"}})
        content = json.dumps({"reply": "pong"}) if "response_format" in request else "pong"
        self.send(200, {"id": "chatcmpl-test", "object": "chat.completion", "created": 1,
            "model": request["model"], "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}})
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
'''


@pytest.fixture(scope="module")
def gateway(tmp_path_factory):
    directory = tmp_path_factory.mktemp("openai-gateway")
    (directory / "fake.py").write_text(FAKE)
    config = (ROOT / "infrastructure/litellm/config.yaml").read_text()
    config = config.replace("api_key: os.environ/OPENAI_API_KEY",
                            "api_key: os.environ/OPENAI_API_KEY\n      api_base: http://fake-provider:8080/v1")
    (directory / "config.yaml").write_text(config)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    override = directory / "compose.yaml"
    override.write_text(f'''services:
  litellm:
    ports: !override ["127.0.0.1:{port}:4000"]
    volumes: [{directory}/config.yaml:/app/config.yaml:ro]
    depends_on: [fake-provider]
  fake-provider:
    image: python:3.12-slim
    command: [python, /fake.py]
    volumes: [{directory}/fake.py:/fake.py:ro]
''')
    env = {**os.environ, "OPENAI_API_KEY": "synthetic-provider-key", "OPENAI_MODEL": "gpt-6-luna",
           "LITELLM_MASTER_KEY": "sk-" + secrets.token_hex(32), "COMPOSE_PROFILES": ""}
    command = ["docker", "compose", "--env-file", str(ROOT / ".env.example"), "-p",
               "bank-openai-test-" + secrets.token_hex(4), "-f", str(ROOT / "infrastructure/compose.yaml"),
               "-f", str(override)]
    try:
        started = subprocess.run(command + ["up", "-d", "--wait", "--wait-timeout", "180",
                                            "litellm", "fake-provider"], env=env, capture_output=True, timeout=240)
        assert started.returncode == 0, "Synthetic gateway failed to start (output withheld)"
        yield f"http://127.0.0.1:{port}", env, command
    finally:
        subprocess.run(command + ["down", "--remove-orphans"], env=env, capture_output=True, timeout=60)


def calls(env, command):
    code = "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/stats').read().decode())"
    result = subprocess.run(command + ["exec", "-T", "fake-provider", "python", "-c", code],
                            env=env, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)["calls"]


@pytest.mark.parametrize("structured", [False, True])
def test_openai_smoke_through_real_gateway(gateway, structured):
    url, env, command = gateway
    before = calls(env, command)
    args = [sys.executable, str(ROOT / "scripts/smoke_llm.py"), "--base-url", url,
            "--models", "cloud-chat", "--timeout", "30"]
    if structured:
        args.append("--structured")
    result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, "OpenAI synthetic smoke failed"
    assert "PASS cloud-chat" in result.stdout
    assert calls(env, command) == before + 1


def test_rate_limit_does_not_retry_provider(gateway):
    url, env, command = gateway
    before = calls(env, command)
    request = urllib.request.Request(url + "/v1/chat/completions", data=json.dumps({
        "model": "cloud-chat", "messages": [{"role": "user", "content": "force-rate-limit"}],
        "max_completion_tokens": 32,
    }).encode(), headers={"Content-Type": "application/json",
                          "Authorization": "Bearer " + env["LITELLM_MASTER_KEY"]})
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=30)
    assert error.value.code == 429
    assert calls(env, command) == before + 1
