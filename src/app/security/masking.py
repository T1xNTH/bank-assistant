"""Fail-closed masking at application boundaries, without retaining raw values."""

from __future__ import annotations

import json
import re
from contextvars import ContextVar
from uuid import UUID

from app.security import pii

REDACTED = "[REDACTED]"
# Placeholders written by app.security.pii.mask_text; their presence means the original text had PII.
_PII_PLACEHOLDER = re.compile(r"<(CCCD|ACCOUNT_NUMBER|PHONE_NUMBER)>")
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
    return require_mask(text)[0]


def require_mask(text: str) -> tuple[str, list[str]]:
    """Masked text and the PII types found (for routing, T-026); raises ``MaskingError``."""
    # Presidio itself emits logs. Never recursively invoke its analyzer from
    # the logging filter, including while the analyzer is being initialized.
    if _MASKING.get():
        raise MaskingError("Masking unavailable")
    token = _MASKING.set(True)
    try:
        masked, types = pii.mask_text(text)
        if not isinstance(masked, str):
            raise MaskingError("Masking unavailable")
        return masked, [str(t) for t in types]
    except Exception:
        raise MaskingError("Masking unavailable") from None
    finally:
        _MASKING.reset(token)


# A JSON \uXXXX escape whose backslash is not itself escaped; "\u0030" decodes to the digit 0.
_UNICODE_ESCAPE = re.compile(r"(?<!\\)((?:\\\\)*)\\u([0-9a-fA-F]{4})")
_KEEP_ESCAPED = frozenset('"\\') | {chr(c) for c in range(0x20)} | {chr(c) for c in range(0xD800, 0xE000)}


def _decode_escapes(text: str) -> str:
    def decode(match: re.Match) -> str:
        char = chr(int(match.group(2), 16))
        return match.group(0) if char in _KEEP_ESCAPED else match.group(1) + char

    return _UNICODE_ESCAPE.sub(decode, text)


def require_mask_content(text: str) -> str:
    """Fail-closed masking of text that may hold JSON: \\uXXXX escapes are decoded first.

    Escapes that JSON requires (quote, backslash, control, surrogate) stay escaped, so valid
    JSON stays valid and decodes to the same value with PII masked. Raises ``MaskingError``.
    """
    return require_mask_content_types(text)[0]


def require_mask_content_types(text: str) -> tuple[str, list[str]]:
    """``require_mask_content`` plus the PII types found (for routing)."""
    return require_mask(_decode_escapes(text))


def require_mask_numbered(text: str, start: int = 0) -> tuple[str, list[str], dict[str, str]]:
    """``require_mask_content_types`` with numbered placeholders and the values they hide.

    ``"Vay 100.000.000 đ"`` -> ``("Vay <ACCOUNT_NUMBER_1> đ", ["ACCOUNT_NUMBER"], {"<ACCOUNT_NUMBER_1>":
    "100.000.000"})``, counting from ``start + 1``. Trusted code (the agent's tools) can use a value the
    model never sees; callers keep the mapping in memory only. When the placeholders cannot be lined up
    with the input (two of them touching), the plain masked text and no values are returned.
    """
    decoded = _decode_escapes(text)
    masked, types = require_mask(decoded)
    parts = _PII_PLACEHOLDER.split(masked)  # literal, TYPE, literal, TYPE, ..., literal
    literals, kinds = parts[0::2], parts[1::2]
    if not kinds or any(not literal for literal in literals[1:-1]):
        return masked, types, {}
    pattern = "(.+?)".join(re.escape(literal) for literal in literals)
    match = re.fullmatch(pattern, decoded, re.DOTALL)
    if match is None:
        return masked, types, {}
    numbered, values = [literals[0]], {}
    for i, (kind, literal) in enumerate(zip(kinds, literals[1:], strict=True)):
        placeholder = f"<{kind}_{start + i + 1}>"
        values[placeholder] = match.group(i + 1)
        numbered += [placeholder, literal]
    return "".join(numbered), types, values


def masked_pii_types(text: str) -> list[str]:
    """PII types whose placeholders appear in already masked text, in textual order."""
    return list(dict.fromkeys(_PII_PLACEHOLDER.findall(text)))


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
