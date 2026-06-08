"""setup — 交互式首次配置向导"""

from src.core.client import ApiClient
from scripts.cli_ui import Style, c, divider, bullet
from scripts.cli_config import CONFIG_FILE, save_config, secure_input
from scripts.cli_ui import Spinner


def run(args):
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
