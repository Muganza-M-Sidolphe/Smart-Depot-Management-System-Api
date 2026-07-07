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


@pytest.mark.anyio
async def test_forgot_and_reset_password_flow(public_client: AsyncClient, monkeypatch) -> None:
    captured: dict[str, str] = {}

    # capture the reset link instead of emailing it, and pull the token out of it
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        lambda to, name, reset_url, minutes: captured.update(to=to, url=reset_url),
    )

    await public_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)  # eric@smartdepot.rw

    # request a reset
    forgot = await public_client.post(
        "/api/v1/auth/forgot-password", json={"email": "eric@smartdepot.rw"}
    )
    assert forgot.status_code == 200
    token = captured["url"].split("token=")[1]

    # reset to a new password
    reset = await public_client.post(
        "/api/v1/auth/reset-password", json={"token": token, "newPassword": "brandnew123"},
    )
    assert reset.status_code == 200

    # old password no longer works, new one does
    old = await public_client.post(
        "/api/v1/auth/login", json={"email": "eric@smartdepot.rw", "password": "supersecret123"}
    )
    assert old.status_code == 401
    new = await public_client.post(
        "/api/v1/auth/login", json={"email": "eric@smartdepot.rw", "password": "brandnew123"}
    )
    assert new.status_code == 200

    # the same token cannot be reused
    reuse = await public_client.post(
        "/api/v1/auth/reset-password", json={"token": token, "newPassword": "another123"}
    )
    assert reuse.status_code == 400


@pytest.mark.anyio
async def test_forgot_password_unknown_email_is_generic(public_client: AsyncClient) -> None:
    # no account -> still 200 (does not reveal whether the email exists)
    resp = await public_client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@nowhere.rw"}
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_reset_password_rejects_bad_token(public_client: AsyncClient) -> None:
    resp = await public_client.post(
        "/api/v1/auth/reset-password", json={"token": "not-a-real-token", "newPassword": "whatever123"}
    )
    assert resp.status_code == 400


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


@pytest.mark.anyio
@pytest.mark.parametrize("role", ["owner", "admin", "manager", "cashier", "storekeeper", "staff"])
async def test_signup_accepts_all_frontend_roles(public_client: AsyncClient, role: str) -> None:
    response = await public_client.post(
        "/api/v1/auth/signup",
        json={"name": role, "email": f"{role}@x.rw", "password": "secret6", "role": role},
    )
    assert response.status_code == 201
    assert response.json()["user"]["role"] == role


@pytest.mark.anyio
async def test_signup_accepts_six_char_password(public_client: AsyncClient) -> None:
    response = await public_client.post(
        "/api/v1/auth/signup",
        json={"name": "Six", "email": "six@x.rw", "password": "123456", "role": "cashier"},
    )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_created_user_without_password_gets_generated_one_and_can_login(
    public_client: AsyncClient, monkeypatch
) -> None:
    from app.services import business_service

    sent: dict[str, str] = {}

    monkeypatch.setattr(business_service, "generate_password", lambda: "Temp123abc")
    # capture the welcome email instead of sending it
    monkeypatch.setattr(
        "app.api.v1.endpoints.business.send_welcome_email",
        lambda to, name, password: sent.update(to=to, name=name, password=password),
    )

    owner = await _token_for(public_client, "owner")
    created = await public_client.post(
        "/api/v1/users/",
        json={"name": "Nopass", "email": "nopass@x.rw", "role": "cashier"},
        headers=_auth(owner),
    )
    assert created.status_code == 201
    assert "password" not in created.json()  # never leaked in the response

    # the generated password was emailed with the user's login email
    assert sent == {"to": "nopass@x.rw", "name": "Nopass", "password": "Temp123abc"}

    # and it actually works for login
    login = await public_client.post(
        "/api/v1/auth/login",
        json={"email": "nopass@x.rw", "password": "Temp123abc"},
    )
    assert login.status_code == 200


@pytest.mark.anyio
async def test_signup_user_does_not_need_password_change(public_client: AsyncClient) -> None:
    body = (await public_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)).json()
    assert body["user"]["mustChangePassword"] is False


@pytest.mark.anyio
async def test_generated_password_user_must_change_then_can_clear_it(
    public_client: AsyncClient, monkeypatch
) -> None:
    from app.services import business_service

    monkeypatch.setattr(business_service, "generate_password", lambda: "Temp123abc")
    monkeypatch.setattr(
        "app.api.v1.endpoints.business.send_welcome_email",
        lambda to, name, password: None,
    )
    owner = await _token_for(public_client, "owner")

    created = await public_client.post(
        "/api/v1/users/",
        json={"name": "Temp", "email": "temp@x.rw", "role": "cashier"},
        headers=_auth(owner),
    )
    assert created.json()["mustChangePassword"] is True

    # the flag comes back on login
    login = await public_client.post(
        "/api/v1/auth/login", json={"email": "temp@x.rw", "password": "Temp123abc"}
    )
    token = login.json()["accessToken"]
    assert login.json()["user"]["mustChangePassword"] is True

    # wrong current password is rejected
    bad = await public_client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "wrong", "newPassword": "Chosen123"},
        headers=_auth(token),
    )
    assert bad.status_code == 400

    # change it -> flag clears
    ok = await public_client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "Temp123abc", "newPassword": "Chosen123"},
        headers=_auth(token),
    )
    assert ok.status_code == 200

    me = await public_client.get("/api/v1/auth/me", headers=_auth(token))
    assert me.json()["mustChangePassword"] is False

    # new password works, old one does not
    assert (
        await public_client.post(
            "/api/v1/auth/login", json={"email": "temp@x.rw", "password": "Chosen123"}
        )
    ).status_code == 200
    assert (
        await public_client.post(
            "/api/v1/auth/login", json={"email": "temp@x.rw", "password": "Temp123abc"}
        )
    ).status_code == 401


@pytest.mark.anyio
async def test_admin_created_user_with_password_can_login(public_client: AsyncClient) -> None:
    owner = await _token_for(public_client, "owner")
    created = await public_client.post(
        "/api/v1/users/",
        json={"name": "Staffer", "email": "staffer@x.rw", "role": "cashier", "password": "secret6"},
        headers=_auth(owner),
    )
    assert created.status_code == 201

    login = await public_client.post(
        "/api/v1/auth/login",
        json={"email": "staffer@x.rw", "password": "secret6"},
    )
    assert login.status_code == 200
    assert login.json()["accessToken"]
