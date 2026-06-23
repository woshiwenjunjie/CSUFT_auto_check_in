"""notification.send_serverchan 测试

测试 4 个路径：
1. SERVERCHAN_KEY 未设置 → 跳过
2. HTTP 200 → 成功
3. HTTP 非 200 → 失败
4. httpx 抛异常 → 重试 2 次后返回 False
"""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from src.utils.notification import send_serverchan


NOTIFICATION_PATH = Path(__file__).resolve().parents[2] / "src" / "utils" / "notification.py"


def test_notification_module_has_no_utf8_bom():
    content = NOTIFICATION_PATH.read_text(encoding="utf-8")

    assert content.startswith("from __future__ import annotations")


class TestSendServerchan:

    def test_skip_when_no_key(self):
        """SERVERCHAN_KEY 未配置时跳过"""
        with patch.dict(os.environ, clear=True):
            result = send_serverchan("title", "content")
        assert result is False

    def test_success_on_http_200(self):
        """HTTP 200 返回 True"""
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"code": 0, "message": "success"}
        with patch.dict(os.environ, {"SERVERCHAN_KEY": "SCT-test"}):
            with patch("httpx.post", return_value=mock_resp) as mock_post:
                result = send_serverchan("title", "content")

        assert result is True
        mock_post.assert_called_once()

    def test_failure_on_http_non_200(self):
        """HTTP 非 200 返回 False"""
        mock_resp = MagicMock(status_code=500)
        mock_resp.text = "Internal Server Error"
        with patch.dict(os.environ, {"SERVERCHAN_KEY": "SCT-test"}):
            with patch("httpx.post", return_value=mock_resp):
                result = send_serverchan("title", "content")

        assert result is False

    def test_failure_on_serverchan_business_error(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"code": 30001, "message": "bad content"}
        with patch.dict(os.environ, {"SERVERCHAN_KEY": "SCT-test"}):
            with patch("httpx.post", return_value=mock_resp):
                result = send_serverchan("title", "content")

        assert result is False

    def test_retry_on_exception(self):
        """httpx 异常时重试 2 次后返回 False"""
        with patch.dict(os.environ, {"SERVERCHAN_KEY": "SCT-test"}):
            with patch("httpx.post", side_effect=ConnectionError("timeout")) as mock_post:
                with patch("time.sleep") as mock_sleep:
                    result = send_serverchan("title", "content")

        assert result is False
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1
