"""checkin — 一键打卡签到 + 补签 + 记录查询 + 月度统计"""

from __future__ import annotations

from argparse import Namespace
from datetime import datetime
from src.utils.geo import haversine, generate_gps_with_retry
from src.utils.notification import send_serverchan, build_notification
from src.core.sign_builder import build_stu_sign_data
from scripts.cli_ui import (
    Style, c, divider, kv, bullet, _status_display,
    STATUS_MAP, Spinner,
)
from scripts.cli_config import load_config, _mask, list_profiles
from scripts.cli_commands._common import (
    get_client, resolve_task_id, token_expired, login_expired_hint,
)


# ═══════════════════════════════════════════════════════════════════════
# cmd_checkin — 一键打卡（单用户 / 多用户）
# ═══════════════════════════════════════════════════════════════════════

def _checkin_single(profile_name: str, args: Namespace) -> str:
    """为一个 profile 执行一次打卡，返回状态描述。"""
    client, cfg = get_client(profile=profile_name)
    token = cfg.get("token", "")
    if not token:
        return f"未登录 (运行 login-openid --profile {profile_name})"

    tid = resolve_task_id(args, cfg)
    if not tid:
        return f"无任务ID (运行 tasks --profile {profile_name})"

    spinner = Spinner(f"[{profile_name}] 获取任务信息")
    spinner.start()
    task_detail = client.get_task_detail(tid)
    spinner.stop()

    if token_expired(task_detail):
        return f"Token过期 (运行 login-openid --profile {profile_name})"
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
        gps = generate_gps_with_retry(
            dorm_lat, dorm_lng, accuracy,
            start_offset=args.offset,
        )
        if gps is None:
            return f"超出范围: 无法在 {accuracy:.0f}m 范围内生成有效坐标"
        cur_lat, cur_lng = gps
        dist = haversine(cur_lat, cur_lng, dorm_lat, dorm_lng)

    loc_accuracy = f"{dist:.1f}"

    if dist > accuracy and not args.force:
        return f"超出范围 {dist:.0f}m > {accuracy}m (用 --force 强制提交)"

    stu_data = build_stu_sign_data(
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

    def _print_status(status: str) -> None:
        if "正常" in status or "已提交" in status:
            kv("状态", c(Style.success, status))
        elif "(" in status and "运行" in status:
            err, hint = status.split(" (", 1)
            kv("状态", f"{c(Style.error, err)} {c(Style.muted, '(' + hint)}")
        elif "超出范围" in status:
            kv("状态", c(Style.error, status))
        else:
            kv("状态", status)

    results: dict[str, str] = {}
    for pname in profiles:
        print(c(Style.heading, f"  [{pname}]"))
        status = _checkin_single(pname, args)
        results[pname] = status
        _print_status(status)
        print()

    if len(profiles) > 1:
        divider("打卡汇总")
        print()
        for pname, status in results.items():
            ok = "正常" in status or "已提交" in status
            icon = c(Style.success, "✓") if ok else c(Style.error, "✗")
            if ok:
                label = c(Style.success, status)
            elif "(" in status and "运行" in status:
                err, hint = status.split(" (", 1)
                label = f"{c(Style.error, err)} {c(Style.muted, '(' + hint)}"
            else:
                label = c(Style.error, status)
            print(f"  {icon}  {c(Style.bold, pname)}: {label}")
        print()

        # Server酱 通知（自适应所有已打卡的用户，无需配置用户列表）
        title, content = build_notification(results)
        send_serverchan(title, content)


# ═══════════════════════════════════════════════════════════════════════
# cmd_record — 查询打卡记录
# ═══════════════════════════════════════════════════════════════════════

def record(args: Namespace) -> None:
    """Query today's check-in record."""
    profile = getattr(args, "profile", None)
    client, cfg = get_client(profile=profile)
    tid = getattr(args, "record", None) or resolve_task_id(args, cfg)
    if not tid:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    date = getattr(args, "date", None)
    spinner = Spinner("正在查询打卡记录")
    spinner.start()
    resp = client.get_one_record(tid, date)
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
    month_str = getattr(args, "month", None)
    if not month_str:
        print()
        print(c(Style.error, "  请指定月份，如 --month 2026-06"))
        return
    if not tid:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    spinner = Spinner(f"正在查询 {month_str} 打卡记录")
    spinner.start()
    resp = client.get_month_records(tid, month_str)
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
            print(c(Style.muted, f"  {month_str} 暂无打卡记录"))
            return

        print()
        divider(f"{month_str} 打卡记录")
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
