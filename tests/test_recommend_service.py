"""LAYER 3 — the service. cf_client and the model are mocked.

CRITICAL: recommender.py does `from app.cf_client import get_user_info`,
which BINDS the name into app.recommender's namespace at import time.
So you must patch app.recommender.get_user_info, NOT app.cf_client.get_user_info.
Patching the source module has no effect on an already-imported name.
"""
import pytest
from app import recommender
from tests.conftest import sub


@pytest.fixture
def mock_user(monkeypatch):
    """Install a fake Codeforces user. Returns a configurator."""
    def _install(rating=1200, subs=None, deterministic_proba=0.5):
        monkeypatch.setattr(recommender, "get_user_info",
                            lambda h: {"handle": h, "rating": rating})
        monkeypatch.setattr(recommender, "get_user_submissions",
                            lambda h: subs or [])
        # Deterministic model: probability derived from problem rating so tests
        # assert on ranking logic, not on model behaviour.
        def fake_predict(records):
            return [max(0.01, min(0.99, 1.0 - (r["problem_rating"] - 800) / 1400))
                    for r in records]
        monkeypatch.setattr(recommender, "predict_batch", fake_predict)
    return _install


class TestRecommendContract:
    def test_raises_on_unknown_handle(self, seeded_db, monkeypatch):
        monkeypatch.setattr(recommender, "get_user_info", lambda h: None)
        with pytest.raises(ValueError, match="Could not find"):
            recommender.recommend(seeded_db, "ghost")

    def test_never_recommends_a_solved_problem(self, seeded_db, mock_user):
        solved = ["P1100", "P1200", "P1400"]
        mock_user(rating=1200, subs=[sub(p, ["dp"], 1200, True) for p in solved])
        recs = recommender.recommend(seeded_db, "alice")
        assert set(solved).isdisjoint({r["id"] for r in recs})

    def test_all_results_inside_rating_band(self, seeded_db, mock_user):
        mock_user(rating=1200, subs=[sub("X", ["dp"], 1200, True)])
        for r in recommender.recommend(seeded_db, "alice"):
            assert 900 <= r["rating"] <= 1500, f"{r['id']} outside band"

    def test_no_duplicate_problems(self, seeded_db, mock_user):
        mock_user(rating=1200, subs=[sub("X", ["dp"], 1200, True)])
        ids = [r["id"] for r in recommender.recommend(seeded_db, "alice")]
        assert len(ids) == len(set(ids))

    def test_every_result_has_required_schema_fields(self, seeded_db, mock_user):
        mock_user(rating=1200, subs=[sub("X", ["dp"], 1200, True)])
        required = {"id", "name", "rating", "tags",
                    "predicted_solve_probability", "difficulty_category"}
        for r in recommender.recommend(seeded_db, "alice"):
            assert required <= set(r.keys())

    def test_probabilities_are_valid(self, seeded_db, mock_user):
        mock_user(rating=1200, subs=[sub("X", ["dp"], 1200, True)])
        for r in recommender.recommend(seeded_db, "alice"):
            assert 0.0 <= r["predicted_solve_probability"] <= 1.0

    def test_categories_are_from_known_set(self, seeded_db, mock_user):
        mock_user(rating=1200, subs=[sub("X", ["dp"], 1200, True)])
        allowed = {"Let's Improve These", "Step Out of Your Comfort Zone"}
        assert {r["difficulty_category"] for r in
                recommender.recommend(seeded_db, "alice")} <= allowed


class TestColdStart:
    def test_unrated_user_rating_estimated_from_solved(self, seeded_db, mock_user):
        # rating=0 => unrated. Solved P1100/P1500 => mean 1300 => band 1000-1600
        mock_user(rating=0, subs=[sub("P1100", ["dp"], 1100, True),
                                  sub("P1500", ["dp"], 1500, True)])
        recs = recommender.recommend(seeded_db, "newbie")
        assert recs, "unrated user with history should still get results"
        for r in recs:
            assert 1000 <= r["rating"] <= 1600

    def test_complete_beginner_falls_back_to_1000(self, seeded_db, mock_user):
        mock_user(rating=0, subs=[])
        for r in recommender.recommend(seeded_db, "brandnew"):
            assert 700 <= r["rating"] <= 1300


class TestRankingLogic:
    def test_comfort_zone_picks_closer_to_075_than_improve_picks(
            self, seeded_db, mock_user):
        mock_user(rating=1200, subs=[sub("X", ["dp"], 1200, True)])
        recs = recommender.recommend(seeded_db, "alice")
        cz = [r["predicted_solve_probability"] for r in recs
              if r["difficulty_category"] == "Step Out of Your Comfort Zone"]
        if cz:
            assert min(abs(p - 0.75) for p in cz) <= 0.5


class TestKnownDefects:
    @pytest.mark.xfail(reason="BUG recommender.py:82 - `n` is validated by FastAPI, "
                              "passed in, and never used.", strict=True)
    def test_n_parameter_limits_result_count(self, seeded_db, mock_user):
        mock_user(rating=1200, subs=[sub("X", ["dp"], 1200, True)])
        assert len(recommender.recommend(seeded_db, "alice", n=2)) <= 2

    @pytest.mark.xfail(reason="BUG recommender.py:118 - avoided_tags is never "
                              "sliced to 5, so the loop runs over every tag in the DB.",
                       strict=True)
    def test_scoring_runs_at_most_ten_times(self, wide_db, mock_user, monkeypatch):
        """Counts predict_batch invocations = number of tag-loop iterations.
        Expected: <=5 weak + <=5 avoided = 10. Actual: ~37."""
        calls = []
        mock_user(rating=1200, subs=[sub("X", ["dp"], 1200, True)])
        real = recommender.predict_batch
        def counting(records):
            calls.append(len(records))
            return real(records)
        monkeypatch.setattr(recommender, "predict_batch", counting)
        recommender.recommend(wide_db, "alice")
        assert len(calls) <= 10, f"predict_batch called {len(calls)} times"
