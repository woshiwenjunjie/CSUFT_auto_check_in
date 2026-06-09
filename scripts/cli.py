#!/usr/bin/env python3
"""
Auto Check-In CLI —— 中南林业科技大学自动晚点名打卡工具

Commands:
  setup            交互式首次配置向导（推荐新用户使用）
  status           查看登录状态、任务信息、今日打卡记录
  config           查看或管理本地配置（show / clear）
  login-openid     OpenID 登录（推荐方式）
  login            密码登录（备用）
  tasks            查看打卡任务列表（自动记住任务 ID）
  detail           查看任务详情（含宿舍坐标、精度上限）
  checkin          一键打卡签到（自动模拟 GPS 偏移）
  record           查询当日打卡状态
  month            按月查询打卡记录
   capture-openid   启动 mitmproxy 自动捕获 OpenID（无需手动翻包）
   login-webvpn    WebVPN 登录（从浏览器复制 token，绕过 OpenID）

配置文件:  ~/.auto_check_in/config.json
文档:      docs/guides/user/CLI教程.md
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force UTF-8 output on Windows — Python may otherwise inherit GBK
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scripts.cli_ui import Style, c
from scripts.cli_config import CONFIG_FILE
from scripts.cli_commands.setup import run as cmd_setup
from scripts.cli_commands.status import run as cmd_status
from scripts.cli_commands.config_cmd import run as cmd_config
from scripts.cli_commands.auth import login_openid as cmd_login_openid, login as cmd_login, login_webvpn as cmd_login_webvpn
from scripts.cli_commands.tasks import tasks as cmd_tasks, detail as cmd_detail
from scripts.cli_commands.checkin import checkin as cmd_checkin, record as cmd_record, month as cmd_month
from scripts.cli_commands.capture import run as cmd_capture


# ═══════════════════════════════════════════════════════════════════════
# Argparse skeleton
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

    _HLP = argparse.RawDescriptionHelpFormatter

    # ---- setup ----
    sub.add_parser(
        "setup", help="🌟 交互式首次配置向导（强烈推荐新用户使用）",
        formatter_class=_HLP,
        description="4 步完成配置：输入 OpenID → 学号 → 密码 → 自动验证登录",
        epilog="示例:\n  python scripts/cli.py setup",
    )

    # ---- status ----
    sub.add_parser(
        "status", help="📋 查看登录状态、任务信息、今日打卡记录",
        formatter_class=_HLP,
        description="一次命令同时查看：配置概况 / 登录是否有效 / 当前任务 / 今日是否已打卡",
        epilog="示例:\n  python scripts/cli.py status\n\n这是每天打开终端后最常用的命令。",
    )

    # ---- config ----
    p_cfg = sub.add_parser(
        "config", help="⚙️  查看或清除本地配置",
        formatter_class=_HLP,
        description="管理 ~/.auto_check_in/config.json 中的凭据信息。\n凭据显示均已脱敏，保护隐私。",
        epilog="示例:\n  python scripts/cli.py config              # 查看配置\n"
               "  python scripts/cli.py config clear         # 清除 token\n"
               "  python scripts/cli.py config clear --all   # 清除全部",
    )
    p_cfg.add_argument("action", nargs="?", default="show", choices=["show", "clear"],
                       help="show = 查看当前配置（凭据已脱敏）  |  clear = 清除指定内容")
    p_cfg.add_argument("--all", action="store_true", help="清除全部配置：学号 / OpenID / 密码 / Token")
    p_cfg.add_argument("--password", action="store_true", help="仅清除已保存的密码")

    # ---- login-openid ----
    p_openid = sub.add_parser(
        "login-openid", help="🔑 OpenID 登录（推荐方式，无需验证码）",
        formatter_class=_HLP,
        description="用微信 OpenID 换取 access_token，一次登录后 credential 自动保存。\n"
                    "支持从配置文件自动读取已保存的凭据。",
        epilog="示例:\n  python scripts/cli.py login-openid oXXXX... 2023XXXXXX\n"
               "  python scripts/cli.py login-openid               # 从配置读取凭据\n"
               "  python scripts/cli.py login-openid --save-password\n"
               "  python scripts/cli.py login-openid --bind 0       # 仅登录不绑定",
    )
    p_openid.add_argument("--tenant", default="000000", help="学校租户 ID，默认 000000（中南林业科技大学）")
    p_openid.add_argument("openid", nargs="?", default="", help="微信 OpenID（o 开头约 28 位），留空则从配置读取")
    p_openid.add_argument("username", nargs="?", default="", help="学号，留空则从配置读取")
    p_openid.add_argument("password", nargs="?", default=None, help="密码（不建议在命令行中明文输入）")
    p_openid.add_argument("--bind", type=int, default=1, choices=[0, 1],
                          help="0 = 仅登录不绑定  |  1 = 绑定 OpenID 与学号（默认）")
    p_openid.add_argument("--save-password", action="store_true", help="将密码保存到本地配置文件")
    p_openid.add_argument("--force-input", action="store_true", help="忽略已保存的密码，强制手动输入")

    # ---- login-webvpn ----
    p_webvpn = sub.add_parser(
        "login-webvpn", help="🌐 WebVPN 登录（从浏览器复制 token，绕过 OpenID 抓包）",
        formatter_class=_HLP,
        description="将 WebVPN 打卡页 API 请求的 flysource-auth 值粘贴进来，\n"
                    "验证有效后自动保存到配置。从此告别 OpenID 抓包。",
        epilog="示例:\n"
               "  python scripts/cli.py login-webvpn \"bearer eyJ...\"\n"
               "  python scripts/cli.py login-webvpn \"bearer eyJ...\" 2023XXXXXX",
    )
    p_webvpn.add_argument("token", help="从 WebVPN 页面 API 请求头 flysource-auth 复制的值")
    p_webvpn.add_argument("username", nargs="?", default="", help="学号，留空则从配置读取")

    # ---- login ----
    p_login = sub.add_parser(
        "login", help="🔐 密码登录（备用方案，需验证码）",
        formatter_class=_HLP,
        description="用学号 + 密码直接登录。需要先获取验证码。",
        epilog="示例:\n  python scripts/cli.py login 2023XXXXXX",
    )
    p_login.add_argument("--tenant", default="000000", help="学校租户 ID，默认 000000")
    p_login.add_argument("username", nargs="?", default="", help="学号，留空则从配置读取")
    p_login.add_argument("password", nargs="?", default=None, help="密码")
    p_login.add_argument("--save-password", action="store_true", help="将密码保存到本地配置文件")
    p_login.add_argument("--force-input", action="store_true", help="忽略已保存的密码，强制手动输入")

    # ---- tasks ----
    p_tasks = sub.add_parser(
        "tasks", help="📝 查看打卡任务列表（自动记住任务 ID）",
        formatter_class=_HLP,
        description="拉取当前所有打卡任务，首次任务 ID 会自动保存到配置中。",
        epilog="示例:\n  python scripts/cli.py tasks\n  python scripts/cli.py tasks --no-save",
    )
    p_tasks.add_argument("--page", type=int, default=1, help="分页页码，默认第 1 页")
    p_tasks.add_argument("--size", type=int, default=10, help="每页数量，默认 10")
    p_tasks.add_argument("--no-save", action="store_true", help="不自动保存第一个任务的 ID 到配置")

    # ---- detail ----
    p_detail = sub.add_parser(
        "detail", help="🔍 查看任务详情（宿舍坐标、精度上限）",
        formatter_class=_HLP,
        description="获取指定任务的完整信息：宿舍名称、坐标、精度要求、时间窗口。",
        epilog="示例:\n  python scripts/cli.py detail\n  python scripts/cli.py detail <任务ID>",
    )
    p_detail.add_argument("task_id", nargs="?", default="", help="任务 ID，留空则自动从配置中读取")

    # ---- checkin ----
    p_checkin = sub.add_parser(
        "checkin", help="✅ 一键打卡签到（自动模拟 GPS 定位）",
        formatter_class=_HLP,
        description="自动获取宿舍坐标 → 生成随机 GPS 偏移 → 计算距离 → 提交打卡 → 回查确认。",
        epilog="示例:\n  python scripts/cli.py checkin\n"
               "  python scripts/cli.py checkin --offset 0.0001\n"
               "  python scripts/cli.py checkin --force\n"
               "  python scripts/cli.py checkin --late-date 2026-06-01\n"
               "  python scripts/cli.py checkin --lat 28.13 --lng 112.99",
    )
    p_checkin.add_argument("task_id", nargs="?", default="", help="任务 ID，留空则自动从配置中读取")
    p_checkin.add_argument("--lat", type=float, help="手动指定纬度")
    p_checkin.add_argument("--lng", type=float, help="手动指定经度")
    p_checkin.add_argument("--offset", type=float, default=0.0003, help="GPS 随机偏移范围（度），默认 0.0003 ≈ 33m")
    p_checkin.add_argument("--force", action="store_true", help="超出精度范围也强制提交")
    p_checkin.add_argument("--late-date", help="补签日期，格式 YYYY-mm-dd")
    p_checkin.add_argument("--file-id", help="附件文件 ID（一般不需要）")

    # ---- record ----
    p_record = sub.add_parser(
        "record", help="📊 查询当日/指定日期的打卡记录",
        formatter_class=_HLP,
        description="查看某一天的打卡状态、坐标、时间。默认查今天。",
        epilog="示例:\n  python scripts/cli.py record\n  python scripts/cli.py record --date 2026-06-01",
    )
    p_record.add_argument("task_id", nargs="?", default="", help="任务 ID，留空则自动从配置中读取")
    p_record.add_argument("--date", help="指定查询日期，格式 YYYY-mm-dd（默认今天）")

    # ---- month ----
    p_month = sub.add_parser(
        "month", help="📅 按月查询打卡记录（含统计汇总）",
        formatter_class=_HLP,
        description="汇总一个月内每天的打卡状态，底部统计正常/迟到/其他天数。",
        epilog="示例:\n  python scripts/cli.py month 2026-06\n"
               "  python scripts/cli.py month 2026-06 --task-id <任务ID>",
    )
    p_month.add_argument("--task-id", default="", help="任务 ID，留空则自动从配置中读取")
    p_month.add_argument("month", help="月份，格式 YYYY-mm（如 2026-06）")

    # ---- capture-openid ----
    p_cap = sub.add_parser(
        "capture-openid", help="🌐 启动 mitmproxy 自动捕获 OpenID（无需手动翻找）",
        formatter_class=_HLP,
        description="启动 mitmproxy 代理，手机设代理后打开小程序即可自动捕获 OpenID。",
        epilog="示例:\n  python scripts/cli.py capture-openid\n"
               "  python scripts/cli.py capture-openid --port 8888",
    )
    p_cap.add_argument("--port", type=int, default=8080, help="代理监听端口，默认 8080")

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
    print(f"    {c(Style.info, 'login-webvpn')}    🌐 WebVPN 登录（从浏览器复制 token，绕过 OpenID）")
    print(f"    {c(Style.info, 'capture-openid')}  🌐 自动捕获 OpenID（mitmproxy）")
    print(f"    {c(Style.muted, 'login-openid')}   OpenID 登录（需重新登录时）")
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
        "login-webvpn": cmd_login_webvpn,
        "tasks": cmd_tasks,
        "detail": cmd_detail,
        "checkin": cmd_checkin,
        "record": cmd_record,
        "month": cmd_month,
        "capture-openid": cmd_capture,
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
