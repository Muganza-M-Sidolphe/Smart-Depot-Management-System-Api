"""Tests for the supplementary (extras) endpoints: filters, search, summaries,
stock adjustments, per-id fetch, and deletes."""

import pytest
from httpx import AsyncClient

PRODUCT = {
    "name": "Primus",
    "brand": "Bralirwa",
    "category": "Lager",
    "fullCases": 5,
    "purchasePrice": 9000,
    "sellingPrice": 10000,
    "supplier": "Bralirwa Ltd",
    "batchNumber": "BR-777",
    "manufactureDate": "2026-01-01T00:00:00",
    "expiryDate": "2026-12-01T00:00:00",
    "lowStockThreshold": 10,
    "depositAmount": 0,
}


@pytest.mark.anyio
async def test_product_filters_and_stock_adjust(client: AsyncClient) -> None:
    product = (await client.post("/api/v1/products/", json=PRODUCT)).json()
    pid = product["id"]

    # low-stock (fullCases 5 <= threshold 10) — literal path must NOT hit /products/{id}
    low = await client.get("/api/v1/products/low-stock")
    assert low.status_code == 200
    assert any(p["id"] == pid for p in low.json())

    # search + category + barcode(batchNumber)
    assert (await client.get("/api/v1/products/search?q=Primus")).json()[0]["id"] == pid
    assert (await client.get("/api/v1/products/category/Lager")).json()[0]["id"] == pid
    assert (await client.get("/api/v1/products/barcode/BR-777")).json()["id"] == pid

    # stock adjust add 10 -> 15
    adj = await client.patch(f"/api/v1/products/{pid}/stock", json={"quantity": 10, "operation": "add"})
    assert adj.status_code == 200
    assert adj.json()["fullCases"] == 15

    # bulk update
    bulk = await client.patch(
        "/api/v1/products/bulk",
        json={"products": [{"id": pid, "data": {"sellingPrice": 12000}}]},
    )
    assert bulk.status_code == 200
    assert bulk.json()[0]["sellingPrice"] == 12000


@pytest.mark.anyio
async def test_sales_filters_summary_and_delete(client: AsyncClient) -> None:
    product = (await client.post("/api/v1/products/", json=PRODUCT)).json()
    customer = (await client.post("/api/v1/customers/", json={"name": "Bar", "phone": "+250788"})).json()
    sale = (
        await client.post(
            "/api/v1/sales/",
            json={
                "customerId": customer["id"],
                "customerName": "Bar",
                "items": [{"productId": product["id"], "quantity": 2}],
                "payment": "cash",
                "amountPaid": 20000,
                "cashier": "Eric",
            },
        )
    ).json()

    # by customer
    assert (await client.get(f"/api/v1/sales/customer/{customer['id']}")).json()[0]["id"] == sale["id"]
    # daily summary
    summary = await client.get("/api/v1/sales/daily-summary/2026-07-07T00:00:00")
    assert summary.status_code == 200
    assert "totalSales" in summary.json()

    # delete restores stock
    assert (await client.delete(f"/api/v1/sales/{sale['id']}")).status_code == 204
    product_after = (await client.get(f"/api/v1/products/{product['id']}")).json()
    assert product_after["fullCases"] == 5  # 5 - 2 + 2 restored


@pytest.mark.anyio
async def test_expense_summaries(client: AsyncClient) -> None:
    for cat, amt in [("rent", 100000), ("fuel", 20000), ("fuel", 30000)]:
        await client.post(
            "/api/v1/expenses/",
            json={"title": cat, "category": cat, "amount": amt, "date": "2026-07-07", "recordedBy": "A"},
        )
    summary = await client.get("/api/v1/expenses/summary/category")
    assert summary.status_code == 200
    by_cat = {r["category"]: r for r in summary.json()}
    assert by_cat["fuel"]["total"] == 50000
    assert by_cat["fuel"]["count"] == 2

    total = (await client.get("/api/v1/expenses/total")).json()
    assert total["total"] == 150000
    assert total["count"] == 3

    monthly = (await client.get("/api/v1/expenses/monthly-breakdown?year=2026")).json()
    assert monthly[0]["total"] == 150000

    report = await client.get("/api/v1/expenses/report")
    assert report.status_code == 200
    assert report.content[:4] == b"%PDF"


@pytest.mark.anyio
async def test_customer_stats_and_phone(client: AsyncClient) -> None:
    customer = (
        await client.post("/api/v1/customers/", json={"name": "Jean", "phone": "+250700111"})
    ).json()
    assert (await client.get("/api/v1/customers/phone/+250700111")).json()["id"] == customer["id"]
    stats = await client.get(f"/api/v1/customers/{customer['id']}/stats")
    assert stats.status_code == 200
    assert "unpaidBalance" in stats.json()


@pytest.mark.anyio
async def test_notifications_lifecycle(client: AsyncClient) -> None:
    await client.post("/api/v1/products/", json=PRODUCT)  # low stock -> generates a notification
    await client.post("/api/v1/notifications/generate")

    unread = await client.get("/api/v1/notifications/unread")
    assert unread.status_code == 200
    count = (await client.get("/api/v1/notifications/count")).json()
    assert count["total"] >= 1

    if unread.json():
        nid = unread.json()[0]["id"]
        assert (await client.patch(f"/api/v1/notifications/{nid}/read")).json()["read"] is True
        assert (await client.get(f"/api/v1/notifications/{nid}")).json()["id"] == nid

    # mark all read then delete read ones
    await client.patch("/api/v1/notifications/mark-all-read")
    deleted = await client.delete("/api/v1/notifications/read")
    assert deleted.status_code == 200
    assert (await client.get("/api/v1/notifications/count")).json()["unread"] == 0


@pytest.mark.anyio
async def test_supplier_search_and_get(client: AsyncClient) -> None:
    supplier = (
        await client.post(
            "/api/v1/suppliers/",
            json={"name": "Bralirwa Ltd", "contact": "Jean", "phone": "+250", "email": "a@b.rw"},
        )
    ).json()
    assert (await client.get("/api/v1/suppliers/search?name=Bralirwa")).json()[0]["id"] == supplier["id"]
    assert (await client.get(f"/api/v1/suppliers/{supplier['id']}")).json()["name"] == "Bralirwa Ltd"
