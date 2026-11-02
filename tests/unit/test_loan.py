"""Five hand-calculated examples and amortization/validation invariants."""

from decimal import Decimal

import pytest

from app.agent.loan import tinh_lai_vay


@pytest.mark.parametrize("principal,annual,months,method,interest,first,last", [
    (1200, 0, 12, "annuity", "0.00", "100.00", "100.00"),
    (1000, 12, 1, "annuity", "10.00", "1010.00", "1010.00"),
    (1000, 12, 2, "annuity", "15.02", "507.51", "507.51"),
    (1200, 12, 12, "declining", "78.00", "112.00", "101.00"),
    (1000, 12, 3, "declining", "20.00", "343.33", "336.67"),
])
def test_five_hand_calculated_examples(principal, annual, months, method, interest, first, last):
    # 2-month annuity: 1000*1.01^2/(1+1.01) = 507.5124 -> 507.51.
    # 12-month declining interest: (12+11+...+1) = 78.
    # 3-month declining: principal 333.33,333.33,333.34; interest 10,6.67,3.33.
    result = tinh_lai_vay(principal, annual, months, method)
    assert result["total_interest"] == interest
    assert result["schedule"][0]["payment"] == first
    assert result["schedule"][-1]["payment"] == last
    assert Decimal(result["total_payment"]) == Decimal(principal) + Decimal(interest)


@pytest.mark.parametrize("method", ["annuity", "declining"])
@pytest.mark.parametrize("principal,annual,months", [
    ("0.01", "0", 600), ("1000.01", "7.5", 37), ("1000000000000000", "100", 600),
    ("12", "1e-100", 12),
])
def test_schedule_conserves_money_and_clears_final_balance(method, principal, annual, months):
    result = tinh_lai_vay(principal, annual, months, method)
    rows = result["schedule"]
    assert len(rows) == months
    assert rows[-1]["closing_balance"] == "0.00"
    assert sum(Decimal(row["principal"]) for row in rows) == Decimal(principal)
    assert sum(Decimal(row["payment"]) for row in rows) == Decimal(result["total_payment"])
    assert sum(Decimal(row["interest"]) for row in rows) == Decimal(result["total_interest"])
    for i, row in enumerate(rows):
        opening, closing = Decimal(row["opening_balance"]), Decimal(row["closing_balance"])
        assert 0 <= closing <= opening
        assert opening - Decimal(row["principal"]) == closing
        assert Decimal(row["payment"]) == Decimal(row["principal"]) + Decimal(row["interest"])
        if i:
            assert rows[i - 1]["closing_balance"] == row["opening_balance"]


@pytest.mark.parametrize("changes", [
    {"principal": 0}, {"principal": -1}, {"principal": "0.001"}, {"principal": True},
    {"principal": "1e16"}, {"principal": "NaN"}, {"principal": "Infinity"},
    {"principal": "not-a-number"}, {"principal": None}, {"principal": "1" * 65},
    {"annual_rate_percent": -1}, {"annual_rate_percent": 101},
    {"annual_rate_percent": float("nan")}, {"annual_rate_percent": float("inf")},
    {"annual_rate_percent": True}, {"months": 0}, {"months": 601}, {"months": True},
    {"months": 2.5}, {"months": "12"}, {"method": "unknown"},
])
def test_invalid_inputs(changes):
    values = {"principal": 1000, "annual_rate_percent": 12, "months": 12}
    values.update(changes)
    with pytest.raises(ValueError):
        tinh_lai_vay(**values)


def test_decimal_float_and_string_inputs_agree():
    assert tinh_lai_vay(1000.50, 7.5, 12) == tinh_lai_vay(Decimal("1000.50"), "7.5", 12)


@pytest.mark.parametrize(
    "annual,shown",
    [("1E+1", "10"), ("-0", "0"), ("10.5000", "10.5"), (12, "12"), ("100", "100"), ("0E-999999", "0"),
     ("1e-100", "1E-100")],
)
def test_annual_rate_is_shown_canonically(annual, shown):
    # PR #89 F-02; a tiny accepted exponent must not expand into a huge fixed-point string.
    assert tinh_lai_vay(1000, annual, 1)["annual_rate_percent"] == shown
