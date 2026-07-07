from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    contact: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    products_supplied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    full_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    empty_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    supplier: Mapped[str] = mapped_column(String(160), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    manufacture_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expiry_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deposit_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    # Container / unit-conversion model (prices entered per container, stored per bottle)
    container_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    container_size_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    bottles_per_container: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purchase_price_per_container: Mapped[float | None] = mapped_column(Float, nullable=True)
    selling_price_per_container: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Bottle-level tracking {damaged, missing, returned, notes}
    bottle_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Opened/partial cases (array of {bottleCount, openedDate, reason, ...})
    partial_cases: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_stock_check: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sale_items: Mapped[list["SaleItem"]] = relationship(back_populates="product")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    address: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    total_spent: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    type: Mapped[str] = mapped_column(String(40), default="retail", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    total_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_empties: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_purchases: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    refundable_deposits: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    unpaid_balance: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    city: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    sales: Mapped[list["Sale"]] = relationship(back_populates="customer")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    receipt_no: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    discount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    tax: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    total: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    payment: Mapped[str] = mapped_column(String(40), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    change: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    is_partial_payment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remaining_balance: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    empty_cases_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remaining_empty_cases_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cashier: Mapped[str] = mapped_column(String(120), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False)
    expected_empties: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returned_empties: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="completed", nullable=False)
    # "paid" | "partial" | "unpaid" — settlement state of this sale
    payment_status: Mapped[str] = mapped_column(String(20), default="paid", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    customer: Mapped[Customer | None] = relationship(back_populates="sales")
    items: Mapped[list["SaleItem"]] = relationship(back_populates="sale", cascade="all, delete-orphan")
    payments: Mapped[list["SalePayment"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", order_by="SalePayment.id"
    )


class SalePayment(Base):
    """An individual payment made toward a sale (supports installments)."""

    __tablename__ = "sale_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(40), default="cash", nullable=False)
    received_by: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="payments")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    empty_cases_returned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remaining_empty_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="sale_items")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recorded_by: Mapped[str] = mapped_column(String(120), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    # Additional fields sent by the frontend expense form
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    receipt_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Uploaded receipt (stored locally, served via /uploads)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    receipt_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ReportSettings(Base):
    """Single-row (id=1) configuration for automatic report delivery."""

    __tablename__ = "report_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipients: Mapped[list | None] = mapped_column(JSON, nullable=True)  # list of emails
    whatsapp_number: Mapped[str | None] = mapped_column(String(40), nullable=True)  # future use
    daily_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weekly_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    monthly_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    send_hour: Mapped[int] = mapped_column(Integer, default=8, nullable=False)  # 0-23, server time
    weekly_weekday: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=Mon..6=Sun
    monthly_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-28
    last_daily_sent: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_weekly_sent: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_monthly_sent: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class EmptyCaseTransaction(Base):
    __tablename__ = "empty_case_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    returned_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deposit_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    total_deposit_value: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    refunded_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    expected_return_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_return_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class SupplierReturn(Base):
    __tablename__ = "supplier_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(160), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    receipt_number: Mapped[str] = mapped_column(String(80), nullable=False)
    returned_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    received_by: Mapped[str] = mapped_column(String(120), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DamagedCase(Base):
    __tablename__ = "damaged_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    damage_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    reported_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reported_by: Mapped[str] = mapped_column(String(120), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TransactionAudit(Base):
    __tablename__ = "transaction_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transaction_id: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    performed_by: Mapped[str] = mapped_column(String(120), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
