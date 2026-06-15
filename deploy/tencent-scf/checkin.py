"""SCF checkin — 使用共享模块的轻量编排层"""

from __future__ import annotations

import os
from datetime import datetime as dt, timezone
from src.core.token_client import ApiTokenClient
from src.utils.notification import send_serverchan, build_notification


# ── 时区工具 ─────────────────────────────────────────────
def _now() -> dt:
    return dt.now(timezone.utc)

def _now_str() -> str:
    return _now().strftime("%Y-%m-%d %H:%M:%S")

def _date_str() -> str:
    return _now().strftime("%Y-%m-%d")


# ── 窗口检测 ─────────────────────────────────────────────
_WINDOW_START = 13  # UTC
_WINDOW_END = 14
_WINDOW_END_MINUTE = 30


def _is_window_open() -> bool:
    now = dt.now(timezone.utc)
    start = now.replace(hour=_WINDOW_START, minute=0, second=0, microsecond=0)
    end = now.replace(hour=_WINDOW_END, minute=_WINDOW_END_MINUTE, second=0, microsecond=0)
    return start <= now <= end


def _nearest_window_hint() -> str:
    now = dt.now(timezone.utc)
    start = now.replace(hour=_WINDOW_START, minute=0, second=0, microsecond=0)
    if now < start:
        diff = (start - now).total_seconds()
        return f"距离开窗还有 {int(diff // 3600)} 小时 {int((diff % 3600) // 60)} 分钟"
    end = now.replace(hour=_WINDOW_END, minute=_WINDOW_END_MINUTE, second=0, microsecond=0)
    diff = (end - now).total_seconds()
    if diff > 0:
        return f"窗口还剩 {int(diff // 60)} 分钟"
    return "窗口已关闭"


# ── 单用户打卡 ───────────────────────────────────────────
def _checkin_one(profile: str) -> dict:
    api = ApiTokenClient(profile)
    ok, msg = api.login()
    if not ok:
        return {"status": "error", "detail": msg, "profile": profile}

    tid = api.task_id or api.fetch_latest_task_id()
    if not tid:
        return {"status": "error", "detail": "无可用 task_id", "profile": profile}

    check_ok, status, detail = api.do_checkin(tid)
    confirm = api.confirm_checkin(tid) if check_ok else ""
    return {
        "status": status,
        "detail": detail,
        "confirm": confirm,
        "profile": profile,
        "date": _date_str(),
    }


# ── 多用户打卡 ─────────────────────────────────────────────
def _do_multi_or_single(profile_names: list[str]) -> list[dict]:
    results: list[dict] = []
    for pname in profile_names:
        try:
            result = _checkin_one(pname)
        except Exception as e:
            result = {"status": "error", "detail": str(e), "profile": pname}
        results.append(result)
        print(f"  [{pname}] 状态: {result['status']}" + (f" | {result.get('detail', '')}" if result.get('detail') else ""))
    return results


def run_multi_checkin() -> dict:
    profiles_str = os.environ.get("CHECKIN_PROFILES", "")
    profile_names = [p.strip() for p in profiles_str.split(",") if p.strip()]
    if not profile_names:
        profile_names = ["default"]

    window_ok = _is_window_open()
    print(f"  [时间] {_now_str()} (UTC) | 窗口{'开启' if window_ok else '关闭'}")
    if not window_ok:
        hint = _nearest_window_hint()
        print(f"  [提示] {hint}")

    results = _do_multi_or_single(profile_names)

    status_map = {r["profile"]: f"{r['status']}|{r.get('detail', '')}" for r in results}
    all_ok = all(r["status"] in ("ok", "duplicate") for r in results)

    title, content = build_notification(
        {r["profile"]: r["status"] for r in results}
    )
    send_serverchan(title, content)

    return {"status": "ok" if all_ok else "partial", "results": status_map}
