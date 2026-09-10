from fastapi.testclient import TestClient

import app.inventory.main as inventory


client = TestClient(inventory.app)


def test_inventory_normal_response(monkeypatch):
    monkeypatch.setattr(
        inventory,
        "get_latency_seconds",
        lambda: 0.0,
    )

    monkeypatch.setattr(
        inventory,
        "get_error_rate",
        lambda: 0.0,
    )

    response = client.get(
        "/inventory/test-widget"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["item_id"] == "test-widget"
    assert body["available"] is True
