import hashlib
import base64


def md5(data: str) -> str:
    """MD5 哈希，输入 Unicode 字符串，输出 32 位十六进制小写"""
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def b64_encode(data: bytes) -> str:
    """标准 Base64 编码，输出 Unicode 字符串"""
    return base64.b64encode(data).decode("utf-8")


def b64_decode(data: str) -> bytes:
    """标准 Base64 解码"""
    return base64.b64decode(data)
