"""capture-openid — 启动 mitmproxy 自动捕获 OpenID"""

from __future__ import annotations

import asyncio
import socket
from argparse import Namespace
from scripts.cli_ui import Style, c, divider, bullet


def _get_lan_ip() -> str:
    """获取本机局域网 IP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def run(args: Namespace) -> None:
    """启动 mitmproxy 代理，自动捕获 OpenID"""
    try:
        from mitmproxy import options
        from mitmproxy.tools import dump
        from mitmproxy.addons import default_addons
        from scripts.capture_addon import OpenIDCapture
    except ImportError:
        print()
        print(c(Style.error, "  mitmproxy 未安装"))
        print()
        bullet("请运行: pip install mitmproxy")
        print()
        return

    port = args.port
    ip = _get_lan_ip()
    profile = getattr(args, "profile", None)

    print()
    divider("OpenID 捕获代理")
    print()
    print(f"  {c(Style.bold, '代理地址')}:  {ip}:{port}")
    if profile:
        print(f"  {c(Style.bold, '目标账号')}:  {profile}")
    print()
    print(f"  {c(Style.heading, '手机设置步骤')}")
    print()
    print(f"  {c(Style.info, '1.')} 手机连上同一 WiFi（与电脑同网络）")
    print(f"  {c(Style.info, '2.')} 设置 WiFi 代理为 {c(Style.bold, f'{ip}:{port}')}")
    print(f"  {c(Style.info, '3.')} 手机浏览器访问 {c(Style.bold, 'mitm.it')} 下载安装 CA 证书")
    print(f"     {c(Style.warning, '⚠ Android 7+ 必须将证书移到系统信任区（需 root）')}")
    print(f"     {c(Style.muted, '   无 root → 换 Reqable 方案（详见 docs/reference/认证流程与抓包分析.md）')}")
    print(f"  {c(Style.info, '4.')} 打开微信 → 进入打卡小程序")
    print()
    print(f"  {c(Style.muted, '代理启动后会自动等待捕获  ·  Ctrl+C 退出')}")
    print()

    async def _start():
        opts = options.Options(
            listen_host="0.0.0.0",
            listen_port=port,
        )
        master = dump.DumpMaster(opts)
        master.addons.add(default_addons())
        master.addons.add(OpenIDCapture(profile=profile))
        await master.run()

    try:
        asyncio.run(_start())
    except KeyboardInterrupt:
        print()
        print(c(Style.muted, "  已退出"))
