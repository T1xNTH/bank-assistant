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
        ("CCCD", "000 000 000 01"),
        ("CCCD", "000 000 000 0001"),
        ("ACCOUNT_NUMBER", "1000001"),
        ("ACCOUNT_NUMBER", "10000000000000000001"),
        ("ACCOUNT_NUMBER", "ref10000001"),
        ("ACCOUNT_NUMBER", "10000001_id"),
        ("ACCOUNT_NUMBER", "100 0001"),
        ("ACCOUNT_NUMBER", "1000\n0001"),
        ("ACCOUNT_NUMBER", "notstk1903678901234"),
        ("ACCOUNT_NUMBER", "STK1000001"),
        ("ACCOUNT_NUMBER", "TK10000000000000000001"),
        ("PHONE_NUMBER", "0100000001"),
        ("PHONE_NUMBER", "090000001"),
        ("PHONE_NUMBER", "09000000001"),
        ("PHONE_NUMBER", "+840900000001"),
        ("PHONE_NUMBER", "+19000000001"),
        ("PHONE_NUMBER", "0900\n000\n001"),
    ],
)
def test_recognizer_rejects_non_entity(entity, text):
    # Another recognizer may conservatively mask a numeric candidate as account.
    assert _analyzer().analyze(text=text, language="vi", entities=[entity]) == []


@pytest.mark.parametrize(
    ("text", "masked", "types"),
    [
        ("CCCD: 001 204 012 345", "CCCD: <CCCD>", ["CCCD"]),
        ("001.204.012.345", "<CCCD>", ["CCCD"]),
        ("001-204-012-345", "<CCCD>", ["CCCD"]),
        ("STK 1903 6789 0123", "STK <ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("STK: 0011-0049-12345", "STK: <ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("1000 0001", "<ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("1000.0000.0000.0000.001", "<ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("(+84) 912 345 678", "<PHONE_NUMBER>", ["PHONE_NUMBER"]),
        ("(+84)-912-345-678", "<PHONE_NUMBER>", ["PHONE_NUMBER"]),
        ("SĐT0912345678", "SĐT<PHONE_NUMBER>", ["PHONE_NUMBER"]),
        ("sdt0912345678", "sdt<PHONE_NUMBER>", ["PHONE_NUMBER"]),
        ("ref0900000001", "ref<PHONE_NUMBER>", ["PHONE_NUMBER"]),
        ("gọi 090.123.4567 nhé", "gọi <PHONE_NUMBER> nhé", ["PHONE_NUMBER"]),
        ("+84-912-345-678", "<PHONE_NUMBER>", ["PHONE_NUMBER"]),
        ("0912 345 678 và 0987654321", "<PHONE_NUMBER> và <PHONE_NUMBER>", ["PHONE_NUMBER"]),
        ("CCCD 0900 000 001 23", "CCCD <CCCD>", ["CCCD"]),
        ("STK 0900 000 001 234", "STK <ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("0900 000 001 100 VND", "<PHONE_NUMBER> 100 VND", ["PHONE_NUMBER"]),
        ("0900 000 001 1000 0001", "<PHONE_NUMBER> <ACCOUNT_NUMBER>", ["PHONE_NUMBER", "ACCOUNT_NUMBER"]),
        ("1000 0001 0900 000 001", "<ACCOUNT_NUMBER> <PHONE_NUMBER>", ["ACCOUNT_NUMBER", "PHONE_NUMBER"]),
    ],
)
def test_review_grouped_and_labelled_entities(text, masked, types):
    assert mask_text(text) == (masked, types)
    assert mask_text(masked) == (masked, [])


@pytest.mark.parametrize(
    ("text", "masked", "types"),
    [
        ("STK1903678901234", "STK<ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("stk1903678901234", "stk<ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("TK1903678901234", "TK<ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("tk0900 000 001 234", "tk<ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("STK190367890123", "STK<ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("0912345678abc", "<PHONE_NUMBER>abc", ["PHONE_NUMBER"]),
        ("0900000001A", "<PHONE_NUMBER>A", ["PHONE_NUMBER"]),
        ("ref0900000001abc", "ref<PHONE_NUMBER>abc", ["PHONE_NUMBER"]),
        ("(+84) 912 345 678abc", "<PHONE_NUMBER>abc", ["PHONE_NUMBER"]),
        ("tài khoản số 1903 6789 0123", "tài khoản số <ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("STK của tôi là 1903 6789 0123", "STK của tôi là <ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("tai khoan so 1903 6789 0123", "tai khoan so <ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("TK cua toi la 0900 000 001 234", "TK cua toi la <ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
    ],
)
def test_pr58_rereview_account_labels_and_phone_suffixes(text, masked, types):
    assert mask_text(text) == (masked, types)
    assert mask_text(masked) == (masked, [])


@pytest.mark.parametrize(
    "phone", ["0900000001", "+84900000001", "0084900000001", "0900 000 001", "+84 24 0000 0001"]
)
@pytest.mark.parametrize(
    ("following", "masked_following", "following_types"),
    [
        ("100 VND", "100 VND", []),
        ("10000001", "<ACCOUNT_NUMBER>", ["ACCOUNT_NUMBER"]),
        ("000000000001", "<CCCD>", ["CCCD"]),
        ("0900000001", "<PHONE_NUMBER>", []),
    ],
)
def test_phone_before_independent_numeric_word(phone, following, masked_following, following_types):
    assert mask_text(f"{phone} {following}") == (
        f"<PHONE_NUMBER> {masked_following}", ["PHONE_NUMBER", *following_types]
    )


@pytest.mark.parametrize("separator", [" ", "\t", "\n", ",", ".", "-"])
def test_ambiguous_formatted_extension_still_masks_complete_phone(separator):
    # Prefer masking a complete candidate over leaking it due to a numeric suffix.
    assert mask_text(f"0900 000 001{separator}2") == (f"<PHONE_NUMBER>{separator}2", ["PHONE_NUMBER"])


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
