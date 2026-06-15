#!/usr/bin/env python3
"""模拟器自动抓取 OpenID 工具

利用 Android 模拟器 + mitmproxy 自动捕获微信小程序 OpenID。
无需 root（使用 Android 6 镜像）或在模拟器自带 root 时自动安装系统证书。

原理：
  1. 通过 ADB 设置模拟器的 HTTP 代理指向本机 mitmproxy
  2. 安装 mitmproxy CA 证书到模拟器（Android 6: 用户证书；Android 7+: adb root 推系统区）
  3. 启动 mitmproxy 加载 capture_addon.py 自动提取 OpenID
  4. 捕获到 OpenID 后自动保存到 ~/.auto_check_in/config.json 并清理

依赖：
  - Android 模拟器运行中且 ADB 可连接
  - 模拟器中已安装微信并登录（首次需手动扫二维码）
  - mitmproxy (pip install mitmproxy)
  - ADB (Android SDK platform-tools，或模拟器自带)

用法：
  python scripts/tools/capture_openid_emulator.py               # 自动模式
  python scripts/tools/capture_openid_emulator.py --check       # 环境检查
  python scripts/tools/capture_openid_emulator.py --port 8888   # 指定端口
  python scripts/tools/capture_openid_emulator.py --cleanup     # 清理代理设置
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CAPTURE_ADDON = PROJECT_ROOT / "scripts" / "capture_addon.py"
CONFIG_FILE = Path.home() / ".auto_check_in" / "config.json"
ADB_COMMANDS = ["adb", "adb.exe"]  # 候选 adb 命令
MITMDUMP_CANDIDATES = [
    "mitmdump", "mitmdump.exe",
    # Python Scripts 目录（pip install 后不在 PATH 的情况）
    str(Path.home() / "AppData" / "Roaming" / "Python" / "Python314" / "Scripts" / "mitmdump.exe"),
    str(Path.home() / "AppData" / "Roaming" / "Python" / "Python313" / "Scripts" / "mitmdump.exe"),
    str(Path.home() / "AppData" / "Roaming" / "Python" / "Python312" / "Scripts" / "mitmdump.exe"),
]


# ── 工具函数 ──────────────────────────────────────────


def _find_adb() -> str | None:
    """查找可用的 adb 可执行文件"""
    for cmd in ADB_COMMANDS:
        which = shutil.which(cmd)
        if which:
            return which
    # 查找 ANDROID_HOME
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk:
        for cmd in ADB_COMMANDS:
            candidate = Path(sdk) / "platform-tools" / cmd
            if candidate.exists():
                return str(candidate)
    return None


def _find_mitmdump() -> str | None:
    """查找可用的 mitmdump 可执行文件"""
    for cmd in MITMDUMP_CANDIDATES:
        which = shutil.which(cmd)
        if which:
            return which
        p = Path(cmd)
        if p.exists():
            return str(p)
    return None


def _adb(args: list[str], timeout: int = 10, serial: str | None = None) -> subprocess.CompletedProcess:
    """执行 adb 命令，返回 CompletedProcess"""
    adb = _find_adb()
    if not adb:
        raise RuntimeError("未找到 adb，请安装 Android SDK platform-tools 或启动模拟器")
    cmd = [adb]
    if serial:
        cmd += ["-s", serial]
    return subprocess.run(cmd + args, capture_output=True, text=True, timeout=timeout)


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


def _get_mitmproxy_cert() -> Path | None:
    """查找 mitmproxy CA 证书路径"""
    candidates = [
        Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem",
        Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.cer",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _cert_hash(pem_path: Path) -> str:
    """计算 Android 系统证书所需的 hash (subject_hash_old)

    优先使用 openssl（正确算法），降级用 Python cryptography 库。
    """
    # 方案 A: openssl
    try:
        result = subprocess.run(
            ["openssl", "x509", "-inform", "PEM", "-subject_hash_old", "-in", str(pem_path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    # 方案 B: Python cryptography
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        data = pem_path.read_bytes()
        cert = x509.load_pem_x509_certificate(data)
        subject_der = cert.subject.public_bytes()
        return hashlib.md5(subject_der).hexdigest()[:8]
    except ImportError:
        pass

    # 方案 C: 退化为 MD5 整个证书（非标准，但部分模拟器接受）
    data = pem_path.read_bytes()
    return hashlib.md5(data).hexdigest()[:8]


# ── 环境检查 ──────────────────────────────────────────


def check_environment() -> bool:
    """检查环境是否就绪，返回 True/False"""
    ok = True

    # 1. ADB
    adb = _find_adb()
    if adb:
        print(f"  [OK] ADB: {adb}")
    else:
        print("  [FAIL] ADB 未找到，请安装 Android SDK platform-tools")
        ok = False

    # 2. ADB devices
    if adb:
        r = _adb(["devices"])
        lines = [l for l in r.stdout.strip().splitlines() if l and not l.startswith("*") and "List" not in l]
        if len(lines) >= 1:
            for l in lines:
                if "device" in l and "offline" not in l:
                    serial = l.split("\t")[0]
                    print(f"  [OK] 模拟器已连接: {serial}")
                    break
            else:
                print("  [FAIL] 未检测到已连接的模拟器（adb devices 为空）")
                ok = False
        else:
            print("  [FAIL] 未检测到已连接的模拟器")
            ok = False

    # 3. mitmproxy
    if _find_mitmdump():
        print(f"  [OK] mitmproxy: {_find_mitmdump()}")
    else:
        print("  [FAIL] mitmproxy 未安装，请运行: pip install mitmproxy")
        ok = False

    # 4. mitmproxy CA 证书
    cert = _get_mitmproxy_cert()
    if cert:
        print(f"  [OK] mitmproxy CA 证书: {cert}")
    else:
        print("  [WARN] mitmproxy CA 证书不存在，启动后将自动生成")

    # 5. capture_addon.py
    if CAPTURE_ADDON.exists():
        print(f"  [OK] capture_addon 插件: {CAPTURE_ADDON}")
    else:
        print(f"  [FAIL] capture_addon 插件不存在: {CAPTURE_ADDON}")
        ok = False

    return ok


# ── 代理管理 ──────────────────────────────────────────


def set_emulator_proxy(ip: str, port: int, serial: str | None = None) -> None:
    """通过 ADB 设置模拟器 HTTP 代理"""
    print(f"  设置模拟器代理 -> {ip}:{port}")
    _adb(["shell", "settings", "put", "global", "http_proxy", f"{ip}:{port}"], serial=serial)


def remove_emulator_proxy(serial: str | None = None) -> None:
    """清除模拟器 HTTP 代理"""
    print("  清除模拟器代理")
    _adb(["shell", "settings", "delete", "global", "http_proxy"], serial=serial)
    _adb(["shell", "settings", "put", "global", "http_proxy", ":0"], serial=serial)


# ── 证书管理 ──────────────────────────────────────────


def install_cert_to_emulator(serial: str | None = None) -> bool:
    """安装 mitmproxy CA 证书到模拟器

    优先级：
      方案 A: adb root → remount → /system/etc/security/cacerts/ (Android 7+ 模拟器, 可写 /system)
      方案 B: adb root → bind mount → /system/etc/security/cacerts/ (Android 12+, /system 只读)
      方案 C: 推送到 /sdcard/, 提示用户手动安装 (Android 6)
    """
    cert_path = _get_mitmproxy_cert()
    if not cert_path:
        print("  mitmproxy CA 证书未生成，先启动一次 mitmproxy 生成...")
        mitmdump = _find_mitmdump()
        if not mitmdump:
            print("  [FAIL] 找不到 mitmdump，请安装 mitmproxy")
            return False
        subprocess.run(
            [mitmdump, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        proc = subprocess.Popen(
            [mitmdump, "-p", "0", "--listen-host", "127.0.0.1"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        proc.terminate()
        time.sleep(1)
        cert_path = _get_mitmproxy_cert()
        if not cert_path:
            print("  [FAIL] 无法生成 mitmproxy CA 证书")
            return False

    print(f"  证书路径: {cert_path}")
    cert_hash = _cert_hash(cert_path)

    # 方案 A: adb root + remount
    root_r = _adb(["root"], serial=serial)
    if root_r.returncode == 0 and "adbd cannot run as root" not in root_r.stderr:
        time.sleep(1)
        r = _adb(["remount"], serial=serial)
        if r.returncode == 0:
            time.sleep(1)
            dest = f"/system/etc/security/cacerts/{cert_hash}.0"
            _adb(["push", str(cert_path), dest], serial=serial)
            _adb(["shell", "chmod", "644", dest], serial=serial)
            print(f"  已将证书安装到系统信任区: {dest}")
            return True

        # 方案 B: remount 失败 → bind mount (Android 12+ 只读 /system)
        print("  remount 失败，尝试 bind mount...")
        _adb(["shell", "mkdir", "-p", "/data/local/tmp/cacerts"], serial=serial)
        _adb(["shell", "cp", "/system/etc/security/cacerts/*", "/data/local/tmp/cacerts/"], serial=serial)
        _adb(["push", str(cert_path), f"/data/local/tmp/cacerts/{cert_hash}.0"], serial=serial)
        _adb(["shell", "chmod", "644", f"/data/local/tmp/cacerts/{cert_hash}.0"], serial=serial)
        b = _adb(["shell", "mount", "-o", "bind", "/data/local/tmp/cacerts", "/system/etc/security/cacerts"], serial=serial)
        if b.returncode == 0:
            print(f"  通过 bind mount 将证书安装到系统信任区: {cert_hash}.0")
            return True
        print("  bind mount 也失败，尝试手动安装...")

    # 方案 C：推送到 /sdcard/ 用户手动安装
    _adb(["push", str(cert_path), "/sdcard/mitmproxy-ca-cert.pem"], serial=serial)
    print("  证书已推送到模拟器 /sdcard/mitmproxy-ca-cert.pem")
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║  请在模拟器中手动安装证书:                      ║")
    print("  ║  设置 -> 安全 -> 从存储设备安装 ->              ║")
    print("  ║  选择 /sdcard/mitmproxy-ca-cert.pem             ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()
    return True


# ── 微信/小程序启动 ──────────────────────────────────


def launch_miniprogram(serial: str | None = None) -> bool:
    """通过 ADB 在模拟器中打开微信打卡小程序

    需要微信已登录且小程序之前打开过（否则 intent 可能失败）。
    返回 True 表示 intent 已发送，False 表示发送失败。
    """
    # 先尝试直接打开小程序（需要 MiniProgram 在微信最近使用列表中有记录）
    r = _adb([
        "shell", "am", "start", "-n",
        "com.tencent.mm/.plugin.appbrand.ui.AppBrandUI",
        "--es", "appid", "wx0e47c34c9982aa09",
    ], serial=serial)
    if r.returncode == 0 and "Error" not in r.stderr:
        print("  已发送启动小程序指令")
        return True

    # 降级：只打开微信
    r = _adb([
        "shell", "monkey", "-p", "com.tencent.mm", "-c",
        "android.intent.category.LAUNCHER", "1",
    ], serial=serial)
    if r.returncode == 0:
        print("  已打开微信，请在微信中手动进入打卡小程序")
        print("  提示: 发现 -> 小程序 -> 搜索「平安打卡」")
        return True

    print("  [WARN] 无法自动打开微信，请在模拟器中手动打开")
    return False


# ── 主流程 ────────────────────────────────────────────


def run_capture(port: int, serial: str | None = None) -> None:
    """主捕获流程"""
    ip = _get_lan_ip()
    print()
    print("=" * 56)
    print("  模拟器自动抓取 OpenID")
    print("=" * 56)
    print()
    print(f"  代理地址: {ip}:{port}")
    if serial:
        print(f"  设备: {serial}")
    print()

    # 1. 检查环境
    if not check_environment():
        sys.exit(1)

    # 2. 安装证书
    print()
    print("  --- 步骤 1/4: 安装 CA 证书 ---")
    if not install_cert_to_emulator(serial=serial):
        sys.exit(1)

    # 3. 设置代理
    print()
    print("  --- 步骤 2/4: 设置代理 ---")
    set_emulator_proxy(ip, port, serial=serial)

    # 4. 启动 mitmproxy
    mitmdump = _find_mitmdump()
    if not mitmdump:
        print("  [FAIL] 找不到 mitmdump，请安装 mitmproxy")
        sys.exit(1)
    print()
    print("  --- 步骤 3/4: 启动 mitmproxy ---")
    print(f"  路径: {mitmdump}")
    print(f"  加载插件: {CAPTURE_ADDON}")
    mitm_proc = subprocess.Popen(
        [mitmdump, "-s", str(CAPTURE_ADDON), "--listen-port", str(port)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True,
    )

    # 5. 打开微信小程序
    print()
    print("  --- 步骤 4/4: 打开小程序 ---")
    launch_miniprogram(serial=serial)
    print()
    print(f"  {'=' * 54}")
    print(f"  等待捕获 OpenID...")
    print(f"  小程序打开后会自动触发 getOpenidByJsCode 请求")
    print(f"  捕获到 OpenID 后 mitmproxy 会自动退出")
    print(f"  {'=' * 54}")
    print()

    # 6. 等待 mitmproxy 退出（addon 捕获后自动 shutdown）
    try:
        mitm_proc.wait(timeout=120)
    except subprocess.TimeoutExpired:
        print("  [TIMEOUT] 120 秒未捕获到 OpenID")
        print("  请确认:")
        print("  - 模拟器中微信已登录")
        print("  - 小程序已正确打开（会触发 getOpenidByJsCode 请求）")
        print("  - CA 证书已安装（安卓 12+ 需要系统证书，已通过 bind mount 安装）")
        print("  - 代理设置正确")
        mitm_proc.kill()
    finally:
        # 清理代理
        remove_emulator_proxy(serial=serial)

    # 7. 检查结果
    if CONFIG_FILE.exists():
        import json
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        openid = cfg.get("openid", "")
        if openid:
            print()
            print("=" * 56)
            print(f"  OpenID 已捕获!")
            print(f"  OpenID: {openid[:4]}***{openid[-4:]}")
            print(f"  已保存到: {CONFIG_FILE}")
            print("=" * 56)
            print()
            print("  下一步: python scripts/cli.py setup")
            return

    print("  未捕获到 OpenID，请检查模拟器网络设置后重试")


# ── 命令行入口 ───────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="模拟器自动抓取 OpenID",
        epilog="示例:\n"
               "  %(prog)s                      # 自动模式\n"
               "  %(prog)s --check              # 环境检查\n"
               "  %(prog)s --port 8888          # 指定端口\n"
               "  %(prog)s --serial 127.0.0.1:7555  # 指定设备序列号\n"
               "  %(prog)s --cleanup            # 清理代理设置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--check", action="store_true", help="仅检查环境，不启动捕获")
    parser.add_argument("--port", type=int, default=8080, help="代理监听端口（默认 8080）")
    parser.add_argument("--serial", type=str, default=None, help="ADB 设备序列号（如 127.0.0.1:7555）")
    parser.add_argument("--cleanup", action="store_true", help="清除模拟器代理设置")
    parser.add_argument("--profile", type=str, default=None,
                        help="保存到哪个账号配置（默认当前账号，如 --profile USER_2）")
    args = parser.parse_args()

    if args.check:
        ok = check_environment()
        sys.exit(0 if ok else 1)

    if args.cleanup:
        remove_emulator_proxy(serial=args.serial)
        print("  模拟器代理已清除")
        return

    # 通过环境变量传递给 capture_addon.py
    if args.profile:
        os.environ["CAPTURE_PROFILE"] = args.profile

    run_capture(args.port, serial=args.serial)


if __name__ == "__main__":
    main()

"""
分支场景总结：

┌─────────────────────┬──────────────────┬─────────────────────────────┐
│ 模拟器类型          │ 证书安装方案      │ 用户操作                   │
├─────────────────────┼──────────────────┼─────────────────────────────┤
│ AVD (adb root 可用) │ 自动推系统区      │ 无需操作                   │
│ MuMu 安卓 6 镜像     │ 推 /sdcard 手动装 │ 设置 > 安全 > 安装证书     │
│ 雷电 安卓 5 镜像     │ 推 /sdcard 手动装 │ 同上                       │
│ Genymotion          │ 自动推系统区      │ 无需操作                   │
│ 任何 Android 7+ 无   │ 不支持（需 root） │ 换 Android 6 镜像或真机    │
│  root 的模拟器       │                  │                             │
└─────────────────────┴──────────────────┴─────────────────────────────┘

路径说明：
  - 捕获 addon:          scripts/capture_addon.py
  - 输出配置文件:         ~/.auto_check_in/config.json
  - 本脚本:              scripts/tools/capture_openid_emulator.py
"""
