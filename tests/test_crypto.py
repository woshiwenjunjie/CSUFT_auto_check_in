"""MD5 / Base64 工具函数测试"""
from src.utils.crypto import md5, b64_encode, b64_decode


def test_md5_empty():
    """空字符串的 MD5"""
    assert md5("") == "d41d8cd98f00b204e9800998ecf8427e"


def test_md5_hello():
    """hello 的标准 MD5"""
    assert md5("hello") == "5d41402abc4b2a76b9719d911017c592"


def test_md5_unicode():
    """Unicode 字符串的 MD5"""
    assert md5("中文") == "a7bac2239fcdcb3a067903d8077c4a07"


def test_b64_encode_standard():
    """Base64 标准向量测试"""
    assert b64_encode(b"hello") == "aGVsbG8="


def test_b64_encode_binary():
    """二进制数据的 Base64 编码"""
    assert b64_encode(bytes(range(3))) == "AAEC"


def test_b64_decode_roundtrip():
    """Base64 编解码往返"""
    original = b"test data \x00\xff"
    encoded = b64_encode(original)
    assert b64_decode(encoded) == original
