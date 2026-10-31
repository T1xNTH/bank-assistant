"""The answer facts of tests/integration/test_ask.py accept real good answers and reject incomplete ones (CI).

The integration test needs Qdrant, LiteLLM and a paid model, so CI never runs its assertions; this keeps
the fact regexes honest. Good answers are replies recorded from gpt-6-luna on the shared corpus.
"""

import re

import pytest

from tests.integration.test_ask import QUESTIONS

FACTS = {question: fact for _, question, _, _, fact in QUESTIONS}
TRANSFER = "Phí chuyển tiền trong nước khác hệ thống là bao nhiêu?"

GOOD = {
    "Mức lương tối thiểu tháng vùng I là bao nhiêu?": "Mức lương tối thiểu tháng vùng I là 5.310.000 đồng/tháng. [1]",
    "Mức lương tối thiểu giờ vùng IV là bao nhiêu?": "Mức lương tối thiểu giờ vùng IV là 17.800 đồng/giờ. [1]",
    "Tổng số giờ làm thêm trong một ngày không được vượt quá bao nhiêu?": (
        "Tổng số giờ làm thêm không quá 12 giờ trong một ngày khi làm thêm vào ngày nghỉ lễ, Tết hoặc ngày nghỉ "
        "hằng tuần. [1] Với ngày làm việc bình thường, giới hạn là 50% số giờ làm việc bình thường trong ngày. [1]"
    ),
    "Hồ sơ đề nghị vay vốn gồm những gì?": (
        "Khách hàng phải cung cấp thông tin, tài liệu, dữ liệu chứng minh đủ điều kiện vay vốn theo Điều 7. [2]"
    ),
    "Tổ chức tín dụng không được cho vay đối với những nhu cầu vốn nào?": (
        "Tổ chức tín dụng không được cho vay để:\n- Mua vàng miếng. [1]\n- Bù đắp tài chính. [3]"
    ),
    "Lãi suất áp dụng với dư nợ gốc bị quá hạn tối đa là bao nhiêu?": (
        "Tối đa 150% lãi suất cho vay trong hạn tại thời điểm chuyển nợ quá hạn. [1][2]"
    ),
    "Chủ thẻ tín dụng VietinBank được phát hành tối đa bao nhiêu thẻ phụ?": (
        "Chủ thẻ chính được phát hành tối đa 03 thẻ phụ, hoặc số lượng khác theo quy định của Ngân hàng.[1]"
    ),
    "Phí phát hành lại thẻ ghi nợ quốc tế là bao nhiêu?": "Phí phát hành lại thẻ ghi nợ quốc tế là 50.000 đ. [1]",
    "Phí cấp lại mã PIN thẻ ghi nợ quốc tế tại quầy là bao nhiêu?": (
        "Phí cấp lại mã PIN thẻ ghi nợ quốc tế tại quầy là 27.273 đ. [1]"
    ),
    TRANSFER: (
        "Phí chuyển tiền VND trong nước khác hệ thống trước 15h: dưới 500 triệu đồng là 0,03%, tối thiểu 20.000 "
        "đồng; từ 500 triệu đồng trở lên là 0,03%, tối đa 3.000.000 đồng. [2]"
    ),
}

# PR #64 review round 2: both cite page 3 correctly and used to pass with the 0,03% pattern.
TRANSFER_INCOMPLETE = [
    "Phí chuyển tiền ngoại tệ trong nước khác hệ thống là 0,03%, tối thiểu 2 USD [2].",
    "Chuyển tiền ngoại tệ khác hệ thống: 0,03%, tối thiểu 2 USD, tối đa 200 USD. [1] Phí VND áp dụng theo mã "
    "B101 và B103. [2]",
    "Phí chuyển tiền khác hệ thống là 120.000 đồng. [1]",
]


def holds(fact, answer):
    return re.search(fact, answer, re.IGNORECASE) is not None


def test_every_question_has_a_recorded_good_answer():
    assert set(GOOD) == set(FACTS)


@pytest.mark.parametrize("question", list(GOOD), ids=range(1, 11))
def test_fact_accepts_the_recorded_answer(question):
    assert holds(FACTS[question], GOOD[question])


@pytest.mark.parametrize("answer", TRANSFER_INCOMPLETE, ids=["foreign-only", "fee-codes-only", "wrong-amount"])
def test_transfer_fact_rejects_answers_without_the_vnd_amounts(answer):
    assert not holds(FACTS[TRANSFER], answer)


@pytest.mark.parametrize("question", list(GOOD), ids=range(1, 11))
def test_fact_rejects_a_refusal_shaped_answer(question):
    assert not holds(FACTS[question], "Tài liệu không nêu thông tin này. [1]")
