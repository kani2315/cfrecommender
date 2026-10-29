"""LAYER 1 — pure functions, no I/O. Fastest, highest value per line."""
import pytest
from app.recommender import _get_weak_tags
from app.model import split_tags
from tests.conftest import sub


class TestSplitTags:
    def test_normal(self):
        assert split_tags("math,greedy,dp") == ["math", "greedy", "dp"]

    def test_strips_whitespace(self):
        assert split_tags("math, greedy ,dp") == ["math", "greedy", "dp"]

    def test_empty_string_returns_empty_list(self):
        # Guards against "".split(",") == [""] polluting the vocabulary
        assert split_tags("") == []

    def test_none_returns_empty_list(self):
        assert split_tags(None) == []

    def test_multiword_tag_preserved(self):
        # Why tokenizer= is overridden: default splits on whitespace
        assert split_tags("binary search,dp") == ["binary search", "dp"]


class TestGetWeakTags:
    def test_picks_lowest_winrate_when_enough_reliable_tags(self):
        subs = []
        # 6 reliable tags (>=5 attempts each), descending competence
        for tag, solves in [("a", 5), ("b", 4), ("c", 3), ("d", 2), ("e", 1), ("f", 0)]:
            for i in range(5):
                subs.append(sub(f"{tag}{i}", [tag], 1200, i < solves))
        weak = _get_weak_tags(subs)
        tags = weak
        assert len(tags) == 5
        assert "a" not in tags          # strongest excluded
        assert "f" in tags and "e" in tags

    def test_ignores_tags_below_attempt_threshold(self):
        subs = [sub("x0", ["rare"], 1200, False)]        # 1 attempt, 0% winrate
        for i in range(6):
            subs.append(sub(f"c{i}", ["common"], 1200, True))
        weak = _get_weak_tags(subs)
        # "rare" is 0% but has 1 attempt -> not statistically reliable
        assert "rare" not in weak

    def test_excludes_special_tag(self):
        subs = [sub(f"s{i}", ["*special", "dp"], 1200, False) for i in range(6)]
        assert "*special" not in _get_weak_tags(subs)

    def test_empty_submissions(self):
        assert _get_weak_tags([]) == []

    # ---- BUG DOCUMENTATION ----
    @pytest.mark.xfail(reason="BUG recommender.py:49 - `else []` drops the only "
                              "reliable weak tag when <=5 reliable tags exist. "
                              "Affects exactly the new users the feature targets.",
                       strict=True)
    def test_user_with_one_reliable_weak_tag_still_gets_it(self):
        subs = [sub(f"d{i}", ["dp"], 1200, i == 0) for i in range(5)]   # dp: 5 att, 1 solve
        subs += [sub("g0", ["greedy"], 1200, True)]                     # greedy: 1 att
        weak = _get_weak_tags(subs)
        assert "dp" in weak
