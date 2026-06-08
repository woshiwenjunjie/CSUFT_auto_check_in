"""密码混淆存储测试"""

import json
import tempfile
from pathlib import Path
from scripts.cli_config import (
    _scramble, _unscramble, load_config, save_config, get_password,
)


def test_scramble_roundtrip_ascii():
    """ASCII 密码往返"""
    for pw in ["test123", "p@ssw0rd!", "", "a" * 200]:
        assert _unscramble(_scramble(pw)) == pw


def test_scramble_roundtrip_unicode():
    """中文密码往返"""
    for pw in ["密码abc", "🔑password", "日本語パスワード"]:
        assert _unscramble(_scramble(pw)) == pw


def test_scramble_not_plaintext():
    """混淆后不等于原文"""
    result = _scramble("my_password")
    assert result != "my_password"
    assert "my_password" not in result


def test_get_password_plaintext():
    """向后兼容：明文密码仍可读取"""
    cfg = {"password": "plaintext_pwd"}
    assert get_password(cfg) == "plaintext_pwd"


def test_get_password_obfuscated():
    """混淆密码可正确还原"""
    cfg = {"_password_raw": "decoded_pwd"}
    assert get_password(cfg) == "decoded_pwd"


def test_get_password_empty():
    """无密码字段返回空字符串"""
    assert get_password({}) == ""
    assert get_password({"other": "data"}) == ""
