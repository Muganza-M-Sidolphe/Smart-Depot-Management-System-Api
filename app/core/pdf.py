"""Render a business report dict to a PDF (bytes) using fpdf2 (pure Python)."""

from typing import Any

from fpdf import FPDF

from app.core.config import settings

_PRIMARY = (30, 58, 95)      # dark blue
_LIGHT = (238, 242, 248)     # light row background
_MUTED = (110, 120, 130)


def _money(value: float) -> str:
    return f"RWF {value:,.0f}"


class _ReportPDF(FPDF):
    def header(self) -> None:  # noqa: D401 - fpdf hook
        self.set_fill_color(*_PRIMARY)
        self.rect(0, 0, self.w, 22, style="F")
        self.set_xy(10, 6)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, settings.email_from_name or "Smart Depot", align="L")
        self.ln(20)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:  # noqa: D401 - fpdf hook
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_MUTED)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _section_title(pdf: FPDF, text: str) -> None:
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_PRIMARY)
    pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def _kv_row(pdf: FPDF, label: str, value: str, fill: bool) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_fill_color(*_LIGHT)
    pdf.cell(90, 8, f"  {label}", border=0, fill=fill)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, value, border=0, fill=fill, new_x="LMARGIN", new_y="NEXT")


def build_report_pdf(data: dict[str, Any]) -> bytes:
    pdf = _ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, data.get("title", "Report"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_MUTED)
    pdf.cell(0, 6, f"Period: {data.get('date_range', '')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Generated: {data.get('generated_at', '')}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    # Summary metrics
    m = data.get("metrics", {})
    _section_title(pdf, "Summary")
    rows = [
        ("Sales", str(m.get("sales_count", 0))),
        ("Revenue", _money(m.get("revenue", 0))),
        ("Expenses", _money(m.get("expenses", 0))),
        ("Gross profit", _money(m.get("profit", 0))),
        ("Cases sold", str(m.get("cases_sold", 0))),
    ]
    for i, (label, value) in enumerate(rows):
        _kv_row(pdf, label, value, fill=(i % 2 == 0))

    # Top products
    top = data.get("top_products", [])
    _section_title(pdf, "Top products")
    if top:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(*_PRIMARY)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(100, 8, "  Product", fill=True)
        pdf.cell(40, 8, "Qty", fill=True, align="R")
        pdf.cell(0, 8, "Revenue", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        for i, p in enumerate(top):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_fill_color(*_LIGHT)
            fill = i % 2 == 0
            pdf.cell(100, 8, f"  {p.get('name', '')[:45]}", fill=fill)
            pdf.cell(40, 8, str(p.get("quantity", 0)), fill=fill, align="R")
            pdf.cell(0, 8, _money(p.get("revenue", 0)), fill=fill, align="R", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, "No sales in this period.", new_x="LMARGIN", new_y="NEXT")

    # Inventory alerts
    inv = data.get("inventory", {})
    _section_title(pdf, "Inventory & deposits (current)")
    inv_rows = [
        ("Low-stock products", str(inv.get("low_stock", 0))),
        ("Expiring within 30 days", str(inv.get("expiring", 0))),
        ("Expired products", str(inv.get("expired", 0))),
        ("Pending empty cases", str(inv.get("pending_empties", 0))),
        ("Refundable deposits", _money(inv.get("refundable_deposits", 0))),
    ]
    for i, (label, value) in enumerate(inv_rows):
        _kv_row(pdf, label, value, fill=(i % 2 == 0))

    out = pdf.output()
    return bytes(out)


def build_expenses_pdf(expenses: list, start_label: str, end_label: str) -> bytes:
    """Render a simple expenses report (list + total) to PDF bytes."""
    pdf = _ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Expenses Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_MUTED)
    pdf.cell(0, 6, f"Period: {start_label} - {end_label}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # header row
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*_PRIMARY)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(28, 8, "  Date", fill=True)
    pdf.cell(70, 8, "Title", fill=True)
    pdf.cell(45, 8, "Category", fill=True)
    pdf.cell(0, 8, "Amount", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    total = 0.0
    for i, e in enumerate(expenses):
        total += e.amount
        pdf.set_font("Helvetica", "", 9)
        pdf.set_fill_color(*_LIGHT)
        fill = i % 2 == 0
        pdf.cell(28, 7, f"  {e.date:%Y-%m-%d}", fill=fill)
        pdf.cell(70, 7, (e.title or "")[:38], fill=fill)
        pdf.cell(45, 7, (e.category or "")[:22], fill=fill)
        pdf.cell(0, 7, _money(e.amount), fill=fill, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(143, 8, "  Total")
    pdf.cell(0, 8, _money(total), align="R", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
