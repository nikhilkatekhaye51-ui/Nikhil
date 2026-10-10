"""Tests for the home page, health check, footer and 404 handling."""


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"CampusPulse" in response.data


def test_home_page_shows_empty_state(client):
    response = client.get("/")
    assert b"No feedback yet" in response.data


def test_health_returns_ok_json(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"status": "ok"}


def test_footer_shows_local_without_commit(client, monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    response = client.get("/")
    assert b"<code>local</code>" in response.data


def test_footer_shows_first_seven_characters_of_commit(client, monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890")
    response = client.get("/")
    assert b"<code>abcdef1</code>" in response.data


def test_unknown_page_returns_404(client):
    assert client.get("/no-such-page").status_code == 404


def test_unknown_api_route_returns_json_404(client):
    response = client.get("/api/nothing")
    assert response.status_code == 404
    assert response.get_json()["status"] == "error"
