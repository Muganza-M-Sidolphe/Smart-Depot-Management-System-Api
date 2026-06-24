import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_create_and_list_depots(client: AsyncClient) -> None:
    payload = {
        "name": "Main Depot",
        "code": "MAIN",
        "location": "Kigali",
        "manager_name": "Prosper",
        "is_active": True,
    }

    create_response = await client.post("/api/v1/depots/", json=payload)
    list_response = await client.get("/api/v1/depots/")

    assert create_response.status_code == 201
    assert create_response.json()["id"] == 1
    assert list_response.status_code == 200
    assert list_response.json()[0]["code"] == "MAIN"


@pytest.mark.anyio
async def test_update_depot(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/depots/",
        json={"name": "Old", "code": "OLD", "is_active": True},
    )
    depot_id = create_response.json()["id"]

    response = await client.patch(f"/api/v1/depots/{depot_id}", json={"name": "Updated"})

    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.anyio
async def test_delete_depot(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/depots/",
        json={"name": "Temporary", "code": "TEMP", "is_active": True},
    )
    depot_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/depots/{depot_id}")
    get_response = await client.get(f"/api/v1/depots/{depot_id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404
