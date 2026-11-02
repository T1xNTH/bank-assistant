"""Tools tinh_lai_vay, tra_cuu_giao_dich, tao_ticket bound to the current user.

Owner: A — Epic E-011. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import sqlite3

from app.agent.core_banking import CoreBanking
from app.agent.loan import tinh_lai_vay
from app.contracts import User
from app.security.masking import require_mask_content


class ToolUnavailable(RuntimeError):
    """Sanitized storage failure; never includes query parameters or DB details."""


class AgentTools:
    """Construct per authenticated request; never expose user/bank as tool args.

    T-030 can wrap these three bound methods as graph tools. No identity, SQL,
    approved_by, decision or destination path is accepted from model arguments.
    """

    def __init__(self, user: User, bank: CoreBanking | None = None):
        if not isinstance(user, User) or not isinstance(user.user_id, str) or not user.user_id.strip():
            raise ValueError("Authenticated user required")
        self._user = user
        self._bank = bank if bank is not None else CoreBanking()

    def tinh_lai_vay(
        self, principal: int | float | str, annual_rate_percent: int | float | str,
        months: int, method: str = "annuity",
    ) -> dict:
        return tinh_lai_vay(principal, annual_rate_percent, months, method)

    def tra_cuu_giao_dich(self, account_id: str | None = None, limit: int = 20) -> list[dict]:
        """Read this user's transactions and mask every string before returning."""
        if account_id is not None and (
            not isinstance(account_id, str) or not account_id.strip() or len(account_id) > 128
        ):
            raise ValueError("Invalid account_id")
        try:
            rows = self._bank.transactions(self._user, account_id, limit=limit)
        except sqlite3.Error:
            raise ToolUnavailable("Transaction lookup unavailable") from None
        return [
            {key: require_mask_content(value) if isinstance(value, str) else value for key, value in row.items()}
            for row in rows
        ]

    def tao_ticket(self, summary: str) -> dict:
        """Propose only; no approval, SQLite write, or TicketStore access.

        Proposal text/identity are masked for model output. The graph must derive
        the actual owner from authenticated state, never from this display field.
        """
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 2000:
            raise ValueError("summary must be non-empty text of at most 2000 characters")
        return {
            "status": "pending", "created_by": require_mask_content(self._user.user_id),
            "summary": require_mask_content(summary),
        }

