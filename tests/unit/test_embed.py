"""embed(): output shape with a fake model (CI); the real bge-m3 under -m integration."""

import math

import numpy as np
import pytest

from app.rag import embed as emb

WAGE = "Mức lương tối thiểu vùng I là 5.310.000 đồng/tháng, áp dụng từ ngày 01/01/2026."
CARD_FEE = "Phí rút tiền mặt tại ATM bằng thẻ do ngân hàng khác phát hành là 4%, tối thiểu 80.000 đồng."
QUERY = "Lương tối thiểu vùng I năm 2026 là bao nhiêu?"


class FakeModel:
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        return {
            "dense_vecs": np.ones((len(texts), emb.DIM), dtype=np.float32) / math.sqrt(emb.DIM),
            "lexical_weights": [{"2045": 0.31, "6": 0.0, "17": np.float32(0.12)} for _ in texts],
        }


@pytest.fixture
def fake(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(emb, "_model", lambda: model)
    return model


def test_embed_shapes_and_sparse_format(fake):
    dense, sparse = emb.embed([WAGE, CARD_FEE])

    assert len(dense) == len(sparse) == 2
    assert all(len(v) == emb.DIM and isinstance(v[0], float) for v in dense)
    assert sparse[0] == {"indices": [17, 2045], "values": [pytest.approx(0.12), pytest.approx(0.31)]}  # sorted
    assert isinstance(sparse[0]["values"][0], float)
    [(texts, kwargs)] = fake.calls
    assert texts == [WAGE, CARD_FEE]
    assert kwargs["return_dense"] and kwargs["return_sparse"] and not kwargs["return_colbert_vecs"]


def test_empty_input_does_not_load_the_model(monkeypatch):
    monkeypatch.setattr(emb, "_model", lambda: pytest.fail("model loaded"))

    assert emb.embed([]) == ([], [])


def _cos(a, b):
    return float(np.dot(a, b))


@pytest.mark.integration
def test_bge_m3_dimensions_normalisation_and_determinism():
    dense, sparse = emb.embed([WAGE, CARD_FEE])
    again, again_sparse = emb.embed([WAGE])  # different batch composition

    assert [len(v) for v in dense] == [emb.DIM, emb.DIM]
    assert all(abs(np.linalg.norm(v) - 1) < 1e-4 for v in dense)
    assert np.allclose(dense[0], again[0], atol=1e-5)
    assert again_sparse[0]["indices"] == sparse[0]["indices"]
    assert np.allclose(again_sparse[0]["values"], sparse[0]["values"], atol=1e-5)
    assert sparse[0]["indices"] == sorted(sparse[0]["indices"]) and sparse[0]["values"]


@pytest.mark.integration
def test_bge_m3_ranks_the_relevant_vietnamese_text_first():
    (q, wage, fee), _ = emb.embed([QUERY, WAGE, CARD_FEE])

    assert _cos(q, wage) > _cos(q, fee)


@pytest.mark.integration
def test_bge_m3_is_loaded_once_per_process():
    emb.embed([WAGE])
    emb.embed([CARD_FEE])

    assert emb._model.cache_info().misses == 1
