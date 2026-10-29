import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.contracts import User
from app.main import create_app
from app.security.auth import get_current_user, require_role

KEY = "test-only-key"
IDENTITY = {"user_id": "tester", "department": "credit", "role": "approver"}


@pytest.fixture
def auth(tmp_path, monkeypatch):
    path = tmp_path / "keys.json"
    path.write_text(json.dumps({hashlib.sha256(KEY.encode()).hexdigest(): IDENTITY}), encoding="utf-8")
    monkeypatch.setenv("AUTH_BACKEND", "apikey")
    monkeypatch.setenv("API_KEYS_FILE", str(path))
    app = create_app()

    @app.get("/identity")
    def identity(user: User = Depends(get_current_user)):
        return asdict(user)

    approver = require_role("approver")

    @app.get("/approval")
    def approval(user: User = Depends(approver)):
        return asdict(user)

    return TestClient(app), path


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}, {"X-API-Key": ""}])
@pytest.mark.parametrize("route", ["/identity", "/approval", "/ask"])
def test_missing_invalid_key_is_401(auth, headers, route):
    client, _ = auth
    response = client.post(route, json={"question": "test"}, headers=headers) if route == "/ask" else client.get(
        route, headers=headers
    )
    assert response.status_code == 401
    assert response.json() == {"error": {"code": "UNAUTHORIZED", "message": "Unauthorized"}}
    assert response.headers["X-Request-ID"]


def test_identity_role_and_ask(auth):
    client, _ = auth
    for route in ("/identity", "/approval"):
        response = client.get(route, headers={"x-api-key": KEY})
        assert response.status_code == 200
        assert response.json() == IDENTITY
    assert client.post("/ask", json={"question": "test"}, headers={"X-API-Key": KEY}).status_code == 200
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("role", ["staff", "service"])
def test_wrong_role_is_403(auth, role):
    client, path = auth
    records = json.loads(path.read_text())
    records[hashlib.sha256(KEY.encode()).hexdigest()]["role"] = role
    path.write_text(json.dumps(records))
    response = client.get("/approval", headers={"X-API-Key": KEY})
    assert response.status_code == 403
    assert response.json() == {"error": {"code": "FORBIDDEN", "message": "Forbidden"}}


def test_revocation_applies_without_restart(auth):
    client, path = auth
    assert client.get("/identity", headers={"X-API-Key": KEY}).status_code == 200
    path.write_text("{}")
    assert client.get("/identity", headers={"X-API-Key": KEY}).status_code == 401


@pytest.mark.parametrize("content", [None, "{", "[]", '{"plaintext": {}}', json.dumps({
    hashlib.sha256(KEY.encode()).hexdigest(): {**IDENTITY, "role": "admin"}
})])
def test_bad_registry_fails_closed(auth, content, caplog):
    client, path = auth
    if content is None:
        path.unlink()
    else:
        path.write_text(content)
    response = client.get("/identity", headers={"X-API-Key": KEY})
    assert response.status_code == 503
    assert KEY not in response.text + caplog.text
    assert str(path) not in response.text


def test_backend_switch(auth, monkeypatch):
    client, _ = auth
    monkeypatch.setenv("AUTH_BACKEND", "fake")
    assert client.get("/identity").json() == {"user_id": "dev", "department": "public", "role": "staff"}
    assert client.get("/approval").status_code == 403
    monkeypatch.setenv("AUTH_BACKEND", "typo")
    assert client.get("/identity").status_code == 503


def test_dependency_override_applies_to_role(auth):
    client, _ = auth
    client.app.dependency_overrides[get_current_user] = lambda: User("override", "hr", "approver")
    assert client.get("/approval").json()["user_id"] == "override"


def test_generated_keys_store_only_hashes(auth):
    client, path = auth
    script = Path(__file__).resolve().parents[2] / "scripts" / "make_key.py"
    keys = []
    for _ in range(2):
        result = subprocess.run([
            sys.executable, str(script), "--user-id", "new-user", "--department", "hr",
            "--role", "approver", "--file", str(path),
        ], capture_output=True, text=True, check=True)
        key = result.stdout.strip()
        keys.append(key)
        assert len(key) >= 43
        assert key not in path.read_text()
        assert client.get("/approval", headers={"X-API-Key": key}).json()["user_id"] == "new-user"
    assert keys[0] != keys[1]
    assert len(json.loads(path.read_text())) == 3


@pytest.mark.parametrize("content", ["invalid", '{"_comment": "legacy", "keys": {}}', json.dumps({
    hashlib.sha256(KEY.encode()).hexdigest(): {**IDENTITY, "role": "admin"}
})])
def test_key_generator_preserves_invalid_file(tmp_path, content):
    path = tmp_path / "keys.json"
    path.write_text(content)
    result = subprocess.run([
        sys.executable, "scripts/make_key.py", "--user-id", "test", "--department", "public", "--file", str(path),
    ], capture_output=True, text=True)
    assert result.returncode != 0
    assert not result.stdout
    assert path.read_text() == content


def test_example_provision_authenticate(auth):
    client, path = auth
    path.write_bytes(Path("config/api_keys.example.json").read_bytes())
    result = subprocess.run([
        sys.executable, "scripts/make_key.py", "--user-id", "from-example", "--department", "public",
        "--file", str(path),
    ], capture_output=True, text=True, check=True)
    response = client.get("/identity", headers={"X-API-Key": result.stdout.strip()})
    assert response.status_code == 200
    assert response.json()["user_id"] == "from-example"
