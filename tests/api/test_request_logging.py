import asyncio
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi.testclient import TestClient

from app.log_config import REQUEST_ID, JsonFormatter, configure_logging, get_logger
from app.main import create_app


def test_request_ids_are_generated_per_request_not_copied_from_input(caplog):
    application = create_app()
    client = TestClient(application)
    secret = "customer-015204000835"
    with caplog.at_level(logging.INFO):
        responses = [client.get("/health", headers={"X-Request-ID": secret}) for _ in range(2)]
    ids = {response.headers["x-request-id"] for response in responses}
    assert len(ids) == 2
    assert all(UUID(value).version == 4 for value in ids)
    logs = [json.loads(JsonFormatter().format(record)) for record in caplog.records if record.name.startswith("app.")]
    assert {entry["request_id"] for entry in logs} == ids
    assert secret not in json.dumps(logs)
    assert REQUEST_ID.get() == "-"


def test_concurrent_request_context_isolated_through_await_and_reset(caplog):
    application = create_app()
    logger = get_logger("app.test")

    @application.get("/overlap/{item}")
    async def overlap(item: int):
        before = REQUEST_ID.get()
        await asyncio.sleep(0.01)
        logger.info("overlap.marker")
        return {"before": before, "after": REQUEST_ID.get()}

    with caplog.at_level(logging.INFO), TestClient(application) as client:
        with ThreadPoolExecutor(max_workers=8) as executor:
            responses = list(executor.map(lambda n: client.get(f"/overlap/{n}"), range(8)))
    ids = {response.headers["x-request-id"] for response in responses}
    assert len(ids) == 8
    assert all(
        response.json() == {"before": response.headers["x-request-id"], "after": response.headers["x-request-id"]}
        for response in responses
    )
    markers = [record for record in caplog.records if record.name == "app.test"]
    assert len(markers) == 8
    assert {record.request_id for record in markers} == ids
    assert REQUEST_ID.get() == "-"


def test_json_formatter_is_single_line_and_uses_sentinel_outside_requests():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.Logger("app.formatter")
    logger.addHandler(handler)
    logger.info("line one\nline two")
    lines = stream.getvalue().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["request_id"] == "-"
    assert json.loads(lines[0])["message"] == "line one\nline two"


def test_access_log_omits_raw_url_and_client_address():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("private-client", "GET", "/customer/015204000835?key=private-key", "1.1", 404),
        None,
    )
    payload = JsonFormatter().format(record)
    assert "015204000835" not in payload and "private-" not in payload
    assert json.loads(payload)["status_code"] == 404
    assert json.loads(payload)["method"] == "GET"


def test_exception_formatter_does_not_emit_exception_message_or_traceback():
    secret = "015204000835-private-key"
    error = RuntimeError(secret)
    record = logging.LogRecord("uvicorn.error", logging.ERROR, "", 1, "ASGI failure", (), (RuntimeError, error, None))
    payload = JsonFormatter().format(record)
    assert json.loads(payload)["exception_type"] == "RuntimeError"
    assert secret not in payload


def test_logging_configuration_is_idempotent_and_preserves_capture_handlers(caplog):
    configure_logging()
    configure_logging()
    root = logging.getLogger()
    assert sum(handler.name == "bank-assistant-json" for handler in root.handlers) == 1
    assert caplog.handler in root.handlers
    for name in ("httpx", "httpx2", "httpcore"):
        assert logging.getLogger(name).level == logging.WARNING
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        assert logging.getLogger(name).propagate
        assert not logging.getLogger(name).handlers
    assert logging.getLogger("uvicorn.access").level == logging.WARNING


def test_access_info_suppressed_and_middleware_completion_retained(caplog):
    configure_logging()
    with caplog.at_level(logging.INFO):
        logging.getLogger("uvicorn.access").info("private-url")
        response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert not any(record.name == "uvicorn.access" for record in caplog.records)
    assert sum(record.getMessage() == "http.request.complete" for record in caplog.records) == 1
