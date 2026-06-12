"""CLI UI 组件 — ANSI 样式系统、格式化终端输出、Spinner 动画

提供 Style 类（ANSI 转义码）+ c() 颜色守卫，支持 NO_COLOR 环境变量和
isatty 自动检测。Spinner 使用 daemon 线程实现动画，非 TTY 环境自动静默。

Important caveats:
  - 颜色输出仅在 stdout 为 TTY 且 NO_COLOR 未设置时生效
  - Spinner 为非线程安全的最小实现，仅适用于 CLI 单线程场景

Variable naming: All names must be meaningful and context-relevant.
"""

import os
import sys
import threading
import time


# ═══════════════════════════════════════════════════════════════════════
# Terminal Style System (ANSI escape codes)
# ═══════════════════════════════════════════════════════════════════════

class Style:
    """ANSI terminal styles — works on Windows 10+ and all Unix terminals.

    Respects NO_COLOR env var and isatty check via the c() helper.
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"

    @classmethod
    def success(cls, text: str) -> str:
        return f"{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def error(cls, text: str) -> str:
        return f"{cls.RED}{text}{cls.RESET}"

    @classmethod
    def warning(cls, text: str) -> str:
        return f"{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def info(cls, text: str) -> str:
        return f"{cls.CYAN}{text}{cls.RESET}"

    @classmethod
    def muted(cls, text: str) -> str:
        return f"{cls.DIM}{text}{cls.RESET}"

    @classmethod
    def bold(cls, text: str) -> str:
        return f"{cls.BOLD}{text}{cls.RESET}"

    @classmethod
    def heading(cls, text: str) -> str:
        return f"{cls.BOLD}{cls.CYAN}{text}{cls.RESET}"


# ---- color guard ----

USE_COLOR = (
    os.environ.get("NO_COLOR", "").lower() not in ("1", "true", "yes")
    and sys.stdout.isatty()
)


def c(style_fn, text: str) -> str:
    """Apply a Style classmethod when color is enabled; otherwise plain text."""
    return style_fn(text) if USE_COLOR else text


# ---- output helpers ----

def divider(title: str = "", char: str = "─", width: int = 56):
    """Print a horizontal rule, optionally with a centered title."""
    if title:
        side = max(0, (width - len(title) - 2) // 2)
        right = max(0, width - side - len(title) - 2)
        line = char * side + " " + c(Style.bold, title) + " " + char * right
    else:
        line = char * width
    print(c(Style.muted, line))


def kv(key: str, value: str, indent: int = 2):
    """Aligned key-value line."""
    print(f"{' ' * indent}{c(Style.muted, key + ':')} {value}")


def bullet(text: str, ok: bool = True):
    """Bullet line with success/error icon."""
    icon = c(Style.success, "✓") if ok else c(Style.error, "✗")
    print(f"  {icon}  {text}")


def warn_box(text: str):
    """Highlighted warning line."""
    print(c(Style.warning, f"  !  {text}"))


# ---- status map ----

STATUS_MAP: dict[int, str] = {
    0: "正常", 1: "迟到", 2: "请假中",
    3: "未归", 4: "走读中", 5: "离校中", 6: "外宿中",
}


def _status_display(status_code: int, status_name: str = "") -> str:
    """Return a color-coded status string for display.

    Uses the status code for color (0=green/success, 1=yellow/warning, else muted)
    and falls back to STATUS_MAP when status_name is empty.
    """
    label = status_name or STATUS_MAP.get(status_code, "未知")
    if status_code == 0:
        return c(Style.success, label)
    elif status_code == 1:
        return c(Style.warning, label)
    else:
        return c(Style.muted, label)


# ═══════════════════════════════════════════════════════════════════════
# Spinner (animated progress indicator for API calls)
# ═══════════════════════════════════════════════════════════════════════

class Spinner:
    """Thread-based braille spinner. No-op when stdout is not a TTY."""

    _chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, message: str = "处理中"):
        self.message = message
        self._running = False
        self._thread = None
        self._active = USE_COLOR and sys.stdout.isatty()

    def _spin(self):
        i = 0
        while self._running:
            sys.stdout.write(
                f"\r  {self._chars[i % len(self._chars)]}  {self.message}..."
            )
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    def start(self):
        if not self._active:
            return
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, clear: bool = True):
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.3)
        if clear and sys.stdout.isatty():
            sys.stdout.write("\r" + " " * (len(self.message) + 25) + "\r")
            sys.stdout.flush()
