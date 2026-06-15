"""FlySource-sign 签名算法与 Basic 认证测试"""
import re
import time
from src.utils.sign import generate_sign, generate_basic_auth, get_credentials


def test_sign_format():
    """签名输出格式校验: MD5(32位) + "1." + Base64(时间戳)"""
    timestamp = int(time.time() * 1000)
    path = "/api/test"
    token = "test_token_123"
    result = generate_sign(path, timestamp, token)
    assert "1." in result
    parts = result.split("1.")
    assert len(parts) == 2
    assert re.match(r"^[a-f0-9]{32}$", parts[0]), "前半部分应为 32 位 MD5"


def test_sign_different_paths():
    """不同路径产生不同签名"""
    ts = 1700000000000
    token = "abc"
    s1 = generate_sign("/api/foo", ts, token)
    s2 = generate_sign("/api/bar", ts, token)
    assert s1 != s2


def test_sign_different_tokens():
    """不同 token 产生不同签名"""
    ts = 1700000000000
    s1 = generate_sign("/api/test", ts, "token_a")
    s2 = generate_sign("/api/test", ts, "token_b")
    assert s1 != s2


def test_sign_different_timestamps():
    """不同时间戳产生不同签名"""
    s1 = generate_sign("/api/test", 1000, "t")
    s2 = generate_sign("/api/test", 2000, "t")
    assert s1 != s2


def test_sign_empty_token():
    """空 token 也能生成签名"""
    result = generate_sign("/api/test", 1700000000000)
    assert "1." in result


def test_sign_empty_path():
    """空路径 '' 也能生成签名"""
    result = generate_sign("", 1700000000000, "test")
    assert "1." in result


def test_sign_chinese_path():
    """中文路径签名可生成"""
    result = generate_sign("/api/测试", 1700000000000, "token_中文")
    assert "1." in result


def test_sign_path_with_space():
    """路径含空格签名可生成"""
    result = generate_sign("/api/test path", 1700000000000, "token")
    assert "1." in result


def test_basic_auth_format():
    """Basic 认证头格式: "Basic " + Base64(clientId:clientSecret)"""
    client_id, client_secret = get_credentials("wxapp")
    result = generate_basic_auth(client_id, client_secret)
    assert result.startswith("Basic ")
    import base64
    decoded = base64.b64decode(result[6:]).decode()
    assert ":" in decoded
