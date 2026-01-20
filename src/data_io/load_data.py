from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence
import logging

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmployeeRow:
    ref: str
    name: str
    designation: str
    department: str
    email: str
    raw: Dict[str, Any]


def load_employee_payroll_rows(
    xlsx_path: Path,
    sheet_name: str,
    required_base_columns: Sequence[str],
    required_value_columns: Sequence[str],
) -> List[EmployeeRow]:
    """Load payroll data from Excel.

    - required_base_columns: identity columns (ref/name/etc)
    - required_value_columns: earning/deduction columns from config
    """
    xlsx_path = xlsx_path.resolve()
    if not xlsx_path.exists():
        logger.error(f"Excel data source not found: {xlsx_path}")
        raise FileNotFoundError(f"Excel data source not found: {xlsx_path}")

    try:
        df = pd.read_excel(str(xlsx_path), sheet_name=sheet_name, engine="openpyxl")
    except ValueError as e:
        logger.error(e, f"Could not read sheet '{sheet_name}' from {xlsx_path}. "
            "Check the sheet name in config."
        )
        raise

    if df is None or df.empty:
        raise ValueError(f"No rows found in '{sheet_name}' sheet of {xlsx_path}")

    df.columns = [str(c).strip() for c in df.columns]

    missing_base = [c for c in required_base_columns if c not in df.columns]
    missing_vals = [c for c in required_value_columns if c not in df.columns]
    if missing_base or missing_vals:
        msg = "Missing required columns in Excel data source."
        if missing_base:
            logger.error(f"{msg} \n- Missing base columns: {missing_base}")
        if missing_vals:
            logger.error(f"{msg} \n- Missing payroll value columns: {missing_vals}")
        logger.info(f"{msg} \nAvailable columns: {list(df.columns)}")
        raise ValueError(msg)

    # Drop rows that have no Reference Number
    ref_col = required_base_columns[0]
    df = df[df[ref_col].notna()].copy()

    rows: List[EmployeeRow] = []
    for _, r in df.iterrows():
        raw = {k: (None if pd.isna(v) else v) for k, v in r.to_dict().items()}
        rows.append(
            EmployeeRow(
                ref=str(raw.get("Reference Number", "")).strip(),
                name=str(raw.get("Employee Name", "")).strip(),
                designation=str(raw.get("Designation", "")).strip(),
                department=str(raw.get("Department", "")).strip(),
                email=str(raw.get("Email", "")).strip(),
                raw=raw,
            )
        )

    if not rows:
        logger.error("No valid employees found (after filtering empty Reference Number)")
        raise ValueError

    return rows
