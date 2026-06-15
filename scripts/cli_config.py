"""CLI 配置管理 — JSON 持久化、密码 base64 混淆、安全终端输入

配置存储于 ~/.auto_check_in/config.json，密码以 $obf:<base64> 格式存储
（防止肩窥，非加密）。同时提供脱敏显示（_mask）和安全密码输入（secure_input）。

Important caveats:
  - 密码混淆仅防一眼看到明文，不作为安全加密手段
  - 旧版明文密码在 load_config 中自动标记为 _needs_migration
  - secure_input 在方 Windows 用 msvcrt，Unix 用 termios

Variable naming: All names must be meaningful and context-relevant.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════════════════════════

CONFIG_DIR = Path.home() / ".auto_check_in"
CONFIG_FILE = CONFIG_DIR / "config.json"


# ═══════════════════════════════════════════════════════════════════════
# Password obfuscation (base64 — 防止一眼看到明文，非加密)
# ═══════════════════════════════════════════════════════════════════════

def _scramble(text: str) -> str:
    """对密码进行 base64 混淆存储"""
    import base64 as _base64
    return _base64.b64encode(text.encode("utf-8")).decode()


def _unscramble(encoded: str) -> str:
    """解码 _scramble 的输出"""
    import base64 as _base64
    return _base64.b64decode(encoded).decode("utf-8")


# ═══════════════════════════════════════════════════════════════════════
# Config load / save
# ═══════════════════════════════════════════════════════════════════════

def _migrate_flat_to_profiles(cfg: dict) -> dict:
    """将旧版扁平配置迁移为 profile 格式"""
    has_legacy_keys = any(k in cfg for k in ("openid", "username", "token", "password"))
    if not has_legacy_keys or "profiles" in cfg:
        return cfg
    profile = {
        "openid": cfg.get("openid", ""),
        "username": cfg.get("username", ""),
        "token": cfg.get("token", ""),
        "tenant_id": cfg.get("tenant_id", "000000"),
        "task_id": cfg.get("task_id", ""),
        "client_mode": cfg.get("client_mode", "wxapp"),
    }
    pw = cfg.get("password", "") or cfg.get("_password_raw", "")
    if pw:
        profile["password"] = pw
    if cfg.get("_password_raw"):
        profile["_password_raw"] = cfg["_password_raw"]
    # 清理迁移后的扁平键（避免新旧数据重复）
    for k in ("openid", "username", "token", "password", "tenant_id", "task_id", "client_mode"):
        cfg.pop(k, None)
    cfg["profiles"] = {"default": profile}
    cfg["current_profile"] = "default"
    return cfg


def load_config(profile: str | None = None) -> dict:
    """读取配置文件，支持 profile。

    返回当前 profile 的子配置（含 _profiles、_current_profile 元信息）。
    """
    raw = {}
    if CONFIG_FILE.exists():
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    raw = _migrate_flat_to_profiles(raw)

    profiles = raw.get("profiles", {})
    cur = profile or raw.get("current_profile", "default")

    if cur not in profiles:
        profiles[cur] = {}
        raw["profiles"] = profiles
        raw["current_profile"] = cur

    cfg = dict(profiles[cur])
    cfg["_profiles"] = profiles
    cfg["_current_profile"] = cur

    # 密码恢复
    pw = cfg.get("password", "")
    if isinstance(pw, str) and pw.startswith("$obf:"):
        try:
            cfg["_password_raw"] = _unscramble(pw[5:])
        except Exception:
            cfg["_password_raw"] = ""
    elif pw:
        cfg["_password_raw"] = pw
        cfg["_needs_migration"] = True

    # 校验 client_mode
    cm = cfg.get("client_mode", "")
    if cm and cm not in ("wxapp", "web"):
        cfg["client_mode"] = "wxapp"

    return cfg


def save_config(cfg: dict[str, Any], profile: str | None = None) -> None:
    """保存配置，支持 profile。自动混淆密码字段。

    如果 cfg 包含 _profiles/_current_profile 元信息，则更新对应 profile。
    否则更新当前 profile 或指定 profile。
    """
    profiles = cfg.pop("_profiles", None)
    cur = cfg.pop("_current_profile", None)
    target = profile or cur or "default"

    raw_pw = cfg.pop("_password_raw", None) or cfg.get("password", "")
    cfg.pop("_needs_migration", None)

    if raw_pw and not str(raw_pw).startswith("$obf:"):
        cfg["password"] = "$obf:" + _scramble(str(raw_pw))

    # 读取完整文件
    full = {}
    if CONFIG_FILE.exists():
        full = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    full = _migrate_flat_to_profiles(full)

    if profiles is None:
        profiles = full.get("profiles", {})
    if cur is None:
        cur = full.get("current_profile", "default")

    profiles[target] = cfg
    full["profiles"] = profiles
    full["current_profile"] = cur

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_profiles() -> list[str]:
    """列出所有可用的 profile 名称"""
    raw = {}
    if CONFIG_FILE.exists():
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    raw = _migrate_flat_to_profiles(raw)
    return list(raw.get("profiles", {}).keys())


def switch_profile(name: str) -> bool:
    """切换到指定 profile"""
    raw = {}
    if CONFIG_FILE.exists():
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    raw = _migrate_flat_to_profiles(raw)
    if name not in raw.get("profiles", {}):
        return False
    raw["current_profile"] = name
    CONFIG_FILE.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return True


def get_password(cfg: dict[str, Any]) -> str:
    """从配置中提取明文密码（兼容新旧格式）"""
    return cfg.get("_password_raw", "") or cfg.get("password", "")


# ═══════════════════════════════════════════════════════════════════════
# Secure password input (with * placeholder echo)
# ═══════════════════════════════════════════════════════════════════════

def secure_input(prompt: str = "密码: ") -> str:
    """Read a password while echoing * for each character.

    Windows: msvcrt.getch().  Unix: termios.setraw().
    Backspace/Delete/Ctrl+C all handled.
    """
    try:
        import msvcrt  # Windows

        sys.stdout.write(prompt)
        sys.stdout.flush()
        chars = []
        while True:
            ch = msvcrt.getch()
            if ch in (b"\r", b"\n"):
                sys.stdout.write("\n")
                break
            elif ch in (b"\x08", b"\x7f"):
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch == b"\x03":
                sys.stdout.write("\n")
                raise KeyboardInterrupt
            else:
                chars.append(ch)
                sys.stdout.write("*")
                sys.stdout.flush()
        return b"".join(chars).decode("utf-8", errors="replace")
    except ImportError:
        import termios
        import tty  # Unix

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdout.write(prompt)
            sys.stdout.flush()
            chars = []
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"):
                    sys.stdout.write("\n")
                    break
                elif ch in ("\x08", "\x7f"):
                    if chars:
                        chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ch == "\x03":
                    sys.stdout.write("\n")
                    raise KeyboardInterrupt
                else:
                    chars.append(ch)
                    sys.stdout.write("*")
                    sys.stdout.flush()
            return "".join(chars)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _mask(text: str | None, show: int = 4) -> str:
    """Mask a sensitive string, showing only first and last few characters.

    Returns '' for None/empty input so callers can supply their own fallback
    (e.g. '(未设置)', '(未登录)') via ``_mask(v) or 'fallback'``.
    """
    if not text:
        return ""
    if len(text) <= show * 2:
        return "*" * len(text)
    return text[:show] + "*" * (len(text) - show * 2) + text[-show:]
