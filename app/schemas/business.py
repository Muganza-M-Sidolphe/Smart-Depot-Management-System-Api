from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )


class UserBase(APIModel):
    name: str
    email: str
    role: str
    phone: str | None = None
    status: str = "active"


class UserCreate(UserBase):
    # Optional so admins can pre-create accounts; if given, the user can log in.
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserUpdate(APIModel):
    name: str | None = None
    email: str | None = None
    role: str | None = None
    phone: str | None = None
    status: str | None = None


class UserRead(UserBase):
    id: int
    created_at: datetime
    must_change_password: bool = False

    @field_validator("must_change_password", mode="before")
    @classmethod
    def _coerce_none(cls, value: object) -> bool:
        return bool(value) if value is not None else False


class SupplierBase(APIModel):
    name: str
    contact: str
    phone: str
    email: str
    products_supplied: int = 0


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(APIModel):
    name: str | None = None
    contact: str | None = None
    phone: str | None = None
    email: str | None = None
    products_supplied: int | None = None


class SupplierRead(SupplierBase):
    id: int
    created_at: datetime


class ProductBase(APIModel):
    name: str
    brand: str
    category: str
    full_cases: int = Field(default=0, ge=0)
    empty_cases: int = Field(default=0, ge=0)
    purchase_price: float = Field(default=0, ge=0)
    selling_price: float = Field(default=0, ge=0)
    supplier: str
    batch_number: str
    manufacture_date: datetime
    expiry_date: datetime
    low_stock_threshold: int = Field(default=0, ge=0)
    deposit_amount: float = Field(default=0, ge=0)
    # Container / bottle-level extras (persisted as-is)
    container_type: str | None = None
    container_size_label: str | None = None
    bottles_per_container: int | None = None
    purchase_price_per_container: float | None = None
    selling_price_per_container: float | None = None
    bottle_info: dict[str, Any] | None = None
    partial_cases: list[Any] | None = None
    last_stock_check: datetime | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(APIModel):
    name: str | None = None
    brand: str | None = None
    category: str | None = None
    full_cases: int | None = Field(default=None, ge=0)
    empty_cases: int | None = Field(default=None, ge=0)
    purchase_price: float | None = Field(default=None, ge=0)
    selling_price: float | None = Field(default=None, ge=0)
    supplier: str | None = None
    batch_number: str | None = None
    manufacture_date: datetime | None = None
    expiry_date: datetime | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0)
    deposit_amount: float | None = Field(default=None, ge=0)
    container_type: str | None = None
    container_size_label: str | None = None
    bottles_per_container: int | None = None
    purchase_price_per_container: float | None = None
    selling_price_per_container: float | None = None
    bottle_info: dict[str, Any] | None = None
    partial_cases: list[Any] | None = None
    last_stock_check: datetime | None = None


class ProductRead(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None


class CustomerBase(APIModel):
    name: str
    phone: str
    email: str = ""
    address: str = ""
    total_spent: float = 0
    type: str = "retail"
    total_transactions: int = 0
    pending_empties: int = 0
    total_purchases: float = 0
    refundable_deposits: float = 0
    unpaid_balance: float = 0
    city: str = ""
    notes: str = ""


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(APIModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    total_spent: float | None = None
    type: str | None = None
    total_transactions: int | None = None
    pending_empties: int | None = None
    total_purchases: float | None = None
    refundable_deposits: float | None = None
    unpaid_balance: float | None = None
    city: str | None = None
    notes: str | None = None


class CustomerRead(CustomerBase):
    id: int
    updated_at: datetime
    created_at: datetime


class SaleItemCreate(APIModel):
    product_id: int
    name: str | None = None
    quantity: int = Field(gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    empty_cases_returned: int = Field(default=0, ge=0)
    remaining_empty_cases: int = Field(default=0, ge=0)


class SaleItemRead(APIModel):
    id: int
    product_id: int
    name: str
    quantity: int
    unit_price: float
    subtotal: float
    empty_cases_returned: int = 0
    remaining_empty_cases: int = 0


class SalePaymentCreate(APIModel):
    amount: float = Field(gt=0)
    method: str = "cash"
    received_by: str
    note: str | None = None


class SalePaymentRead(APIModel):
    id: int
    sale_id: int
    amount: float
    method: str
    received_by: str
    note: str | None = None
    created_at: datetime


class SaleCreate(APIModel):
    customer_id: int | None = None
    customer_name: str
    items: list[SaleItemCreate]
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)  # percentage, e.g. 10 for 10%
    payment: str
    amount_paid: float = Field(default=0, ge=0)
    is_partial_payment: bool = False
    remaining_balance: float | None = Field(default=None, ge=0)
    cashier: str


class SaleRead(APIModel):
    id: int
    receipt_no: str
    customer_id: int | None = None
    customer_name: str
    items: list[SaleItemRead]
    subtotal: float
    discount: float
    tax: float
    total: float
    payment: str
    amount_paid: float
    change: float
    is_partial_payment: bool
    remaining_balance: float
    cashier: str
    payment_method: str
    expected_empties: int
    returned_empties: int
    empty_cases_total: int
    remaining_empty_cases_total: int
    invoice_number: str
    status: str
    payment_status: str
    payments: list[SalePaymentRead] = []
    created_at: datetime

    @field_validator(
        "tax",
        "remaining_balance",
        "empty_cases_total",
        "remaining_empty_cases_total",
        "is_partial_payment",
        "payment_status",
        mode="before",
    )
    @classmethod
    def _fill_none(cls, value: object, info) -> object:
        # Older rows (migrated) may be NULL for these newer columns.
        if value is not None:
            return value
        return {"payment_status": "paid", "is_partial_payment": False}.get(info.field_name, 0)


class ExpenseBase(APIModel):
    title: str
    category: str
    amount: float
    date: datetime
    note: str | None = None
    status: str | None = None
    recorded_by: str
    invoice_number: str = ""
    supplier_name: str | None = None
    # Additional fields from the frontend expense form (persisted as-is)
    description: str | None = None
    payment_method: str | None = None
    due_date: datetime | None = None
    receipt_number: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    created_by: str | None = None
    updated_by: str | None = None


# Input-only receipt fields shared by create/update. The base64 `receipt` is
# stored on disk and turned into `receipt_url`; it is never persisted verbatim.
class ExpenseReceiptInput(APIModel):
    receipt: str | None = None
    receipt_file_name: str | None = None
    receipt_file_type: str | None = None
    receipt_file_size: int | None = None
    notes: str | None = None  # frontend alias for `note`


class ExpenseCreate(ExpenseBase, ExpenseReceiptInput):
    pass


class ExpenseUpdate(ExpenseReceiptInput):
    title: str | None = None
    category: str | None = None
    amount: float | None = None
    date: datetime | None = None
    note: str | None = None
    status: str | None = None
    recorded_by: str | None = None
    invoice_number: str | None = None
    supplier_name: str | None = None
    description: str | None = None
    payment_method: str | None = None
    due_date: datetime | None = None
    receipt_number: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    created_by: str | None = None
    updated_by: str | None = None


class ExpenseRead(ExpenseBase):
    id: int
    updated_at: datetime | None = None
    receipt_url: str | None = None
    receipt_file_name: str | None = None


class ActivityCreate(APIModel):
    type: str
    message: str


class ActivityRead(ActivityCreate):
    id: int
    created_at: datetime


class NotificationCreate(APIModel):
    level: str
    title: str
    message: str
    read: bool = False


class NotificationRead(NotificationCreate):
    id: int
    created_at: datetime


class EmptyCaseTransactionBase(APIModel):
    product_id: int
    customer_id: int | None = None
    customer_name: str | None = None
    transaction_type: str
    total_quantity: int
    returned_quantity: int = 0
    pending_quantity: int
    deposit_amount: float
    total_deposit_value: float
    refunded_amount: float = 0
    expected_return_date: datetime | None = None
    actual_return_date: datetime | None = None
    product_name: str
    status: str = "pending"
    notes: str | None = None
    created_by: str


class EmptyCaseTransactionCreate(EmptyCaseTransactionBase):
    pass


class EmptyCaseTransactionUpdate(APIModel):
    returned_quantity: int | None = None
    pending_quantity: int | None = None
    refunded_amount: float | None = None
    expected_return_date: datetime | None = None
    actual_return_date: datetime | None = None
    status: str | None = None
    notes: str | None = None


class EmptyCaseTransactionRead(EmptyCaseTransactionBase):
    id: int
    created_at: datetime
    updated_at: datetime


class EmptyCaseReturnRequest(APIModel):
    return_quantity: int = Field(gt=0)
    processed_by: str


class SupplierReturnBase(APIModel):
    supplier_id: int
    supplier_name: str
    product_id: int
    product_name: str
    quantity: int
    receipt_number: str
    returned_date: datetime
    received_by: str
    notes: str | None = None


class SupplierReturnCreate(SupplierReturnBase):
    pass


class SupplierReturnRead(SupplierReturnBase):
    id: int


class DamagedCaseBase(APIModel):
    product_id: int
    product_name: str
    quantity: int
    reason: str
    damage_cost: float
    reported_date: datetime
    reported_by: str
    notes: str | None = None


class DamagedCaseCreate(DamagedCaseBase):
    pass


class DamagedCaseRead(DamagedCaseBase):
    id: int


class TransactionAuditCreate(APIModel):
    transaction_id: int
    transaction_type: str
    action: str
    previous_state: dict[str, Any] | None = None
    new_state: dict[str, Any] | None = None
    performed_by: str
    notes: str | None = None


class TransactionAuditRead(TransactionAuditCreate):
    id: int
    performed_at: datetime


class DashboardReport(APIModel):
    total_products: int
    total_customers: int
    total_sales: int
    sales_revenue: float
    total_expenses: float
    gross_profit: float
    low_stock_products: int
    expiring_products: int
    expired_products: int
    pending_empty_cases: int
    refundable_deposits: float
    recent_activities: list[ActivityRead]


class ReportSettingsUpdate(APIModel):
    recipients: list[str] | None = None
    whatsapp_number: str | None = None
    daily_enabled: bool | None = None
    weekly_enabled: bool | None = None
    monthly_enabled: bool | None = None
    send_hour: int | None = Field(default=None, ge=0, le=23)
    weekly_weekday: int | None = Field(default=None, ge=0, le=6)
    monthly_day: int | None = Field(default=None, ge=1, le=28)


class ReportMetrics(APIModel):
    sales_count: int
    revenue: float
    expenses: float
    profit: float
    cases_sold: int


class ReportSendResult(APIModel):
    period: str
    recipients: list[str]
    emailed: bool
    pdf_bytes: int
    metrics: ReportMetrics


class ReportSettingsRead(APIModel):
    id: int
    recipients: list[str] = []
    whatsapp_number: str | None = None
    daily_enabled: bool
    weekly_enabled: bool
    monthly_enabled: bool
    send_hour: int
    weekly_weekday: int
    monthly_day: int
    last_daily_sent: datetime | None = None
    last_weekly_sent: datetime | None = None
    last_monthly_sent: datetime | None = None
    updated_at: datetime
