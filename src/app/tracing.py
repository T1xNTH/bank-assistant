"""Langfuse tracing helpers (inputs masked before tracing).

Owner: B — Epic E-013. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import json
import os
import re
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache

from app.contracts import LLMResult
from app.llm_cost import CURRENT_USAGE, cost_of
from app.security.masking import REDACTED, MaskingError, require_mask_content

_CURRENT: ContextVar[Observation | None] = ContextVar("bank_trace", default=None)
_BACKEND_LOCK = threading.Lock()


def _after_fork() -> None:
    global _BACKEND_LOCK
    _BACKEND_LOCK = threading.Lock()  # A child must not inherit a lock held by a vanished thread.


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork)


def _safe(value):
    if isinstance(value, str):
        try:
            return require_mask_content(value)
        except MaskingError:
            return REDACTED
    if isinstance(value, dict):
        return {_safe(str(k)): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if value is None or type(value) in (bool, int, float):
        return value
    return "<REDACTED>"


@lru_cache(maxsize=1)
def _backend(pid: int, public: str, secret: str, base: str):
    # A provider per process prevents RQ forks from reusing the parent's exporter thread.
    from langfuse import Langfuse
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider()
    client = Langfuse(
        public_key=public, secret_key=secret, base_url=base, tracer_provider=provider, timeout=2,
        should_export_span=lambda span: span.instrumentation_scope.name == "bank-assistant",
    )
    return client, provider.get_tracer("bank-assistant")


def _runtime():
    public, secret = os.getenv("LANGFUSE_PUBLIC_KEY", ""), os.getenv("LANGFUSE_SECRET_KEY", "")
    if not public or not secret:
        return None  # No SDK import, thread or network activity without both keys.
    try:
        # lru_cache allows concurrent cache misses; serialize construction as well as cache access.
        with _BACKEND_LOCK:
            return _backend(os.getpid(), public, secret, os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000"))
    except Exception:
        return None  # Telemetry must never change the answer's availability.


class Observation:
    def __init__(self, span=None, name: str = "", root: bool = False):
        self.span, self.name, self.root = span, name, root
        self.metadata: dict = {}

    @property
    def trace_id(self) -> str | None:
        return f"{self.span.get_span_context().trace_id:032x}" if self.span is not None else None

    def update(self, *, input=None, output=None, metadata=None):
        if metadata is not None:
            self.metadata.update(metadata)
            metadata = self.metadata
        if self.span is None:
            return
        try:
            for key, value in (("input", input), ("output", output), ("metadata", metadata)):
                if value is not None:
                    encoded = json.dumps(_safe(value), ensure_ascii=False)
                    self.span.set_attribute(f"langfuse.observation.{key}", encoded)
                    if self.root:
                        self.span.set_attribute(f"langfuse.trace.{key}", encoded)
            if metadata is not None and "found" in metadata:
                self.span.set_attribute("langfuse.trace.tags", [f"found={str(bool(metadata['found'])).lower()}"])
        except Exception:
            pass

    def generation(self, result: LLMResult) -> None:
        """Record accounting before attempting optional telemetry; never capture the prompt."""
        cost = cost_of(result.model, result.input_tokens, result.output_tokens)
        if result.meta.get("usage_known") is False:
            cost = None
        usage = CURRENT_USAGE.get()
        if usage is not None:
            usage.calls += 1
            usage.input_tokens += result.input_tokens
            usage.output_tokens += result.output_tokens
            usage.unknown |= cost is None
            usage.total += cost or 0.0
        if self.span is None:
            return
        try:
            self.span.set_attribute("langfuse.observation.type", "generation")
            self.span.set_attribute("langfuse.observation.model.name", _safe(result.model))
            self.span.set_attribute("langfuse.observation.usage_details", json.dumps({
                "input": result.input_tokens, "output": result.output_tokens,
            }))
            if cost is not None:
                self.span.set_attribute("langfuse.observation.cost_details", json.dumps({"total": cost}))
            self.update(metadata={"cost_usd": cost})
        except Exception:
            pass


@contextmanager
def observation(name: str, *, root: bool = False, input=None, start_time: int | None = None):
    """Manual spans: equivalent to capture_input=False/capture_output=False.

    Only explicit, re-masked fields enter telemetry; no function args, user objects, prompts,
    exception messages or stack traces are captured. start_time is UTC epoch nanoseconds.
    """
    parent = _CURRENT.get()
    runtime = _runtime() if root or parent is not None else None
    active, token = Observation(), None
    context, span = None, None
    try:
        if runtime is not None:
            from opentelemetry.trace import use_span

            span = runtime[1].start_span(name, start_time=start_time)
            context = use_span(span, end_on_exit=False, record_exception=False, set_status_on_exception=False)
            context.__enter__()
            active = Observation(span, name if root else parent.name, root)
            span.set_attribute("langfuse.trace.name", active.name)
            span.set_attribute("langfuse.observation.type", "span")
            active.update(input=input)
            token = _CURRENT.set(active)
    except Exception:
        active = Observation()
    try:
        yield active
    except BaseException:
        if active.span is not None:
            try:
                active.span.set_attribute("langfuse.observation.level", "ERROR")
                active.span.set_attribute("langfuse.observation.status_message", "Operation failed")
            except Exception:
                pass
        raise
    finally:
        usage = CURRENT_USAGE.get()
        if root and usage is not None:
            active.update(metadata=usage.fields())
        if token is not None:
            _CURRENT.reset(token)
        if context is not None:
            try:
                context.__exit__(None, None, None)  # Never hand the SDK an unsanitized exception.
            except Exception:
                pass
        if span is not None:
            try:
                span.end()
            except Exception:
                pass


def flush() -> None:
    runtime = _runtime()
    if runtime is not None:
        try:
            runtime[0].flush()
        except Exception:
            pass


def score(trace_id: str, value: int, comment: str) -> None:
    # Caller-supplied IDs must never be sent as arbitrary text/PII to telemetry.
    if not re.fullmatch(r"[0-9a-f]{32}", trace_id) or trace_id == "0" * 32:
        return
    runtime = _runtime()
    if runtime is not None:
        try:
            runtime[0].create_score(
                trace_id=trace_id, name="user-feedback", value=value,
                data_type="NUMERIC", comment=_safe(comment),
            )
        except Exception:
            pass  # Unknown traces and telemetry outages must not turn feedback into HTTP 500.

