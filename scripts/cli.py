#!/usr/bin/env python3
"""
Auto Check-In CLI —— 中南林业科技大学自动晚点名打卡工具

Commands:
  setup          交互式首次配置向导（推荐新用户使用）
  status         查看登录状态、任务信息、今日打卡记录
  config         查看或管理本地配置（show / clear）
  login-openid   OpenID 登录（推荐方式）
  login          密码登录（备用）
  tasks          查看打卡任务列表（自动记住任务 ID）
  detail         查看任务详情（含宿舍坐标、精度上限）
  checkin        一键打卡签到（自动模拟 GPS 偏移）
  record         查询当日打卡状态
  month          按月查询打卡记录

配置文件:  ~/.auto_check_in/config.json
文档:      docs/guides/user/CLI教程.md
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force UTF-8 output on Windows — Python may otherwise inherit GBK
# from the console codepage, garbling Chinese characters.
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.core.client import ApiClient
from src.utils.crypto import md5
from src.utils.geo import haversine, random_offset

# 从拆分后的子模块导入 UI 和配置工具
from scripts.cli_ui import (
    Style, c, divider, kv, bullet, warn_box,
    STATUS_MAP, _status_display, Spinner,
)
from scripts.cli_config import (
    CONFIG_DIR, CONFIG_FILE,
    load_config, save_config, get_password, secure_input, _mask,
)


# ═══════════════════════════════════════════════════════════════════════
# Shared utilities
# ═══════════════════════════════════════════════════════════════════════

def get_client():
    """Build an ApiClient from saved token, returning (client, config_dict)."""
    cfg = load_config()
    return ApiClient(cfg.get("token", "")), cfg


def _resolve_task_id(args, cfg: dict) -> str:
    """Return task_id from args or saved config, with hint text."""
    tid = getattr(args, "task_id", None)
    if tid:
        return tid
    tid = cfg.get("task_id", "")
    if tid:
        print(c(Style.muted, f"  (使用已保存的任务 ID: {tid[:16]}...)"))
        return tid
    return ""


def _token_expired(resp: dict) -> bool:
    """Heuristic: does the API response indicate an expired token?"""
    if resp.get("code") == 401:
        return True
    msg = str(resp.get("msg", ""))
    return "过期" in msg or "login" in msg.lower() or "登录" in msg


def _login_expired_hint():
    """Print a consistent re-login suggestion."""
    print(c(Style.muted, "  请重新登录: python scripts/cli.py login-openid"))


# ═══════════════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════════════

# ---- setup ----

def cmd_setup(args):
    """Interactive first-time configuration wizard."""
    print()
    divider("首次配置向导")
    print()
    print(f"  {c(Style.bold, '欢迎！')} 这个向导会引导你完成首次设置，约 2 分钟。")
    print()

    # Step 1 — OpenID
    print(f"  {c(Style.heading, '第 1 步：获取 OpenID')}")
    print()
    print(f"  OpenID 是微信给你的唯一标识（o 开头约 28 位字符）。")
    print(f"  它不在任何地方显示，需要通过抓包工具获取。")
    print(f"  📖 教程: docs/guides/user/fiddler-抓包获取OpenID.md")
    print()

    openid = input("  OpenID: ").strip()
    if not openid:
        print()
        print(c(Style.error, "  OpenID 不能为空，向导退出。"))
        return

    # Step 2 — student ID
    print()
    print(f"  {c(Style.heading, '第 2 步：学号')}")
    print(f"  {c(Style.muted, '就是你在学校的学号，如 2023XXXXXX')}")
    print()
    username = input("  学号: ").strip()
    if not username:
        print()
        print(c(Style.error, "  学号不能为空，向导退出。"))
        return

    # Step 3 — password
    print()
    print(f"  {c(Style.heading, '第 3 步：密码')}")
    print(
        f"  {c(Style.muted, '注意：密码保存时会自动混淆（base64），不是明文存储。')}"
    )
    save_pwd = input("  是否保存密码？[Y/n]: ").strip().lower()
    password = ""
    if save_pwd in ("", "y", "yes"):
        password = secure_input("  密码: ")
    else:
        password = secure_input("  密码 (仅本次使用): ")

    # Step 4 — test login
    print()
    print(f"  {c(Style.heading, '第 4 步：验证登录')}")
    print()

    spinner = Spinner("正在登录验证")
    spinner.start()
    client = ApiClient()
    resp = client.sign_in_openid("000000", openid, username, password, 1)
    spinner.stop()

    cfg = {"tenant_id": "000000", "username": username, "openid": openid}

    if resp.get("access_token"):
        cfg["token"] = resp["access_token"]
        if save_pwd in ("", "y", "yes"):
            cfg["_password_raw"] = password
        save_config(cfg)
        bullet("登录验证成功")
        bullet(f"配置已保存到 {CONFIG_FILE}")
        print()
        print(f"  {c(Style.success, '🎉 配置完成！')}")
        print()
        print(c(Style.bold, "  🚀 你现在可以："))
        print(f"    {c(Style.info, 'python scripts/cli.py status')}     查看状态概览")
        print(f"    {c(Style.info, 'python scripts/cli.py tasks')}      查看打卡任务")
        print(f"    {c(Style.info, 'python scripts/cli.py checkin')}    一键打卡签到")
        print()
        print(c(Style.muted, "  💡 日常使用只需 status + checkin 两条命令即可。"))
    else:
        err = resp.get("error_description") or resp.get("msg", "未知错误")
        bullet(f"登录失败: {err}", ok=False)
        save_config(cfg)
        print()
        if "绑定" in str(err):
            print(c(Style.warning, "  ⚠️  账号已被绑定到其他 OpenID"))
            print(c(Style.muted, "  重试: python scripts/cli.py login-openid --bind 0"))
        elif "密码" in str(err) or "password" in str(err).lower():
            print(c(Style.warning, "  ⚠️  密码可能输入错误"))
            print(c(Style.muted, "  你可以手动重试: python scripts/cli.py login-openid --force-input"))
        else:
            print(c(Style.warning, "  配置已保存但登录未成功，请检查："))
            print(c(Style.muted, "    1. OpenID 是否正确（o 开头约 28 位）"))
            print(c(Style.muted, "    2. 学号和密码是否正确"))
            print(c(Style.muted, "    3. 校园网或 VPN 是否已连接"))
            print(c(Style.muted, "  确认后重试: python scripts/cli.py login-openid"))
    print()


# ---- status ----

def cmd_status(args):
    """Show login status, current task, and today's check-in record."""
    cfg = load_config()

    print()
    divider("系统状态")
    print()

    # ---- config summary ----
    print(c(Style.bold, "  配置"))
    kv("配置文件", str(CONFIG_FILE))
    kv("学号", _mask(cfg.get("username"), 3) or "(未设置)")
    kv("OpenID", _mask(cfg.get("openid")) or "(未设置)")
    kv("密码", "已保存 (混淆)" if get_password(cfg) else "未保存")
    kv("任务ID", _mask(cfg.get("task_id"), 8) or "(未设置)")
    print()

    # ---- login check ----
    token = cfg.get("token", "")
    if not token:
        print(c(Style.warning, "  !  未登录"))
        print(c(Style.muted, "  请运行: python scripts/cli.py login-openid"))
        print()
        return

    spinner = Spinner("正在验证登录状态")
    spinner.start()
    client = ApiClient(token)
    resp = client.get_task_list(current=1, size=1)
    spinner.stop()

    if _token_expired(resp):
        bullet("登录状态: Token 已过期", ok=False)
        _login_expired_hint()
        print()
        return

    if resp.get("success"):
        records = resp.get("data", {}).get("records", [])
        bullet("登录状态: 已登录 ✓")
        if records and isinstance(records, list) and len(records) > 0:
            task = records[0]
            task_name = task.get("taskName", "")
            task_id = task.get("taskId", "")
            print()
            print(c(Style.bold, "  当前任务"))
            kv("名称", task_name)
            kv("ID", _mask(task_id, 8))
            kv(
                "时间",
                f"{task.get('signStartTime', '')} — {task.get('signEndTime', '')}",
            )

            # Today's record
            if task_id:
                today = datetime.now().strftime("%Y-%m-%d")
                rec = client.get_one_record(task_id, today)
                print()
                if _token_expired(rec):
                    bullet("登录状态: Token 已过期", ok=False)
                    _login_expired_hint()
                    print()
                    return
                if rec.get("success"):
                    d = rec.get("data")
                    if d and d.get("signStatus") is not None:
                        sc = int(d.get("signStatus", 0))
                        sn = d.get("signStatusName", "")
                        print(c(Style.bold, "  今日打卡"))
                        kv("日期", str(d.get("signDate", "")))
                        kv("状态", _status_display(sc, sn))
                        if d.get("signLat"):
                            kv("坐标", f"({d.get('signLat', '')}, {d.get('signLng', '')})")
                        if d.get("signTime"):
                            kv("打卡时间", str(d["signTime"]))
                    else:
                        print(c(Style.warning, "  ⚠️  今日尚未打卡"))
                        print(c(Style.muted, "  打卡窗口: 每晚 21:00 — 22:30"))
                        print()
                        print(c(Style.info, "  👉 python scripts/cli.py checkin"))
                else:
                    print(c(Style.error, f"  查询失败: {rec.get('msg', '-')}"))
                    print(c(Style.muted, "  请检查网络连接或校园 VPN 是否正常"))
    else:
        bullet("登录状态: API 连接失败", ok=False)
        print(c(Style.muted, f"  原因: {resp.get('msg', '-')}"))

    print()
    print(c(Style.muted, "  💡 下一步:"))
    if cfg.get("task_id"):
        print(c(Style.muted, "     python scripts/cli.py checkin     一键打卡"))
    else:
        print(c(Style.muted, "     python scripts/cli.py tasks        查看任务列表"))
    print(c(Style.muted, "     python scripts/cli.py status -h    查看更多用法"))


# ---- config ----

def cmd_config(args):
    """View or clear local configuration."""
    cfg = load_config()
    action = getattr(args, "action", "show")

    if action == "clear":
        if args.all:
            print()
            print(
                c(
                    Style.warning,
                    "  即将清除全部配置: 学号 / OpenID / 密码 / token",
                )
            )
            confirm = input("  确认？[y/N]: ").strip().lower()
            if confirm in ("y", "yes"):
                if CONFIG_FILE.exists():
                    CONFIG_FILE.unlink()
                print(c(Style.success, "  配置已全部清除"))
            else:
                print(c(Style.muted, "  已取消"))
        elif args.password:
            if cfg.pop("password", None) is not None or cfg.pop("_password_raw", None) is not None:
                save_config(cfg)
                print(c(Style.success, "  密码已清除"))
            else:
                print(c(Style.muted, "  没有已保存的密码"))
        else:
            # default: clear token
            if cfg.pop("token", None) is not None:
                save_config(cfg)
                print(c(Style.success, "  Token 已清除"))
            else:
                print(c(Style.muted, "  没有已保存的 token"))
        return

    # ---- show ----
    print()
    divider("本地配置")
    print()

    kv("路径", str(CONFIG_FILE))
    if CONFIG_FILE.exists():
        st = CONFIG_FILE.stat()
        mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
        kv("大小", f"{st.st_size} bytes  ·  修改于 {mtime}")
    print()

    print(c(Style.bold, "  凭据"))
    kv("学号", _mask(cfg.get("username"), 3) or "(未设置)")
    kv("OpenID", _mask(cfg.get("openid")) or "(未设置)")
    kv("密码", f"已保存 {_mask(get_password(cfg))}" if get_password(cfg) else "(未保存)")
    kv("Token", _mask(cfg.get("token"), 8) or "(未登录)")
    kv("租户", cfg.get("tenant_id", "000000"))
    print()
    kv("任务ID", _mask(cfg.get("task_id"), 8) or "(未设置)")
    print()

    print(c(Style.muted, "  子命令:"))
    print(c(Style.muted, "    config show         查看配置"))
    print(c(Style.muted, "    config clear        清除 token"))
    print(c(Style.muted, "    config clear --all  清除全部"))
    print(c(Style.muted, "    config clear --password  清除密码"))


# ---- login-openid ----

def cmd_login_openid(args):
    """OpenID login (recommended)."""
    cfg = load_config()
    openid = args.openid or cfg.get("openid", "")
    username = args.username or cfg.get("username", "")

    if not openid:
        print()
        print(c(Style.error, "  请提供 OpenID"))
        print(c(Style.muted, "    python scripts/cli.py login-openid <OpenID> <学号>"))
        print(c(Style.muted, "    或运行交互向导: python scripts/cli.py setup"))
        return
    if not username:
        print()
        print(c(Style.error, "  请提供学号"))
        return

    # Auto-detect already-bound users to avoid duplicate bind error
    from_config = not args.openid and not args.username
    if from_config and args.bind == 1:
        args.bind = 0

    password = (
        args.password
        or (get_password(cfg) if not args.force_input else None)
        or secure_input("密码: ")
    )

    spinner = Spinner("正在登录")
    spinner.start()
    client = ApiClient()
    resp = client.sign_in_openid(
        args.tenant, openid, username, password, args.bind
    )
    spinner.stop()

    if resp.get("access_token"):
        cfg["token"] = resp["access_token"]
        cfg["tenant_id"] = args.tenant
        cfg["username"] = username
        cfg["openid"] = openid
        if args.save_password:
            cfg["_password_raw"] = password
        save_config(cfg)

        tag = " (密码已保存)" if args.save_password else ""
        print()
        bullet("登录成功" + tag)
        kv("学号", _mask(username, 3))
        kv("Token", _mask(resp["access_token"], 8))
        print()
        print(c(Style.muted, "  下一步: python scripts/cli.py tasks"))
    else:
        err = resp.get("error_description") or resp.get("msg", "未知错误")
        print()
        bullet(f"登录失败: {err}", ok=False)
        if "绑定" in str(err):
            print(c(Style.muted, "  提示: 账号已绑定，用 --bind 0 仅登录"))
        elif "密码" in str(err) or "password" in str(err).lower():
            print(c(Style.muted, "  提示: 密码错误，或用 --force-input 重试"))


# ---- login (password, fallback) ----

def cmd_login(args):
    """Password login (fallback — needs captcha)."""
    cfg = load_config()
    username = args.username or cfg.get("username", "")
    if not username:
        print()
        print(c(Style.error, "  请提供学号"))
        return
    password = (
        args.password
        or (get_password(cfg) if not args.force_input else None)
        or secure_input("密码: ")
    )

    spinner = Spinner("正在登录")
    spinner.start()
    client = ApiClient()
    resp = client.sign_in(args.tenant, username, password)
    spinner.stop()

    if resp.get("access_token"):
        cfg["token"] = resp["access_token"]
        cfg["tenant_id"] = args.tenant
        cfg["username"] = username
        if args.save_password:
            cfg["_password_raw"] = password
        save_config(cfg)
        print()
        bullet("登录成功")
        kv("学号", _mask(username, 3))
        kv("Token", _mask(resp["access_token"], 8))
    else:
        print()
        bullet(
            "登录失败: "
            + resp.get("error_description", resp.get("msg", "未知错误")),
            ok=False,
        )


# ---- tasks ----

def cmd_tasks(args):
    """List check-in tasks, auto-save the first task ID."""
    client, cfg = get_client()

    spinner = Spinner("正在获取任务列表")
    spinner.start()
    resp = client.get_task_list(current=args.page, size=args.size)
    spinner.stop()

    if _token_expired(resp):
        print()
        print(c(Style.error, "  Token 已过期"))
        _login_expired_hint()
        return

    if resp.get("success"):
        records = resp.get("data", {}).get("records", [])
        records = records if isinstance(records, list) else []
        if not records:
            print()
            print(c(Style.muted, "  暂无打卡任务"))
            return

        print()
        divider("打卡任务")
        print()
        for i, t in enumerate(records):
            task_id = t.get("taskId", "")
            task_name = t.get("taskName", "")
            start = t.get("signStartTime", "")
            end = t.get("signEndTime", "")
            print(f"  {c(Style.bold, f'[{i + 1}]')}  {c(Style.info, task_name)}")
            kv("任务ID", _mask(task_id, 8))
            kv("打卡时间", f"{start} — {end}")
            print()

        print(c(Style.muted, f"  共 {len(records)} 个任务"))

        if records and not args.no_save:
            cfg["task_id"] = records[0]["taskId"]
            save_config(cfg)
            print(
                c(
                    Style.success,
                    "  已记住任务 ID，后续命令可省略 task_id",
                )
            )
    else:
        print()
        print(c(Style.error, f"  获取任务失败: {resp.get('msg', '未知错误')}"))


# ---- detail ----

def cmd_detail(args):
    """Show task detail including dorm coordinates and accuracy limit."""
    client, cfg = get_client()
    args.task_id = _resolve_task_id(args, cfg)
    if not args.task_id:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    spinner = Spinner("正在获取任务详情")
    spinner.start()
    resp = client.get_task_detail(args.task_id)
    spinner.stop()

    if _token_expired(resp):
        print()
        print(c(Style.error, "  Token 已过期"))
        _login_expired_hint()
        return

    if resp.get("success"):
        d = resp.get("data", {})
        dorm = d.get("dormitoryRegisterVO", {}) or {}

        print()
        divider("任务详情")
        print()

        print(c(Style.bold, "  基本信息"))
        kv("任务名称", c(Style.bold, d.get("taskName", "")))
        kv("打卡时间", f"{d.get('signStartTime', '')} — {d.get('signEndTime', '')}")
        kv("任务ID", _mask(d.get("taskId", "") or args.task_id, 12))
        print()

        print(c(Style.bold, "  宿舍信息"))
        kv(
            "宿舍",
            f"{dorm.get('dormName', '')} {dorm.get('floorName', '')} {dorm.get('roomNo', '')}",
        )
        kv(
            "坐标",
            f"({dorm.get('locationLat', '')}, {dorm.get('locationLng', '')})",
        )
        kv("精度上限", f"{d.get('locationAccuracy', '')}m")

        loc_enabled = d.get("openLocate") == 1
        kv(
            "定位校验",
            c(Style.success, "已开启") if loc_enabled else c(Style.warning, "已关闭"),
        )

        if loc_enabled:
            acc = d.get("locationAccuracy", "N/A")
            print()
            print(
                c(
                    Style.muted,
                    f"  打卡时模拟坐标与宿舍距离需 < {acc}m",
                )
            )
    else:
        print()
        print(c(Style.error, f"  获取详情失败: {resp.get('msg', '未知错误')}"))


# ---- checkin ----

def _prepare_stu_sign_data(
    task_detail, cur_lat, cur_lng, loc_accuracy, sign_date, file_id, task_id
):
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


def cmd_checkin(args):
    """Submit a check-in with simulated GPS offset."""
    client, cfg = get_client()
    token = cfg.get("token", "")
    if not token:
        print()
        print(c(Style.error, "  请先登录: python scripts/cli.py login-openid"))
        return
    args.task_id = _resolve_task_id(args, cfg)
    if not args.task_id:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    spinner = Spinner("正在获取任务信息")
    spinner.start()
    task_detail = client.get_task_detail(args.task_id)
    spinner.stop()

    if _token_expired(task_detail):
        print()
        print(c(Style.error, "  Token 已过期"))
        _login_expired_hint()
        return
    if not task_detail.get("success"):
        print()
        print(
            c(
                Style.error,
                f"  获取任务详情失败: {task_detail.get('msg', '')}",
            )
        )
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
            print(
                c(
                    Style.muted,
                    "  使用 --force 强制提交，或 --offset 减小偏移量",
                )
            )
            return
        print(c(Style.warning, "  --force 模式下继续提交..."))

    stu_data = _prepare_stu_sign_data(
        td, cur_lat, cur_lng, loc_accuracy, sign_date,
        args.file_id or "", args.task_id,
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

    # ---- re-query to confirm actual record ----
    print()
    print(c(Style.muted, "  正在确认打卡状态..."))
    record_resp = client.get_one_record(args.task_id, sign_date)
    if _token_expired(record_resp):
        print(c(Style.warning, "  Token 已过期，无法确认"))
        _login_expired_hint()
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
            # 机器可读状态行（供 auto_checkin.sh 解析）
            print(f"CHECKIN_RESULT: status={sn} date={d.get('signDate', '')}")
            print()
        else:
            print(c(Style.warning, "  服务器未返回打卡记录，请稍后确认"))
            print("CHECKIN_RESULT: status=未知 date=未知")
    else:
        print(c(Style.muted, "  (无法确认打卡状态，请稍后运行 record 命令查看)"))
        print("CHECKIN_RESULT: status=未知 date=未知")


# ---- record ----

def cmd_record(args):
    """Query today's check-in record."""
    client, cfg = get_client()
    args.task_id = _resolve_task_id(args, cfg)
    if not args.task_id:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    spinner = Spinner("正在查询打卡记录")
    spinner.start()
    resp = client.get_one_record(args.task_id, args.date)
    spinner.stop()

    if _token_expired(resp):
        print()
        print(c(Style.error, "  Token 已过期"))
        _login_expired_hint()
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
            print(
                c(Style.muted, "  打卡窗口: 每天 21:00 — 22:30")
            )
    else:
        print()
        print(c(Style.error, f"  查询失败: {resp.get('msg', '未知错误')}"))


# ---- month ----

def cmd_month(args):
    """Query monthly check-in records with summary stats."""
    client, cfg = get_client()
    args.task_id = _resolve_task_id(args, cfg)
    if not args.task_id:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    spinner = Spinner(f"正在查询 {args.month} 打卡记录")
    spinner.start()
    resp = client.get_month_records(args.task_id, args.month)
    spinner.stop()

    if _token_expired(resp):
        print()
        print(c(Style.error, "  Token 已过期"))
        _login_expired_hint()
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

        # Summary
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


# ═══════════════════════════════════════════════════════════════════════
# Main dispatcher
# ═══════════════════════════════════════════════════════════════════════

def _build_parser():
    """Build the argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="python scripts/cli.py",
        description="中南林业科技大学自动晚点名打卡工具\n\n"
                    "新手上路：python scripts/cli.py setup   ← 推荐从这里开始",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"配置文件: {CONFIG_FILE}\n"
               f"详细文档: docs/guides/user/CLI教程.md\n"
               f"概念解释: docs/guides/user/关键词与概念解释.md",
    )
    sub = parser.add_subparsers(
        dest="command",
        title="可用命令",
        description="输入 python scripts/cli.py <命令> --help 查看每个命令的详细用法",
    )

    _HELP = argparse.RawDescriptionHelpFormatter  # shorthand

    # ---- setup ----
    p_setup = sub.add_parser(
        "setup", help="🌟 交互式首次配置向导（强烈推荐新用户使用）",
        formatter_class=_HELP,
        description="4 步完成配置：输入 OpenID → 学号 → 密码 → 自动验证登录",
        epilog="示例:\n  python scripts/cli.py setup",
    )

    # ---- status ----
    p_status = sub.add_parser(
        "status", help="📋 查看登录状态、任务信息、今日打卡记录",
        formatter_class=_HELP,
        description="一次命令同时查看：配置概况 / 登录是否有效 / 当前任务 / 今日是否已打卡",
        epilog="示例:\n  python scripts/cli.py status\n\n"
               "这是每天打开终端后最常用的命令。",
    )

    # ---- config ----
    p_cfg = sub.add_parser(
        "config", help="⚙️  查看或清除本地配置",
        formatter_class=_HELP,
        description="管理 ~/.auto_check_in/config.json 中的凭据信息。\n"
                    "凭据显示均已脱敏，保护隐私。",
        epilog="示例:\n"
               "  python scripts/cli.py config              # 查看配置\n"
               "  python scripts/cli.py config clear         # 清除 token\n"
               "  python scripts/cli.py config clear --all   # 清除全部",
    )
    p_cfg.add_argument(
        "action", nargs="?", default="show",
        choices=["show", "clear"],
        help="show = 查看当前配置（凭据已脱敏）  |  clear = 清除指定内容",
    )
    p_cfg.add_argument("--all", action="store_true",
                       help="清除全部配置：学号 / OpenID / 密码 / Token")
    p_cfg.add_argument("--password", action="store_true",
                       help="仅清除已保存的密码")

    # ---- login-openid ----
    p_openid = sub.add_parser(
        "login-openid", help="🔑 OpenID 登录（推荐方式，无需验证码）",
        formatter_class=_HELP,
        description="用微信 OpenID 换取 access_token，一次登录后 credential 自动保存。\n"
                    "支持从配置文件自动读取已保存的凭据。",
        epilog="示例:\n"
               "  python scripts/cli.py login-openid oXXXX... 2023XXXXXX              # 完整登录\n"
               "  python scripts/cli.py login-openid                                # 从配置读取凭据\n"
               "  python scripts/cli.py login-openid --save-password                 # 登录并保存密码\n"
               "  python scripts/cli.py login-openid --bind 0                        # 仅登录不绑定",
    )
    p_openid.add_argument("--tenant", default="000000",
                          help="学校租户 ID，默认 000000（中南林业科技大学）")
    p_openid.add_argument("openid", nargs="?", default="",
                          help="微信 OpenID（o 开头约 28 位），留空则从配置读取")
    p_openid.add_argument("username", nargs="?", default="",
                          help="学号，留空则从配置读取")
    p_openid.add_argument("password", nargs="?", default=None,
                          help="密码（不建议在命令行中明文输入）")
    p_openid.add_argument("--bind", type=int, default=1, choices=[0, 1],
                          help="0 = 仅登录不绑定  |  1 = 绑定 OpenID 与学号（默认，首次使用建议）")
    p_openid.add_argument("--save-password", action="store_true",
                          help="将密码保存到本地配置文件（方便后续自动登录）")
    p_openid.add_argument("--force-input", action="store_true",
                          help="忽略配置文件中已保存的密码，强制手动输入")

    # ---- login ----
    p_login = sub.add_parser(
        "login", help="🔐 密码登录（备用方案，需验证码）",
        formatter_class=_HELP,
        description="用学号 + 密码直接登录。需要先获取验证码。\n"
                    "一般只有在 OpenID 登录不可用时才用此方式。",
        epilog="示例:\n"
               "  python scripts/cli.py login 2023XXXXXX               # 交互式输入密码登录",
    )
    p_login.add_argument("--tenant", default="000000",
                         help="学校租户 ID，默认 000000")
    p_login.add_argument("username", nargs="?", default="",
                         help="学号，留空则从配置读取")
    p_login.add_argument("password", nargs="?", default=None,
                         help="密码（不建议在命令行中明文输入）")
    p_login.add_argument("--save-password", action="store_true",
                         help="将密码保存到本地配置文件")
    p_login.add_argument("--force-input", action="store_true",
                         help="忽略已保存的密码，强制手动输入")

    # ---- tasks ----
    p_tasks = sub.add_parser(
        "tasks", help="📝 查看打卡任务列表（自动记住任务 ID）",
        formatter_class=_HELP,
        description="拉取当前所有打卡任务，首次任务 ID 会自动保存到配置中。\n"
                    "后续 detail / checkin / record / month 无需再输 task_id。",
        epilog="示例:\n"
               "  python scripts/cli.py tasks                # 查看任务并自动记住 ID\n"
               "  python scripts/cli.py tasks --no-save      # 仅查看，不保存",
    )
    p_tasks.add_argument("--page", type=int, default=1, help="分页页码，默认第 1 页")
    p_tasks.add_argument("--size", type=int, default=10, help="每页数量，默认 10")
    p_tasks.add_argument("--no-save", action="store_true",
                         help="不自动保存第一个任务的 ID 到配置")

    # ---- detail ----
    p_detail = sub.add_parser(
        "detail", help="🔍 查看任务详情（宿舍坐标、精度上限）",
        formatter_class=_HELP,
        description="获取指定任务的完整信息：宿舍名称、坐标（经纬度）、打卡精度要求、时间窗口。\n"
                    "task_id 可从 tasks 命令获取，留空则使用已保存的任务 ID。",
        epilog="示例:\n"
               "  python scripts/cli.py detail                # 自动使用已保存的任务 ID\n"
               "  python scripts/cli.py detail <任务ID>        # 指定任务 ID",
    )
    p_detail.add_argument("task_id", nargs="?", default="",
                          help="任务 ID，留空则自动从配置中读取")

    # ---- checkin ----
    p_checkin = sub.add_parser(
        "checkin", help="✅ 一键打卡签到（自动模拟 GPS 定位）",
        formatter_class=_HELP,
        description="自动获取宿舍坐标 → 生成随机 GPS 偏移 → 计算距离 → 提交打卡 → 回查确认结果。\n"
                    "如果已打过卡会自动检测并提示。",
        epilog="示例:\n"
               "  python scripts/cli.py checkin                                # 日常打卡\n"
               "  python scripts/cli.py checkin --offset 0.0001                # 减小 GPS 偏移\n"
               "  python scripts/cli.py checkin --force                        # 超出范围强制提交\n"
               "  python scripts/cli.py checkin --late-date 2026-06-01         # 补签指定日期\n"
               "  python scripts/cli.py checkin --lat 28.13 --lng 112.99       # 手动指定坐标",
    )
    p_checkin.add_argument("task_id", nargs="?", default="",
                           help="任务 ID，留空则自动从配置中读取")
    p_checkin.add_argument("--lat", type=float,
                           help="手动指定纬度（覆盖 GPS 模拟）")
    p_checkin.add_argument("--lng", type=float,
                           help="手动指定经度（覆盖 GPS 模拟）")
    p_checkin.add_argument("--offset", type=float, default=0.0003,
                           help="GPS 随机偏移范围（度），默认 0.0003 ≈ 33m")
    p_checkin.add_argument("--force", action="store_true",
                           help="即使模拟坐标超出精度范围也强制提交")
    p_checkin.add_argument("--late-date",
                           help="补签日期，格式 YYYY-mm-dd（如 2026-06-01）")
    p_checkin.add_argument("--file-id",
                           help="附件文件 ID（一般不需要）")

    # ---- record ----
    p_record = sub.add_parser(
        "record", help="📊 查询当日/指定日期的打卡记录",
        formatter_class=_HELP,
        description="查看某一天的打卡状态、坐标、时间。默认查今天。",
        epilog="示例:\n"
               "  python scripts/cli.py record                # 查询今天的打卡状态\n"
               "  python scripts/cli.py record --date 2026-06-01  # 查询指定日期",
    )
    p_record.add_argument("task_id", nargs="?", default="",
                          help="任务 ID，留空则自动从配置中读取")
    p_record.add_argument("--date",
                          help="指定查询日期，格式 YYYY-mm-dd（默认今天）")

    # ---- month ----
    p_month = sub.add_parser(
        "month", help="📅 按月查询打卡记录（含统计汇总）",
        formatter_class=_HELP,
        description="汇总一个月内每天的打卡状态，底部统计正常/迟到/其他天数。",
        epilog="示例:\n"
               "  python scripts/cli.py month 2026-06                      # 查询 2026 年 6 月打卡记录\n"
               "  python scripts/cli.py month 2026-06 --task-id <任务ID>  # 指定任务 ID",
    )
    p_month.add_argument("--task-id", default="",
                         help="任务 ID，留空则自动从配置中读取")
    p_month.add_argument("month",
                         help="月份，格式 YYYY-mm（如 2026-06）")

    return parser


def _show_welcome():
    """Print branded welcome screen when no command is given."""
    print()
    print(c(Style.heading, "  中南林业科技大学  ·  自动晚点名打卡"))
    print(c(Style.muted, "  ───────────────────────────────────────────"))
    print()
    print(c(Style.bold, "  🚀 快速开始（新用户 3 步搞定）"))
    print(f"    {c(Style.info, '1.')}  {c(Style.bold, 'setup')}           交互式配置向导（输入 OpenID + 学号 + 密码）")
    print(f"    {c(Style.info, '2.')}  {c(Style.bold, 'tasks')}          查看打卡任务（自动记住任务 ID）")
    print(f"    {c(Style.info, '3.')}  {c(Style.bold, 'checkin')}        一键打卡签到")
    print()
    print(c(Style.bold, "  📋 日常使用"))
    print(f"    {c(Style.info, 'status')}         查看登录状态 + 今日打卡概况")
    print(f"    {c(Style.info, 'record')}         查询打卡记录")
    print(f"    {c(Style.info, 'month <月>')}     月度汇总统计（如 month 2026-06）")
    print()
    print(c(Style.bold, "  🔧 其他"))
    print(f"    {c(Style.muted, 'login-openid')}    OpenID 登录（需重新登录时）")
    print(f"    {c(Style.muted, 'detail')}         查看任务详情（宿舍坐标 / 精度）")
    print(f"    {c(Style.muted, 'config')}         管理本地配置（查看 / 清除）")
    print()
    print(c(Style.muted, "  💡 提示: 所有命令都支持 --help 查看详细用法"))
    print(c(Style.muted, f"  📁 配置: {CONFIG_FILE}"))
    print()


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        _show_welcome()
        return

    dispatch = {
        "setup": cmd_setup,
        "status": cmd_status,
        "config": cmd_config,
        "login": cmd_login,
        "login-openid": cmd_login_openid,
        "tasks": cmd_tasks,
        "detail": cmd_detail,
        "checkin": cmd_checkin,
        "record": cmd_record,
        "month": cmd_month,
    }

    try:
        dispatch[args.command](args)
    except KeyboardInterrupt:
        print()
        print(c(Style.muted, "  已取消"))
    except Exception as exc:
        print()
        print(c(Style.error, f"  程序异常: {exc}"))


if __name__ == "__main__":
    main()
