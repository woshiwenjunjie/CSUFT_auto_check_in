"""notification — Server酱 微信推送（共享模块，CLI + SCF 共用）"""

from __future__ import annotations

import os
import time as time_module
from datetime import datetime, timezone


_SERVERCHAN_URL = "https://sctapi.ftqq.com/{key}.send"
_MAX_RETRIES = 2
_RETRY_DELAY = 3

_STATUS_LABELS: dict[str, str] = {
    "ok": "正常",
    "duplicate": "已签到",
    "expired": "已过期",
    "error": "失败",
}

_WINDOW_START = 13       # UTC
_WINDOW_END = 14
_WINDOW_END_MINUTE = 30


def send_serverchan(title: str, content: str, key: str = "") -> bool:
    if not key:
        key = os.environ.get("SERVERCHAN_KEY", "")
    if not key:
        return False
    try:
        import httpx
    except ImportError:
        return False
    last_err = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = httpx.post(
                _SERVERCHAN_URL.format(key=key),
                data={"title": title, "desp": content},
                timeout=15,
            )
            return resp.status_code == 200
        except Exception as e:
            last_err = e
            if attempt < _MAX_RETRIES:
                time_module.sleep(_RETRY_DELAY)
    return False


# ── 窗口检测 ─────────────────────────────────────────────

def is_window_open() -> bool:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=_WINDOW_START, minute=0, second=0, microsecond=0)
    end = now.replace(hour=_WINDOW_END, minute=_WINDOW_END_MINUTE, second=0, microsecond=0)
    return start <= now <= end


def window_hint() -> str:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=_WINDOW_START, minute=0, second=0, microsecond=0)
    if now < start:
        diff = (start - now).total_seconds()
        return f"距离开窗还有 {int(diff // 3600)} 小时 {int((diff % 3600) // 60)} 分钟"
    end = now.replace(hour=_WINDOW_END, minute=_WINDOW_END_MINUTE, second=0, microsecond=0)
    diff = (end - now).total_seconds()
    if diff > 0:
        return f"窗口还剩 {int(diff // 60)} 分钟"
    return "窗口已关闭"


# ── 通知内容构建 ─────────────────────────────────────────

def _is_success(status: str) -> bool:
    fail_keywords = ("error", "失败", "过期", "超出", "未登录", "无任务", "异常", "退出")
    for kw in fail_keywords:
        if kw in status.lower():
            return False
    return bool(status.strip())


def _map_display(status: str) -> str:
    for code, label in _STATUS_LABELS.items():
        prefix = code + ":"
        if status == code:
            return label
        if status.startswith(prefix):
            detail = status[len(prefix):].strip()
            if code == "ok":
                return f"{label} ({detail}km)"
            return f"{label}: {detail}"
    return status


def build_notification(results: dict[str, str]) -> tuple[str, str]:
    ok_count = sum(1 for s in results.values() if _is_success(s))
    total = len(results)
    ts = datetime.now().strftime("%m-%d")
    title = f"打卡汇总 {ts} | {ok_count}/{total}"

    lines = [f"## 自动打卡结果", f"共 {total} 个账号，成功 {ok_count} 个", ""]
    lines.append(f"🪟 {window_hint()}（窗口 21:00-22:30 北京时间）")
    lines.append("")
    ok_lines: list[str] = []
    fail_lines: list[str] = []
    for pname, status in results.items():
        display = _map_display(status)
        if _is_success(status):
            ok_lines.append(f"✅ **{pname}**: {display}")
        else:
            fail_lines.append(f"❌ **{pname}**: {display}")
    if ok_lines:
        lines.extend(ok_lines)
    if fail_lines:
        if ok_lines:
            lines.append("")
        lines.extend(fail_lines)
    lines.append("")
    lines.append("---")
    ts_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"🕐 {ts_full} (北京时间)")
    return title, "\n".join(lines)
