from datetime import datetime, timedelta
from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.business import (
    Activity,
    Customer,
    DamagedCase,
    EmptyCaseTransaction,
    Expense,
    Notification,
    Product,
    Sale,
    SaleItem,
    SalePayment,
    Supplier,
    SupplierReturn,
    TransactionAudit,
    User,
    utcnow,
)
from app.schemas import business as schema

ModelT = TypeVar("ModelT")


def list_records(db: Session, model: type[ModelT]) -> list[ModelT]:
    return list(db.scalars(select(model).order_by(model.id.desc())))  # type: ignore[attr-defined]


def get_record(db: Session, model: type[ModelT], record_id: int) -> ModelT | None:
    return db.get(model, record_id)


def create_record(db: Session, model: type[ModelT], payload: Any) -> ModelT:
    record = model(**payload.model_dump())  # type: ignore[call-arg]
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def generate_password(length: int = 10) -> str:
    """Generate a readable random password for a newly created account."""
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_user(db: Session, payload: schema.UserCreate) -> tuple[User, str | None]:
    """Create a user and ensure they have a password so they can log in.

    If the caller did not supply a password, a default one is generated and
    returned (as plaintext) so the endpoint can email it to the user. The
    returned password is None when the caller supplied their own.
    """
    from app.core.security import hash_password

    data = payload.model_dump()
    password = data.pop("password", None)
    generated: str | None = None
    if not password:
        password = generate_password()
        generated = password

    user = User(**data)
    user.password_hash = hash_password(password)
    # Users given a system-generated temp password must change it on first login.
    user.must_change_password = generated is not None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, generated


_EXPENSE_RECEIPT_KEYS = ("receipt", "receipt_file_name", "receipt_file_type", "receipt_file_size", "notes")


def _apply_expense_receipt(data: dict[str, Any]) -> None:
    """Handle the input-only receipt/notes fields in an expense payload in place.

    Saves the base64 receipt to disk and replaces it with receipt_url +
    receipt_file_name; maps the frontend `notes` alias onto `note`.
    """
    from app.core.uploads import save_receipt

    receipt = data.pop("receipt", None)
    receipt_file_name = data.pop("receipt_file_name", None)
    data.pop("receipt_file_type", None)
    data.pop("receipt_file_size", None)
    notes = data.pop("notes", None)

    if notes is not None and not data.get("note"):
        data["note"] = notes

    if receipt:
        try:
            data["receipt_url"] = save_receipt(receipt, receipt_file_name)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if receipt_file_name:
            data["receipt_file_name"] = receipt_file_name


def create_expense(db: Session, payload: schema.ExpenseCreate) -> Expense:
    data = payload.model_dump()
    _apply_expense_receipt(data)
    expense = Expense(**data)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def update_expense(db: Session, record_id: int, payload: schema.ExpenseUpdate) -> Expense | None:
    expense = db.get(Expense, record_id)
    if expense is None:
        return None

    data = payload.model_dump(exclude_unset=True)
    _apply_expense_receipt(data)
    for key, value in data.items():
        setattr(expense, key, value)
    expense.updated_at = utcnow()

    db.commit()
    db.refresh(expense)
    return expense


def update_record(db: Session, model: type[ModelT], record_id: int, payload: Any) -> ModelT | None:
    record = get_record(db, model, record_id)
    if record is None:
        return None

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    if hasattr(record, "updated_at"):
        setattr(record, "updated_at", utcnow())

    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, model: type[ModelT], record_id: int) -> bool:
    record = get_record(db, model, record_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True


def create_activity(db: Session, activity_type: str, message: str) -> Activity:
    activity = Activity(type=activity_type, message=message)
    db.add(activity)
    return activity


def create_audit(
    db: Session,
    transaction_id: int,
    transaction_type: str,
    action: str,
    performed_by: str,
    previous_state: dict[str, Any] | None = None,
    new_state: dict[str, Any] | None = None,
    notes: str | None = None,
) -> TransactionAudit:
    audit = TransactionAudit(
        transaction_id=transaction_id,
        transaction_type=transaction_type,
        action=action,
        previous_state=previous_state,
        new_state=new_state,
        performed_by=performed_by,
        notes=notes,
    )
    db.add(audit)
    return audit


def create_sale(db: Session, payload: schema.SaleCreate) -> Sale:
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sale must include at least one item")

    products_by_id: dict[int, Product] = {}
    for item in payload.items:
        product = db.get(Product, item.product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item.product_id} not found")
        if product.full_cases < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product.name}",
            )
        products_by_id[item.product_id] = product

    sale_count = db.scalar(select(func.count(Sale.id))) or 0
    subtotal = 0.0
    pending_empties = 0       # cases still owed after any returned at the sale
    returned_empties = 0      # cases returned right at the point of sale
    pending_deposit_value = 0.0
    total_deposit_value = 0.0  # deposit value for all cases sold (returned or not)

    sale = Sale(
        receipt_no=f"RCP-{1001 + sale_count}",
        customer_id=payload.customer_id,
        customer_name=payload.customer_name,
        subtotal=0,
        discount=payload.discount,
        tax=0,
        total=0,
        payment=payload.payment,
        amount_paid=payload.amount_paid,
        change=0,
        is_partial_payment=payload.is_partial_payment,
        remaining_balance=0,
        cashier=payload.cashier,
        payment_method=payload.payment,
        expected_empties=0,
        returned_empties=0,
        empty_cases_total=0,
        remaining_empty_cases_total=0,
        total_deposit_value=0,
        invoice_number=f"INV-{1001 + sale_count}",
        status="completed",
    )
    db.add(sale)
    db.flush()

    for item in payload.items:
        product = products_by_id[item.product_id]
        unit_price = item.unit_price if item.unit_price is not None else product.selling_price
        line_subtotal = item.quantity * unit_price
        subtotal += line_subtotal

        # Empties returned immediately at the sale reduce what the customer still owes.
        returned_now = min(item.empty_cases_returned, item.quantity)
        pending_now = item.quantity - returned_now
        pending_empties += pending_now
        returned_empties += returned_now
        pending_deposit_value += pending_now * product.deposit_amount
        total_deposit_value += item.quantity * product.deposit_amount
        product.full_cases -= item.quantity

        db.add(
            SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                name=item.name or product.name,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=line_subtotal,
                empty_cases_returned=returned_now,
                remaining_empty_cases=pending_now,
            )
        )

        db.add(
            EmptyCaseTransaction(
                product_id=product.id,
                customer_id=payload.customer_id,
                customer_name=payload.customer_name,
                transaction_type="sale",
                total_quantity=item.quantity,
                returned_quantity=returned_now,
                pending_quantity=pending_now,
                deposit_amount=product.deposit_amount,
                total_deposit_value=item.quantity * product.deposit_amount,
                refunded_amount=returned_now * product.deposit_amount,
                expected_return_date=utcnow() + timedelta(days=7),
                actual_return_date=utcnow() if pending_now == 0 and returned_now > 0 else None,
                product_name=product.name,
                status="completed" if pending_now == 0 else ("partial" if returned_now > 0 else "pending"),
                created_by=payload.cashier,
            )
        )

    taxable = max(0.0, subtotal - payload.discount)
    tax_amount = round(taxable * payload.tax / 100.0, 2)
    total = taxable + tax_amount
    remaining_balance = (
        payload.remaining_balance
        if payload.remaining_balance is not None
        else max(0.0, total - payload.amount_paid)
    )
    if not payload.is_partial_payment:
        remaining_balance = 0.0

    amount_toward_sale = min(payload.amount_paid, total)
    sale.subtotal = subtotal
    sale.tax = tax_amount
    sale.total = total
    sale.change = max(0.0, payload.amount_paid - total)
    sale.expected_empties = pending_empties
    sale.returned_empties = returned_empties
    sale.empty_cases_total = returned_empties
    sale.remaining_empty_cases_total = pending_empties
    sale.total_deposit_value = total_deposit_value
    sale.remaining_balance = remaining_balance
    sale.payment_status = (
        "paid" if remaining_balance <= 0 else ("unpaid" if amount_toward_sale <= 0 else "partial")
    )

    # Record the amount paid at the point of sale as the first payment.
    if amount_toward_sale > 0:
        db.add(
            SalePayment(
                sale_id=sale.id,
                amount=amount_toward_sale,
                method=payload.payment,
                received_by=payload.cashier,
                note="Payment at point of sale",
            )
        )

    if payload.customer_id is not None:
        customer = db.get(Customer, payload.customer_id)
        if customer is not None:
            customer.pending_empties += pending_empties
            customer.total_purchases += total
            customer.total_spent += total
            customer.refundable_deposits += pending_deposit_value
            customer.unpaid_balance += remaining_balance
            customer.total_transactions += 1
            customer.updated_at = utcnow()

    create_activity(
        db,
        "sale",
        f"{payload.cashier} sold {pending_empties + returned_empties} cases to {payload.customer_name}",
    )
    db.commit()
    return get_sale(db, sale.id)  # type: ignore[return-value]


def get_sale(db: Session, sale_id: int) -> Sale | None:
    return db.scalars(
        select(Sale)
        .options(selectinload(Sale.items), selectinload(Sale.payments))
        .where(Sale.id == sale_id)
    ).first()


def list_sales(db: Session) -> list[Sale]:
    return list(
        db.scalars(
            select(Sale)
            .options(selectinload(Sale.items), selectinload(Sale.payments))
            .order_by(Sale.id.desc())
        )
    )


def list_outstanding_sales(db: Session) -> list[Sale]:
    """Sales that still have an unpaid balance (for a receivables view)."""
    return list(
        db.scalars(
            select(Sale)
            .options(selectinload(Sale.items), selectinload(Sale.payments))
            .where(Sale.remaining_balance > 0)
            .order_by(Sale.id.desc())
        )
    )


def list_sale_payments(db: Session, sale_id: int) -> list[SalePayment] | None:
    if db.get(Sale, sale_id) is None:
        return None
    return list(
        db.scalars(select(SalePayment).where(SalePayment.sale_id == sale_id).order_by(SalePayment.id))
    )


def record_sale_payment(db: Session, sale_id: int, payload: schema.SalePaymentCreate) -> Sale | None:
    """Record a payment toward a sale's outstanding balance (installments)."""
    sale = db.get(Sale, sale_id)
    if sale is None:
        return None
    if sale.remaining_balance <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This sale is already fully paid",
        )
    if payload.amount > sale.remaining_balance + 1e-9:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount exceeds the remaining balance of {sale.remaining_balance:.0f}",
        )

    sale.amount_paid += payload.amount
    sale.remaining_balance = round(max(0.0, sale.total - sale.amount_paid), 2)
    sale.is_partial_payment = sale.remaining_balance > 0
    sale.payment_status = "paid" if sale.remaining_balance <= 0 else "partial"

    db.add(
        SalePayment(
            sale_id=sale.id,
            amount=payload.amount,
            method=payload.method,
            received_by=payload.received_by,
            note=payload.note,
        )
    )

    if sale.customer_id is not None:
        customer = db.get(Customer, sale.customer_id)
        if customer is not None:
            customer.unpaid_balance = round(max(0.0, customer.unpaid_balance - payload.amount), 2)
            customer.updated_at = utcnow()

    create_activity(
        db,
        "sale",
        f"{payload.received_by} received {payload.amount:.0f} payment for {sale.receipt_no} "
        f"({sale.payment_status})",
    )
    db.commit()
    return get_sale(db, sale.id)


def create_empty_case_transaction(
    db: Session,
    payload: schema.EmptyCaseTransactionCreate,
) -> EmptyCaseTransaction:
    transaction = EmptyCaseTransaction(**payload.model_dump())
    db.add(transaction)
    db.flush()
    create_audit(
        db,
        transaction_id=transaction.id,
        transaction_type="empty_case",
        action="created",
        performed_by=payload.created_by,
        new_state={"status": payload.status},
        notes="Initial transaction created",
    )
    create_activity(db, "empty", f"Empty case transaction created for {payload.customer_name or 'Unknown'}")
    db.commit()
    db.refresh(transaction)
    return transaction


def process_empty_case_return(
    db: Session,
    transaction_id: int,
    payload: schema.EmptyCaseReturnRequest,
) -> EmptyCaseTransaction | None:
    transaction = db.get(EmptyCaseTransaction, transaction_id)
    if transaction is None:
        return None
    if payload.return_quantity > transaction.pending_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return quantity cannot exceed pending quantity",
        )

    previous_state = {
        "status": transaction.status,
        "returnedQuantity": transaction.returned_quantity,
        "pendingQuantity": transaction.pending_quantity,
    }
    transaction.returned_quantity += payload.return_quantity
    transaction.pending_quantity -= payload.return_quantity
    transaction.refunded_amount += payload.return_quantity * transaction.deposit_amount
    transaction.status = "completed" if transaction.pending_quantity == 0 else "partial"
    transaction.actual_return_date = utcnow() if transaction.pending_quantity == 0 else transaction.actual_return_date
    transaction.updated_at = utcnow()

    if transaction.customer_id is not None:
        customer = db.get(Customer, transaction.customer_id)
        if customer is not None:
            refund = payload.return_quantity * transaction.deposit_amount
            customer.pending_empties = max(0, customer.pending_empties - payload.return_quantity)
            customer.refundable_deposits = max(0, customer.refundable_deposits - refund)
            customer.updated_at = utcnow()

    create_audit(
        db,
        transaction_id=transaction.id,
        transaction_type="empty_case",
        action="updated",
        performed_by=payload.processed_by,
        previous_state=previous_state,
        new_state={
            "status": transaction.status,
            "returnedQuantity": transaction.returned_quantity,
            "pendingQuantity": transaction.pending_quantity,
        },
        notes=f"Processed return of {payload.return_quantity} cases",
    )
    create_activity(
        db,
        "empty",
        f"{payload.processed_by} processed {payload.return_quantity} empty case return from {transaction.customer_name or 'Unknown'}",
    )
    db.commit()
    db.refresh(transaction)
    return transaction


def add_supplier_return(db: Session, payload: schema.SupplierReturnCreate) -> SupplierReturn:
    supplier_return = SupplierReturn(**payload.model_dump())
    db.add(supplier_return)
    db.flush()
    create_audit(
        db,
        transaction_id=supplier_return.id,
        transaction_type="supplier_return",
        action="created",
        performed_by=payload.received_by,
        new_state={"quantity": payload.quantity},
        notes="Supplier return recorded",
    )
    create_activity(
        db,
        "empty",
        f"{payload.received_by} returned {payload.quantity} cases to {payload.supplier_name}",
    )
    db.commit()
    db.refresh(supplier_return)
    return supplier_return


def add_damaged_case(db: Session, payload: schema.DamagedCaseCreate) -> DamagedCase:
    damaged_case = DamagedCase(**payload.model_dump())
    db.add(damaged_case)
    db.flush()
    create_audit(
        db,
        transaction_id=damaged_case.id,
        transaction_type="damage_report",
        action="created",
        performed_by=payload.reported_by,
        new_state={"quantity": payload.quantity, "damageCost": payload.damage_cost},
        notes="Damaged case reported",
    )
    create_activity(
        db,
        "empty",
        f"{payload.reported_by} reported {payload.quantity} damaged cases of {payload.product_name}",
    )
    db.commit()
    db.refresh(damaged_case)
    return damaged_case


def mark_notifications_read(db: Session) -> list[Notification]:
    notifications = list_records(db, Notification)
    for notification in notifications:
        notification.read = 1
    db.commit()
    return notifications


def generate_notifications(db: Session) -> list[Notification]:
    now = utcnow()
    created: list[Notification] = []
    products = list(db.scalars(select(Product)))
    overdue_count = db.scalar(
        select(func.count(EmptyCaseTransaction.id)).where(
            EmptyCaseTransaction.status.in_(["pending", "partial"]),
            EmptyCaseTransaction.expected_return_date < now,
        )
    ) or 0

    low_stock = [p for p in products if p.full_cases <= p.low_stock_threshold]
    expiring = [p for p in products if now <= p.expiry_date <= now + timedelta(days=30)]
    expired = [p for p in products if p.expiry_date < now]

    specs = []
    if low_stock:
        specs.append(("warning", "Low stock", f"{len(low_stock)} products are below threshold"))
    if expiring:
        specs.append(("warning", "Expiring soon", f"{len(expiring)} products expire within 30 days"))
    if expired:
        specs.append(("urgent", "Expired product", f"{len(expired)} products are expired"))
    if overdue_count:
        specs.append(("urgent", "Overdue returns", f"{overdue_count} empty case returns are overdue"))

    for level, title, message in specs:
        notification = Notification(level=level, title=title, message=message, read=0)
        db.add(notification)
        created.append(notification)
    db.commit()
    for notification in created:
        db.refresh(notification)
    return created


def dashboard_report(db: Session) -> schema.DashboardReport:
    now = utcnow()
    products = list(db.scalars(select(Product)))
    activities = list(db.scalars(select(Activity).order_by(Activity.id.desc()).limit(10)))
    sales_revenue = db.scalar(select(func.coalesce(func.sum(Sale.total), 0.0))) or 0.0
    total_expenses = db.scalar(select(func.coalesce(func.sum(Expense.amount), 0.0))) or 0.0
    pending_empty_cases = db.scalar(
        select(func.coalesce(func.sum(EmptyCaseTransaction.pending_quantity), 0))
    ) or 0
    refundable_deposits = db.scalar(select(func.coalesce(func.sum(Customer.refundable_deposits), 0.0))) or 0.0

    return schema.DashboardReport(
        total_products=db.scalar(select(func.count(Product.id))) or 0,
        total_customers=db.scalar(select(func.count(Customer.id))) or 0,
        total_sales=db.scalar(select(func.count(Sale.id))) or 0,
        sales_revenue=sales_revenue,
        total_expenses=total_expenses,
        gross_profit=sales_revenue - total_expenses,
        low_stock_products=sum(1 for p in products if p.full_cases <= p.low_stock_threshold),
        expiring_products=sum(1 for p in products if now <= p.expiry_date <= now + timedelta(days=30)),
        expired_products=sum(1 for p in products if p.expiry_date < now),
        pending_empty_cases=pending_empty_cases,
        refundable_deposits=refundable_deposits,
        recent_activities=activities,
    )
