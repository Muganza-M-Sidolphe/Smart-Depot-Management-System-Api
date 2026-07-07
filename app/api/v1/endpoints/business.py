from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.roles import MANAGEMENT, OPERATIONS_ROLES, SALES_ROLES, STOCK_ROLES, USER_ADMIN_ROLES
from app.models.business import (
    Activity,
    Customer,
    Expense,
    Notification,
    Product,
    Supplier,
    TransactionAudit,
    User,
)
from app.schemas import business as schema
from app.services import business_service

router = APIRouter()


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")


@router.get("/users/", response_model=list[schema.UserRead])
async def list_users(db: Session = Depends(get_db)) -> list[User]:
    return business_service.list_records(db, User)


@router.post(
    "/users/",
    response_model=schema.UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*USER_ADMIN_ROLES))],
)
async def create_user(payload: schema.UserCreate, db: Session = Depends(get_db)) -> User:
    return business_service.create_user(db, payload)


@router.patch(
    "/users/{record_id}",
    response_model=schema.UserRead,
    dependencies=[Depends(require_roles(*USER_ADMIN_ROLES))],
)
async def update_user(record_id: int, payload: schema.UserUpdate, db: Session = Depends(get_db)) -> User:
    record = business_service.update_record(db, User, record_id, payload)
    if record is None:
        raise not_found("User")
    return record


@router.delete(
    "/users/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*USER_ADMIN_ROLES))],
)
async def delete_user(record_id: int, db: Session = Depends(get_db)) -> None:
    if not business_service.delete_record(db, User, record_id):
        raise not_found("User")


@router.get("/suppliers/", response_model=list[schema.SupplierRead])
async def list_suppliers(db: Session = Depends(get_db)) -> list[Supplier]:
    return business_service.list_records(db, Supplier)


@router.post(
    "/suppliers/",
    response_model=schema.SupplierRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def create_supplier(payload: schema.SupplierCreate, db: Session = Depends(get_db)) -> Supplier:
    return business_service.create_record(db, Supplier, payload)


@router.patch(
    "/suppliers/{record_id}",
    response_model=schema.SupplierRead,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def update_supplier(record_id: int, payload: schema.SupplierUpdate, db: Session = Depends(get_db)) -> Supplier:
    record = business_service.update_record(db, Supplier, record_id, payload)
    if record is None:
        raise not_found("Supplier")
    return record


@router.delete(
    "/suppliers/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def delete_supplier(record_id: int, db: Session = Depends(get_db)) -> None:
    if not business_service.delete_record(db, Supplier, record_id):
        raise not_found("Supplier")


@router.get("/products/", response_model=list[schema.ProductRead])
async def list_products(db: Session = Depends(get_db)) -> list[Product]:
    return business_service.list_records(db, Product)


@router.post(
    "/products/",
    response_model=schema.ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def create_product(payload: schema.ProductCreate, db: Session = Depends(get_db)) -> Product:
    return business_service.create_record(db, Product, payload)


@router.get("/products/{record_id}", response_model=schema.ProductRead)
async def get_product(record_id: int, db: Session = Depends(get_db)) -> Product:
    record = business_service.get_record(db, Product, record_id)
    if record is None:
        raise not_found("Product")
    return record


@router.patch(
    "/products/{record_id}",
    response_model=schema.ProductRead,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def update_product(record_id: int, payload: schema.ProductUpdate, db: Session = Depends(get_db)) -> Product:
    record = business_service.update_record(db, Product, record_id, payload)
    if record is None:
        raise not_found("Product")
    return record


@router.delete(
    "/products/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def delete_product(record_id: int, db: Session = Depends(get_db)) -> None:
    if not business_service.delete_record(db, Product, record_id):
        raise not_found("Product")


@router.get("/customers/", response_model=list[schema.CustomerRead])
async def list_customers(db: Session = Depends(get_db)) -> list[Customer]:
    return business_service.list_records(db, Customer)


@router.post(
    "/customers/",
    response_model=schema.CustomerRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*SALES_ROLES))],
)
async def create_customer(payload: schema.CustomerCreate, db: Session = Depends(get_db)) -> Customer:
    return business_service.create_record(db, Customer, payload)


@router.get("/customers/{record_id}", response_model=schema.CustomerRead)
async def get_customer(record_id: int, db: Session = Depends(get_db)) -> Customer:
    record = business_service.get_record(db, Customer, record_id)
    if record is None:
        raise not_found("Customer")
    return record


@router.patch(
    "/customers/{record_id}",
    response_model=schema.CustomerRead,
    dependencies=[Depends(require_roles(*SALES_ROLES))],
)
async def update_customer(record_id: int, payload: schema.CustomerUpdate, db: Session = Depends(get_db)) -> Customer:
    record = business_service.update_record(db, Customer, record_id, payload)
    if record is None:
        raise not_found("Customer")
    return record


@router.delete(
    "/customers/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*SALES_ROLES))],
)
async def delete_customer(record_id: int, db: Session = Depends(get_db)) -> None:
    if not business_service.delete_record(db, Customer, record_id):
        raise not_found("Customer")


@router.get("/sales/", response_model=list[schema.SaleRead])
async def list_sales(db: Session = Depends(get_db)):
    return business_service.list_sales(db)


@router.post(
    "/sales/",
    response_model=schema.SaleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*SALES_ROLES))],
)
async def create_sale(payload: schema.SaleCreate, db: Session = Depends(get_db)):
    return business_service.create_sale(db, payload)


@router.get("/sales/{record_id}", response_model=schema.SaleRead)
async def get_sale(record_id: int, db: Session = Depends(get_db)):
    record = business_service.get_sale(db, record_id)
    if record is None:
        raise not_found("Sale")
    return record


@router.get("/expenses/", response_model=list[schema.ExpenseRead])
async def list_expenses(db: Session = Depends(get_db)) -> list[Expense]:
    return business_service.list_records(db, Expense)


@router.post(
    "/expenses/",
    response_model=schema.ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def create_expense(payload: schema.ExpenseCreate, db: Session = Depends(get_db)) -> Expense:
    return business_service.create_expense(db, payload)


@router.patch(
    "/expenses/{record_id}",
    response_model=schema.ExpenseRead,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def update_expense(record_id: int, payload: schema.ExpenseUpdate, db: Session = Depends(get_db)) -> Expense:
    record = business_service.update_expense(db, record_id, payload)
    if record is None:
        raise not_found("Expense")
    return record


@router.delete(
    "/expenses/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def delete_expense(record_id: int, db: Session = Depends(get_db)) -> None:
    if not business_service.delete_record(db, Expense, record_id):
        raise not_found("Expense")


@router.get("/activities/", response_model=list[schema.ActivityRead])
async def list_activities(db: Session = Depends(get_db)) -> list[Activity]:
    return business_service.list_records(db, Activity)


@router.post(
    "/activities/",
    response_model=schema.ActivityRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*OPERATIONS_ROLES))],
)
async def create_activity(payload: schema.ActivityCreate, db: Session = Depends(get_db)) -> Activity:
    return business_service.create_record(db, Activity, payload)


@router.get("/notifications/", response_model=list[schema.NotificationRead])
async def list_notifications(db: Session = Depends(get_db)) -> list[Notification]:
    return business_service.list_records(db, Notification)


@router.post(
    "/notifications/generate",
    response_model=list[schema.NotificationRead],
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def generate_notifications(db: Session = Depends(get_db)) -> list[Notification]:
    return business_service.generate_notifications(db)


@router.post(
    "/notifications/mark-read",
    response_model=list[schema.NotificationRead],
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def mark_notifications_read(db: Session = Depends(get_db)) -> list[Notification]:
    return business_service.mark_notifications_read(db)


@router.get("/empty-case-transactions/", response_model=list[schema.EmptyCaseTransactionRead])
async def list_empty_case_transactions(db: Session = Depends(get_db)):
    from app.models.business import EmptyCaseTransaction

    return business_service.list_records(db, EmptyCaseTransaction)


@router.post(
    "/empty-case-transactions/",
    response_model=schema.EmptyCaseTransactionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*OPERATIONS_ROLES))],
)
async def create_empty_case_transaction(payload: schema.EmptyCaseTransactionCreate, db: Session = Depends(get_db)):
    return business_service.create_empty_case_transaction(db, payload)


@router.post(
    "/empty-case-transactions/{record_id}/process-return",
    response_model=schema.EmptyCaseTransactionRead,
    dependencies=[Depends(require_roles(*OPERATIONS_ROLES))],
)
async def process_empty_case_return(
    record_id: int,
    payload: schema.EmptyCaseReturnRequest,
    db: Session = Depends(get_db),
):
    record = business_service.process_empty_case_return(db, record_id, payload)
    if record is None:
        raise not_found("Empty case transaction")
    return record


@router.get("/supplier-returns/", response_model=list[schema.SupplierReturnRead])
async def list_supplier_returns(db: Session = Depends(get_db)):
    from app.models.business import SupplierReturn

    return business_service.list_records(db, SupplierReturn)


@router.post(
    "/supplier-returns/",
    response_model=schema.SupplierReturnRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def create_supplier_return(payload: schema.SupplierReturnCreate, db: Session = Depends(get_db)):
    return business_service.add_supplier_return(db, payload)


@router.get("/damaged-cases/", response_model=list[schema.DamagedCaseRead])
async def list_damaged_cases(db: Session = Depends(get_db)):
    from app.models.business import DamagedCase

    return business_service.list_records(db, DamagedCase)


@router.post(
    "/damaged-cases/",
    response_model=schema.DamagedCaseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
async def create_damaged_case(payload: schema.DamagedCaseCreate, db: Session = Depends(get_db)):
    return business_service.add_damaged_case(db, payload)


@router.get("/transaction-audits/", response_model=list[schema.TransactionAuditRead])
async def list_transaction_audits(db: Session = Depends(get_db)) -> list[TransactionAudit]:
    return business_service.list_records(db, TransactionAudit)


@router.post(
    "/transaction-audits/",
    response_model=schema.TransactionAuditRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MANAGEMENT))],
)
async def create_transaction_audit(payload: schema.TransactionAuditCreate, db: Session = Depends(get_db)):
    return business_service.create_record(db, TransactionAudit, payload)


@router.get("/reports/dashboard", response_model=schema.DashboardReport)
async def get_dashboard_report(db: Session = Depends(get_db)) -> schema.DashboardReport:
    return business_service.dashboard_report(db)
