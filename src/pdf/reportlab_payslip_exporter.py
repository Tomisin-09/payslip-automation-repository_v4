from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas


@dataclass(frozen=True)
class LineItem:
    label: str
    amount: float


def fmt_currency(amount: float, symbol: str) -> str:
    # Use "NGN " (with trailing space) in config for: "NGN 450,468.97"
    sym = "" if symbol is None else str(symbol)
    return f"{sym}{amount:,.2f}"


class ReportLabPayslipExporter:
    """
    Pure-Python payslip PDF renderer.

    Layout:
    - Header: titles centered + logo fixed in a top-right header box
    - Employee info: labels left, values shifted right
    - Earnings section + computed gross
    - Deductions section + computed total deduction
    - Net pay divider + larger font row
    - Footer: Approved By + signature bottom-left
    """

    def __init__(self, margin_mm: float = 14.0, line_gap: float = 14.0):
        self.page_size = A4
        self.margin = margin_mm * mm
        self.line_gap = float(line_gap)

    def render_pdf(
        self,
        output_pdf_path: Path,
        company_line1: str,
        company_line2: str,
        period_display: str,
        employee: Dict[str, Any],
        earnings: List[LineItem],
        deductions: List[LineItem],
        totals_labels: Dict[str, str],
        logo_path: Optional[Path],
        signature_path: Optional[Path],
        currency_symbol: str,
        footer_cfg: Optional[Dict[str, Any]] = None,
        generated_at: Optional[str] = None,
    ) -> Path:
        output_pdf_path = output_pdf_path.resolve()
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

        gross = sum(x.amount for x in earnings)
        total_deduction = sum(x.amount for x in deductions)
        net_pay = gross - total_deduction
        generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c = Canvas(str(output_pdf_path), pagesize=self.page_size)
        width, height = self.page_size

        x0 = self.margin
        x1 = width - self.margin
        y = height - self.margin

        # ------------------------------------------------------------
        # Logo: FIXED to the top-right "header box" (red box area)
        #
        # TWEAK THESE 4 VALUES until it matches your preferences:
        #   - logo_box_w / logo_box_h  (size of the red box)
        #   - logo_right_pad           (gap from page right edge)
        #   - logo_top_pad             (gap from page top edge)
        # ------------------------------------------------------------
        logo_box_w = 60 * mm
        logo_box_h = 32 * mm
        logo_right_pad = 0 * mm
        logo_top_pad = 2 * mm

        # This is the *bottom-left* of the red box container
        box_x = width - logo_right_pad - logo_box_w
        box_y = height - logo_top_pad - logo_box_h

        if logo_path:
            try:
                # Draw logo scaled into the box; aspect ratio preserved
                c.drawImage(
                    str(logo_path),
                    box_x,
                    box_y,
                    width=logo_box_w,
                    height=logo_box_h,
                    preserveAspectRatio=True,
                    anchor="c",      # centre within the box (helps with wide logos)
                    mask="auto",
                )
            except Exception:
                pass

        # Titles centered
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString((x0 + x1) / 2, y - 2 * mm, company_line1)

        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString((x0 + x1) / 2, y - 9 * mm, company_line2)

        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString((x0 + x1) / 2, y - 16 * mm, period_display)

        y -= 22 * mm
        self._sep(c, x0, x1, y)
        y -= 10 * mm

        # Employee info
        label_x = x0
        value_x = x0 + 70 * mm

        info_rows = [
            ("EMPLOYEE REFERENCE NO", employee.get("ref", "")),
            ("NAME", employee.get("name", "")),
            ("DESIGNATION", employee.get("designation", "")),
            ("DEPARTMENT", employee.get("department", "")),
            ("MONTH", period_display),
        ]

        c.setFont("Helvetica-Bold", 11)
        for k, v in info_rows:
            c.drawString(label_x, y, str(k))
            c.setFont("Helvetica", 11)
            c.drawString(value_x, y, str(v))
            c.setFont("Helvetica-Bold", 11)
            y -= self.line_gap

        y -= 2 * mm
        self._sep(c, x0, x1, y)
        y -= 12 * mm

        # Earnings
        y = self._section_title(c, x0, y, "EARNINGS:")
        y = self._line_items(c, x0, x1, y, earnings, currency_symbol)

        c.setFont("Helvetica-Bold", 11)
        c.drawString(x0, y, totals_labels["gross_income_label"])
        c.drawRightString(x1, y, fmt_currency(gross, currency_symbol))
        y -= self.line_gap

        y -= 6 * mm
        self._sep(c, x0, x1, y)
        y -= 12 * mm

        # Deductions
        y = self._section_title(c, x0, y, "DEDUCTIONS:")
        y = self._line_items(c, x0, x1, y, deductions, currency_symbol)

        c.setFont("Helvetica-Bold", 11)
        c.drawString(x0, y, totals_labels["total_deduction_label"])
        c.drawRightString(x1, y, fmt_currency(total_deduction, currency_symbol))
        y -= self.line_gap

        
        # Net pay
        
        # Net pay (balanced spacing)
        net_pay_pad = 10 * mm

        # Top separator
        self._sep(c, x0, x1, y)
        y -= net_pay_pad

        # Net pay row
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x0, y, totals_labels["net_pay_label"])
        c.drawRightString(x1, y, fmt_currency(net_pay, currency_symbol))
        y -= net_pay_pad

        # Bottom Separator
        self._sep(c, x0, x1, y)
        y -= net_pay_pad

        # Footer
        footer_cfg = footer_cfg or {}
        approved_by_label = str(footer_cfg.get("approved_by_label", "Approved By:"))
        approved_by_name = str(footer_cfg.get("approved_by_name", "")).strip()

        signature_gap_mm = float(footer_cfg.get("signature_gap_mm", 4))  # tighter default
        name_gap_mm = float(footer_cfg.get("name_gap_mm", 3))            # gap below signature

        c.setFont("Helvetica-Bold", 11)
        c.drawString(x0, y, approved_by_label)

        # tighter spacing between label and signature
        y -= signature_gap_mm * mm

        sig_w = 45 * mm
        sig_h = 18 * mm
        sig_drawn = False

        if signature_path:
            try:

                sig_x_offset = 9 * mm

                c.drawImage(
                    str(signature_path),
                    x0 - sig_x_offset,
                    y - sig_h,  # drawImage uses bottom-left; this places it "below" current y
                    width=sig_w,
                    height=sig_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
                sig_drawn = True
            except Exception:
                sig_drawn = False

        # Move y below signature (or below label if no signature)
        if sig_drawn:
            y = (y - sig_h) - (name_gap_mm * mm)
        else:
            y -= (name_gap_mm * mm)

        # Printed name under signature (if provided)
        if approved_by_name:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x0, y, approved_by_name)
            y -= 10  # small extra spacing if you add more footer lines later


        c.setFont("Helvetica", 9)
        c.drawRightString(x1, (self.margin / 2), f"Generated: {generated_at}")

        c.showPage()
        c.save()
        return output_pdf_path

    def _sep(self, c: Canvas, x0: float, x1: float, y: float) -> None:
        c.setLineWidth(4)
        c.line(x0, y, x1, y)

    def _section_title(self, c: Canvas, x0: float, y: float, title: str) -> float:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x0, y, title)
        c.setLineWidth(1)
        c.line(x0, y - 2, x0 + 30 * mm, y - 2)
        return y - 20

    def _line_items(
        self,
        c: Canvas,
        x0: float,
        x1: float,
        y: float,
        items: List[LineItem],
        currency_symbol: str,
    ) -> float:
        c.setFont("Helvetica", 11)
        for it in items:
            c.drawString(x0, y, str(it.label))
            c.drawRightString(x1, y, fmt_currency(float(it.amount), currency_symbol))
            y -= self.line_gap
        return y
