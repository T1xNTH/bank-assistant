"""Regex-only Vietnamese PII masking. Owner: B, Epic E-007.

Bare account candidates are conservatively defined as 8-19 ASCII digits.
These can also be amounts or identifiers: masking favors privacy over precision.
CCCD (12 digits) and Vietnamese phone patterns take precedence over accounts.
"""

from __future__ import annotations

from functools import lru_cache

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
from presidio_analyzer.nlp_engine import NoOpNlpEngine


@lru_cache(maxsize=1)
def _analyzer() -> AnalyzerEngine:
    # Explicit registry prevents loading Presidio's default NLP recognizers.
    digit = r"[ .-]?[0-9]"
    phone = rf"(?:0|\+84[ .-]?|0084[ .-]?)(?:[35789](?:{digit}){{8}}|2(?:{digit}){{9}})"
    patterns = {
        "CCCD": r"(?<!\w)[0-9]{12}(?!\w)",
        # A numeric word after whitespace/punctuation may be an independent
        # amount/account. Redact the complete candidate even if ambiguous.
        "PHONE_NUMBER": rf"(?<![\w+]){phone}(?!\w)",
        "ACCOUNT_NUMBER": r"(?<![\w+])[0-9]{8,19}(?!\w)",
    }
    registry = RecognizerRegistry(supported_languages=["vi"])
    for entity, regex in patterns.items():
        registry.add_recognizer(
            PatternRecognizer(
                supported_entity=entity,
                supported_language="vi",
                patterns=[Pattern(entity, regex, 1.0)],
            )
        )
    return AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "vi", "model_name": ""}]),
        supported_languages=["vi"],
    )


def mask_text(text: str) -> tuple[str, list[str]]:
    """Replace PII with ``<TYPE>`` and return unique types in textual order.

    Resolve overlaps by keeping the longest span, then CCCD/phone over account.
    Already masked text is unchanged. No original text is logged or retained.
    """
    if not text:
        return text, []
    results = _analyzer().analyze(text=text, language="vi")
    priority = {"CCCD": 0, "PHONE_NUMBER": 1, "ACCOUNT_NUMBER": 2}
    # Account candidates may be contained in a formatted phone number. Prefer
    # the complete span so no country code or phone segment survives masking.
    results.sort(key=lambda r: (-(r.end - r.start), priority[r.entity_type], r.start))
    selected = []
    for result in results:
        if not any(result.start < other.end and other.start < result.end for other in selected):
            selected.append(result)
    selected.sort(key=lambda r: r.start)
    pieces: list[str] = []
    types: list[str] = []
    cursor = 0
    for result in selected:
        pieces.extend((text[cursor : result.start], f"<{result.entity_type}>"))
        if result.entity_type not in types:
            types.append(result.entity_type)
        cursor = result.end
    pieces.append(text[cursor:])
    return "".join(pieces), types
