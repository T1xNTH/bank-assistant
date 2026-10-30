"""rerank(): ordering, scores and the refusal threshold with a fake cross-encoder (CI)."""

import math
import threading
import time
from types import SimpleNamespace

import pytest
import torch

from app.contracts import Hit, User
from app.rag import rerank as rr
from app.rag import retrieve as rag

QUESTION = "Mức lương tối thiểu vùng I là bao nhiêu?"


def hit(doc_id, text, score=0.03):
    return Hit(doc_id=doc_id, source=f"{doc_id}.pdf", page=2, text=text, score=score, department="hr")


class FakeModel:
    """Scores a pair by the number after "score=" in the chunk text, already a sigmoid probability."""

    def __init__(self):
        self.calls = []

    def score(self, pairs):
        self.calls.append(pairs)
        return [float(text.split("score=")[1].split()[0]) for _, text in pairs]


@pytest.fixture
def fake(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(rr, "_model", lambda: model)
    monkeypatch.delenv("REFUSAL_THRESHOLD", raising=False)
    monkeypatch.setattr(rr, "DEFAULT_THRESHOLD", 0.3)
    return model


HITS = [
    hit("fusion-1st", "score=0.2 phí thẻ"),
    hit("fusion-2nd", "score=0.9 lương"),
    hit("fusion-3rd", "score=0.6 bảo hiểm"),
]


def test_hits_are_reordered_by_the_cross_encoder_and_carry_its_score(fake):
    out = rr.rerank(QUESTION, HITS, k=5)

    assert [(h.doc_id, h.score) for h in out] == [("fusion-2nd", 0.9), ("fusion-3rd", 0.6)]
    assert out[0] == HITS[1].__class__(**{**HITS[1].__dict__, "score": 0.9})  # only the score changes


def test_pairs_are_question_and_chunk_text_scored_in_one_call(fake):
    rr.rerank(QUESTION, HITS, k=5)

    assert fake.calls == [[(QUESTION, h.text) for h in HITS]]


def test_k_limits_the_result_after_ranking(fake):
    assert [h.doc_id for h in rr.rerank(QUESTION, HITS, k=1)] == ["fusion-2nd"]


def test_an_out_of_scope_question_returns_nothing(fake):
    unrelated = [hit("a", "score=0.01 phí thẻ"), hit("b", "score=0.29 lãi suất")]

    assert rr.rerank("Thời tiết Hà Nội hôm nay thế nào?", unrelated, k=5) == []


def test_a_score_equal_to_the_threshold_is_kept(fake):
    assert [h.doc_id for h in rr.rerank(QUESTION, [hit("edge", "score=0.3 x")], k=5)] == ["edge"]


def test_a_single_pair_is_scored(fake):
    assert [h.score for h in rr.rerank(QUESTION, [hit("one", "score=0.7 x")], k=5)] == [0.7]


def test_ties_keep_the_fusion_order(fake):
    tied = [hit("first", "score=0.5 a"), hit("second", "score=0.5 b")]
    assert [h.doc_id for h in rr.rerank(QUESTION, tied, k=5)] == ["first", "second"]


def test_no_hits_does_not_load_the_model(monkeypatch):
    monkeypatch.setattr(rr, "_model", lambda: pytest.fail("model loaded"))
    monkeypatch.delenv("REFUSAL_THRESHOLD", raising=False)
    assert rr.rerank(QUESTION, [], k=5) == []


def test_a_malformed_threshold_is_an_error_even_without_hits(monkeypatch):
    monkeypatch.setenv("REFUSAL_THRESHOLD", "abc")  # a misconfiguration must not hide behind empty results
    with pytest.raises(ValueError, match="REFUSAL_THRESHOLD"):
        rr.rerank(QUESTION, [], k=5)


@pytest.mark.parametrize(("env", "expected"), [("0.75", 0.75), (" 0 ", 0.0), ("1", 1.0), ("", 0.3)])
def test_threshold_comes_from_the_environment(fake, monkeypatch, env, expected):
    monkeypatch.setenv("REFUSAL_THRESHOLD", env)
    assert rr.refusal_threshold() == expected


def test_the_environment_threshold_applies(fake, monkeypatch):
    monkeypatch.setenv("REFUSAL_THRESHOLD", "0.7")
    assert [h.doc_id for h in rr.rerank(QUESTION, HITS, k=5)] == ["fusion-2nd"]


def test_an_explicit_threshold_overrides_the_environment(fake, monkeypatch):
    monkeypatch.setenv("REFUSAL_THRESHOLD", "0.95")
    assert len(rr.rerank(QUESTION, HITS, k=5, threshold=0.0)) == 3


@pytest.mark.parametrize("env", ["abc", "-0.1", "1.5", "nan", "50%"])
def test_a_malformed_threshold_is_an_error(fake, monkeypatch, env):
    monkeypatch.setenv("REFUSAL_THRESHOLD", env)
    with pytest.raises(ValueError, match="REFUSAL_THRESHOLD"):
        rr.rerank(QUESTION, HITS, k=5)


def test_k_must_be_positive(fake):
    with pytest.raises(ValueError):
        rr.rerank(QUESTION, HITS, k=0)


def test_concurrent_first_calls_load_the_model_once(monkeypatch):
    loads = []

    def slow_load():
        loads.append(1)
        time.sleep(0.05)
        return FakeModel()

    monkeypatch.setattr(rr, "_instance", None)
    monkeypatch.setattr(rr, "_load", slow_load)
    threads = [threading.Thread(target=rr._model) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(loads) == 1


class _Calls(list):
    """(k, mode, kwargs) of each hybrid call, and the users it was asked for."""

    def __init__(self):
        super().__init__()
        self.users = []


@pytest.fixture
def hybrid(monkeypatch):
    """Stub the hybrid stage of retrieve(): hybrid_rerank looks retrieve up in its module."""
    monkeypatch.delenv("RERANK_CANDIDATES", raising=False)
    real, calls = rag.retrieve, _Calls()

    def stub(question, user, k, mode, **kwargs):
        calls.append((k, mode, kwargs))
        calls.users.append(user)
        return HITS

    monkeypatch.setattr(rag, "retrieve", stub)
    return real, calls


def test_hybrid_rerank_rescores_more_hybrid_candidates_than_k(fake, hybrid):
    real, calls = hybrid
    asker = User("u-public", "public")

    out = real(QUESTION, asker, 1, "hybrid_rerank", collection="c")

    assert calls.users == [asker]  # the hybrid stage, and so the access filter, gets the asking user

    assert calls == [(rag.DEFAULT_RERANK_CANDIDATES, "hybrid", {"client": None, "collection": "c"})]
    assert [(h.doc_id, h.score) for h in out] == [("fusion-2nd", 0.9)]


def test_hybrid_rerank_asks_for_at_least_k_candidates(fake, hybrid):
    real, calls = hybrid
    real(QUESTION, User("u", "hr"), rag.DEFAULT_RERANK_CANDIDATES + 5, "hybrid_rerank")
    assert calls[0][0] == rag.DEFAULT_RERANK_CANDIDATES + 5


def test_hybrid_rerank_returns_nothing_for_an_out_of_scope_question(fake, hybrid, monkeypatch):
    real, _ = hybrid
    monkeypatch.setenv("REFUSAL_THRESHOLD", "0.95")
    assert real("Thời tiết Hà Nội hôm nay thế nào?", User("u", "hr"), 5, "hybrid_rerank") == []


def test_the_number_of_candidates_comes_from_the_environment(fake, hybrid, monkeypatch):
    real, calls = hybrid
    monkeypatch.setenv("RERANK_CANDIDATES", "12")
    real(QUESTION, User("u", "hr"), 5, "hybrid_rerank")
    assert calls[0][0] == 12


@pytest.mark.parametrize("env", ["0", "-3", "five", "2.5", "²", "101"])
def test_a_malformed_candidate_count_is_an_error(fake, hybrid, monkeypatch, env):
    real, _ = hybrid
    monkeypatch.setenv("RERANK_CANDIDATES", env)
    with pytest.raises(ValueError, match="RERANK_CANDIDATES"):
        real(QUESTION, User("u", "hr"), 5, "hybrid_rerank")


class FakeTokenizer:
    """Words are tokens. A pair batch carries each chunk's "logit=" marker for FakeHead."""

    def __init__(self):
        self.batches = []

    def __call__(self, first, second=None, **kwargs):
        if second is None:
            return {"input_ids": first.split()}
        self.batches.append((first, second, kwargs))
        return {"logit": torch.tensor([float(t.split("logit=")[1].split()[0]) for t in second])}

    def decode(self, ids):
        return " ".join(ids)


class FakeHead:
    def __call__(self, logit):
        return SimpleNamespace(logits=logit.view(-1, 1))


@pytest.fixture
def encoder():
    ce = object.__new__(rr._CrossEncoder)  # no download: tokenizer and model are fakes
    ce.tokenizer, ce.model = FakeTokenizer(), FakeHead()
    return ce


def test_scores_are_the_sigmoid_of_the_logits(encoder):
    assert encoder.score([(QUESTION, "logit=0"), (QUESTION, "logit=2"), (QUESTION, "logit=-3")]) == pytest.approx(
        [0.5, 1 / (1 + math.exp(-2)), 1 / (1 + math.exp(3))]
    )


def test_pairs_are_scored_in_batches_in_input_order(encoder):
    pairs = [(QUESTION, f"logit={i}") for i in range(rr.BATCH_SIZE + 2)]

    scores = encoder.score(pairs)

    assert [len(second) for _, second, _ in encoder.tokenizer.batches] == [rr.BATCH_SIZE, 2]
    assert scores == sorted(scores) and len(scores) == len(pairs)  # logits 0, 1, 2, ... keep their order


def test_only_the_chunk_is_truncated_to_the_model_length(encoder):
    encoder.score([(QUESTION, "logit=1")])

    [(_, _, kwargs)] = encoder.tokenizer.batches
    assert kwargs == {"padding": True, "truncation": "only_second", "max_length": rr.MAX_LENGTH, "return_tensors": "pt"}


def test_a_long_question_is_cut_before_pairing(encoder):
    long = " ".join(f"w{i}" for i in range(rr.QUESTION_MAX_LENGTH + 50))

    encoder.score([(long, "logit=1"), (QUESTION, "logit=1")])

    [(questions, _, _)] = encoder.tokenizer.batches
    assert questions[0].split() == long.split()[: rr.QUESTION_MAX_LENGTH]
    assert questions[1] == QUESTION  # a short question is passed through unchanged
