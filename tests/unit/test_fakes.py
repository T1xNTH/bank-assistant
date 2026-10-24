from app.contracts import REFUSAL, Hit, User
from tests.fakes import FakeAnswerer, FakeMasker, FakeRetriever

HITS = [
    Hit("d1", "credit.pdf", 1, "lãi suất", 0.9, "credit"),
    Hit("d2", "hr.pdf", 2, "lương", 0.8, "hr"),
    Hit("d3", "public.pdf", 3, "phí", 0.7, "public"),
]


def test_fake_retriever_enforces_department():
    got = FakeRetriever(HITS).retrieve("q", User("u", "credit"), 5)
    assert [h.doc_id for h in got] == ["d1", "d3"]


def test_fake_answerer_refuses_without_hits():
    assert FakeAnswerer().answer("q", User("u", "hr")).answer == REFUSAL


def test_fake_masker_masks_cccd():
    assert FakeMasker().mask_text("CCCD 015204000835") == ("CCCD <CCCD>", ["CCCD"])
