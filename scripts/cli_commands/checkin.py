"""checkin — 一键打卡签到 + 补签 + 记录查询 + 月度统计"""

import json
from datetime import datetime
from src.utils.crypto import md5
from src.utils.geo import haversine, random_offset
from scripts.cli_ui import (
    Style, c, divider, kv, bullet, warn_box, _status_display,
    STATUS_MAP, Spinner,
)
from scripts.cli_config import load_config, _mask
from scripts.cli_commands._common import (
    get_client, resolve_task_id, token_expired, login_expired_hint,
)


# ═══════════════════════════════════════════════════════════════════════
# stuSign 请求体构建
# ═══════════════════════════════════════════════════════════════════════

def _prepare_stu_sign_data(task_detail, cur_lat, cur_lng, loc_accuracy, sign_date, file_id, task_id):
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
# cmd_checkin — 一键打卡
# ═══════════════════════════════════════════════════════════════════════

def checkin(args):
    """Submit a check-in with simulated GPS offset."""
    client, cfg = get_client()
    token = cfg.get("token", "")
    if not token:
        print()
        print(c(Style.error, "  请先登录: python scripts/cli.py login-openid"))
        return
    tid = resolve_task_id(args, cfg)
    if not tid:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    spinner = Spinner("正在获取任务信息")
    spinner.start()
    task_detail = client.get_task_detail(tid)
    spinner.stop()

    if token_expired(task_detail):
        print()
        print(c(Style.error, "  Token 已过期"))
        login_expired_hint()
        return
    if not task_detail.get("success"):
        print()
        print(c(Style.error, f"  获取任务详情失败: {task_detail.get('msg', '')}"))
        return

    td = task_detail.get("data", {})
    dorm = td.get("dormitoryRegisterVO", {}) or {}
    dorm_lat = float(dorm.get("locationLat", 0))
    dorm_lng = float(dorm.get("locationLng", 0))
    accuracy = float(td.get("locationAccuracy", 100))
    is_late = bool(args.late_date)
    sign_date = args.late_date or datetime.now().strftime("%Y-%m-%d")

    if args.lat is not None and args.lng is not None:
        cur_lat, cur_lng = float(args.lat), float(args.lng)
        source = "手动指定"
    elif args.lat is not None or args.lng is not None:
        print(c(Style.error, "  --lat 和 --lng 必须同时指定"))
        return
    else:
        cur_lat, cur_lng = random_offset(dorm_lat, dorm_lng, args.offset)
        source = f"模拟偏移 ±{args.offset}°"

    dist = haversine(cur_lat, cur_lng, dorm_lat, dorm_lng)
    loc_accuracy = f"{dist:.1f}"

    print()
    divider("打卡签到")
    print()
    kv("任务", td.get("taskName", ""))
    kv("日期", sign_date + (" (补签)" if is_late else ""))
    kv("坐标", f"({cur_lat}, {cur_lng})  —  {source}")
    kv("与宿舍距离", f"{loc_accuracy}m")
    kv("精度上限", f"{accuracy}m")
    print()

    if dist > accuracy:
        warn_box(f"超出打卡范围  {dist:.0f}m > {accuracy}m")
        if not args.force:
            print(c(Style.muted, "  使用 --force 强制提交，或 --offset 减小偏移量"))
            return
        print(c(Style.warning, "  --force 模式下继续提交..."))

    stu_data = _prepare_stu_sign_data(
        td, cur_lat, cur_lng, loc_accuracy, sign_date,
        args.file_id or "", tid,
    )

    spinner = Spinner("正在提交打卡" if not is_late else "正在提交补签")
    spinner.start()
    if is_late:
        stu_data["signDate"] = sign_date
        resp = client.stu_late_sign(stu_data)
    else:
        resp = client.stu_sign(stu_data)
    spinner.stop()

    if resp.get("success"):
        print()
        print(c(Style.success, "  打卡成功！"))
    else:
        msg = resp.get("msg", "未知错误")
        if "重复" in str(msg) or "已签" in str(msg):
            print()
            print(c(Style.warning, f"  {msg}"))
        else:
            print()
            print(c(Style.error, f"  打卡失败: {msg}"))

    # ---- re-query to confirm ----
    print()
    print(c(Style.muted, "  正在确认打卡状态..."))
    record_resp = client.get_one_record(tid, sign_date)
    if token_expired(record_resp):
        print(c(Style.warning, "  Token 已过期，无法确认"))
        login_expired_hint()
        return
    if record_resp.get("success"):
        d = record_resp.get("data")
        if d and d.get("signStatus") is not None:
            sc = int(d.get("signStatus", 0))
            sn = d.get("signStatusName", "")
            kv("日期", str(d.get("signDate", "")))
            kv("状态", _status_display(sc, sn))
            if d.get("signLat"):
                kv("坐标", f"({d.get('signLat', '')}, {d.get('signLng', '')})")
            if d.get("signTime"):
                kv("打卡时间", str(d["signTime"]))
            print(f"CHECKIN_RESULT: status={sn} date={d.get('signDate', '')}")
            print()
        else:
            print(c(Style.warning, "  服务器未返回打卡记录，请稍后确认"))
            print("CHECKIN_RESULT: status=未知 date=未知")
    else:
        print(c(Style.muted, "  (无法确认打卡状态，请稍后运行 record 命令查看)"))
        print("CHECKIN_RESULT: status=未知 date=未知")


# ═══════════════════════════════════════════════════════════════════════
# cmd_record — 查询打卡记录
# ═══════════════════════════════════════════════════════════════════════

def record(args):
    """Query today's check-in record."""
    client, cfg = get_client()
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

def month(args):
    """Query monthly check-in records with summary stats."""
    client, cfg = get_client()
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
