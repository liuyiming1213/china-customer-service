from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module


def test_health_endpoint():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_knowledge_stats_exposes_expected_collections():
    response = TestClient(app).get("/api/knowledge/stats")
    assert response.status_code == 200
    assert set(response.json()) == {"support_cases", "policies", "terminology", "indexed_source"}


def test_ticket_stream_endpoint_returns_sse(monkeypatch):
    async def fake_stream(_request):
        yield {"event": "stage", "data": {"stage": "received", "message": "ok"}}
        yield {"event": "done", "data": {"status": "completed"}}

    monkeypatch.setattr(main_module.ticket_service, "analyze_stream", fake_stream)
    response = TestClient(app).post("/api/tickets/analyze/stream", json={"message": "テスト"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: stage" in response.text
    assert '"status": "completed"' in response.text
