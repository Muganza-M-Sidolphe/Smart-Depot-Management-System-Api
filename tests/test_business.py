import pytest
from httpx import AsyncClient


PRODUCT_PAYLOAD = {
    "name": "Primus",
    "brand": "Bralirwa",
    "category": "Lager",
    "fullCases": 100,
    "emptyCases": 40,
    "purchasePrice": 9000,
    "sellingPrice": 11000,
    "supplier": "Bralirwa Ltd",
    "batchNumber": "BR-001",
    "manufactureDate": "2026-01-01T00:00:00",
    "expiryDate": "2026-12-01T00:00:00",
    "lowStockThreshold": 10,
    "depositAmount": 3000,
}


CUSTOMER_PAYLOAD = {
    "name": "Kigali Bar",
    "phone": "+250788000000",
    "email": "orders@kigali-bar.rw",
    "address": "Kigali",
    "type": "wholesale",
    "city": "Kigali",
    "notes": "",
}


@pytest.mark.anyio
async def test_product_crud_uses_frontend_camel_case(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/products/", json=PRODUCT_PAYLOAD)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["fullCases"] == 100
    assert created["sellingPrice"] == 11000

    update_response = await client.patch(f"/api/v1/products/{created['id']}", json={"fullCases": 80})
    assert update_response.status_code == 200
    assert update_response.json()["fullCases"] == 80

    list_response = await client.get("/api/v1/products/")
    assert list_response.status_code == 200
    assert list_response.json()[0]["batchNumber"] == "BR-001"

    delete_response = await client.delete(f"/api/v1/products/{created['id']}")
    assert delete_response.status_code == 204


@pytest.mark.anyio
async def test_create_sale_updates_stock_customer_and_empty_cases(client: AsyncClient) -> None:
    product = (await client.post("/api/v1/products/", json=PRODUCT_PAYLOAD)).json()
    customer = (await client.post("/api/v1/customers/", json=CUSTOMER_PAYLOAD)).json()

    response = await client.post(
        "/api/v1/sales/",
        json={
            "customerId": customer["id"],
            "customerName": customer["name"],
            "items": [{"productId": product["id"], "quantity": 5}],
            "discount": 5000,
            "payment": "mobile",
            "amountPaid": 60000,
            "cashier": "Eric Mugisha",
        },
    )

    assert response.status_code == 201
    sale = response.json()
    assert sale["subtotal"] == 55000
    assert sale["total"] == 50000
    assert sale["expectedEmpties"] == 5
    assert sale["items"][0]["unitPrice"] == 11000

    product_after = (await client.get(f"/api/v1/products/{product['id']}")).json()
    customer_after = (await client.get(f"/api/v1/customers/{customer['id']}")).json()
    empty_cases = (await client.get("/api/v1/empty-case-transactions/")).json()

    assert product_after["fullCases"] == 95
    assert customer_after["pendingEmpties"] == 5
    assert customer_after["totalPurchases"] == 50000
    assert customer_after["refundableDeposits"] == 15000
    assert empty_cases[0]["pendingQuantity"] == 5
    assert empty_cases[0]["totalDepositValue"] == 15000


@pytest.mark.anyio
async def test_process_empty_case_return_updates_customer_and_audit(client: AsyncClient) -> None:
    product = (await client.post("/api/v1/products/", json=PRODUCT_PAYLOAD)).json()
    customer = (await client.post("/api/v1/customers/", json=CUSTOMER_PAYLOAD)).json()
    await client.post(
        "/api/v1/sales/",
        json={
            "customerId": customer["id"],
            "customerName": customer["name"],
            "items": [{"productId": product["id"], "quantity": 5}],
            "discount": 0,
            "payment": "cash",
            "amountPaid": 55000,
            "cashier": "Eric Mugisha",
        },
    )
    transaction = (await client.get("/api/v1/empty-case-transactions/")).json()[0]

    response = await client.post(
        f"/api/v1/empty-case-transactions/{transaction['id']}/process-return",
        json={"returnQuantity": 3, "processedBy": "Claude Niyonzima"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["returnedQuantity"] == 3
    assert updated["pendingQuantity"] == 2
    assert updated["refundedAmount"] == 9000
    assert updated["status"] == "partial"

    customer_after = (await client.get(f"/api/v1/customers/{customer['id']}")).json()
    audits = (await client.get("/api/v1/transaction-audits/")).json()
    assert customer_after["pendingEmpties"] == 2
    assert customer_after["refundableDeposits"] == 6000
    assert audits[0]["action"] == "updated"


@pytest.mark.anyio
async def test_dashboard_report_returns_frontend_summary(client: AsyncClient) -> None:
    product = (await client.post("/api/v1/products/", json=PRODUCT_PAYLOAD)).json()
    customer = (await client.post("/api/v1/customers/", json=CUSTOMER_PAYLOAD)).json()
    await client.post(
        "/api/v1/sales/",
        json={
            "customerId": customer["id"],
            "customerName": customer["name"],
            "items": [{"productId": product["id"], "quantity": 2}],
            "discount": 0,
            "payment": "card",
            "amountPaid": 22000,
            "cashier": "Eric Mugisha",
        },
    )
    await client.post(
        "/api/v1/expenses/",
        json={
            "title": "Fuel",
            "category": "fuel",
            "amount": 5000,
            "date": "2026-06-24T00:00:00",
            "recordedBy": "Aline Uwase",
            "invoiceNumber": "EXP-001",
        },
    )

    response = await client.get("/api/v1/reports/dashboard")

    assert response.status_code == 200
    report = response.json()
    assert report["totalProducts"] == 1
    assert report["totalCustomers"] == 1
    assert report["totalSales"] == 1
    assert report["salesRevenue"] == 22000
    assert report["totalExpenses"] == 5000
    assert report["grossProfit"] == 17000
    assert report["pendingEmptyCases"] == 2
