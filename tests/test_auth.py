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
async def test_signup_returns_token_and_user(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["tokenType"] == "bearer"
    assert body["accessToken"]
    assert body["user"]["email"] == "eric@smartdepot.rw"
    assert body["user"]["role"] == "manager"
    assert "password" not in body["user"]
    assert "passwordHash" not in body["user"]


@pytest.mark.anyio
async def test_signup_rejects_duplicate_email(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    response = await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    assert response.status_code == 409


@pytest.mark.anyio
async def test_login_succeeds_with_correct_credentials(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "eric@smartdepot.rw", "password": "supersecret123"},
    )

    assert response.status_code == 200
    assert response.json()["accessToken"]


@pytest.mark.anyio
async def test_login_fails_with_wrong_password(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "eric@smartdepot.rw", "password": "wrong-password"},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_me_returns_current_user_with_token(client: AsyncClient) -> None:
    token = (await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)).json()["accessToken"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "eric@smartdepot.rw"


@pytest.mark.anyio
async def test_me_rejects_missing_or_invalid_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    bad = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert bad.status_code == 401
