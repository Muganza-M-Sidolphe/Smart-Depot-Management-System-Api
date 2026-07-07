"""Tests for the automatic report feature: settings, PDF, and send-now."""

import pytest
from httpx import AsyncClient

PRODUCT_PAYLOAD = {
    "name": "Primus",
    "brand": "Bralirwa",
    "category": "Lager",
    "fullCases": 100,
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
async def test_report_settings_get_and_update(client: AsyncClient) -> None:
    # default settings are created on first read
    initial = await client.get("/api/v1/reports/settings")
    assert initial.status_code == 200
    assert initial.json()["dailyEnabled"] is False
    assert initial.json()["recipients"] == []

    updated = await client.put(
        "/api/v1/reports/settings",
        json={
            "recipients": ["boss@depot.rw", "owner@depot.rw"],
            "dailyEnabled": True,
            "sendHour": 7,
            "weeklyWeekday": 0,
            "monthlyDay": 1,
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["recipients"] == ["boss@depot.rw", "owner@depot.rw"]
    assert body["dailyEnabled"] is True
    assert body["sendHour"] == 7


@pytest.mark.anyio
async def test_download_report_pdf(client: AsyncClient) -> None:
    await client.post("/api/v1/products/", json=PRODUCT_PAYLOAD)
    resp = await client.get("/api/v1/reports/daily/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    # a real PDF file starts with the %PDF magic bytes
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 500


@pytest.mark.anyio
async def test_send_report_now_returns_summary(client: AsyncClient) -> None:
    # make a sale so the report has data
    product = (await client.post("/api/v1/products/", json=PRODUCT_PAYLOAD)).json()
    await client.post(
        "/api/v1/sales/",
        json={
            "customerName": "Walk-in",
            "items": [{"productId": product["id"], "quantity": 3}],
            "payment": "cash",
            "amountPaid": 33000,
            "cashier": "Eric",
        },
    )

    resp = await client.post("/api/v1/reports/send?period=daily&recipients=me@depot.rw")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "daily"
    assert data["recipients"] == ["me@depot.rw"]
    assert data["emailed"] is True  # email is stubbed to logging in tests
    assert data["pdfBytes"] > 500
    assert data["metrics"]["salesCount"] == 1
    assert data["metrics"]["revenue"] == 33000


@pytest.mark.anyio
async def test_send_report_rejects_bad_period(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/reports/send?period=yearly")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_dispatch_due_reports_respects_schedule(db_session) -> None:
    from datetime import datetime

    from app.services import report_service

    settings_row = report_service.get_or_create_settings(db_session)
    settings_row.recipients = ["boss@depot.rw"]
    settings_row.daily_enabled = True
    settings_row.send_hour = 9
    db_session.commit()

    # not the configured hour -> nothing sent
    sent = report_service.dispatch_due_reports(db_session, now=datetime(2026, 7, 7, 8, 0))
    assert sent == []

    # at the configured hour -> daily sent once
    sent = report_service.dispatch_due_reports(db_session, now=datetime(2026, 7, 7, 9, 5))
    assert sent == ["daily"]

    # same day, same hour again -> not resent
    sent = report_service.dispatch_due_reports(db_session, now=datetime(2026, 7, 7, 9, 30))
    assert sent == []
