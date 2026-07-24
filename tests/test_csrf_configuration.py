from __future__ import annotations

from config import DevelopmentConfig, ProductionConfig


def test_csrf_time_limit_is_integer_seconds():
    assert DevelopmentConfig.WTF_CSRF_TIME_LIMIT == 7200
    assert isinstance(DevelopmentConfig.WTF_CSRF_TIME_LIMIT, int)
    assert ProductionConfig.WTF_CSRF_TIME_LIMIT == 7200
    assert isinstance(ProductionConfig.WTF_CSRF_TIME_LIMIT, int)
