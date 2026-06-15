"""checkin 核心工具函数测试

测试内容（无外部依赖）：
- _now() / _now_str() / _date_str()  时间延迟计算
- _is_window_open() / _nearest_window_hint()  窗口检测
- build_notification()  通知构造
"""
import os
import re
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest
from checkin import _now, _now_str, _date_str, _is_window_open, _nearest_window_hint
from src.utils.notification import build_notification


DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


class TestTimeFunctions:

    def test_now_returns_datetime(self):
        result = _now()
        assert isinstance(result, datetime)

    def test_now_str_format(self):
        result = _now_str()
        assert DATETIME_PATTERN.match(result)

    def test_date_str_format(self):
        result = _date_str()
        assert DATE_PATTERN.match(result)

    def test_now_str_contains_date_str_prefix(self):
        assert _now_str().startswith(_date_str())


class TestBuildNotification:

    def test_all_ok_summary(self):
        title, body = build_notification({"USER_1": "ok", "USER_2": "ok"})
        assert "2/2" in title
        assert "USER_1" in body
        assert "USER_2" in body

    def test_partial_summary(self):
        title, body = build_notification({"USER_1": "ok", "USER_2": "error"})
        assert "1/2" in title
        assert "USER_2" in body
        assert "error" in body

    def test_duplicate_counts_as_success(self):
        title, body = build_notification({"USER_1": "duplicate"})
        assert "1/1" in title

    def test_single_profile(self):
        title, body = build_notification({"default": "ok"})
        assert "1/1" in title


class TestWindowFunctions:

    def test_is_window_open_during_window(self):
        with patch("checkin.dt") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 13, 30)
            assert _is_window_open() is True

    def test_is_window_open_before_window(self):
        with patch("checkin.dt") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 12, 0)
            assert _is_window_open() is False

    def test_is_window_open_after_window(self):
        with patch("checkin.dt") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 15, 0)
            assert _is_window_open() is False

    def test_nearest_window_hint_before(self):
        with patch("checkin.dt") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 10, 0)
            hint = _nearest_window_hint()
            assert "距离开窗" in hint
            assert "3 小时" in hint

    def test_nearest_window_hint_during(self):
        with patch("checkin.dt") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 13, 30)
            hint = _nearest_window_hint()
            assert "窗口还剩" in hint

    def test_nearest_window_hint_after(self):
        with patch("checkin.dt") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 15, 0)
            hint = _nearest_window_hint()
            assert "窗口已关闭" in hint
