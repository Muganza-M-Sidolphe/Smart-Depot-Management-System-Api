"""Tests for paying off a partial sale in installments."""

import pytest
from httpx import AsyncClient

PRODUCT_PAYLOAD = {
    "name": "Primus",
    "brand": "Bralirwa",
    "category": "Lager",
    "fullCases": 100,
    "purchasePrice": 9000,
    "sellingPrice": 10000,
    "supplier": "Bralirwa Ltd",
    "batchNumber": "BR-1",
    "manufactureDate": "2026-01-01T00:00:00",
    "expiryDate": "2026-12-01T00:00:00",
    "lowStockThreshold": 10,
    "depositAmount": 0,
}


async def _partial_sale(client: AsyncClient) -> tuple[dict, dict]:
    product = (await client.post("/api/v1/products/", json=PRODUCT_PAYLOAD)).json()
    customer = (
        await client.post("/api/v1/customers/", json={"name": "Bar", "phone": "+250788000000"})
    ).json()
    # 10 cases * 10000 = 100000 total; pay 30000 now -> 70000 owed
    sale = (
        await client.post(
            "/api/v1/sales/",
            json={
                "customerId": customer["id"],
                "customerName": customer["name"],
                "items": [{"productId": product["id"], "quantity": 10}],
                "payment": "cash",
                "amountPaid": 30000,
                "isPartialPayment": True,
                "cashier": "Eric",
            },
        )
    ).json()
    return sale, customer


@pytest.mark.anyio
async def test_partial_sale_starts_unpaid_with_first_payment_recorded(client: AsyncClient) -> None:
    sale, customer = await _partial_sale(client)
    assert sale["total"] == 100000
    assert sale["amountPaid"] == 30000
    assert sale["remainingBalance"] == 70000
    assert sale["paymentStatus"] == "partial"
    # the point-of-sale payment is recorded in the ledger
    assert len(sale["payments"]) == 1
    assert sale["payments"][0]["amount"] == 30000

    customer_after = (await client.get(f"/api/v1/customers/{customer['id']}")).json()
    assert customer_after["unpaidBalance"] == 70000


@pytest.mark.anyio
async def test_pay_off_balance_in_installments(client: AsyncClient) -> None:
    sale, customer = await _partial_sale(client)
    sale_id = sale["id"]

    # first installment: 40000 -> 30000 left, still partial
    r1 = await client.post(
        f"/api/v1/sales/{sale_id}/payments",
        json={"amount": 40000, "method": "mobile", "receivedBy": "Aline"},
    )
    assert r1.status_code == 201
    assert r1.json()["remainingBalance"] == 30000
    assert r1.json()["paymentStatus"] == "partial"

    # second installment clears it -> paid
    r2 = await client.post(
        f"/api/v1/sales/{sale_id}/payments",
        json={"amount": 30000, "receivedBy": "Aline"},
    )
    assert r2.status_code == 201
    body = r2.json()
    assert body["remainingBalance"] == 0
    assert body["paymentStatus"] == "paid"
    assert body["amountPaid"] == 100000
    assert len(body["payments"]) == 3  # 30000 (POS) + 40000 + 30000

    # customer balance cleared
    customer_after = (await client.get(f"/api/v1/customers/{customer['id']}")).json()
    assert customer_after["unpaidBalance"] == 0


@pytest.mark.anyio
async def test_cannot_overpay_or_pay_settled_sale(client: AsyncClient) -> None:
    sale, _ = await _partial_sale(client)
    sale_id = sale["id"]

    # overpay (70001 > 70000 remaining) -> 400
    over = await client.post(
        f"/api/v1/sales/{sale_id}/payments", json={"amount": 70001, "receivedBy": "X"}
    )
    assert over.status_code == 400

    # pay it off, then paying again -> 400
    await client.post(f"/api/v1/sales/{sale_id}/payments", json={"amount": 70000, "receivedBy": "X"})
    again = await client.post(
        f"/api/v1/sales/{sale_id}/payments", json={"amount": 1000, "receivedBy": "X"}
    )
    assert again.status_code == 400


@pytest.mark.anyio
async def test_outstanding_sales_listing(client: AsyncClient) -> None:
    sale, _ = await _partial_sale(client)
    outstanding = await client.get("/api/v1/sales/outstanding")
    assert outstanding.status_code == 200
    ids = [s["id"] for s in outstanding.json()]
    assert sale["id"] in ids

    # after full payment it drops off the outstanding list
    await client.post(
        f"/api/v1/sales/{sale['id']}/payments", json={"amount": 70000, "receivedBy": "X"}
    )
    outstanding2 = await client.get("/api/v1/sales/outstanding")
    assert sale["id"] not in [s["id"] for s in outstanding2.json()]


@pytest.mark.anyio
async def test_full_paid_sale_has_paid_status(client: AsyncClient) -> None:
    product = (await client.post("/api/v1/products/", json=PRODUCT_PAYLOAD)).json()
    sale = (
        await client.post(
            "/api/v1/sales/",
            json={
                "customerName": "Walk-in",
                "items": [{"productId": product["id"], "quantity": 2}],
                "payment": "cash",
                "amountPaid": 20000,
                "cashier": "Eric",
            },
        )
    ).json()
    assert sale["paymentStatus"] == "paid"
    assert sale["remainingBalance"] == 0
