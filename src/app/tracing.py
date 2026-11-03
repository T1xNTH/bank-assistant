"""Langfuse tracing helpers (inputs masked before tracing).

Owner: B — Epic E-013. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache

from app.security.masking import REDACTED, MaskingError, require_mask_content

_CURRENT: ContextVar[Observation | None] = ContextVar("bank_trace", default=None)


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
        return _backend(os.getpid(), public, secret, os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000"))
    except Exception:
        return None  # Telemetry must never change the answer's availability.


class Observation:
    def __init__(self, span=None, name: str = "", root: bool = False):
        self.span, self.name, self.root = span, name, root

    @property
    def trace_id(self) -> str | None:
        return f"{self.span.get_span_context().trace_id:032x}" if self.span is not None else None

    def update(self, *, input=None, output=None, metadata=None):
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


@contextmanager
def observation(name: str, *, root: bool = False, input=None, start_time: int | None = None):
    """Manual spans: equivalent to capture_input=False/capture_output=False.

    Only explicit, re-masked fields enter telemetry; no function args, user objects, prompts,
    exception messages or stack traces are captured. start_time is UTC epoch nanoseconds.
    """
    parent = _CURRENT.get()
    runtime = _runtime() if root or parent is not None else None
    active, token = Observation(), None
    context = None
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
        if token is not None:
            _CURRENT.reset(token)
        if context is not None:
            try:
                context.__exit__(None, None, None)  # Never hand the SDK an unsanitized exception.
            except Exception:
                pass
        if active.span is not None:
            try:
                active.span.end()
            except Exception:
                pass


def flush() -> None:
    runtime = _runtime()
    if runtime is not None:
        try:
            runtime[0].flush()
        except Exception:
            pass

