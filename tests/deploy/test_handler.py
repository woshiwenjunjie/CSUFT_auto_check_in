"""handler.main_handler 测试

测试 3 个场景：
1. 空 event → 健康检查返回 {"status": "healthy"}
2. 正常执行 → 返回 run_multi_checkin 的 result
3. run_multi_checkin 抛异常 → 捕获并通知
"""
from unittest.mock import patch, MagicMock
import pytest
from handler import main_handler


class TestMainHandler:

    def test_empty_event_returns_healthy(self):
        """SCF 控制台健康检查"""
        result = main_handler({}, {})
        assert result == {"status": "healthy"}

    def test_falsy_event_returns_healthy(self):
        """None 或空字典也算健康检查"""
        result = main_handler(None, {})
        assert result == {"status": "healthy"}

    def test_normal_execution_returns_result(self):
        """正常流程返回 run_multi_checkin 结果"""
        expected = {"status": "ok", "msg": "正常", "date": "2026-06-12"}
        with patch("handler.run_multi_checkin", return_value=expected):
            result = main_handler({"test": True}, {})

        assert result == expected

    def test_exception_caught_and_notified(self):
        """异常时发送通知并返回 error 状态"""
        with patch("handler.run_multi_checkin", side_effect=RuntimeError("API 不可达")):
            with patch("handler.send_notifications") as mock_send:
                result = main_handler({"test": True}, {})

        assert result["status"] == "error"
        assert "API 不可达" in result["msg"]
        mock_send.assert_called_once()
