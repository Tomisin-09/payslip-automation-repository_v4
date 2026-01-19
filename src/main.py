from __future__ import annotations

import csv
import logging
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.data_io.load_data import EmployeeRow, load_employee_payroll_rows
from src.email.outlook_sender import EmailRequest, send_or_display_via_outlook
from src.pdf.reportlab_payslip_exporter import LineItem, ReportLabPayslipExporter
from src.preflight import run_preflight
from src.utils.asset_validation import validate_branding_assets
from src.utils.config import load_settings
from src.utils.logging_utils import configure_logging
from src.utils.period import resolve_period

logger = logging.getLogger(__name__)


def _safe_float(v: Any) -> float:
    try:
        if v is None:
            return 0.0
        if isinstance(v, str) and not v.strip():
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def _sanitise_filename_part(s: str) -> str:
    s = (s or "").strip()
    # Keep it filesystem-friendly
    for ch in ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "\n", "\r", "\t"]:
        s = s.replace(ch, "-")
    return " ".join(s.split())


def _build_line_items(emp: EmployeeRow, fields_cfg: List[Dict[str, Any]]) -> List[LineItem]:
    items: List[LineItem] = []
    for f in fields_cfg:
        label = str(f.get("label", "")).strip()
        col = str(f.get("column", "")).strip()
        if not label or not col:
            continue
        amount = _safe_float(emp.raw.get(col))
        # If empty/NaN treated as 0.0
        items.append(LineItem(label=label, amount=amount))
    return items


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    settings = load_settings(project_root / "config" / "settings.yml")

    # Resolve payroll period
    run_cfg = settings.get("run", {})
    period = resolve_period(
        period_mode=str(run_cfg.get("period_mode", "manual")),
        manual_year=int(run_cfg.get("manual_period", {}).get("year", datetime.now().year)),
        manual_month=int(run_cfg.get("manual_period", {}).get("month", datetime.now().month)),
        reference_date=str(run_cfg.get("reference_date", "") or ""),
    )

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    run_date = now.strftime("%Y-%m-%d")

    output_cfg = settings.get("output", {})
    output_root = project_root / str(output_cfg.get("root_dir", "output"))
    run_root = output_root / period.period_id

    pdf_dir = run_root / "pdf"
    logs_dir = run_root / "logs" / run_date
    summary_dir = run_root / "summary"

    log_file = logs_dir / f"run_log_{timestamp}.log"
    configure_logging(log_file_path=log_file, level="INFO")

    logger.info("Payslip generation run started")
    logger.info("Period: %s (%s)", period.display, period.period_id)
    logger.info("Output dir: %s", run_root)

    # Preflight checks (Python version, data source presence, email platform warning)
    run_preflight(settings=settings, project_root=project_root)

    # Validate branding assets
    branding_cfg = settings.get("branding", {})
    logo_path = project_root / str(branding_cfg.get("logo_path", ""))
    signature_path = project_root / str(branding_cfg.get("signature_path", ""))

    validate_branding_assets(
        logo_path=logo_path,
        signature_path=signature_path,
        allowed_extensions=branding_cfg.get("allowed_extensions", [".png", ".jpg", ".jpeg"]),
        enforce_resolution=bool(branding_cfg.get("enforce_resolution", False)),
        logo_required_px=tuple(branding_cfg.get("logo_required_px", [])) or None,
        signature_required_px=tuple(branding_cfg.get("signature_required_px", [])) or None,
    )

    # Load employees
    data_cfg = settings.get("data", {})
    xlsx_path = project_root / str(data_cfg.get("data_source_xlsx", ""))
    sheet_name = str(data_cfg.get("sheet_name", "Data Source"))

    fields_cfg = settings.get("fields", {})
    earnings_cfg = fields_cfg.get("earnings", []) or []
    deductions_cfg = fields_cfg.get("deductions", []) or []

    required_value_columns = [str(f.get("column")) for f in (earnings_cfg + deductions_cfg) if f.get("column")]

    employees = load_employee_payroll_rows(
        xlsx_path=xlsx_path,
        sheet_name=sheet_name,
        required_base_columns=list(data_cfg.get("required_base_columns", [])),
        required_value_columns=required_value_columns,
    )
    logger.info("Loaded %d employee row(s) from Excel", len(employees))

    # Renderer
    company_cfg = settings.get("company", {})
    footer_cfg = settings.get("footer", {}) or {}
    exporter = ReportLabPayslipExporter()

    totals_labels = settings.get("pdf", {}).get("totals_labels", {}) or {}
    for k in ("gross_income_label", "total_deduction_label", "net_pay_label"):
        totals_labels.setdefault(k, k.replace("_", " ").upper())

    currency_symbol = str(company_cfg.get("currency_symbol", "£"))

    # Manifest
    summary_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = summary_dir / f"manifest_{timestamp}.csv"

    manifest_rows: List[Dict[str, Any]] = []
    pdf_paths: List[Path] = []

    fail_fast = bool(run_cfg.get("fail_fast", False))

    for emp in employees:
        try:
            earnings_items = _build_line_items(emp, earnings_cfg)
            deduction_items = _build_line_items(emp, deductions_cfg)

            safe_name = _sanitise_filename_part(emp.name).replace(" ", "_")
            filename = f"{emp.ref}_{safe_name}_{period.period_id}.pdf"
            out_pdf = pdf_dir / filename

            exporter.render_pdf(
                output_pdf_path=out_pdf,
                company_line1=str(company_cfg.get("line1", "")),
                company_line2=str(company_cfg.get("line2", "")),
                period_display=period.display,
                employee={
                    "ref": emp.ref,
                    "name": emp.name,
                    "designation": emp.designation,
                    "department": emp.department,
                },
                earnings=earnings_items,
                deductions=deduction_items,
                totals_labels=totals_labels,
                logo_path=logo_path,
                signature_path=signature_path,
                currency_symbol=currency_symbol,
                footer_cfg=footer_cfg
            )

            gross = sum(li.amount for li in earnings_items)
            total_ded = sum(li.amount for li in deduction_items)
            net_pay = gross - total_ded

            pdf_paths.append(out_pdf)
            manifest_rows.append(
                {
                    "employee_ref": emp.ref,
                    "name": emp.name,
                    "email": emp.email,
                    "period_id": period.period_id,
                    "period_display": period.display,
                    "pdf_path": str(out_pdf.resolve()),
                    "gross_income": f"{gross:.2f}",
                    "total_deductions": f"{total_ded:.2f}",
                    "net_pay": f"{net_pay:.2f}",
                    "status": "generated",
                }
            )
            logger.info("Generated: %s", out_pdf.name)

        except Exception as e:
            logger.exception("Failed to generate payslip for %s (%s)", emp.name, emp.ref)
            manifest_rows.append(
                {
                    "employee_ref": emp.ref,
                    "name": emp.name,
                    "email": emp.email,
                    "period_id": period.period_id,
                    "period_display": period.display,
                    "pdf_path": "",
                    "gross_income": "",
                    "total_deductions": "",
                    "net_pay": "",
                    "status": f"error: {e}",
                }
            )
            if fail_fast:
                raise

    # Write manifest
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()) if manifest_rows else [])
        writer.writeheader()
        writer.writerows(manifest_rows)

    logger.info("Manifest written: %s", manifest_path)

    # Optional email step
    email_cfg = settings.get("email", {})
    if bool(email_cfg.get("enabled", False)):
        if bool(run_cfg.get("approval_gate_before_email", True)):
            logger.info(f"\nGenerated {len(pdf_paths)} PDF(s) in: {pdf_dir}")
            logger.info(f"Manifest: {manifest_path}")
            ans = input("\nDo you want to proceed with emailing now? (y/N): ").strip().lower()
            if ans not in ("y", "yes"):
                logger.info("Email step skipped by user")
                return

        mode = str(email_cfg.get("mode", "display"))
        subject_t = str(email_cfg.get("subject_template", "Your Payslip - {period_display}"))
        body_t = str(email_cfg.get("body_template", ""))

        sent = 0
        for emp, row in zip(employees, manifest_rows):
            if not row.get("pdf_path"):
                continue
            req = EmailRequest(
                to=emp.email,
                subject=subject_t.format(name=emp.name, period_display=period.display, period_id=period.period_id),
                body=body_t.format(name=emp.name, period_display=period.display, period_id=period.period_id),
                attachment_path=Path(row["pdf_path"]),
            )
            send_or_display_via_outlook(req, mode=mode)
            sent += 1

        logger.info("Email step complete. Processed %d email(s)", sent)

    logger.info("Run complete")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.getLogger(__name__).exception("Fatal error in main()")
        raise

