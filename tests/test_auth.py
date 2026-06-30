import pytest
from httpx import AsyncClient

SIGNUP_PAYLOAD = {
    "name": "Eric Mugisha",
    "email": "eric@smartdepot.rw",
    "password": "supersecret123",
    "role": "manager",
    "phone": "+250788000000",
}


@pytest.mark.anyio
async def test_signup_returns_token_and_user(public_client: AsyncClient) -> None:
    response = await public_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["tokenType"] == "bearer"
    assert body["accessToken"]
    assert body["user"]["email"] == "eric@smartdepot.rw"
    assert body["user"]["role"] == "manager"
    assert "password" not in body["user"]
    assert "passwordHash" not in body["user"]


@pytest.mark.anyio
async def test_signup_rejects_duplicate_email(public_client: AsyncClient) -> None:
    await public_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    response = await public_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    assert response.status_code == 409


@pytest.mark.anyio
async def test_login_succeeds_with_correct_credentials(public_client: AsyncClient) -> None:
    await public_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    response = await public_client.post(
        "/api/v1/auth/login",
        json={"email": "eric@smartdepot.rw", "password": "supersecret123"},
    )

    assert response.status_code == 200
    assert response.json()["accessToken"]


@pytest.mark.anyio
async def test_login_fails_with_wrong_password(public_client: AsyncClient) -> None:
    await public_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    response = await public_client.post(
        "/api/v1/auth/login",
        json={"email": "eric@smartdepot.rw", "password": "wrong-password"},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_me_returns_current_user_with_token(public_client: AsyncClient) -> None:
    token = (await public_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)).json()["accessToken"]

    response = await public_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "eric@smartdepot.rw"


@pytest.mark.anyio
async def test_me_rejects_missing_or_invalid_token(public_client: AsyncClient) -> None:
    assert (await public_client.get("/api/v1/auth/me")).status_code == 401
    bad = await public_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert bad.status_code == 401


@pytest.mark.anyio
async def test_logout_revokes_token(public_client: AsyncClient) -> None:
    token = (await public_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # token works before logout
    assert (await public_client.get("/api/v1/auth/me", headers=headers)).status_code == 200

    logout = await public_client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json()["detail"] == "Successfully logged out"

    # same token is rejected after logout
    assert (await public_client.get("/api/v1/auth/me", headers=headers)).status_code == 401
    assert (await public_client.get("/api/v1/products/", headers=headers)).status_code == 401


@pytest.mark.anyio
async def test_logout_requires_authentication(public_client: AsyncClient) -> None:
    assert (await public_client.post("/api/v1/auth/logout")).status_code == 401


async def _token_for(public_client: AsyncClient, role: str) -> str:
    payload = {
        "name": f"{role.title()} User",
        "email": f"{role}@smartdepot.rw",
        "password": "supersecret123",
        "role": role,
    }
    return (await public_client.post("/api/v1/auth/signup", json=payload)).json()["accessToken"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


PRODUCT_PAYLOAD = {
    "name": "Primus",
    "brand": "Bralirwa",
    "category": "Lager",
    "fullCases": 100,
    "emptyCases": 0,
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
async def test_signup_rejects_invalid_role(public_client: AsyncClient) -> None:
    response = await public_client.post(
        "/api/v1/auth/signup",
        json={"name": "X", "email": "x@smartdepot.rw", "password": "supersecret123", "role": "superuser"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_unauthenticated_request_is_rejected(public_client: AsyncClient) -> None:
    assert (await public_client.get("/api/v1/products/")).status_code == 401


@pytest.mark.anyio
async def test_storekeeper_can_create_product_but_cashier_cannot(public_client: AsyncClient) -> None:
    storekeeper = await _token_for(public_client, "storekeeper")
    cashier = await _token_for(public_client, "cashier")

    allowed = await public_client.post("/api/v1/products/", json=PRODUCT_PAYLOAD, headers=_auth(storekeeper))
    denied = await public_client.post("/api/v1/products/", json=PRODUCT_PAYLOAD, headers=_auth(cashier))

    assert allowed.status_code == 201
    assert denied.status_code == 403


@pytest.mark.anyio
async def test_only_owner_can_create_users(public_client: AsyncClient) -> None:
    owner = await _token_for(public_client, "owner")
    manager = await _token_for(public_client, "manager")
    new_user = {"name": "New", "email": "new@smartdepot.rw", "role": "cashier"}

    assert (await public_client.post("/api/v1/users/", json=new_user, headers=_auth(owner))).status_code == 201
    assert (await public_client.post("/api/v1/users/", json=new_user, headers=_auth(manager))).status_code == 403


@pytest.mark.anyio
async def test_any_authenticated_role_can_read(public_client: AsyncClient) -> None:
    cashier = await _token_for(public_client, "cashier")
    assert (await public_client.get("/api/v1/products/", headers=_auth(cashier))).status_code == 200
