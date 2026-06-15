"""checkin — 一键打卡签到 + 补签 + 记录查询 + 月度统计"""

from __future__ import annotations

import json
import os
from argparse import Namespace
from datetime import datetime
from src.utils.crypto import md5
from src.utils.geo import haversine, random_offset
from scripts.cli_ui import (
    Style, c, divider, kv, bullet, warn_box, _status_display,
    STATUS_MAP, Spinner,
)
from scripts.cli_config import load_config, _mask, list_profiles
from scripts.cli_commands._common import (
    get_client, resolve_task_id, token_expired, login_expired_hint,
)

def _send_serverchan(title: str, content: str, key: str = "") -> bool:
    """发送 Server酱 通知（内联版，避免 deploy/ 路径导入问题）"""
    if not key:
        key = os.environ.get("SERVERCHAN_KEY", "")
    if not key:
        return False
    try:
        import httpx
        resp = httpx.post(
            f"https://sctapi.ftqq.com/{key}.send",
            data={"title": title, "desp": content},
            timeout=15,
        )
        return resp.status_code == 200
    except Exception:
        return False

_DEFAULT_GPS_OFFSET = 0.0003
_DEFAULT_GPS_RETRIES = 6
_MIN_GPS_OFFSET = 1e-6

# ═══════════════════════════════════════════════════════════════════════
# stuSign 请求体构建
# ═══════════════════════════════════════════════════════════════════════

def _prepare_stu_sign_data(task_detail: dict, cur_lat: float, cur_lng: float, loc_accuracy: str, sign_date: str, file_id: str, task_id: str) -> dict:
    """Build the stuSign request body, including the stuTaskId hash."""
    dorm = task_detail.get("dormitoryRegisterVO", {}) or {}
    stu_data = {
        "taskId": task_id,
        "scanType": task_detail.get("scanType", 1),
        "roomId": dorm.get("roomId", ""),
        "signLat": str(cur_lat),
        "signLng": str(cur_lng),
        "locationAccuracy": loc_accuracy,
        "signType": 0,
        "scanCode": "",
        "fileId": file_id or "",
    }
    hash_input = {
        "latitude": str(cur_lat),
        "longitude": str(cur_lng),
        "locationAccuracy": loc_accuracy,
        "signDate": sign_date,
        "taskId": task_id,
        "fileId": file_id or "",
    }
    stu_data["stuTaskId"] = md5(
        json.dumps(hash_input, ensure_ascii=False, separators=(",", ":"))
    )
    return stu_data


# ═══════════════════════════════════════════════════════════════════════
# cmd_checkin — 一键打卡（单用户 / 多用户）
# ═══════════════════════════════════════════════════════════════════════

def _checkin_single(profile_name: str, args: Namespace) -> str:
    """为一个 profile 执行一次打卡，返回状态描述。"""
    client, cfg = get_client(profile=profile_name)
    token = cfg.get("token", "")
    if not token:
        return "未登录"

    tid = resolve_task_id(args, cfg)
    if not tid:
        return "无任务ID"

    spinner = Spinner(f"[{profile_name}] 获取任务信息")
    spinner.start()
    task_detail = client.get_task_detail(tid)
    spinner.stop()

    if token_expired(task_detail):
        return "Token过期"
    if not task_detail.get("success"):
        return f"任务详情失败: {task_detail.get('msg', '')}"

    td = task_detail.get("data", {})
    dorm = td.get("dormitoryRegisterVO", {}) or {}
    dorm_lat = float(dorm.get("locationLat", 0))
    dorm_lng = float(dorm.get("locationLng", 0))
    accuracy = float(td.get("locationAccuracy", 100))
    is_late = bool(args.late_date)
    sign_date = args.late_date or datetime.now().strftime("%Y-%m-%d")

    if args.lat is not None and args.lng is not None:
        cur_lat, cur_lng = float(args.lat), float(args.lng)
        dist = haversine(cur_lat, cur_lng, dorm_lat, dorm_lng)
    elif args.lat is not None or args.lng is not None:
        return "--lat 和 --lng 必须同时指定"
    else:
        cur_offset = args.offset
        for attempt in range(_DEFAULT_GPS_RETRIES):
            cur_lat, cur_lng = random_offset(dorm_lat, dorm_lng, cur_offset)
            dist = haversine(cur_lat, cur_lng, dorm_lat, dorm_lng)
            if dist <= accuracy:
                break
            if cur_offset < _MIN_GPS_OFFSET:
                break
            cur_offset /= 2
        else:
            return f"超出范围 {dist:.0f}m > {accuracy}m"

    loc_accuracy = f"{dist:.1f}"

    if dist > accuracy and not args.force:
        return f"超出范围 {dist:.0f}m > {accuracy}m"

    stu_data = _prepare_stu_sign_data(
        td, cur_lat, cur_lng, loc_accuracy, sign_date,
        args.file_id or "", tid,
    )

    spinner = Spinner(f"[{profile_name}] 提交打卡")
    spinner.start()
    if is_late:
        stu_data["signDate"] = sign_date
        resp = client.stu_late_sign(stu_data)
    else:
        resp = client.stu_sign(stu_data)
    spinner.stop()

    if resp.get("success"):
        result = "已提交"
    else:
        msg = resp.get("msg", "未知错误")
        result = msg

    # 确认
    record_resp = client.get_one_record(tid, sign_date)
    if record_resp.get("success"):
        d = record_resp.get("data")
        if d and d.get("signStatus") is not None:
            sn = d.get("signStatusName", "")
            return f"{sn}"
    return result


def checkin(args: Namespace) -> None:
    """一键打卡签到，支持单用户或多用户。

    多用户: 用 --profiles 指定多个，逗号分隔（默认全部账号）
    单用户: 用 --profile 指定
    """
    explicit = getattr(args, "profiles", None) or getattr(args, "profile", None)
    if explicit:
        profiles_str = explicit
    else:
        all_p = list_profiles()
        profiles_str = ",".join(all_p) if all_p else "default"
    profiles = [p.strip() for p in profiles_str.split(",")]

    print()
    if len(profiles) > 1:
        divider("批量打卡")
        print()
        print(c(Style.info, f"  共 {len(profiles)} 个账号"))
        print()

    results: dict[str, str] = {}
    for pname in profiles:
        print(c(Style.heading, f"  [{pname}]"))
        status = _checkin_single(pname, args)
        results[pname] = status
        kv("状态", status)
        print()

    if len(profiles) > 1:
        divider("打卡汇总")
        print()
        for pname, status in results.items():
            icon = c(Style.success, "✓") if "正常" in status or "已提交" in status else c(Style.error, "✗")
            print(f"  {icon}  {pname}: {status}")
        print()

        # Server酱 通知（自适应所有已打卡的用户，无需配置用户列表）
        ok_count = sum(1 for s in results.values() if "正常" in s or "已提交" in s)
        total = len(results)
        title = f"打卡汇总 {ok_count}/{total}"
        content = f"""## 自动打卡结果
共 {total} 个账号，成功 {ok_count} 个
"""
        for pname, status in results.items():
            content += f"- {pname}: {status}\n"
        content += f"\n---\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        _send_serverchan(title, content)


# ═══════════════════════════════════════════════════════════════════════
# cmd_record — 查询打卡记录
# ═══════════════════════════════════════════════════════════════════════

def record(args: Namespace) -> None:
    """Query today's check-in record."""
    profile = getattr(args, "profile", None)
    client, cfg = get_client(profile=profile)
    tid = resolve_task_id(args, cfg)
    if not tid:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    spinner = Spinner("正在查询打卡记录")
    spinner.start()
    resp = client.get_one_record(tid, args.date)
    spinner.stop()

    if token_expired(resp):
        print()
        print(c(Style.error, "  Token 已过期"))
        login_expired_hint()
        return

    if resp.get("success"):
        d = resp.get("data")
        if d and d.get("signStatus") is not None:
            sc = int(d.get("signStatus", 0))
            sn = d.get("signStatusName", "")

            print()
            divider("打卡记录")
            print()

            kv("日期", c(Style.bold, str(d.get("signDate", ""))))
            kv("状态", _status_display(sc, sn))

            if d.get("signLat"):
                kv("坐标", f"({d.get('signLat', '')}, {d.get('signLng', '')})")
            if d.get("signTime"):
                kv("打卡时间", str(d["signTime"]))
        else:
            print()
            print(c(Style.muted, "  暂无打卡记录"))
            print(c(Style.muted, "  打卡窗口: 每天 21:00 — 22:30"))
    else:
        print()
        print(c(Style.error, f"  查询失败: {resp.get('msg', '未知错误')}"))


# ═══════════════════════════════════════════════════════════════════════
# cmd_month — 月度打卡记录汇总
# ═══════════════════════════════════════════════════════════════════════

def month(args: Namespace) -> None:
    """Query monthly check-in records with summary stats."""
    profile = getattr(args, "profile", None)
    client, cfg = get_client(profile=profile)
    tid = resolve_task_id(args, cfg)
    if not tid:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    spinner = Spinner(f"正在查询 {args.month} 打卡记录")
    spinner.start()
    resp = client.get_month_records(tid, args.month)
    spinner.stop()

    if token_expired(resp):
        print()
        print(c(Style.error, "  Token 已过期"))
        login_expired_hint()
        return

    if resp.get("success"):
        data = resp.get("data", {}) or {}
        if not data:
            print()
            print(c(Style.muted, f"  {args.month} 暂无打卡记录"))
            return

        print()
        divider(f"{args.month} 打卡记录")
        print()

        sorted_items = sorted(data.items())
        normal = late = other = 0

        for date, info in sorted_items:
            sc = int(info.get("signStatus", 0))
            sn = info.get("signStatusName", "") or STATUS_MAP.get(sc, "未知")

            if sc == 0:
                icon = c(Style.success, "✓")
                normal += 1
            elif sc == 1:
                icon = c(Style.warning, "!")
                late += 1
            else:
                icon = c(Style.muted, "-")
                other += 1

            print(f"  {icon}  {date}  {c(Style.muted, sn)}")

        parts = [f"{c(Style.success, '正常')}: {normal}天"]
        if late:
            parts.append(f"{c(Style.warning, '迟到')}: {late}天")
        if other:
            parts.append(f"{c(Style.muted, '其他')}: {other}天")
        print()
        print(c(Style.muted, "  " + "  |  ".join(parts)))
        print(c(Style.muted, f"  共 {len(data)} 条记录"))
    else:
        print()
        print(c(Style.error, f"  查询失败: {resp.get('msg', '未知错误')}"))
