"""CLI 配置管理 — 持久化、密码混淆、安全输入"""

import json
import os
import sys
from pathlib import Path


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

def load_config() -> dict:
    """读取配置文件，自动检测并还原密码"""
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        pw = cfg.get("password", "")
        if isinstance(pw, str) and pw.startswith("$obf:"):
            try:
                cfg["_password_raw"] = _unscramble(pw[5:])
            except Exception:
                cfg["_password_raw"] = ""  # 解密失败，静默丢弃
        elif pw:
            # 明文密码 → 标记为需要迁移
            cfg["_password_raw"] = pw
            cfg["_needs_migration"] = True
        return cfg
    return {}


def save_config(cfg: dict):
    """保存配置，自动混淆密码字段"""
    raw_pw = cfg.pop("_password_raw", None) or cfg.get("password", "")
    cfg.pop("_needs_migration", None)  # 清理内部标记
    if raw_pw and not str(raw_pw).startswith("$obf:"):
        cfg["password"] = "$obf:" + _scramble(str(raw_pw))
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_password(cfg: dict) -> str:
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
