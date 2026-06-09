"""auth — OpenID 登录 + 密码登录 + WebVPN 登录"""

from src.core.client import ApiClient
from scripts.cli_ui import Style, c, bullet, kv, Spinner
from scripts.cli_config import load_config, save_config, get_password, secure_input, _mask


def login_openid(args):
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
    resp = client.sign_in_openid(args.tenant, openid, username, password, args.bind)
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


def login(args):
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
            "登录失败: " + resp.get("error_description", resp.get("msg", "未知错误")),
            ok=False,
        )


def login_webvpn(args):
    """WebVPN 登录 — 从浏览器拷 token 验证并保存

    从 WebVPN 平安打卡页面的 API 请求头 flysource-auth 中复制 access_token
    验证有效后自动保存到配置。
    """
    cfg = load_config()
    token = args.token or ""

    if not token:
        print()
        print(c(Style.error, "  请提供 access_token"))
        print(c(Style.muted, "  在 WebVPN 打卡页 F12 → Network → 任意 API 请求"))
        print(c(Style.muted, "  从 Request Headers 中复制 flysource-auth 的值"))
        return

    if not token.startswith("bearer ") and not token.startswith("Bearer "):
        token = "bearer " + token

    username = args.username or cfg.get("username", "")
    if not username:
        print()
        username = input("  学号: ").strip()

    print()
    bullet("正在验证 token ...")
    client = ApiClient(token=token, client_mode="web")
    try:
        tasks = client.get_task_list(size=1)
    except Exception as exc:
        print()
        bullet(f"验证失败: 网络错误或 token 无效 — {exc}", ok=False)
        return

    if tasks.get("success") or tasks.get("code") == 200 or tasks.get("data"):
        cfg["token"] = token
        cfg["username"] = username
        cfg["tenant_id"] = "000000"
        cfg["client_mode"] = "web"
        save_config(cfg)
        print()
        bullet("token 验证成功")
        kv("学号", _mask(username, 3))
        kv("Token", _mask(token, 8))
        print()
        print(c(Style.muted, "  下一步: python scripts/cli.py tasks"))
    else:
        err = tasks.get("msg", "token 无效或已过期")
        print()
        bullet(f"验证失败: {err}", ok=False)
        print(c(Style.muted, "  请重新从 WebVPN 页面复制 flysource-auth 的值"))
