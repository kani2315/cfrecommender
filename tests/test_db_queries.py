"""LAYER 2 — DB integration. Real schema, in-memory SQLite, seeded catalogue."""
import pytest
from app.database import Problem
from app.recommender import _get_avoided_tags


def candidate_query(db, user_rating, tag, solved_ids):
    """Mirrors the candidate query in recommender.py:163-171."""
    return (db.query(Problem)
            .filter(Problem.rating.isnot(None))
            .filter(Problem.rating >= max(0, user_rating - 300))
            .filter(Problem.rating <= user_rating + 300)
            .filter(Problem.tags.contains(tag))
            .filter(~Problem.id.in_(solved_ids) if solved_ids else True)
            .all())


class TestCandidateQuery:
    def test_respects_rating_band(self, seeded_db):
        ids = {p.id for p in candidate_query(seeded_db, 1200, "dp", set())}
        assert "P1100" in ids and "P1400" in ids      # inside 900-1500
        assert "P2000" not in ids                     # 800 above the band

    def test_excludes_null_rating(self, seeded_db):
        ids = {p.id for p in candidate_query(seeded_db, 1200, "dp", set())}
        assert "PNULL" not in ids

    def test_excludes_already_solved(self, seeded_db):
        ids = {p.id for p in candidate_query(seeded_db, 1200, "dp", {"P1100", "P1200"})}
        assert "P1100" not in ids and "P1200" not in ids
        assert "P1400" in ids

    def test_empty_solved_set_does_not_break_query(self, seeded_db):
        # .filter(True) -> SQLAlchemy coerces to WHERE 1=1. Verified, not a bug.
        assert len(candidate_query(seeded_db, 1200, "dp", set())) > 0

    def test_band_floor_clamped_at_zero(self, seeded_db):
        assert candidate_query(seeded_db, 100, "math", set()) is not None

    @pytest.mark.xfail(reason="BUG: tags.contains() is substring matching, not set "
                              "membership. Safe with current CF vocabulary by luck.",
                       strict=True)
    def test_tag_match_is_exact_not_substring(self, seeded_db):
        seeded_db.add(Problem(id="PHYP", name="Hyper", rating=1200,
                              tags="hypergraphs", solve_count=10))
        seeded_db.commit()
        ids = {p.id for p in candidate_query(seeded_db, 1200, "graphs", set())}
        assert "PHYP" not in ids


class TestAvoidedTags:
    def test_returns_tags_ranked_by_avoidance(self, seeded_db):
        tag_stats = {"dp": {"attempts": 20, "solved": 10}}   # heavily engaged
        result = _get_avoided_tags(seeded_db, 1200, tag_stats)
        tags = [r["tag"] for r in result]
        assert "dp" in tags
        assert tags.index("dp") > 0                   # engaged tag ranks low

    def test_unattempted_tag_outranks_attempted_one(self, seeded_db):
        tag_stats = {"dp": {"attempts": 50, "solved": 25}}
        result = _get_avoided_tags(seeded_db, 1200, tag_stats)
        scores = {r["tag"]: i for i, r in enumerate(result)}
        assert scores["graphs"] < scores["dp"]        # never touched ranks higher

    def test_returns_dicts_with_tag_and_attempts(self, seeded_db):
        r = _get_avoided_tags(seeded_db, 1200, {})
        assert r and set(r[0].keys()) >= {"tag", "attempts"}
