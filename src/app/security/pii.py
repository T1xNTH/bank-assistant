"""Regex-only Vietnamese PII masking. Owner: B, Epic E-007.

Account candidates are conservatively defined as 8-19 ASCII digits, optionally grouped.
These can also be amounts or identifiers: masking favors privacy over precision.
Explicit labels and complete phones delimit generic numeric candidates.
"""

from __future__ import annotations

import re
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry, RecognizerResult
from presidio_analyzer.nlp_engine import NoOpNlpEngine


@lru_cache(maxsize=1)
def _analyzer() -> AnalyzerEngine:
    # Explicit registry prevents loading Presidio's default NLP recognizers.
    digit = r"[ .-]?[0-9]"
    phone = rf"(?:0|\+84[ .-]?|0084[ .-]?|\(\+84\)[ .-]?)(?:[35789](?:{digit}){{8}}|2(?:{digit}){{9}})"
    patterns = {
        "CCCD": rf"(?<!\w)[0-9](?:{digit}){{11}}(?!\w)",
        # A numeric word after whitespace/punctuation may be an independent
        # amount/account. Redact the complete candidate even if ambiguous.
        "PHONE_NUMBER": rf"(?<![0-9+]){phone}(?![0-9])",
        "ACCOUNT_NUMBER": rf"(?:(?<![\w+])|(?<=\b(?:stk|tk)))[0-9](?:{digit}){{7,18}}(?!\w)",
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


def _non_overlapping(results: list[RecognizerResult]) -> list[RecognizerResult]:
    priority = {"CCCD": 0, "PHONE_NUMBER": 1, "ACCOUNT_NUMBER": 2}
    results.sort(key=lambda r: (-(r.end - r.start), priority[r.entity_type], r.start))
    selected = []
    for result in results:
        if not any(result.start < other.end and other.start < result.end for other in selected):
            selected.append(result)
    selected.sort(key=lambda r: r.start)
    return selected


def mask_text(text: str) -> tuple[str, list[str]]:
    """Replace PII with ``<TYPE>`` and return unique types in textual order.

    Explicit numeric labels take precedence; otherwise complete phones delimit
    grouped numbers, so a following amount/account is not swallowed by a match.
    Already masked text is unchanged. No original text is logged or retained.
    """
    if not text:
        return text, []
    analyzer = _analyzer()
    results = analyzer.analyze(text=text, language="vi")
    labels = {
        "CCCD": r"\bcccd[ \t]*[:=]?[ \t]*$",
        "ACCOUNT_NUMBER": (
            r"\b(?:stk|tk|số tài khoản|so tai khoan|tài khoản|tai khoan)"
            r"(?:[ \t]+(?:số|so|của[ \t]+tôi[ \t]+là|cua[ \t]+toi[ \t]+la))?[ \t]*[:=]?[ \t]*$"
        ),
    }
    # An explicitly labelled grouped account/CCCD can itself start like a phone.
    labelled = _non_overlapping([
        r for r in results
        if r.entity_type in labels
        and re.search(labels[r.entity_type], text[max(0, r.start - 64) : r.start], re.IGNORECASE)
    ])
    phones = [
        r for r in results if r.entity_type == "PHONE_NUMBER"
        and not any(r.start < n.end and n.start < r.end for n in labelled)
    ]
    anchors = _non_overlapping(labelled + phones)
    selected = list(anchors)
    cursor = 0
    # Analyze the gaps separately: generic grouped-number patterns must not
    # bridge two phone spans or consume a phone and an independent numeric word.
    for end, next_start in [(r.start, r.end) for r in anchors] + [(len(text), len(text))]:
        if re.search(r"[0-9]", text[cursor:end]):
            numeric = analyzer.analyze(
                text=text[cursor:end], language="vi", entities=["CCCD", "ACCOUNT_NUMBER"]
            )
            for result in _non_overlapping(numeric):
                result.start += cursor
                result.end += cursor
                selected.append(result)
        cursor = next_start
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
