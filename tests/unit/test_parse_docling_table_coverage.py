"""Table-selection regressions use OCR results only; no PDF models are needed."""

import pytest

from app.rag.parse_docling import choose_pages

NARRATIVE = "Điều khoản của ngân hàng quy định về dịch vụ thanh toán. " * 12
WAGES = (
    "| Vung | Muc luong toi thieu thang theo quy dinh |\n|---|---|\n"
    "| Vung I cac quan noi thanh | 5.310.000 |\n| Vung II cac huyen ngoai thanh | 4.730.000 |"
)
RATES = (
    "| Loai phi | Muc phi |\n|---|---|\n"
    "| Phi rut tien mat tai cay ATM ngoai he thong | 4% |\n"
    "| Phi chuyen doi ngoai te khi giao dich | 5% |"
)


def _page(text=NARRATIVE, tables=()):
    return {"source": "fees.pdf", "page": 1, "text": text, "tables": list(tables)}


def test_keeps_missing_wage_row_even_when_half_the_figures_survive():
    partial = (
        "| Vùng | Mức lương tối thiểu tháng theo quy định |\n|---|---|\n"
        "| Vùng I các quận nội thành | 5.310.000 |"
    )
    original, copy = _page(tables=[WAGES]), _page(tables=[partial])

    [chosen] = choose_pages([original], [copy])

    assert chosen["text"] == copy["text"]
    assert chosen["tables"] == [partial, WAGES]
    assert copy["tables"] == [partial]  # preserving content must not mutate either pass


def test_rates_in_unrelated_prose_do_not_cover_a_missing_fee_table():
    text = NARRATIVE + " Lãi suất tiết kiệm là 4%, lãi suất cho vay là 5%."
    original, copy = _page(text, [RATES]), _page(text)

    [chosen] = choose_pages([original], [copy])

    assert chosen["tables"] == [RATES]


def test_rates_in_an_unrelated_table_do_not_cover_missing_fee_rows():
    unrelated = "| Sản phẩm | Lãi suất |\n|---|---|\n| Tiết kiệm | 4% |\n| Cho vay | 5% |"

    [chosen] = choose_pages([_page(tables=[RATES])], [_page(tables=[unrelated])])

    assert chosen["tables"] == [unrelated, RATES]


def test_complete_table_with_accents_is_kept_without_duplicating_the_original():
    read = (
        "| Vùng | Mức lương tối thiểu tháng theo quy định |\n|---|---|\n"
        "| Vùng I các quận nội thành | 5.310.000 |\n| Vùng II các huyện ngoại thành | 4.730.000 |"
    )
    copy = _page(tables=[read])

    [chosen] = choose_pages([_page(tables=[WAGES])], [copy])

    assert chosen is copy


def test_repeated_rates_do_not_hide_a_missing_service_row():
    original = RATES.replace("5%", "4%")
    partial = (
        "| Loại phí | Mức phí |\n|---|---|\n"
        "| Phí rút tiền mặt tại cây ATM ngoài hệ thống | 4% |"
    )

    [chosen] = choose_pages([_page(tables=[original])], [_page(tables=[partial])])

    assert chosen["tables"] == [partial, original]


def test_one_copy_row_cannot_cover_two_identical_original_rows():
    row = RATES.splitlines()[2]
    original = "\n".join([*RATES.splitlines()[:2], row, row])
    partial = "\n".join([*RATES.splitlines()[:2], row])
    copy = _page(NARRATIVE + " của và các", [partial])

    [chosen] = choose_pages([_page(tables=[original])], [copy])

    assert chosen["tables"] == [partial, original]


def test_swapping_rates_between_services_does_not_count_as_preserved_content():
    swapped = (
        "| Loại phí | Mức phí |\n|---|---|\n"
        "| Phí rút tiền mặt tại cây ATM ngoài hệ thống | 5% |\n"
        "| Phí chuyển đổi ngoại tệ khi giao dịch | 4% |"
    )

    [chosen] = choose_pages([_page(tables=[RATES])], [_page(tables=[swapped])])

    assert chosen["tables"] == [swapped, RATES]


def test_swapping_rates_between_columns_does_not_count_as_preserved_content():
    original = (
        "| Loai phi ap dung cho dich vu | Trong nuoc | Nuoc ngoai |\n|---|---|---|\n"
        "| Phi rut tien mat tai cay ATM ngoai he thong | 4% | 5% |"
    )
    swapped = (
        "| Loại phí áp dụng cho dịch vụ | Trong nước | Nước ngoài |\n|---|---|---|\n"
        "| Phí rút tiền mặt tại cây ATM ngoài hệ thống | 5% | 4% |"
    )

    [chosen] = choose_pages([_page(tables=[original])], [_page(tables=[swapped])])

    assert chosen["tables"] == [swapped, original]


@pytest.mark.parametrize("rate", ["0,5%", "1.5%"])
def test_decimal_rate_is_not_covered_by_a_tenfold_rate(rate):
    original = RATES.replace("4%", rate)
    read = original.replace(rate, rate.replace(",", "").replace(".", ""))
    copy = _page(NARRATIVE + " của và các", [read])

    [chosen] = choose_pages([_page(tables=[original])], [copy])

    assert chosen["tables"] == [read, original]
