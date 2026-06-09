"""config — 查看或清除本地配置"""

from datetime import datetime
from scripts.cli_ui import Style, c, divider, kv
from scripts.cli_config import CONFIG_FILE, load_config, save_config, get_password, _mask


def run(args):
    """View or clear local configuration."""
    cfg = load_config()
    action = getattr(args, "action", "show")

    if action == "clear":
        if args.all:
            print()
            print(c(Style.warning, "  即将清除全部配置: 学号 / OpenID / 密码 / token"))
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
    kv("客户端模式", "WebVPN" if cfg.get("client_mode") == "web" else "微信小程序")
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
