"""Synthetic values only; exercise the real Presidio regex pipeline."""

import logging

import pytest

from app.security.pii import NoOpNlpEngine, _analyzer, mask_text


@pytest.mark.parametrize(
    ("text", "entity"),
    [
        ("000000000001", "CCCD"),
        ("999999999999", "CCCD"),
        ("10000001", "ACCOUNT_NUMBER"),
        ("1000000000000000001", "ACCOUNT_NUMBER"),
        ("0900000001", "PHONE_NUMBER"),
        ("0300000001", "PHONE_NUMBER"),
        ("0500000001", "PHONE_NUMBER"),
        ("0700000001", "PHONE_NUMBER"),
        ("0800000001", "PHONE_NUMBER"),
        ("+84900000001", "PHONE_NUMBER"),
        ("0084900000001", "PHONE_NUMBER"),
        ("+84 900 000 001", "PHONE_NUMBER"),
        ("0900.000.001", "PHONE_NUMBER"),
        ("0900-000-001", "PHONE_NUMBER"),
        ("0900 000 001", "PHONE_NUMBER"),
        ("02400000001", "PHONE_NUMBER"),
        ("+84 24 0000 0001", "PHONE_NUMBER"),
    ],
)
def test_masks_complete_entity(text, entity):
    assert mask_text(f"Giá trị: ({text}).") == (f"Giá trị: (<{entity}>).", [entity])


@pytest.mark.parametrize(
    ("entity", "text"),
    [
        ("CCCD", "00000000001"),
        ("CCCD", "0000000000001"),
        ("CCCD", "mã000000000001"),
        ("CCCD", "000000000001A"),
        ("CCCD", "０００００００００００１"),
        ("ACCOUNT_NUMBER", "1000001"),
        ("ACCOUNT_NUMBER", "10000000000000000001"),
        ("ACCOUNT_NUMBER", "ref10000001"),
        ("ACCOUNT_NUMBER", "10000001_id"),
        ("PHONE_NUMBER", "0100000001"),
        ("PHONE_NUMBER", "090000001"),
        ("PHONE_NUMBER", "09000000001"),
        ("PHONE_NUMBER", "+840900000001"),
        ("PHONE_NUMBER", "+19000000001"),
        ("PHONE_NUMBER", "0900 000 001 2"),
        ("PHONE_NUMBER", "0900\n000\n001"),
        ("PHONE_NUMBER", "ref0900000001"),
        ("PHONE_NUMBER", "0900000001A"),
    ],
)
def test_recognizer_rejects_non_entity(entity, text):
    # Another recognizer may conservatively mask a numeric candidate as account.
    assert _analyzer().analyze(text=text, language="vi", entities=[entity]) == []


@pytest.mark.parametrize("text", ["", "Xin chào Việt Nam!", "100.000 VND, 30/10/2026", "abc10000001"])
def test_preserves_non_pii(text):
    assert mask_text(text) == (text, [])


def test_mixed_repeated_entities_preserve_surroundings_and_order():
    text = "ĐT +84 900 000 001; CCCD 000000000001; STK 10000001; ĐT 0900000001."
    masked, types = mask_text(text)
    assert masked == "ĐT <PHONE_NUMBER>; CCCD <CCCD>; STK <ACCOUNT_NUMBER>; ĐT <PHONE_NUMBER>."
    assert types == ["PHONE_NUMBER", "CCCD", "ACCOUNT_NUMBER"]
    assert mask_text(masked) == (masked, [])


def test_adjacent_entities_and_cccd_account_overlap():
    assert mask_text("000000000001/10000001") == ("<CCCD>/<ACCOUNT_NUMBER>", ["CCCD", "ACCOUNT_NUMBER"])


def test_engine_never_loads_spacy_model(monkeypatch):
    import spacy

    def forbidden(*args, **kwargs):
        pytest.fail("PII masking must not load or download an NLP model")

    monkeypatch.setattr(spacy, "load", forbidden)
    monkeypatch.setattr(spacy.cli, "download", forbidden)
    _analyzer.cache_clear()
    assert mask_text("000000000001") == ("<CCCD>", ["CCCD"])
    engine = _analyzer().nlp_engine
    assert isinstance(engine, NoOpNlpEngine)
    assert engine.is_loaded()
    assert list(engine.process_batch(["a", "b"], "vi"))[0][1].entities == []


def test_no_raw_values_in_logs(caplog):
    raw = "CCCD 000000000001, STK 10000001, ĐT +84 900 000 001"
    with caplog.at_level(logging.DEBUG):
        mask_text(raw)
    for value in ("000000000001", "10000001", "+84 900 000 001"):
        assert value not in caplog.text
