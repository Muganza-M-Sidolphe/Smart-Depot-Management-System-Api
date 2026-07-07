"""Tests covering the backend changes that align it with the frontend forms:
inventory extras, POS sale extras (tax / partial payment / empties at sale),
and expense extras + receipt upload.
"""

import base64

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


@pytest.mark.anyio
async def test_product_persists_container_and_bottle_extras(client: AsyncClient) -> None:
    payload = {
        **PRODUCT_PAYLOAD,
        "containerType": "case",
        "containerSizeLabel": "Standard",
        "bottlesPerContainer": 24,
        "purchasePricePerContainer": 12000,
        "sellingPricePerContainer": 15000,
        "bottleInfo": {"damaged": 2, "missing": 1, "returned": 0, "notes": "chipped"},
        "partialCases": [{"bottleCount": 5, "reason": "sold_individual"}],
        "lastStockCheck": "2026-07-07T00:00:00",
    }
    created = (await client.post("/api/v1/products/", json=payload)).json()

    assert created["containerType"] == "case"
    assert created["bottlesPerContainer"] == 24
    assert created["purchasePricePerContainer"] == 12000
    assert created["bottleInfo"]["damaged"] == 2
    assert created["partialCases"][0]["bottleCount"] == 5

    # values survive a round-trip (persisted, not dropped)
    fetched = (await client.get(f"/api/v1/products/{created['id']}")).json()
    assert fetched["bottleInfo"]["notes"] == "chipped"
    assert fetched["containerSizeLabel"] == "Standard"


@pytest.mark.anyio
async def test_sale_applies_tax_partial_payment_and_empties_returned(client: AsyncClient) -> None:
    product = (await client.post("/api/v1/products/", json=PRODUCT_PAYLOAD)).json()
    customer = (
        await client.post(
            "/api/v1/customers/",
            json={"name": "Kigali Bar", "phone": "+250788000000"},
        )
    ).json()

    sale = (
        await client.post(
            "/api/v1/sales/",
            json={
                "customerId": customer["id"],
                "customerName": customer["name"],
                "items": [
                    {
                        "productId": product["id"],
                        "quantity": 10,
                        "emptyCasesReturned": 4,
                        "remainingEmptyCases": 6,
                    }
                ],
                "discount": 0,
                "tax": 10,  # percent
                "payment": "cash",
                "amountPaid": 60000,
                "isPartialPayment": True,
                "cashier": "Eric",
            },
        )
    ).json()

    # subtotal 10 * 11000 = 110000; tax 10% = 11000; total = 121000
    assert sale["subtotal"] == 110000
    assert sale["tax"] == 11000
    assert sale["total"] == 121000
    # partial payment: 60000 paid -> 61000 owed
    assert sale["isPartialPayment"] is True
    assert sale["remainingBalance"] == 61000
    assert sale["change"] == 0
    # empties: 4 returned at sale, 6 still pending
    assert sale["returnedEmpties"] == 4
    assert sale["expectedEmpties"] == 6
    assert sale["emptyCasesTotal"] == 4
    assert sale["remainingEmptyCasesTotal"] == 6
    assert sale["items"][0]["emptyCasesReturned"] == 4

    customer_after = (await client.get(f"/api/v1/customers/{customer['id']}")).json()
    assert customer_after["pendingEmpties"] == 6
    assert customer_after["unpaidBalance"] == 61000
    # deposit owed only on the 6 pending cases: 6 * 3000
    assert customer_after["refundableDeposits"] == 18000


@pytest.mark.anyio
async def test_expense_persists_extras_and_receipt_upload(client: AsyncClient) -> None:
    receipt_b64 = base64.b64encode(b"fake-receipt-bytes").decode()
    payload = {
        "title": "Office rent",
        "description": "Monthly rent",
        "category": "rent",
        "amount": 150000,
        "quantity": 1,
        "unitPrice": 150000,
        "paymentMethod": "bank_transfer",
        "date": "2026-07-07",
        "dueDate": "2026-07-30",
        "supplierName": "ABC Ltd",
        "receiptNumber": "RCP-001",
        "notes": "paid early",
        "status": "paid",
        "recordedBy": "Aline",
        "createdBy": "Aline",
        "receipt": f"data:image/png;base64,{receipt_b64}",
        "receiptFileName": "rent.png",
        "receiptFileType": "image/png",
        "receiptFileSize": 18,
    }
    created = (await client.post("/api/v1/expenses/", json=payload)).json()

    assert created["description"] == "Monthly rent"
    assert created["paymentMethod"] == "bank_transfer"
    assert created["receiptNumber"] == "RCP-001"
    assert created["note"] == "paid early"  # notes -> note alias
    assert created["receiptFileName"] == "rent.png"
    assert created["receiptUrl"].endswith(".png")
    assert "/uploads/receipts/" in created["receiptUrl"]


@pytest.mark.anyio
async def test_expense_rejects_invalid_receipt(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/expenses/",
        json={
            "title": "Bad",
            "category": "other",
            "amount": 1,
            "date": "2026-07-07",
            "recordedBy": "X",
            "receipt": "!!!not-base64!!!",
            "receiptFileName": "x.png",
        },
    )
    assert response.status_code == 400
