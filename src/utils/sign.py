"""FlySource 签名算法与客户端凭据管理

提供 FlySource-sign 请求头签名生成和 Basic 认证头构造。
凭据可通过环境变量 FLYSOURCE_CLIENT_ID / FLYSOURCE_CLIENT_SECRET 覆盖，
默认值来自微信小程序反编译源码（应用级公开常量），无需保密。

Environment variables:
  FLYSOURCE_CLIENT_ID      客户端 ID（默认按模式匹配 wxapp/web 版）
  FLYSOURCE_CLIENT_SECRET  客户端密钥（同上）

Variable naming: All names must be meaningful and context-relevant.
"""
import os
from src.utils.crypto import md5, b64_encode

# 飞源认证客户端凭据，可通过环境变量覆盖（用于不同部署环境）
# 微信小程序版
WX_CLIENT_ID = "flysource_wise_wxapp"
WX_CLIENT_SECRET = "DA788asdUDjnasd_flysource_wxappdsdadDAIUiuwqe"
# WebVPN 版
WEB_CLIENT_ID = "flysource_wise_app"
WEB_CLIENT_SECRET = "DA788asdUDjnasd_flysource_dsdadDAIUiuwqe"


def get_credentials(mode: str = "wxapp") -> tuple[str, str]:
    """获取指定模式的客户端凭据（从环境变量或默认值）"""
    if mode == "web":
        return (
            os.getenv("FLYSOURCE_CLIENT_ID", WEB_CLIENT_ID),
            os.getenv("FLYSOURCE_CLIENT_SECRET", WEB_CLIENT_SECRET),
        )
    else:
        return (
            os.getenv("FLYSOURCE_CLIENT_ID", WX_CLIENT_ID),
            os.getenv("FLYSOURCE_CLIENT_SECRET", WX_CLIENT_SECRET),
        )


def generate_sign(path: str, timestamp: int, token: str = "",
                  client_id: str = "", client_secret: str = "") -> str:
    """生成 FlySource-sign 请求头

    算法: MD5(path + MD5(timestamp + token)) + "1." + Base64(timestamp)
    - path: 去掉 query 的请求路径
    - timestamp: 13 位毫秒时间戳
    - token: access_token（登录后获得），空字符串也可生成
    - client_id/client_secret: 预留参数，当前签名算法不依赖凭据
    """
    ts_str = str(timestamp)
    inner_hash = md5(ts_str + token)
    outer_str = path + "?sign=" + inner_hash
    outer_hash = md5(outer_str)
    return outer_hash + "1." + b64_encode(ts_str.encode("utf-8"))


def generate_basic_auth(client_id: str, client_secret: str) -> str:
    """生成 Basic 认证头: Base64(ClientId + ":" + ClientSecret)"""
    raw = f"{client_id}:{client_secret}"
    return "Basic " + b64_encode(raw.encode("utf-8"))
