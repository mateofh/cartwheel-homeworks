"""Homework 2 authentication tests for the session endpoints.

The client is used without its context manager, so the lifespan (and tracing
setup) never runs. A rejected request fails before the agent is built, so no
model provider key, Langfuse, or Docker is needed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server import app as server_app


@pytest.fixture
def client(world: dict) -> TestClient:
    server_app._SESSIONS.clear()
    return TestClient(server_app.app)


def _session(client: TestClient, user_id: int, role: str) -> dict:
    response = client.post("/sessions", json={"user_id": user_id, "role": role})
    assert response.status_code == 200, response.text
    return response.json()


def test_session_rejects_role_that_differs_from_database(client: TestClient) -> None:
    # User 1 is a shopper in the seeded world; claiming support must fail.
    response = client.post("/sessions", json={"user_id": 1, "role": "support"})
    assert response.status_code == 403
    assert server_app._SESSIONS == {}


def test_session_rejects_unknown_role_and_user(client: TestClient) -> None:
    assert client.post("/sessions", json={"user_id": 1, "role": "admin"}).status_code == 400
    assert client.post("/sessions", json={"user_id": 999999, "role": "shopper"}).status_code == 404


def test_token_cannot_authorize_a_different_session(client: TestClient) -> None:
    first = _session(client, 1, "shopper")
    second = _session(client, 2, "shopper")

    response = client.post(
        f"/sessions/{second['session_id']}/messages",
        headers={"Authorization": f"Bearer {first['token']}"},
        json={"message": "Show my recent orders."},
    )
    assert response.status_code == 403


def test_message_requires_a_valid_bearer_token(client: TestClient) -> None:
    session = _session(client, 1, "shopper")
    url = f"/sessions/{session['session_id']}/messages"
    body = {"message": "Show my recent orders."}

    assert client.post(url, json=body).status_code == 401
    token = session["token"]
    flipped = "1" if token[-1] == "0" else "0"  # always changes the signature
    tampered = {"Authorization": f"Bearer {token[:-1]}{flipped}"}
    assert client.post(url, headers=tampered, json=body).status_code == 401
