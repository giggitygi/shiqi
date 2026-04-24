from fastapi.testclient import TestClient

from dangdang_kgqa.api import app


def test_health_endpoint_reports_service_status():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["service"] == "dangdang-kgqa"


def test_ask_endpoint_returns_sparql_when_graphdb_is_unavailable(monkeypatch):
    def fake_query(_sparql: str):
        raise RuntimeError("GraphDB unavailable")

    monkeypatch.setattr("dangdang_kgqa.api.graphdb_query", fake_query)
    client = TestClient(app)

    response = client.post("/api/ask", json={"question": "余华写过哪些书"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "author_books"
    assert "kg:authoredBy" in payload["sparql"]
    assert payload["graphdb_available"] is False
