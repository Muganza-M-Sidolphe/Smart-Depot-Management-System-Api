from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON
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
    total: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    payment: Mapped[str] = mapped_column(String(40), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    change: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    cashier: Mapped[str] = mapped_column(String(120), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False)
    expected_empties: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returned_empties: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="completed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    customer: Mapped[Customer | None] = relationship(back_populates="sales")
    items: Mapped[list["SaleItem"]] = relationship(back_populates="sale", cascade="all, delete-orphan")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

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
