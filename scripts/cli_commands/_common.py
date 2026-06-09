"""CLI 命令共享工具 — get_client / task_id 解析 / token 过期检测"""

from src.core.client import ApiClient
from scripts.cli_ui import Style, c
from scripts.cli_config import load_config


def get_client():
    """Build an ApiClient from saved token, returning (client, config_dict).

    自动从配置中读取 client_mode（wxapp/web），确保使用正确的客户端凭据。
    """
    cfg = load_config()
    mode = cfg.get("client_mode", "wxapp")
    return ApiClient(cfg.get("token", ""), client_mode=mode), cfg


def resolve_task_id(args, cfg: dict) -> str:
    """Return task_id from args or saved config, with hint text."""
    tid = getattr(args, "task_id", None)
    if tid:
        return tid
    tid = cfg.get("task_id", "")
    if tid:
        print(c(Style.muted, f"  (使用已保存的任务 ID: {tid[:16]}...)"))
        return tid
    return ""


def token_expired(resp: dict) -> bool:
    """Heuristic: does the API response indicate an expired token?"""
    if resp.get("code") == 401:
        return True
    msg = str(resp.get("msg", ""))
    return "过期" in msg or "login" in msg.lower() or "登录" in msg


def login_expired_hint():
    """Print a consistent re-login suggestion."""
    cfg = load_config()
    if cfg.get("client_mode") == "web":
        print(c(Style.muted, "  请重新登录: python scripts/cli.py login-webvpn <token>"))
    else:
        print(c(Style.muted, "  请重新登录: python scripts/cli.py login-openid <OpenID> <学号>"))
