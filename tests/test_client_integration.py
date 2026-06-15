"""ApiClient 集成测试 — 使用 mock 模拟 httpx"""

from __future__ import annotations

import json
import time
import re

import httpx
import pytest
from unittest.mock import Mock, patch

from src.core.client import ApiClient


class TestTokenExpired:
    """token_expired 检测逻辑测试"""

    def test_401_code_detected(self):
        """HTTP 401 状态码触发过期"""
        client = ApiClient(token="fake")
        mock_response = Mock()
        mock_response.status_code = 401
        client._client.get = Mock(return_value=mock_response)
        result = client._request("GET", "/test", retry=1)
        assert result["code"] == 401
        assert result["success"] is False

    def test_expired_in_msg_detected(self):
        """响应 msg 含"过期"触发过期"""
        from scripts.cli_commands._common import token_expired
        assert token_expired({"code": 400, "msg": "登录已过期"}) is True

    def test_login_in_msg_detected(self):
        """响应 msg 含"login"触发过期"""
        from scripts.cli_commands._common import token_expired
        assert token_expired({"code": 400, "msg": "please login"}) is True

    def test_normal_response_not_expired(self):
        """正常响应不触发过期"""
        from scripts.cli_commands._common import token_expired
        assert token_expired({"code": 200, "msg": "success", "success": True}) is False


class TestSignFormat:
    """签名生成格式验证"""

    def test_sign_contains_md5_and_base64(self):
        """签名格式: MD5(32位) + "1." + Base64(时间戳)"""
        ts = int(time.time() * 1000)
        sign = client_sign("/api/test", ts, "test_token")
        assert "1." in sign
        parts = sign.split("1.")
        assert len(parts) == 2
        assert re.match(r"^[a-f0-9]{32}$", parts[0])
        import base64
        decoded = base64.b64decode(parts[1]).decode()
        assert decoded == str(ts)

    def test_sign_without_token(self):
        """无 token 也能生成有效格式签名"""
        ts = 1700000000000
        sign = client_sign("/api/test", ts)
        assert "1." in sign

    def test_sign_different_paths_different(self):
        """不同路径签名不同"""
        ts = 1700000000000
        s1 = client_sign("/api/foo", ts, "t")
        s2 = client_sign("/api/bar", ts, "t")
        assert s1 != s2


class TestRetryMechanism:
    """指数退避重试机制测试"""

    def test_retry_on_request_error(self):
        """网络错误时触发重试"""
        client = ApiClient(token="fake")
        mock_post = Mock(side_effect=httpx.RequestError("connection error"))
        client._client.post = mock_post
        result = client._request("POST", "/api/test", retry=2)
        assert mock_post.call_count == 2
        assert result["success"] is False

    def test_no_retry_on_401(self):
        """401 不重试，立即返回"""
        client = ApiClient(token="fake")
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get = Mock(return_value=mock_response)
        client._client.get = mock_get
        result = client._request("GET", "/api/test", retry=3)
        assert mock_get.call_count == 1
        assert result["code"] == 401


def client_sign(path: str, timestamp: int, token: str = "") -> str:
    """调用 ApiClient._headers 内部签名逻辑"""
    from src.utils.sign import generate_sign
    return generate_sign(path, timestamp, token)
