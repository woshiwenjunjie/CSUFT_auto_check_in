"""checkin 核心工具函数测试

测试内容（无外部依赖）：
- _now() / _now_str() / _date_str()  时间延迟计算
- is_window_open() / window_hint()  窗口检测
- build_notification()  通知构造
"""
import os
import re
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest
from checkin import _now, _now_str, _date_str
from src.utils.notification import build_notification, _map_display, is_window_open, window_hint


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
        assert "失败" in body

    def test_duplicate_counts_as_success(self):
        title, body = build_notification({"USER_1": "duplicate"})
        assert "1/1" in title

    def test_single_profile(self):
        title, body = build_notification({"default": "ok"})
        assert "1/1" in title

    def test_known_failure_codes_do_not_count_as_success(self):
        title, body = build_notification({
            "USER_1": "expired",
            "USER_2": "out_of_range",
            "USER_3": "task_detail_failed",
        })

        assert "0/3" in title

    def test_timestamp_uses_explicit_beijing_time(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 13, 30)
            title, body = build_notification({"USER_1": "ok"})

        assert "2026-06-15 21:30:00" in body


class TestMapDisplay:

    def test_ok_code_mapped(self):
        assert _map_display("ok") == "正常"

    def test_ok_with_distance(self):
        assert _map_display("ok: 0.12") == "正常 (0.12km)"

    def test_error_code_mapped(self):
        assert _map_display("error") == "失败"

    def test_error_with_detail(self):
        assert _map_display("error: 登录失败") == "失败: 登录失败"

    def test_duplicate_mapped(self):
        assert _map_display("duplicate") == "已签到"

    def test_expired_mapped(self):
        assert _map_display("expired") == "已过期"

    def test_passthrough_chinese(self):
        assert _map_display("未登录 (运行 login-openid --profile USER_1)") == "未登录 (运行 login-openid --profile USER_1)"


class TestBuildNotificationDetail:

    def test_ok_with_distance_in_body(self):
        title, body = build_notification({"USER_1": "ok: 0.12", "USER_2": "duplicate"})
        assert "2/2" in title
        assert "0.12km" in body
        assert "已签到" in body

    def test_error_with_detail_in_body(self):
        title, body = build_notification({"USER_1": "error: 登录失败: 网络超时"})
        assert "0/1" in title
        assert "失败: 登录失败: 网络超时" in body

    def test_grouping_separates_ok_and_fail(self):
        title, body = build_notification({"A": "ok", "B": "error"})
        assert body.index("✅") < body.index("❌"), "success antes fail"

    def test_mixed_scf_and_cli_statuses(self):
        title, body = build_notification({
            "USER_1": "ok: 0.12",
            "USER_2": "未登录 (运行 login-openid --profile USER_2)",
        })
        assert "1/2" in title
        assert "0.12km" in body
        assert "USER_2" in body


class TestWindowFunctions:

    def test_is_window_open_during_window(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 13, 30)
            assert is_window_open() is True

    def test_is_window_open_before_window(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 12, 0)
            assert is_window_open() is False

    def test_is_window_open_after_window(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 15, 0)
            assert is_window_open() is False

    def test_nearest_window_hint_before(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 10, 0)
            hint = window_hint()
            assert "距离开窗" in hint
            assert "3 小时" in hint

    def test_nearest_window_hint_during(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 13, 30)
            hint = window_hint()
            assert "窗口还剩" in hint

    def test_nearest_window_hint_after(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 15, 0)
            hint = window_hint()
            assert "窗口已关闭" in hint


class TestNotificationWindowLine:

    def test_window_line_present(self):
        title, body = build_notification({"U1": "ok", "U2": "error"})
        assert "北京" in body
        assert "21:00-22:30" in body

    def test_window_hint_before(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 10, 0)
            title, body = build_notification({"U1": "ok"})
            assert "距离开窗" in body

    def test_window_hint_during(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 13, 30)
            title, body = build_notification({"U1": "ok"})
            assert "窗口还剩" in body

    def test_window_hint_after(self):
        with patch("src.utils.notification.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15, 15, 0)
            title, body = build_notification({"U1": "ok"})
            assert "窗口已关闭" in body
