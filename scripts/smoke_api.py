"""Exercise a running API with fake backends over HTTP (no TestClient or extra dependencies).

Usage: python scripts/smoke_api.py [--base-url http://127.0.0.1:8000] [--qdrant-url http://qdrant:6333]
Run inside the API container in CI. A failure exits nonzero; no cloud keys or corpus are required.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def request_json(base_url: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = Request(base_url.rstrip("/") + path, data=data, headers={"Content-Type": "application/json"})
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error  # validation/404 responses are checked below, never treated as success by default
    with response:
        status = response.status
        require(UUID(response.headers.get("X-Request-ID", "")).version == 4, f"{path}: missing/invalid request id")
        body = json.loads(response.read().decode("utf-8"))
    require(isinstance(body, dict), f"{path}: expected a JSON object")
    return status, body


def check_api(base_url: str) -> None:
    status, body = request_json(base_url, "/health")
    require(status == 200 and body == {"status": "ok"}, "/health: API is not healthy")

    status, body = request_json(base_url, "/ask", {"question": "Phí thường niên thẻ?", "mode": "dense"})
    require(status == 200 and body.get("found") is True, "/ask: expected an answer from the fake backend")
    require(isinstance(body.get("answer"), str) and bool(body["answer"].strip()), "/ask: empty answer")
    require(body.get("retrieval_mode") == "dense", "/ask: requested retrieval mode was not preserved")
    citations = body.get("citations")
    require(isinstance(citations, list) and bool(citations), "/ask: missing citations")
    for citation in citations:
        require(isinstance(citation, dict), "/ask: invalid citation")
        require(isinstance(citation.get("source"), str) and bool(citation["source"]), "/ask: missing source")
        require(isinstance(citation.get("page"), int) and citation["page"] >= 1, "/ask: invalid page")

    status, body = request_json(base_url, "/ask", {"question": "Câu hỏi ngoài phạm vi"})
    require(status == 200 and body.get("found") is False, "/ask: expected an out-of-scope refusal")
    require(isinstance(body.get("answer"), str) and bool(body["answer"].strip()), "/ask: empty refusal")
    require(body.get("citations") == [], "/ask: refusal must not contain citations")

    for path, payload, expected_status, code in (
        ("/ask", {"question": ""}, 400, "BAD_REQUEST"),
        ("/ci-missing-route", None, 404, "NOT_FOUND"),
    ):
        status, body = request_json(base_url, path, payload)
        require(status == expected_status, f"{path}: expected HTTP {expected_status}, got {status}")
        error = body.get("error")
        require(isinstance(error, dict) and error.get("code") == code, f"{path}: invalid error envelope")
    print("API smoke passed: health, answer/citations, refusal, validation, 404 and request IDs")


def wait_for_qdrant(base_url: str) -> None:
    deadline = time.monotonic() + 60
    url = base_url.rstrip("/") + "/readyz"
    while True:
        try:
            with urlopen(url, timeout=5) as response:
                require(response.status == 200, "Qdrant is not ready")
            print("Qdrant readiness passed")
            return
        except (URLError, TimeoutError) as error:
            if time.monotonic() >= deadline:
                raise RuntimeError("Qdrant did not become ready within 60 seconds") from error
            time.sleep(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--qdrant-url")
    args = parser.parse_args()
    try:
        check_api(args.base_url)
        if args.qdrant_url:
            wait_for_qdrant(args.qdrant_url)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Smoke failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
