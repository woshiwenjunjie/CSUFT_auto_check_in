from __future__ import annotations

import os
import time as time_module
from datetime import datetime, timedelta, timezone
from typing import Any


_SERVERCHAN_URL = "https://sctapi.ftqq.com/{key}.send"
_MAX_RETRIES = 2
_RETRY_DELAY = 3
_TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

_STATUS_LABELS: dict[str, str] = {
    "ok": "正常",
    "duplicate": "已签到",
    "expired": "已过期",
    "error": "失败",
}
_SUCCESS_STATUS_CODES = {"ok", "duplicate"}
_FAILURE_STATUS_CODES = {
    "error",
    "expired",
    "no_login",
    "out_of_range",
    "task_detail_failed",
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
            if resp.status_code != 200:
                return False
            try:
                payload = resp.json()
            except Exception:
                return True
            return payload.get("code") in (0, "0")
        except Exception as e:
            last_err = e
            if attempt < _MAX_RETRIES:
                time_module.sleep(_RETRY_DELAY)
    return False


def send_telegram(text: str, bot_token: str = "", chat_id: str = "") -> bool:
    """发送 Telegram 通知。

    从环境变量 TG_BOT_TOKEN / TG_CHAT_ID 读取凭据，可传参覆盖。
    返回 True 表示发送成功，False 表示未配置或发送失败。
    """
    if not bot_token:
        bot_token = os.environ.get("TG_BOT_TOKEN", "")
    if not chat_id:
        chat_id = os.environ.get("TG_CHAT_ID", "")
    if not bot_token or not chat_id:
        return False
    try:
        import httpx
    except ImportError:
        return False
    last_err: Any = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = httpx.post(
                _TELEGRAM_API_URL.format(token=bot_token),
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=15,
            )
            return resp.status_code == 200
        except Exception as e:
            last_err = e
            if attempt < _MAX_RETRIES:
                time_module.sleep(_RETRY_DELAY)
    return False


def send_notifications(title: str, content: str, telegram_text: str = "") -> None:
    """统一发送所有通道的通知（Server酱 + Telegram）。

    优先使用 Server酱（主通道），Telegram 为备用通道。
    两个通道独立失败互不影响。
    """
    sc_ok = send_serverchan(title, content)
    tg_text = telegram_text or content
    tg_ok = send_telegram(tg_text)
    if not sc_ok and not tg_ok:
        print("[通知] Server酱和Telegram均未配置，跳过通知")
    elif sc_ok:
        print("[通知] Server酱推送成功")
    elif tg_ok:
        print("[通知] Telegram推送成功")


# ── 窗口检测 ────────────────

def is_window_open() -> bool:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=_WINDOW_START, minute=0, second=0, microsecond=0)
    end = now.replace(hour=_WINDOW_END, minute=_WINDOW_END_MINUTE, second=0, microsecond=0)
    return start <= now <= end


def _beijing_now() -> datetime:
    now = datetime.now(timezone.utc)
    beijing_timezone = timezone(timedelta(hours=8))
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc).astimezone(beijing_timezone)
    return now.astimezone(beijing_timezone)


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


# ── 通知内容构建 ────────────────

def _is_success(status: str) -> bool:
    status = status.strip()
    if not status:
        return False
    status_code = status.split(":", 1)[0].strip().split("|", 1)[0].strip().lower()
    if status_code in _SUCCESS_STATUS_CODES:
        return True
    if status_code in _FAILURE_STATUS_CODES:
        return False

    fail_keywords = (
        "error", "failed", "failure", "expired", "out_of_range",
        "失败", "过期", "超出", "未登录", "无任务", "异常", "退出",
    )
    for kw in fail_keywords:
        if kw in status.lower():
            return False
    success_keywords = ("正常", "已提交", "已签到")
    return any(kw in status for kw in success_keywords)


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
    ts = _beijing_now().strftime("%m-%d")
    title = f"打卡汇总 {ts} | {ok_count}/{total}"

    lines = [f"## 自动打卡结果", f"共 {total} 个账号，成功 {ok_count} 个", ""]
    lines.append(f"🕐 {window_hint()}（窗口21:00-22:30 北京时间）")
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
    ts_full = _beijing_now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"🕒 {ts_full} (北京时间)")
    return title, "\n".join(lines)
