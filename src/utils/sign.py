import os
from src.utils.crypto import md5, b64_encode

# 飞源认证客户端凭据，可通过环境变量覆盖（用于不同部署环境）
CLIENT_ID = os.getenv("FLYSOURCE_CLIENT_ID", "flysource_wise_wxapp")
CLIENT_SECRET = os.getenv("FLYSOURCE_CLIENT_SECRET", "DA788asdUDjnasd_flysource_wxappdsdadDAIUiuwqe")


def generate_sign(path: str, timestamp: int, token: str = "") -> str:
    """生成 FlySource-sign 请求头

    算法: MD5(path + MD5(timestamp + token)) + "1." + Base64(timestamp)
    - path: 去掉 query 的请求路径
    - timestamp: 13 位毫秒时间戳
    - token: access_token（登录后获得），空字符串也可生成
    """
    ts_str = str(timestamp)
    inner_hash = md5(ts_str + token)
    outer_str = path + "?sign=" + inner_hash
    outer_hash = md5(outer_str)
    return outer_hash + "1." + b64_encode(ts_str.encode("utf-8"))


def generate_basic_auth() -> str:
    """生成 Basic 认证头: Base64(ClientId + ":" + ClientSecret)"""
    raw = f"{CLIENT_ID}:{CLIENT_SECRET}"
    return "Basic " + b64_encode(raw.encode("utf-8"))
