"""Loan interest calculation (annuity / declining balance).

Owner: A — Epic E-011. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

CENT = Decimal("0.01")


def _number(value: int | float | str | Decimal, name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)) or len(str(value)) > 64:
        raise ValueError(f"Invalid {name}")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"Invalid {name}") from None
    if not result.is_finite():
        raise ValueError(f"Invalid {name}")
    return result


def _rate_text(rate: Decimal) -> str:
    """Canonical rate text: "1E+1" -> "10", "-0" -> "0", "10.5000" -> "10.5".

    Fixed-point only down to 1e-20 so an accepted "1e-999999" stays short.
    """
    rate = rate.normalize() + 0  # + 0 turns -0 into 0
    return format(rate, "f") if rate == 0 or rate.adjusted() >= -20 else str(rate)


def tinh_lai_vay(
    principal: int | float | str | Decimal,
    annual_rate_percent: int | float | str | Decimal,
    months: int,
    method: str = "annuity",
) -> dict:
    """Monthly annuity or equal-principal declining-balance schedule, no fees.

    Nominal annual percentage / 12; money rounds HALF_UP to 2 decimals each month.
    The final installment clears rounding residue. JSON money values are strings.
    Bounds: principal 0.01..10^15 (at most 2 decimals), annual rate 0..100%,
    integer months 1..600. Inputs are never included in validation errors.
    """
    if method not in ("annuity", "declining"):
        raise ValueError("method must be annuity or declining")
    if type(months) is not int or not 1 <= months <= 600:
        raise ValueError("months must be an integer between 1 and 600")
    amount = _number(principal, "principal")
    annual = _number(annual_rate_percent, "annual_rate_percent")
    if not CENT <= amount <= Decimal("1e15") or amount % CENT:
        raise ValueError("principal must be 0.01..10^15 with at most 2 decimal places")
    if not 0 <= annual <= 100:
        raise ValueError("annual_rate_percent must be between 0 and 100")
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_HALF_UP
        rate = annual / 1200
        # Geometric sum avoids cancellation/division by zero at tiny or zero rates.
        factor, weights = Decimal(1), Decimal(0)
        for _ in range(months):
            weights += factor
            factor *= 1 + rate
        payment = (amount * factor / weights).quantize(CENT)
        equal_principal = (amount / months).quantize(CENT)
        balance, total_interest = amount, Decimal(0)
        schedule = []
        for month in range(1, months + 1):
            interest = (balance * rate).quantize(CENT)
            repaid = payment - interest if method == "annuity" else equal_principal
            repaid = balance if month == months else min(balance, max(Decimal(0), repaid))
            closing = balance - repaid
            schedule.append({
                "month": month,
                "opening_balance": f"{balance:.2f}",
                "principal": f"{repaid:.2f}",
                "interest": f"{interest:.2f}",
                "payment": f"{repaid + interest:.2f}",
                "closing_balance": f"{closing:.2f}",
            })
            balance = closing
            total_interest += interest
        return {
            "method": method, "principal": f"{amount:.2f}",
            "annual_rate_percent": _rate_text(annual), "months": months,
            "total_interest": f"{total_interest:.2f}",
            "total_payment": f"{amount + total_interest:.2f}", "schedule": schedule,
        }

