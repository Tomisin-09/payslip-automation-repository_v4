from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Tuple


@dataclass(frozen=True)
class PayrollPeriod:
    year: int
    month: int

    @property
    def period_id(self) -> str:
        # e.g. 2026-01
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def display(self) -> str:
        # e.g. January 2026
        d = date(self.year, self.month, 1)
        return d.strftime("%B %Y")


def resolve_period(period_mode: str, manual_year: int, manual_month: int, reference_date: str = "") -> PayrollPeriod:
    """Resolve payroll period based on settings."""
    ref: date
    if reference_date:
        try:
            ref = datetime.strptime(reference_date, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(f"Invalid reference_date '{reference_date}'. Expected YYYY-MM-DD.") from e
    else:
        ref = date.today()

    mode = (period_mode or "").strip().lower()

    if mode == "manual":
        return PayrollPeriod(year=int(manual_year), month=int(manual_month))

    if mode in ("auto_current_month", "current", "auto_current"):
        return PayrollPeriod(year=ref.year, month=ref.month)

    if mode in ("auto_previous_month", "previous", "auto_previous"):
        y = ref.year
        m = ref.month - 1
        if m == 0:
            m = 12
            y -= 1
        return PayrollPeriod(year=y, month=m)

    raise ValueError(
        "period_mode must be one of: auto_previous_month | auto_current_month | manual. "
        f"Got: {period_mode!r}"
    )
