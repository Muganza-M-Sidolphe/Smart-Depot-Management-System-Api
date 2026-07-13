"""Supplementary endpoints the frontend services reference (filters, search,
summaries, stock adjustments, per-id fetch, deletes).

This router is registered BEFORE the main business router so its literal paths
(e.g. /products/low-stock) win over the business router's /products/{id}.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.pdf import build_expenses_pdf
from app.core.roles import MANAGEMENT, OPERATIONS_ROLES, SALES_ROLES, STOCK_ROLES
from app.models.business import (
    Activity,
    DamagedCase,
    EmptyCaseTransaction,
    Expense,
    Notification,
    Product,
    Supplier,
    SupplierReturn,
    TransactionAudit,
)
from app.schemas import business as schema
from app.services import business_service as svc

router = APIRouter()


def _not_found(name: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found")


# ============================ PRODUCTS ============================


@router.get("/products/low-stock", response_model=list[schema.ProductRead])
async def products_low_stock(threshold: int | None = Query(default=None), db: Session = Depends(get_db)):
    return svc.low_stock_products(db, threshold)


@router.get("/products/search", response_model=list[schema.ProductRead])
async def products_search(q: str = Query(...), db: Session = Depends(get_db)):
    return svc.search_records(db, Product, ["name", "brand", "category", "batch_number"], q)


@router.get("/products/category/{category}", response_model=list[schema.ProductRead])
async def products_by_category(category: str, db: Session = Depends(get_db)):
    return svc.filter_records(db, Product, category=category)


@router.get("/products/barcode/{code}", response_model=schema.ProductRead)
async def product_by_barcode(code: str, db: Session = Depends(get_db)):
    product = svc.product_by_barcode(db, code)
    if product is None:
        raise _not_found("Product")
    return product


@router.patch(
    "/products/{product_id}/stock",
    response_model=schema.ProductRead,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def adjust_product_stock(product_id: int, payload: schema.ProductStockAdjust, db: Session = Depends(get_db)):
    product = svc.adjust_product_stock(db, product_id, payload.quantity, payload.operation)
    if product is None:
        raise _not_found("Product")
    return product


@router.patch(
    "/products/bulk",
    response_model=list[schema.ProductRead],
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def bulk_update_products(payload: schema.ProductBulkUpdate, db: Session = Depends(get_db)):
    return svc.bulk_update_products(db, payload.products)


# ============================ SALES ============================


@router.get("/sales/date-range", response_model=list[schema.SaleRead])
async def sales_date_range(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return svc.sales_by_date_range(db, svc._parse_dt(startDate), svc._parse_dt(endDate))


@router.get("/sales/daily-summary/{date}", response_model=schema.DailySalesSummary)
async def sales_daily_summary(date: str, db: Session = Depends(get_db)):
    day = svc._parse_dt(date)
    if day is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date")
    return svc.daily_sales_summary(db, day)


@router.get("/sales/customer/{customer_id}", response_model=list[schema.SaleRead])
async def sales_by_customer(customer_id: int, db: Session = Depends(get_db)):
    return svc.sales_by_customer(db, customer_id)


@router.patch(
    "/sales/{sale_id}",
    response_model=schema.SaleRead,
    dependencies=[Depends(require_roles(*SALES_ROLES))],
)
async def update_sale(sale_id: int, payload: schema.SaleUpdate, db: Session = Depends(get_db)):
    sale = svc.update_sale(db, sale_id, payload)
    if sale is None:
        raise _not_found("Sale")
    return sale


@router.delete(
    "/sales/{sale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def delete_sale(sale_id: int, db: Session = Depends(get_db)) -> None:
    if not svc.delete_sale(db, sale_id):
        raise _not_found("Sale")


# ============================ EXPENSES ============================


@router.get("/expenses/date-range", response_model=list[schema.ExpenseRead])
async def expenses_date_range(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return svc._expenses_in_range(db, svc._parse_dt(startDate), svc._parse_dt(endDate))


@router.get("/expenses/category/{category}", response_model=list[schema.ExpenseRead])
async def expenses_by_category(category: str, db: Session = Depends(get_db)):
    return svc.filter_records(db, Expense, category=category)


@router.get("/expenses/payment-method/{method}", response_model=list[schema.ExpenseRead])
async def expenses_by_payment_method(method: str, db: Session = Depends(get_db)):
    return svc.filter_records(db, Expense, payment_method=method)


@router.get("/expenses/summary/category", response_model=list[schema.ExpenseCategorySummary])
async def expenses_summary_category(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return svc.expenses_summary_by_category(db, svc._parse_dt(startDate), svc._parse_dt(endDate))


@router.get("/expenses/total", response_model=schema.ExpenseTotalSummary)
async def expenses_total(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return svc.expenses_total(db, svc._parse_dt(startDate), svc._parse_dt(endDate))


@router.get("/expenses/monthly-breakdown", response_model=list[schema.ExpenseMonthlyBreakdown])
async def expenses_monthly_breakdown(year: int = Query(...), db: Session = Depends(get_db)):
    return svc.expenses_monthly_breakdown(db, year)


@router.get("/expenses/report")
async def expenses_report(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    start, end = svc._parse_dt(startDate), svc._parse_dt(endDate)
    expenses = svc._expenses_in_range(db, start, end)
    pdf = build_expenses_pdf(expenses, startDate or "all", endDate or "now")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="expenses-report.pdf"'},
    )


@router.get("/expenses/{expense_id}", response_model=schema.ExpenseRead)
async def get_expense(expense_id: int, db: Session = Depends(get_db)):
    record = svc.get_record(db, Expense, expense_id)
    if record is None:
        raise _not_found("Expense")
    return record


# ============================ CUSTOMERS ============================


@router.get("/customers/phone/{phone}", response_model=schema.CustomerRead)
async def customer_by_phone(phone: str, db: Session = Depends(get_db)):
    customer = svc.customer_by_phone(db, phone)
    if customer is None:
        raise _not_found("Customer")
    return customer


@router.get("/customers/{customer_id}/stats", response_model=schema.CustomerStats)
async def customer_stats(customer_id: int, db: Session = Depends(get_db)):
    stats = svc.customer_stats(db, customer_id)
    if stats is None:
        raise _not_found("Customer")
    return stats


# ============================ SUPPLIERS ============================


@router.get("/suppliers/search", response_model=list[schema.SupplierRead])
async def suppliers_search(name: str = Query(...), db: Session = Depends(get_db)):
    return svc.search_records(db, Supplier, ["name", "contact", "email"], name)


@router.get("/suppliers/{supplier_id}", response_model=schema.SupplierRead)
async def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = svc.get_record(db, Supplier, supplier_id)
    if supplier is None:
        raise _not_found("Supplier")
    return supplier


# ============================ NOTIFICATIONS ============================


@router.get("/notifications/count", response_model=schema.NotificationCount)
async def notifications_count(db: Session = Depends(get_db)):
    return svc.notifications_count(db)


@router.get("/notifications/unread", response_model=list[schema.NotificationRead])
async def notifications_unread(db: Session = Depends(get_db)):
    return svc.notifications_unread(db)


@router.get("/notifications/recent", response_model=list[schema.NotificationRead])
async def notifications_recent(limit: int = Query(default=10), db: Session = Depends(get_db)):
    return svc.list_records(db, Notification)[:limit]


@router.get("/notifications/priority/{level}", response_model=list[schema.NotificationRead])
async def notifications_by_priority(level: str, db: Session = Depends(get_db)):
    return svc.filter_records(db, Notification, level=level)


@router.get("/notifications/type/{level}", response_model=list[schema.NotificationRead])
async def notifications_by_type(level: str, db: Session = Depends(get_db)):
    # Notifications are categorised by `level`; treat the requested "type" as level.
    return svc.filter_records(db, Notification, level=level)


@router.get("/notifications/date-range", response_model=list[schema.NotificationRead])
async def notifications_date_range(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    start, end = svc._parse_dt(startDate), svc._parse_dt(endDate)
    return [
        n
        for n in svc.list_records(db, Notification)
        if (start is None or n.created_at >= start) and (end is None or n.created_at <= end)
    ]


@router.patch("/notifications/mark-all-read", response_model=list[schema.NotificationRead])
async def notifications_mark_all_read(db: Session = Depends(get_db)):
    return svc.notifications_mark_all_read(db)


@router.delete("/notifications/read")
async def delete_read_notifications(db: Session = Depends(get_db)) -> dict:
    return {"deleted": svc.delete_read_notifications(db)}


@router.get("/notifications/{notification_id}", response_model=schema.NotificationRead)
async def get_notification(notification_id: int, db: Session = Depends(get_db)):
    notification = svc.get_record(db, Notification, notification_id)
    if notification is None:
        raise _not_found("Notification")
    return notification


@router.patch("/notifications/{notification_id}/read", response_model=schema.NotificationRead)
async def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    notification = svc.notification_set_read(db, notification_id, read=1)
    if notification is None:
        raise _not_found("Notification")
    return notification


@router.patch("/notifications/{notification_id}/dismiss", response_model=schema.NotificationRead)
async def dismiss_notification(notification_id: int, db: Session = Depends(get_db)):
    notification = svc.notification_set_read(db, notification_id, read=1)
    if notification is None:
        raise _not_found("Notification")
    return notification


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: int, db: Session = Depends(get_db)) -> None:
    if not svc.delete_record(db, Notification, notification_id):
        raise _not_found("Notification")


# ============================ ACTIVITIES ============================


@router.get("/activities/recent", response_model=list[schema.ActivityRead])
async def activities_recent(limit: int = Query(default=10), db: Session = Depends(get_db)):
    return svc.activities_recent(db, limit)


@router.get("/activities/user/{name}", response_model=list[schema.ActivityRead])
async def activities_by_user(name: str, db: Session = Depends(get_db)):
    return svc.search_records(db, Activity, ["message"], name)


@router.get("/activities/{activity_id}", response_model=schema.ActivityRead)
async def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = svc.get_record(db, Activity, activity_id)
    if activity is None:
        raise _not_found("Activity")
    return activity


@router.patch(
    "/activities/{activity_id}",
    response_model=schema.ActivityRead,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def update_activity(activity_id: int, payload: schema.ActivityUpdate, db: Session = Depends(get_db)):
    activity = svc.update_record(db, Activity, activity_id, payload)
    if activity is None:
        raise _not_found("Activity")
    return activity


@router.delete(
    "/activities/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def delete_activity(activity_id: int, db: Session = Depends(get_db)) -> None:
    if not svc.delete_record(db, Activity, activity_id):
        raise _not_found("Activity")


# ============================ DAMAGED CASES ============================


@router.get("/damaged-cases/product/{product_id}", response_model=list[schema.DamagedCaseRead])
async def damaged_cases_by_product(product_id: int, db: Session = Depends(get_db)):
    return svc.filter_records(db, DamagedCase, product_id=product_id)


@router.get("/damaged-cases/{record_id}", response_model=schema.DamagedCaseRead)
async def get_damaged_case(record_id: int, db: Session = Depends(get_db)):
    record = svc.get_record(db, DamagedCase, record_id)
    if record is None:
        raise _not_found("Damaged case")
    return record


@router.patch(
    "/damaged-cases/{record_id}",
    response_model=schema.DamagedCaseRead,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def update_damaged_case(record_id: int, payload: schema.DamagedCaseUpdate, db: Session = Depends(get_db)):
    record = svc.update_record(db, DamagedCase, record_id, payload)
    if record is None:
        raise _not_found("Damaged case")
    return record


@router.delete(
    "/damaged-cases/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def delete_damaged_case(record_id: int, db: Session = Depends(get_db)) -> None:
    if not svc.delete_record(db, DamagedCase, record_id):
        raise _not_found("Damaged case")


# ======================= EMPTY CASE TRANSACTIONS =======================


@router.get("/empty-case-transactions/pending", response_model=list[schema.EmptyCaseTransactionRead])
async def empty_cases_pending(db: Session = Depends(get_db)):
    txns = svc.list_records(db, EmptyCaseTransaction)
    return [t for t in txns if t.status in ("pending", "partial")]


@router.get("/empty-case-transactions/customer/{customer_id}", response_model=list[schema.EmptyCaseTransactionRead])
async def empty_cases_by_customer(customer_id: int, db: Session = Depends(get_db)):
    return svc.filter_records(db, EmptyCaseTransaction, customer_id=customer_id)


@router.get("/empty-case-transactions/{record_id}", response_model=schema.EmptyCaseTransactionRead)
async def get_empty_case(record_id: int, db: Session = Depends(get_db)):
    record = svc.get_record(db, EmptyCaseTransaction, record_id)
    if record is None:
        raise _not_found("Empty case transaction")
    return record


@router.patch(
    "/empty-case-transactions/{record_id}",
    response_model=schema.EmptyCaseTransactionRead,
    dependencies=[Depends(require_roles(*OPERATIONS_ROLES))],
)
async def update_empty_case(
    record_id: int, payload: schema.EmptyCaseTransactionUpdate, db: Session = Depends(get_db)
):
    record = svc.update_record(db, EmptyCaseTransaction, record_id, payload)
    if record is None:
        raise _not_found("Empty case transaction")
    return record


@router.delete(
    "/empty-case-transactions/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*OPERATIONS_ROLES))],
)
async def delete_empty_case(record_id: int, db: Session = Depends(get_db)) -> None:
    if not svc.delete_record(db, EmptyCaseTransaction, record_id):
        raise _not_found("Empty case transaction")


# ============================ DASHBOARD ============================


@router.get("/dashboard/recent-activity", response_model=list[schema.ActivityRead])
async def dashboard_recent_activity(limit: int = Query(default=10), db: Session = Depends(get_db)):
    return svc.activities_recent(db, limit)


# ============================ SUPPLIER RETURNS ============================


@router.get("/supplier-returns/supplier/{supplier_id}", response_model=list[schema.SupplierReturnRead])
async def supplier_returns_by_supplier(supplier_id: int, db: Session = Depends(get_db)):
    return svc.filter_records(db, SupplierReturn, supplier_id=supplier_id)


@router.get("/supplier-returns/{record_id}", response_model=schema.SupplierReturnRead)
async def get_supplier_return(record_id: int, db: Session = Depends(get_db)):
    record = svc.get_record(db, SupplierReturn, record_id)
    if record is None:
        raise _not_found("Supplier return")
    return record


@router.patch(
    "/supplier-returns/{record_id}",
    response_model=schema.SupplierReturnRead,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def update_supplier_return(record_id: int, payload: schema.SupplierReturnUpdate, db: Session = Depends(get_db)):
    record = svc.update_record(db, SupplierReturn, record_id, payload)
    if record is None:
        raise _not_found("Supplier return")
    return record


@router.delete(
    "/supplier-returns/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def delete_supplier_return(record_id: int, db: Session = Depends(get_db)) -> None:
    if not svc.delete_record(db, SupplierReturn, record_id):
        raise _not_found("Supplier return")


# ============================ TRANSACTION AUDITS ============================


@router.get("/transaction-audits/date-range", response_model=list[schema.TransactionAuditRead])
async def audits_date_range(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    audits = svc.list_records(db, TransactionAudit)
    start, end = svc._parse_dt(startDate), svc._parse_dt(endDate)
    return [
        a
        for a in audits
        if (start is None or a.performed_at >= start) and (end is None or a.performed_at <= end)
    ]


@router.get("/transaction-audits/type/{transaction_type}", response_model=list[schema.TransactionAuditRead])
async def audits_by_type(transaction_type: str, db: Session = Depends(get_db)):
    return svc.filter_records(db, TransactionAudit, transaction_type=transaction_type)


@router.get("/transaction-audits/user/{name}", response_model=list[schema.TransactionAuditRead])
async def audits_by_user(name: str, db: Session = Depends(get_db)):
    return svc.filter_records(db, TransactionAudit, performed_by=name)


@router.get("/transaction-audits/{record_id}", response_model=schema.TransactionAuditRead)
async def get_audit(record_id: int, db: Session = Depends(get_db)):
    record = svc.get_record(db, TransactionAudit, record_id)
    if record is None:
        raise _not_found("Transaction audit")
    return record
