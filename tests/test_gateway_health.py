import pytest
from fastapi.testclient import TestClient

import app.gateway.main as gateway


client = TestClient(gateway.app)


def test_liveness():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
    }


def test_readiness_when_dependencies_are_healthy(monkeypatch):
    monkeypatch.setattr(
        gateway,
        "database_is_ready",
        lambda: True,
    )
    monkeypatch.setattr(
        gateway,
        "redis_is_ready",
        lambda: True,
    )
    monkeypatch.setattr(
        gateway,
        "inventory_is_ready",
        lambda: True,
    )

    response = client.get("/health/ready")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ready"
    assert all(body["dependencies"].values())


@pytest.mark.parametrize(
    "failed_dependency",
    [
        "database",
        "redis",
        "inventory",
    ],
)
def test_readiness_fails_when_dependency_is_down(
    monkeypatch,
    failed_dependency,
):
    state = {
        "database": True,
        "redis": True,
        "inventory": True,
    }

    state[failed_dependency] = False

    monkeypatch.setattr(
        gateway,
        "database_is_ready",
        lambda: state["database"],
    )
    monkeypatch.setattr(
        gateway,
        "redis_is_ready",
        lambda: state["redis"],
    )
    monkeypatch.setattr(
        gateway,
        "inventory_is_ready",
        lambda: state["inventory"],
    )

    response = client.get("/health/ready")

    assert response.status_code == 503

    detail = response.json()["detail"]

    assert detail["status"] == "not_ready"
    assert detail["dependencies"][failed_dependency] is False
