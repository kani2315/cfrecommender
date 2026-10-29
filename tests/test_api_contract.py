"""LAYER 4 — HTTP contract. Uses dependency_overrides to swap the real DB."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app import recommender
from tests.conftest import sub


@pytest.fixture
def client(seeded_db, monkeypatch):
    app.dependency_overrides[get_db] = lambda: seeded_db
    monkeypatch.setattr(recommender, "get_user_info",
                        lambda h: {"handle": h, "rating": 1200})
    monkeypatch.setattr(recommender, "get_user_submissions",
                        lambda h: [sub("P1100", ["dp"], 1100, True)])
    monkeypatch.setattr(recommender, "predict_batch",
                        lambda records: [0.5] * len(records))
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestRecommendEndpoint:
    def test_returns_200(self, client):
        assert client.get("/recommend/alice").status_code == 200

    def test_response_matches_ProblemOut_schema(self, client):
        body = client.get("/recommend/alice").json()
        assert isinstance(body, list) and body
        required = {"id", "name", "rating", "tags",
                    "predicted_solve_probability", "difficulty_category"}
        assert required <= set(body[0].keys())

    def test_rejects_n_out_of_range(self, client):
        assert client.get("/recommend/alice?n=0").status_code == 422
        assert client.get("/recommend/alice?n=51").status_code == 422

    def test_accepts_valid_n(self, client):
        assert client.get("/recommend/alice?n=10").status_code == 200

    def test_adds_timing_header(self, client):
        assert "X-Process-Time" in client.get("/recommend/alice").headers


class TestMetricsEndpoint:
    def test_metrics_exposed(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "http_requests_total" in r.text


class TestErrorHandling:
    @pytest.mark.xfail(reason="BUG main.py:101 - unknown handle is a CLIENT error "
                              "but is returned as 500 with the raw exception text.",
                       strict=True)
    def test_unknown_handle_returns_404(self, seeded_db, monkeypatch):
        app.dependency_overrides[get_db] = lambda: seeded_db
        monkeypatch.setattr(recommender, "get_user_info", lambda h: None)
        try:
            assert TestClient(app).get("/recommend/ghost").status_code == 404
        finally:
            app.dependency_overrides.clear()
