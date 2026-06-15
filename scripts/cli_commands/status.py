"""status — 查看登录状态、任务信息、今日打卡记录"""

from __future__ import annotations

from argparse import Namespace
from datetime import datetime
from src.core.client import ApiClient
from scripts.cli_ui import Style, c, divider, kv, bullet, _status_display, Spinner
from scripts.cli_config import CONFIG_FILE, load_config, get_password, _mask
from scripts.cli_commands._common import token_expired, login_expired_hint


def run(args: Namespace) -> None:
    """Show login status, current task, and today's check-in record."""
    profile = getattr(args, "profile", None)
    cfg = load_config(profile=profile)

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

    if token_expired(resp):
        bullet("登录状态: Token 已过期", ok=False)
        login_expired_hint(profile=getattr(args, "profile", None))
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
            kv("时间", f"{task.get('signStartTime', '')} — {task.get('signEndTime', '')}")

            if task_id:
                today = datetime.now().strftime("%Y-%m-%d")
                rec = client.get_one_record(task_id, today)
                print()
                if token_expired(rec):
                    bullet("登录状态: Token 已过期", ok=False)
                    login_expired_hint()
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
