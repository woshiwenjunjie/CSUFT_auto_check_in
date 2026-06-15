#!/usr/bin/env python3
"""
Auto Check-In CLI —— CSUFT自动晚点名打卡工具

架构：argparse + 子命令 dispatch 模式。每个子命令为独立模块
在 scripts/cli_commands/ 下实现 run(args) 函数，cli.py 负责路由。

Available commands:
  setup         交互式首次配置向导（推荐新用户使用）
  status        查看登录状态、任务信息、今日打卡记录
  config        查看或管理本地配置（show / clear）
  login-openid  OpenID 登录（推荐方式）
  tasks         查看打卡任务列表（自动记住任务 ID）
  detail        查看任务详情（含宿舍坐标、精度上限）
  checkin       一键打卡签到（含 --record / --month 查询）
  capture-openid 启动 mitmproxy 自动捕获 OpenID
  login-webvpn  WebVPN 登录（绕过 OpenID）

配置文件:  ~/.auto_check_in/config.json
文档:      docs/guides/user/CLI教程.md

Variable naming: All names must be meaningful and context-relevant.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force UTF-8 output on Windows — Python may otherwise inherit GBK
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scripts.cli_ui import Style, c
from scripts.cli_config import CONFIG_FILE, list_profiles, switch_profile
from scripts.cli_commands.setup import run as cmd_setup
from scripts.cli_commands.status import run as cmd_status
from scripts.cli_commands.config_cmd import run as cmd_config
from scripts.cli_commands.auth import login_openid as cmd_login_openid, login_webvpn as cmd_login_webvpn
from scripts.cli_commands.config_sync import run as cmd_config_sync
from scripts.cli_commands.tasks import tasks as cmd_tasks, detail as cmd_detail
from scripts.cli_commands.checkin import checkin as checkin_checkin, record as checkin_record, month as checkin_month
from scripts.cli_commands.capture import run as cmd_capture


# ═══════════════════════════════════════════════════════════════════════
# Argparse skeleton
# ═══════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="python scripts/cli.py",
        description="CSUFT自动晚点名打卡工具\n\n"
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

    # 全局可选参数：--profile
    _profile_parent = argparse.ArgumentParser(add_help=False)
    profiles_avail = list_profiles()
    profile_help = f"账号配置名称（默认 default）"
    if profiles_avail:
        profile_help += f"  · 已有: {', '.join(profiles_avail)}"
    _profile_parent.add_argument(
        "--profile", type=str, default=None, help=profile_help,
    )

    # ---- setup ----
    sub.add_parser(
        "setup", help="🌟 交互式首次配置向导（强烈推荐新用户使用）",
        parents=[_profile_parent],
        formatter_class=_HLP,
        description="4 步完成配置：输入 OpenID → 学号 → 密码 → 自动验证登录",
        epilog="示例:\n  python scripts/cli.py setup\n  python scripts/cli.py setup --profile USER_2",
    )

    # ---- status ----
    sub.add_parser(
        "status", help="📋 查看登录状态、任务信息、今日打卡记录",
        parents=[_profile_parent],
        formatter_class=_HLP,
        description="一次命令同时查看：配置概况 / 登录是否有效 / 当前任务 / 今日是否已打卡",
        epilog="示例:\n  python scripts/cli.py status\n  python scripts/cli.py status --profile USER_2",
    )

    # ---- config ----
    p_cfg = sub.add_parser(
        "config", help="⚙️  查看或清除本地配置",
        parents=[_profile_parent],
        formatter_class=_HLP,
        description="管理 ~/.auto_check_in/config.json 中的凭据信息。\n凭据显示均已脱敏，保护隐私。",
        epilog=                "示例:\n  python scripts/cli.py config                 # 查看配置\n"
               "  python scripts/cli.py config show                  # 查看当前 profile\n"
               "  python scripts/cli.py config profile USER_2        # 切换 profile\n"
               "  python scripts/cli.py config profile list          # 列出所有 profile\n"
               "  python scripts/cli.py config clear                 # 清除 token\n"
               "  python scripts/cli.py config clear --all           # 清除全部\n"
               "  python scripts/cli.py config sync                   # 同步到 password.txt + SCF 环境变量",
    )
    p_cfg.add_argument("action", nargs="?", default="show",
                       choices=["show", "clear", "profile", "sync"],
                       help="show = 查看配置  |  clear = 清除指定内容  |  profile = 切换/列出账号  |  sync = 同步到 password.txt 和 SCF 环境变量")
    p_cfg.add_argument("--all", action="store_true", help="清除全部配置：学号 / OpenID / 密码 / Token")
    p_cfg.add_argument("--password", action="store_true", help="仅清除已保存的密码")
    p_cfg.add_argument("name", nargs="?", default="", help="profile 名称（用于 profile 子命令）")

    # ---- login-openid ----
    p_openid = sub.add_parser(
        "login-openid", help="🔑 OpenID 登录（推荐方式，无需验证码）",
        parents=[_profile_parent],
        formatter_class=_HLP,
        description="用微信 OpenID 换取 access_token，一次登录后 credential 自动保存。\n"
                    "支持 --bind 0 免密码登录（适用于已绑定账号）。",
        epilog="示例:\n  python scripts/cli.py login-openid oXXXX... 2023XXXXXX\n"
               "  python scripts/cli.py login-openid               # 从配置读取凭据\n"
               "  python scripts/cli.py login-openid --bind 0       # 免密码登录（已绑定账号）\n"
               "  python scripts/cli.py login-openid --profile USER_2 --bind 0\n"
               "  python scripts/cli.py login-openid --profile USER_N --username 2023XXXXXX --bind 0  # 新用户",
    )
    p_openid.add_argument("--tenant", default="000000", help="学校租户 ID，默认 000000（CSUFT）")
    p_openid.add_argument("openid", nargs="?", default="", help="微信 OpenID（o 开头约 28 位），留空则从配置读取")
    p_openid.add_argument("username", nargs="?", default="", help="学号，留空则从配置读取（或用 --username 标志）")
    p_openid.add_argument("password", nargs="?", default=None, help="密码（不建议在命令行中明文输入）")
    p_openid.add_argument("--bind", type=int, default=1, choices=[0, 1],
                          help="0 = 仅登录不绑定（已绑账号免密码） | 1 = 绑定 OpenID 与学号（默认）")
    p_openid.add_argument("--username", "--user", dest="username_flag", default="",
                          help="学号（可替代位置参数，适用于 OpenID 已在配置中的场景）")
    p_openid.add_argument("--save-password", action="store_true", help="将密码保存到本地配置文件")
    p_openid.add_argument("--force-input", action="store_true", help="忽略已保存的密码，强制手动输入")

    # ---- login-webvpn ----
    p_webvpn = sub.add_parser(
        "login-webvpn", help="🌐 WebVPN 登录（从浏览器复制 token，绕过 OpenID 抓包）",
        parents=[_profile_parent],
        formatter_class=_HLP,
        description="将 WebVPN 打卡页 API 请求的 flysource-auth 值粘贴进来，\n"
                    "验证有效后自动保存到配置。从此告别 OpenID 抓包。",
        epilog="示例:\n"
               "  python scripts/cli.py login-webvpn \"bearer eyJ...\"\n"
               "  python scripts/cli.py login-webvpn \"bearer eyJ...\" 2023XXXXXX\n"
               "  python scripts/cli.py login-webvpn --profile USER_2",
    )
    p_webvpn.add_argument("token", help="从 WebVPN 页面 API 请求头 flysource-auth 复制的值")
    p_webvpn.add_argument("username", nargs="?", default="", help="学号，留空则从配置读取")

    # ---- tasks ----
    p_tasks = sub.add_parser(
        "tasks", help="📝 查看打卡任务列表（自动记住任务 ID）",
        parents=[_profile_parent],
        formatter_class=_HLP,
        description="拉取当前所有打卡任务，首次任务 ID 会自动保存到配置中。",
        epilog="示例:\n  python scripts/cli.py tasks\n  python scripts/cli.py tasks --no-save\n  python scripts/cli.py tasks --profile USER_2",
    )
    p_tasks.add_argument("--page", type=int, default=1, help="分页页码，默认第 1 页")
    p_tasks.add_argument("--size", type=int, default=10, help="每页数量，默认 10")
    p_tasks.add_argument("--no-save", action="store_true", help="不自动保存第一个任务的 ID 到配置")

    # ---- detail ----
    p_detail = sub.add_parser(
        "detail", help="🔍 查看任务详情（宿舍坐标、精度上限）",
        parents=[_profile_parent],
        formatter_class=_HLP,
        description="获取指定任务的完整信息：宿舍名称、坐标、精度要求、时间窗口。",
        epilog="示例:\n  python scripts/cli.py detail\n  python scripts/cli.py detail <任务ID>\n  python scripts/cli.py detail --profile USER_2",
    )
    p_detail.add_argument("task_id", nargs="?", default="", help="任务 ID，留空则自动从配置中读取")

    # ---- checkin ----
    p_checkin = sub.add_parser(
        "checkin", help="✅ 一键打卡签到（自动模拟 GPS 定位）",
        parents=[_profile_parent],
        formatter_class=_HLP,
        description="自动获取宿舍坐标 → 生成随机 GPS 偏移 → 计算距离 → 提交打卡 → 回查确认。",
        epilog="示例:\n  python scripts/cli.py checkin\n"
               "  python scripts/cli.py checkin --offset 0.0001\n"
               "  python scripts/cli.py checkin --force\n"
               "  python scripts/cli.py checkin --late-date 2026-06-01\n"
               "  python scripts/cli.py checkin --lat 28.13 --lng 112.99\n"
               "  python scripts/cli.py checkin --profile USER_2\n"
               "  python scripts/cli.py checkin --profiles default,USER_2  # 批量两个账号",
    )
    p_checkin.add_argument("task_id", nargs="?", default="", help="任务 ID，留空则自动从配置中读取")
    p_checkin.add_argument("--lat", type=float, help="手动指定纬度")
    p_checkin.add_argument("--lng", type=float, help="手动指定经度")
    p_checkin.add_argument("--offset", type=float, default=0.0003, help="GPS 随机偏移范围（度），默认 0.0003 ≈ 33m")
    p_checkin.add_argument("--force", action="store_true", help="超出精度范围也强制提交")
    p_checkin.add_argument("--late-date", help="补签日期，格式 YYYY-mm-dd")
    p_checkin.add_argument("--file-id", help="附件文件 ID（一般不需要）")
    p_checkin.add_argument("--profiles", type=str, default=None,
                           help="批量打卡多个账号，逗号分隔（如 default,USER_2），覆盖 --profile")
    p_checkin.add_argument(
        "--record", nargs="?", const="", default=None,
        metavar="TASK_ID",
        help="查询当日打卡记录（可选指定 task_id）",
    )
    p_checkin.add_argument(
        "--month", nargs="?", const=None, default=None,
        metavar="YYYY-MM",
        help="查询月度打卡统计（如 --month 2026-06）",
    )

    # ---- capture-openid ----
    p_cap = sub.add_parser(
        "capture-openid", help="🌐 启动 mitmproxy 自动捕获 OpenID（无需手动翻找）",
        parents=[_profile_parent],
        formatter_class=_HLP,
        description="启动 mitmproxy 代理，手机设代理后打开小程序即可自动捕获 OpenID。\n"
                    "支持 --profile 指定保存到哪个账号（默认当前账号）。",
        epilog="示例:\n  python scripts/cli.py capture-openid\n"
               "  python scripts/cli.py capture-openid --port 8888\n"
               "  python scripts/cli.py capture-openid --profile USER_2",
    )
    p_cap.add_argument("--port", type=int, default=8080, help="代理监听端口，默认 8080")

    return parser


def _show_welcome() -> None:
    """Print branded welcome screen when no command is given."""
    print()
    print(c(Style.heading, "  CSUFT  ·  自动晚点名打卡"))
    print(c(Style.muted, "  ───────────────────────────────────────────"))
    print()
    print(c(Style.bold, "  🚀 快速开始（新用户 3 步搞定）"))
    print(f"    {c(Style.info, '1.')}  {c(Style.bold, 'setup')}           交互式配置向导（输入 OpenID + 学号 + 密码）")
    print(f"    {c(Style.info, '2.')}  {c(Style.bold, 'tasks')}          查看打卡任务（自动记住任务 ID）")
    print(f"    {c(Style.info, '3.')}  {c(Style.bold, 'checkin')}        一键打卡签到")
    print()
    print(c(Style.bold, "  📋 日常使用"))
    print(f"    {c(Style.info, 'status')}         查看登录状态 + 今日打卡概况")
    print(f"    {c(Style.info, 'checkin --record')}   查询打卡记录")
    print(f"    {c(Style.info, 'checkin --month <月>')} 月度汇总统计（如 --month 2026-06）")
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


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        _show_welcome()
        return

    def _dispatch_checkin(args):
        if getattr(args, "month", None) is not None:
            return checkin_month(args)
        if getattr(args, "record", None) is not None:
            return checkin_record(args)
        return checkin_checkin(args)

    dispatch = {
        "setup": cmd_setup,
        "status": cmd_status,
        "config": cmd_config,
        "login-openid": cmd_login_openid,
        "login-webvpn": cmd_login_webvpn,
        "tasks": cmd_tasks,
        "detail": cmd_detail,
        "checkin": _dispatch_checkin,
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
