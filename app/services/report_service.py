"""Build period business reports, render to PDF, and email them."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_email
from app.core.pdf import build_report_pdf
from app.models.business import (
    Customer,
    EmptyCaseTransaction,
    Expense,
    Product,
    ReportSettings,
    Sale,
    SaleItem,
    utcnow,
)

PERIODS = ("daily", "weekly", "monthly")


def local_now() -> datetime:
    """Current wall-clock time in the configured timezone, as a naive datetime.

    Used for scheduling decisions (send_hour) so the schedule is in local time.
    """
    return datetime.now(settings.tzinfo()).replace(tzinfo=None)


def _to_local_label(dt_utc: datetime) -> str:
    local = dt_utc.replace(tzinfo=timezone.utc).astimezone(settings.tzinfo())
    return f"{local:%Y-%m-%d %H:%M} ({settings.timezone})"


def get_or_create_settings(db: Session) -> ReportSettings:
    settings_row = db.get(ReportSettings, 1)
    if settings_row is None:
        settings_row = ReportSettings(id=1, recipients=[])
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


def _period_bounds(period: str, now: datetime) -> tuple[datetime, datetime, str]:
    if period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        title = "Daily Report"
    elif period == "weekly":
        start = now - timedelta(days=7)
        title = "Weekly Report"
    elif period == "monthly":
        start = now - timedelta(days=30)
        title = "Monthly Report"
    else:
        raise ValueError(f"Unknown period: {period}")
    return start, now, title


def period_report(db: Session, period: str) -> dict[str, Any]:
    # Data is filtered in UTC (matches stored created_at); labels shown in local tz.
    now = utcnow()
    start, end, title = _period_bounds(period, now)

    sales_in_range = select(Sale.id).where(Sale.created_at >= start, Sale.created_at <= end).subquery()

    sales_count = db.scalar(select(func.count()).select_from(sales_in_range)) or 0
    revenue = db.scalar(
        select(func.coalesce(func.sum(Sale.total), 0.0)).where(Sale.created_at >= start, Sale.created_at <= end)
    ) or 0.0
    expenses = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0.0)).where(Expense.date >= start, Expense.date <= end)
    ) or 0.0
    cases_sold = db.scalar(
        select(func.coalesce(func.sum(SaleItem.quantity), 0)).where(SaleItem.sale_id.in_(select(sales_in_range.c.id)))
    ) or 0

    top_rows = db.execute(
        select(
            SaleItem.name,
            func.sum(SaleItem.quantity).label("qty"),
            func.sum(SaleItem.subtotal).label("rev"),
        )
        .where(SaleItem.sale_id.in_(select(sales_in_range.c.id)))
        .group_by(SaleItem.name)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(5)
    ).all()
    top_products = [{"name": r[0], "quantity": int(r[1] or 0), "revenue": float(r[2] or 0)} for r in top_rows]

    # Current inventory snapshot (not period-scoped)
    products = list(db.scalars(select(Product)))
    inventory = {
        "low_stock": sum(1 for p in products if p.full_cases <= p.low_stock_threshold),
        "expiring": sum(1 for p in products if now <= p.expiry_date <= now + timedelta(days=30)),
        "expired": sum(1 for p in products if p.expiry_date < now),
        "pending_empties": db.scalar(select(func.coalesce(func.sum(EmptyCaseTransaction.pending_quantity), 0))) or 0,
        "refundable_deposits": db.scalar(select(func.coalesce(func.sum(Customer.refundable_deposits), 0.0))) or 0.0,
    }

    return {
        "period": period,
        "title": title,
        "date_range": f"{_to_local_label(start)} - {_to_local_label(end)}",
        "generated_at": _to_local_label(now),
        "metrics": {
            "sales_count": int(sales_count),
            "revenue": float(revenue),
            "expenses": float(expenses),
            "profit": float(revenue) - float(expenses),
            "cases_sold": int(cases_sold),
        },
        "top_products": top_products,
        "inventory": inventory,
    }


def generate_and_send(
    db: Session,
    period: str,
    recipients: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or local_now()
    settings_row = get_or_create_settings(db)
    to = recipients if recipients is not None else (settings_row.recipients or [])

    data = period_report(db, period)
    pdf_bytes = build_report_pdf(data)
    filename = f"{period}-report-{now:%Y%m%d}.pdf"

    m = data["metrics"]
    subject = f"{data['title']} - {now:%Y-%m-%d}"
    body = (
        f"{data['title']} for {data['date_range']}\n\n"
        f"Sales: {m['sales_count']}\n"
        f"Revenue: RWF {m['revenue']:,.0f}\n"
        f"Expenses: RWF {m['expenses']:,.0f}\n"
        f"Gross profit: RWF {m['profit']:,.0f}\n"
        f"Cases sold: {m['cases_sold']}\n\n"
        f"The full report is attached as a PDF.\n"
    )

    emailed = False
    if to:
        send_email(to, subject, body, attachments=[(filename, pdf_bytes, "application/pdf")])
        emailed = True

    return {
        "period": period,
        "recipients": to,
        "emailed": emailed,
        "pdf_bytes": len(pdf_bytes),
        "metrics": m,
    }


def dispatch_due_reports(db: Session, now: datetime | None = None) -> list[str]:
    """Send any enabled reports that are due at ``now`` (called on a schedule).

    ``now`` defaults to the current wall-clock time in the configured timezone,
    so ``send_hour`` is interpreted in local time.
    """
    now = now or local_now()
    s = get_or_create_settings(db)
    sent: list[str] = []

    if not s.recipients:
        return sent

    def _already_sent_today(last: datetime | None) -> bool:
        return last is not None and last.date() == now.date()

    if s.daily_enabled and now.hour == s.send_hour and not _already_sent_today(s.last_daily_sent):
        generate_and_send(db, "daily", now=now)
        s.last_daily_sent = now
        sent.append("daily")

    if (
        s.weekly_enabled
        and now.weekday() == s.weekly_weekday
        and now.hour == s.send_hour
        and (s.last_weekly_sent is None or (now - s.last_weekly_sent).days >= 6)
    ):
        generate_and_send(db, "weekly", now=now)
        s.last_weekly_sent = now
        sent.append("weekly")

    if (
        s.monthly_enabled
        and now.day == s.monthly_day
        and now.hour == s.send_hour
        and (
            s.last_monthly_sent is None
            or s.last_monthly_sent.month != now.month
            or s.last_monthly_sent.year != now.year
        )
    ):
        generate_and_send(db, "monthly", now=now)
        s.last_monthly_sent = now
        sent.append("monthly")

    if sent:
        db.commit()
    return sent
