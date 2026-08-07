import pytest
from core.ai_analyzer import AIAnalyzer
from core.risk import RiskConfig, RiskManager
from core.store import DataStore


class TestDataStore:
    def test_init_creates_tables(self, tmp_path):
        db = tmp_path / "test.db"
        store = DataStore(db_path=str(db))
        import sqlite3

        with sqlite3.connect(db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        assert ("ohlcv",) in tables
        assert ("trade_journal",) in tables


class TestRiskManager:
    def test_can_open_respects_limits(self):
        cfg = RiskConfig(max_position=0.1, max_total=0.5)
        rm = RiskManager(cfg)
        assert rm.can_open("BTC", 100, 1000, 10000)
        rm.add_position("BTC", 100, 1)
        assert not rm.can_open("ETH", 100, 1000, 1000)

    def test_stop_loss_trigger(self):
        rm = RiskManager(RiskConfig(stop_loss=-0.05))
        rm.add_position("BTC", 100, 1)
        assert rm.update_price("BTC", 94) == "stop_loss"
        assert rm.update_price("BTC", 101) is None

    def test_trailing_stop(self):
        rm = RiskManager(RiskConfig(trailing_stop=0.05))
        rm.add_position("BTC", 100, 1)
        rm.update_price("BTC", 110)
        assert rm.update_price("BTC", 104) == "trailing_stop"


class TestAIAnalyzer:
    def test_analyze_news_returns_structure(self, monkeypatch):
        def fake_call(*, model, messages, result_format):
            class FakeResp:
                class output:
                    class choices:
                        @staticmethod
                        def __getitem__(i):
                            class FakeMsg:
                                content = '{"sentiment_score": 0.5, "impact_level": "中", "reasoning": "test", "confidence": 0.8}'
                            return type("obj", (object,), {"message": FakeMsg()})
            return FakeResp()

        monkeypatch.setattr("core.ai_analyzer.Generation.call", staticmethod(fake_call))
        a = AIAnalyzer(api_key="test")
        result = a.analyze_news("BTC", "some news")
        assert "sentiment_score" in result
        assert "confidence" in result
