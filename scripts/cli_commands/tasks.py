"""tasks — 查看打卡任务列表 + 任务详情"""

from __future__ import annotations

from argparse import Namespace
from src.core.client import ApiClient
from scripts.cli_ui import Style, c, divider, kv, bullet, Spinner
from scripts.cli_config import load_config, save_config, _mask
from scripts.cli_commands._common import get_client, resolve_task_id, token_expired, login_expired_hint


# ═══════════════════════════════════════════════════════════════════════
# cmd_tasks — 任务列表
# ═══════════════════════════════════════════════════════════════════════

def tasks(args: Namespace) -> None:
    """List check-in tasks, auto-save the first task ID."""
    profile = getattr(args, "profile", None)
    client, cfg = get_client(profile=profile)

    spinner = Spinner("正在获取任务列表")
    spinner.start()
    resp = client.get_task_list(current=args.page, size=args.size)
    spinner.stop()

    if token_expired(resp):
        print()
        print(c(Style.error, "  Token 已过期"))
        login_expired_hint()
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
            print(c(Style.success, "  已记住任务 ID，后续命令可省略 task_id"))
    else:
        print()
        print(c(Style.error, f"  获取任务失败: {resp.get('msg', '未知错误')}"))


# ═══════════════════════════════════════════════════════════════════════
# cmd_detail — 任务详情
# ═══════════════════════════════════════════════════════════════════════

def detail(args: Namespace) -> None:
    """Show task detail including dorm coordinates and accuracy limit."""
    profile = getattr(args, "profile", None)
    client, cfg = get_client(profile=profile)
    tid = resolve_task_id(args, cfg)
    if not tid:
        print()
        print(c(Style.error, "  请提供任务 ID，或先运行 tasks"))
        return

    spinner = Spinner("正在获取任务详情")
    spinner.start()
    resp = client.get_task_detail(tid)
    spinner.stop()

    if token_expired(resp):
        print()
        print(c(Style.error, "  Token 已过期"))
        login_expired_hint()
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
        kv("任务ID", _mask(d.get("taskId", "") or tid, 12))
        print()

        print(c(Style.bold, "  宿舍信息"))
        kv("宿舍", f"{dorm.get('dormName', '')} {dorm.get('floorName', '')} {dorm.get('roomNo', '')}")
        kv("坐标", f"({dorm.get('locationLat', '')}, {dorm.get('locationLng', '')})")
        kv("精度上限", f"{d.get('locationAccuracy', '')}m")

        loc_enabled = d.get("openLocate") == 1
        kv("定位校验", c(Style.success, "已开启") if loc_enabled else c(Style.warning, "已关闭"))

        if loc_enabled:
            acc = d.get("locationAccuracy", "N/A")
            print()
            print(c(Style.muted, f"  打卡时模拟坐标与宿舍距离需 < {acc}m"))
    else:
        print()
        print(c(Style.error, f"  获取详情失败: {resp.get('msg', '未知错误')}"))
