"""Recovery must reject damaged backups and existing destination collections."""

import importlib.util
import json
from pathlib import Path

import httpx2 as httpx
import pytest
import yaml

spec = importlib.util.spec_from_file_location(
    "qdrant_backup", Path(__file__).resolve().parents[2] / "scripts/qdrant_backup.py",
)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def client(handler):
    return httpx.Client(base_url="http://qdrant", transport=httpx.MockTransport(handler))


def make_backup(tmp_path):
    def handler(request):
        if request.url.path.endswith("/points/count"):
            return httpx.Response(200, json={"result": {"count": 3}})
        if request.method == "POST":
            return httpx.Response(200, json={"result": {"name": "test.snapshot"}})
        return httpx.Response(200, content=b"snapshot-data")
    with client(handler) as connection:
        assert tool.backup(connection, "docs", tmp_path) == 3


@pytest.mark.parametrize("failure", ["checksum", "collection", "filename", "count"])
def test_invalid_backup_never_contacts_destination(tmp_path, failure):
    make_backup(tmp_path)
    manifest = json.loads((tmp_path / "backup.json").read_text())
    if failure == "checksum":
        (tmp_path / manifest["snapshot"]).write_bytes(b"corrupt")
    elif failure == "collection":
        manifest["collection"] = "other"
    elif failure == "filename":
        manifest["snapshot"] = "../escape.snapshot"
    else:
        manifest["points_count"] = True
    (tmp_path / "backup.json").write_text(json.dumps(manifest))
    with client(lambda request: pytest.fail("invalid backup contacted destination")) as connection:
        with pytest.raises(ValueError):
            tool.restore(connection, "docs", tmp_path)


def test_restore_refuses_existing_collection(tmp_path):
    make_backup(tmp_path)
    def handler(request):
        assert request.method == "GET"
        return httpx.Response(200, json={"result": {}})
    with client(handler) as connection, pytest.raises(ValueError, match="already exists"):
        tool.restore(connection, "docs", tmp_path)


@pytest.mark.parametrize("restored_count", [3, 2])
def test_restore_upload_and_exact_count(tmp_path, restored_count):
    make_backup(tmp_path)
    def handler(request):
        if request.method == "GET":
            return httpx.Response(404)
        if request.url.path.endswith("/upload"):
            assert request.url.params["priority"] == "snapshot"
            assert request.url.params["wait"] == "true"
            assert b"snapshot-data" in request.read()
            return httpx.Response(200, json={"result": True})
        assert json.loads(request.content) == {"exact": True}
        return httpx.Response(200, json={"result": {"count": restored_count}})
    with client(handler) as connection:
        if restored_count == 3:
            assert tool.restore(connection, "docs", tmp_path) == 3
        else:
            with pytest.raises(ValueError, match="count mismatch"):
                tool.restore(connection, "docs", tmp_path)


def test_failed_backup_preserves_previous_manifest(tmp_path):
    make_backup(tmp_path)
    previous = (tmp_path / "backup.json").read_bytes()
    counts = iter([3, 4])
    def handler(request):
        if request.url.path.endswith("/points/count"):
            return httpx.Response(200, json={"result": {"count": next(counts)}})
        if request.method == "POST":
            return httpx.Response(200, json={"result": {"name": "changed.snapshot"}})
        return httpx.Response(200, content=b"changed")
    with client(handler) as connection, pytest.raises(ValueError, match="changed"):
        tool.backup(connection, "docs", tmp_path)
    assert (tmp_path / "backup.json").read_bytes() == previous
    assert not list(tmp_path.glob("*.partial"))


@pytest.mark.parametrize("profile", ["local-llm", "automation", "obs"])
def test_profile_has_no_dependency_on_other_profiles(profile):
    compose = yaml.safe_load((Path(__file__).resolve().parents[2] / "infrastructure/compose.yaml").read_text())
    active = {
        name: service for name, service in compose["services"].items()
        if not service.get("profiles") or profile in service["profiles"]
    }
    assert any(profile in service.get("profiles", []) for service in active.values())
    for name, service in active.items():
        assert set(service.get("depends_on", [])) <= active.keys(), name
        assert service.get("healthcheck"), name
