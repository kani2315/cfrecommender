"""LAYER 5 — ML contracts. The tests almost nobody writes, and the ones that
would have caught this project's two most damaging bugs.
"""
import pytest
from app import recommender
from tests.conftest import sub

# The exact feature set train.py fits on (train.py:138).
FEATURE_COLUMNS = ["user_rating", "problem_rating", "problem_solve_count",
                   "user_total_solved", "user_topic_winrate", "tags"]


def capture_feature_records(db, monkeypatch, rating, subs):
    """Intercept the records dict recommender builds before inference."""
    captured = []
    monkeypatch.setattr(recommender, "get_user_info",
                        lambda h: {"handle": h, "rating": rating})
    monkeypatch.setattr(recommender, "get_user_submissions", lambda h: subs)
    def spy(records):
        captured.extend(records)
        return [0.5] * len(records)
    monkeypatch.setattr(recommender, "predict_batch", spy)
    recommender.recommend(db, "tester")
    return captured


class TestFeatureSchemaContract:
    """Catches silent drift between what training fits and what serving sends."""

    def test_serving_sends_exactly_the_training_columns(self, seeded_db, monkeypatch):
        recs = capture_feature_records(seeded_db, monkeypatch, 1200,
                                       [sub("P1100", ["dp"], 1100, True)])
        assert recs, "no records captured"
        assert set(recs[0].keys()) == set(FEATURE_COLUMNS), (
            f"MISMATCH\n  serving: {sorted(recs[0].keys())}\n"
            f"  training: {sorted(FEATURE_COLUMNS)}")

    def test_no_feature_is_none(self, seeded_db, monkeypatch):
        for r in capture_feature_records(seeded_db, monkeypatch, 1200,
                                         [sub("P1100", ["dp"], 1100, True)]):
            for k, v in r.items():
                assert v is not None, f"{k} is None -> NaN into the model"

    def test_winrate_is_a_valid_probability(self, seeded_db, monkeypatch):
        for r in capture_feature_records(seeded_db, monkeypatch, 1200,
                                         [sub("P1100", ["dp"], 1100, True)]):
            assert 0.0 <= r["user_topic_winrate"] <= 1.0


class TestTrainServeParity:
    """THE test that would have caught the skew."""

    @pytest.mark.xfail(reason="BUG: train.py:91 computes user_total_solved as "
                              "groupby().size() = ATTEMPTS. recommender.py:93 "
                              "computes len(solved_ids) = DISTINCT SOLVES.",
                       strict=True)
    def test_user_total_solved_means_the_same_thing_in_both_paths(
            self, seeded_db, monkeypatch):
        subs = [sub("P1100", ["dp"], 1100, False),
                sub("P1100", ["dp"], 1100, False),
                sub("P1100", ["dp"], 1100, True),
                sub("P1200", ["dp"], 1200, True)]
        training_value = len(subs)                                   # groupby().size()
        serving = capture_feature_records(seeded_db, monkeypatch, 1200, subs)
        assert serving[0]["user_total_solved"] == training_value

    @pytest.mark.xfail(reason="BUG: recommender.py:133 falls back to hardcoded 0.50 "
                              "for unseen tags; train.py:133 uses global_winrate.",
                       strict=True)
    def test_unseen_tag_fallback_matches_training(self, seeded_db, monkeypatch):
        TRAINING_GLOBAL_WINRATE = 0.35        # what train.py would compute
        recs = capture_feature_records(seeded_db, monkeypatch, 1200,
                                       [sub("P1100", ["dp"], 1100, True)])
        graph_rows = [r for r in recs if r["tags"] == "graphs"]
        assert graph_rows
        assert abs(graph_rows[0]["user_topic_winrate"] - TRAINING_GLOBAL_WINRATE) < 0.01


class TestModelArtifact:
    """Guards the serialization boundary — both bugs you already debugged."""

    def test_split_tags_is_importable_from_a_stable_module(self):
        # If this moves back into train.py, pickled models break under uvicorn.
        from app.model import split_tags
        assert split_tags.__module__ == "app.model"

    @pytest.mark.skipif(True, reason="Enable in CI after a training run")
    def test_saved_model_loads_and_predicts(self):
        from app.model import predict_batch
        out = predict_batch([{ "user_rating": 1200, "problem_rating": 1200,
                               "problem_solve_count": 3000, "user_total_solved": 50,
                               "user_topic_winrate": 0.5, "tags": "dp" }])
        assert len(out) == 1 and 0.0 <= out[0] <= 1.0 and isinstance(out[0], float)
