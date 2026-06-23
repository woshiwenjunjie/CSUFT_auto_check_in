"""SCF checkin — 使用共享模块的轻量编排层"""

from __future__ import annotations

import os
from datetime import datetime as dt, timezone
from src.core.token_client import ApiTokenClient
from src.utils.notification import send_notifications, build_notification, is_window_open, window_hint


# ── 时区工具 ─────────────────────────────────────────────
def _now() -> dt:
    return dt.now(timezone.utc)

def _now_str() -> str:
    return _now().strftime("%Y-%m-%d %H:%M:%S")

def _date_str() -> str:
    return _now().strftime("%Y-%m-%d")


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

    window_ok = is_window_open()
    print(f"  [时间] {_now_str()} (UTC) | 窗口{'开启' if window_ok else '关闭'}")
    if not window_ok:
        hint = window_hint()
        print(f"  [提示] {hint}")

    results = _do_multi_or_single(profile_names)

    status_map = {r["profile"]: f"{r['status']}|{r.get('detail', '')}" for r in results}
    success_statuses = {"ok", "duplicate"}
    success_count = sum(1 for r in results if r["status"] in success_statuses)
    if success_count == len(results):
        final_status = "ok"
    elif success_count == 0:
        final_status = "error"
    else:
        final_status = "partial"

    title, content = build_notification(
        {
            r["profile"]: (
                r["status"] if not r.get("detail")
                else f"{r['status']}: {r['detail']}"
            )
            for r in results
        }
    )
    send_notifications(title, content)

    return {"status": final_status, "results": status_map}
