"""checkin 核心工具函数测试

测试内容（无外部依赖）：
- _now() / _now_str() / _date_str()  时间延迟计算
- get_env_str()                       环境变量读取
- _build_notification()               通知构造（5 种状态 + detail 分支）

注：_build_notification 内部调用 _now_str()/ _date_str()，测试时控制场景。
"""
import os
import re
from datetime import datetime
from unittest.mock import patch
import pytest
from checkin import _now, _now_str, _date_str, get_env_str, _build_notification


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


class TestGetEnvStr:

    def test_default_when_not_set(self):
        assert get_env_str("NONEXIST_VAR", "fallback") == "fallback"

    def test_default_empty_when_not_specified(self):
        assert get_env_str("NONEXIST_VAR") == ""

    def test_returns_env_value(self):
        with patch.dict(os.environ, {"TEST_VAR": "hello"}):
            assert get_env_str("TEST_VAR") == "hello"

    def test_returns_env_over_default(self):
        with patch.dict(os.environ, {"TEST_VAR": "env"}):
            assert get_env_str("TEST_VAR", "default") == "env"


class TestBuildNotification:

    def test_ok_status(self):
        title, body = _build_notification(
            {"status": "ok", "msg": "正常", "date": "2026-06-12", "detail": "状态：正常"}
        )
        assert "打卡成功" in title
        assert "2026-06-12" in title
        assert "正常" in body

    def test_ok_without_detail(self):
        title, body = _build_notification(
            {"status": "ok", "msg": "正常", "date": "2026-06-12"}
        )
        assert "打卡成功" in title

    def test_duplicate_status(self):
        title, body = _build_notification(
            {"status": "duplicate", "msg": "今日已打卡", "date": "2026-06-12"}
        )
        assert "今日已打卡" in title
        assert "无需重复" in body

    def test_expired_status(self):
        title, body = _build_notification(
            {"status": "expired", "msg": "token 过期", "date": "2026-06-12"}
        )
        assert "Token 过期" in title
        assert "重新抓包" in body

    def test_nowindow_status(self):
        title, body = _build_notification(
            {"status": "nowindow", "msg": "不在打卡窗口", "date": "2026-06-12"}
        )
        assert "未到签到时间" in title
        assert "21:00–22:30" in body

    def test_error_status(self):
        title, body = _build_notification(
            {"status": "error", "msg": "登录失败", "date": "2026-06-12"}
        )
        assert "打卡失败" in title
        assert "登录失败" in body

    def test_fallback_date_in_result_is_overridden(self):
        """result 中带的 date 会被使用，而非自动计算"""
        title, body = _build_notification(
            {"status": "ok", "msg": "正常", "date": "2026-01-01"}
        )
        assert "2026-01-01" in title

    def test_fallback_date_when_missing_in_result(self):
        """result 中无 date 时自动计算，格式正确"""
        title, body = _build_notification({"status": "ok", "msg": "正常"})
        assert re.search(r"\d{4}-\d{2}-\d{2}", title) is not None

    def test_partial_status(self):
        title, body = _build_notification(
            {"status": "partial", "msg": "1/2 个账号打卡成功", "date": "2026-06-12"}
        )
        assert "部分打卡成功" in title
        assert "1/2" in body

    def test_partial_with_detail(self):
        title, body = _build_notification(
            {"status": "partial", "msg": "1/2 个账号打卡成功", "date": "2026-06-12",
             "detail": "✅ [USER_1] 正常\n❌ [USER_2] 登录失败"}
        )
        assert "USER_1" in body
        assert "USER_2" in body

    def test_detail_appended_when_present(self):
        title, body = _build_notification(
            {"status": "ok", "msg": "正常", "date": "2026-06-12", "detail": "状态：正常\n地点：宿舍"}
        )
        assert "状态：正常" in body
        assert "地点：宿舍" in body
