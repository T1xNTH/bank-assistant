"""Fail-closed masking at application boundaries, without retaining raw values."""

from __future__ import annotations

import json
from contextvars import ContextVar
from uuid import UUID

from app.security import pii

REDACTED = "[REDACTED]"
_MASKING: ContextVar[bool] = ContextVar("pii_masking", default=False)


def masking_active() -> bool:
    return _MASKING.get()


def mask_identifier(value: str) -> str:
    """Keep canonical UUID correlation IDs intact despite numeric group matches."""
    try:
        if str(UUID(value)) == value:
            return value
    except ValueError:
        pass
    return mask_text(value)


class MaskingError(RuntimeError):
    """The masker could not produce safe text; never includes original input."""


def require_mask_text(text: str) -> str:
    # Presidio itself emits logs. Never recursively invoke its analyzer from
    # the logging filter, including while the analyzer is being initialized.
    if _MASKING.get():
        raise MaskingError("Masking unavailable")
    token = _MASKING.set(True)
    try:
        masked, _ = pii.mask_text(text)
        if not isinstance(masked, str):
            raise MaskingError("Masking unavailable")
        return masked
    except Exception:
        raise MaskingError("Masking unavailable") from None
    finally:
        _MASKING.reset(token)


def mask_text(text: str) -> str:
    """Best-effort fail-closed redaction for output, log and audit sinks."""
    try:
        return require_mask_text(text)
    except MaskingError:
        return REDACTED


def mask_data(value):
    """Copy JSON-like values, masking string values while preserving schemas."""
    if isinstance(value, str):
        return mask_content(value)
    if isinstance(value, dict):
        return {k: mask_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(mask_data(v) for v in value)
    return value


def mask_content(text: str) -> str:
    """Decode structured LLM text first so JSON escapes cannot bypass masking."""
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return mask_text(text)
    if isinstance(value, (dict, list)):
        return json.dumps(mask_data(value), ensure_ascii=False)
    if isinstance(value, str):
        return json.dumps(mask_text(value), ensure_ascii=False)
    return mask_text(text)
