"""
tests/unit/data/test_smart_cache.py — TASK 3.4: SmartCache unit tests.
"""
import pytest
import os
from src.data.cache import SmartCache


@pytest.fixture
def cache(tmp_path):
    return SmartCache(db_path=str(tmp_path / "test_cache.db"))


class TestSmartCache:
    def test_update_and_get_score_online(self, cache):
        cache.update("PC-001", "online")
        # First insert: baseline 50. Second online update increases score.
        cache.update("PC-001", "online")
        score = cache.get_score("PC-001")
        assert score > 50  # online increases score from default 50

    def test_update_offline_decreases_score(self, cache):
        # First set baseline
        cache.update("PC-002", "online")
        cache.update("PC-002", "offline")
        score = cache.get_score("PC-002")
        assert score < 100

    def test_unknown_pc_returns_minus_one(self, cache):
        score = cache.get_score("NOTEXIST")
        assert score == -1

    def test_name_stored_uppercase(self, cache):
        cache.update("pc-lowcase", "online")
        all_pcs = cache.all_pcs()
        assert "PC-LOWCASE" in all_pcs

    def test_all_pcs_returns_dict(self, cache):
        cache.update("PC-A", "online", "john")
        cache.update("PC-B", "offline")
        pcs = cache.all_pcs()
        assert "PC-A" in pcs
        assert "PC-B" in pcs
        assert pcs["PC-A"]["user"] == "john"
        assert pcs["PC-B"]["status"] == "offline"

    def test_update_existing_overwrites(self, cache):
        cache.update("PC-X", "online", "alice")
        cache.update("PC-X", "online", "bob")
        pcs = cache.all_pcs()
        assert pcs["PC-X"]["user"] == "bob"

    def test_score_caps_at_100(self, cache):
        for _ in range(20):
            cache.update("PC-HIGH", "online")
        score = cache.get_score("PC-HIGH")
        assert score <= 100

    def test_score_floors_at_0(self, cache):
        for _ in range(20):
            cache.update("PC-LOW", "offline")
        score = cache.get_score("PC-LOW")
        assert score >= 0

    def test_save_is_noop(self, cache):
        cache.update("PC-Z", "online")
        cache.save()  # Should not raise
        assert cache.get_score("PC-Z") > 0
