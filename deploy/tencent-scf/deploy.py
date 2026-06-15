#!/usr/bin/env python3
"""腾讯云 SCF 一键打包部署脚本

将 SCF 函数代码打包为 zip 并通过 SCF CLI 上传到腾讯云。支持多种模式：
  1. python deploy/tencent-scf/deploy.py                       打包 + 部署 + 创建触发器
  2. python deploy/tencent-scf/deploy.py --dry-run             仅打包，不上传
  3. python deploy/tencent-scf/deploy.py --invoke              部署后立即触发测试
  4. python deploy/tencent-scf/deploy.py gen-env               从 config.json 生成环境变量 JSON
  5. python deploy/tencent-scf/deploy.py --env-json scf_env.json  部署时附带环境变量

打包结构:
    scf_package.zip/
    ├── handler.py          # SCF 入口
    ├── checkin.py          # 打卡编排逻辑（共享模块）
    ├── requirements.txt    # pip 依赖
    ├── src/
    │   ├── __init__.py
    │   ├── core/
    │   │   ├── __init__.py
    │   │   └── client.py   # ApiClient（8 个学校 API）
    │   └── utils/
    │       ├── __init__.py
    │       ├── crypto.py   # MD5 / Base64
    │       ├── sign.py     # FlySource 签名
    │       └── geo.py      # Haversine 距离 + GPS 偏移
    └── <pip packages>      # httpx, certifi, httpcore, h11 等

前置条件:
    1. 安装 SCF CLI: npm install -g @scf/cli
    2. 配置密钥: scf configure --region ap-guangzhou
    3. Python 环境已激活（依赖安装需要）

配置常量:
    FUNCTION_NAME   SCF 函数名（默认 CSUFT_AutoCheckIn）
    REGION          部署地域（默认 ap-guangzhou 广州）
    TIMER_CRON      定时 Cron 表达式（默认 "0 5 21 * * ? *"，北京时间，7 字段格式含秒+年）
    RUNTIME         Python 运行时版本（SCF 最高支持 Python3.10，
                    可通过 SCF_RUNTIME 环境变量覆盖）
    注意:           SCF 控制台 Cron 默认使用北京时间（UTC+8），
                    无需额外转换。

错误处理:
    - build_package(): try/except/finally 三明治 — pip 失败时清理临时目录
    - main(): 捕获 RuntimeError/OSError，sys.exit(1) 避免继续部署
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
from scripts.cli_config import CONFIG_FILE
FUNCTION_NAME = "CSUFT_AutoCheckIn"
REGION = "ap-guangzhou"
TIMER_CRON = "0 5 21 * * ? *"
RUNTIME = os.environ.get("SCF_RUNTIME", "Python3.10")


def _fmt_size(path: Path) -> str:
    size_kb = path.stat().st_size / 1024
    if size_kb >= 1024:
        return f"{size_kb / 1024:.1f} MB"
    return f"{size_kb:.0f} KB"


def build_package() -> str:
    """复制必要文件到临时目录并打包 zip"""
    build_dir = Path(tempfile.mkdtemp())
    output_zip = SCRIPT_DIR / "scf_package.zip"

    try:
        print("[1/4] 复制入口文件...")
        for f in ["handler.py", "checkin.py"]:
            shutil.copy2(SCRIPT_DIR / f, build_dir / f)

        print("[2/4] 复制核心库...")
        target_src_dir = build_dir / "src"
        for subdir in ["", "core", "utils"]:
            (target_src_dir / subdir).mkdir(parents=True, exist_ok=True)
        for pkg_file in ["__init__.py"]:
            shutil.copy2(PROJECT_DIR / "src" / pkg_file, target_src_dir / pkg_file)
        for pkg_file in ["__init__.py", "client.py", "token_client.py", "sign_builder.py"]:
            shutil.copy2(PROJECT_DIR / "src/core" / pkg_file, target_src_dir / "core" / pkg_file)
        for pkg_file in ["__init__.py", "crypto.py", "sign.py", "geo.py", "notification.py"]:
            shutil.copy2(PROJECT_DIR / "src/utils" / pkg_file, target_src_dir / "utils" / pkg_file)

        print("[3/4] 安装 pip 依赖...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r",
             str(SCRIPT_DIR / "requirements.txt"), "-t", str(build_dir)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  ❌ pip install 失败:\n{result.stderr}")
            raise RuntimeError("pip install 失败")

        print("[4/4] 打包...")
        if output_zip.exists():
            output_zip.unlink()
        shutil.make_archive(str(output_zip.with_suffix("")), "zip", build_dir)

        print(f"  → {output_zip.name} ({_fmt_size(output_zip)})")
        return str(output_zip)
    except Exception:
        if output_zip.exists():
            output_zip.unlink()
        raise
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


def deploy_scf(zip_path: str, dry_run: bool = False, env_cli_arg: list[str] | None = None) -> None:
    """通过 SCF CLI 更新或创建函数"""
    if dry_run:
        print(f"\n[部署] DRY RUN — 跳过上传")
        print(f"  函数名: {FUNCTION_NAME}")
        print(f"  地域:   {REGION}")
        print(f"  运行时: {RUNTIME}")
        print(f"  定时:   {TIMER_CRON} (北京时间)")
        print(f"  入口:   handler.main_handler")
        print(f"  包:     {zip_path}")
        if env_cli_arg:
            print(f"  环境变量: 已配置 {len(env_cli_arg[1])} 个")
        print(f"\n  手动上传: SCF 控制台 → 函数代码 → 提交")
        return

    if not shutil.which("scf"):
        print("\n[部署] SCF CLI 未安装")
        print("  安装: npm install -g @scf/cli")
        print("  配置: scf configure --region ap-guangzhou")
        print(f"\n  手动上传: 打开 SCF 控制台 → 创建函数 → 上传 {zip_path}")
        print(f"    运行时: {RUNTIME}")
        print(f"    入口:   handler.main_handler")
        print(f"    定时:   {TIMER_CRON} (北京时间)")
        return

    env_args = env_cli_arg or []

    print(f"\n[部署] 上传到 SCF...")
    result = subprocess.run(
        ["scf", "function", "update",
         "--function-name", FUNCTION_NAME,
         "--region", REGION,
         "--code", zip_path] + env_args,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("  (函数不存在，尝试创建...)")
        result = subprocess.run(
            ["scf", "function", "create",
             "--function-name", FUNCTION_NAME,
             "--region", REGION,
             "--runtime", RUNTIME,
             "--entry-point", "handler.main_handler",
             "--code", zip_path,
             "--description", "CSUFT 自动晚点名打卡"] + env_args,
            capture_output=True, text=True,
        )
    if result.returncode == 0:
        print(f"  ✅ 部署成功")
    else:
        print(f"  ❌ 部署失败: {result.stderr}")
        print(f"  手动上传: SCF 控制台上传 {zip_path}")


def create_timer_trigger(dry_run: bool = False) -> None:
    if dry_run:
        print(f"\n[触发器] DRY RUN — 跳过")
        print(f"  定时: {TIMER_CRON} (每天 21:05 北京时间)")
        print(f"  说明: 自动打卡")
        return

    result = subprocess.run(
        ["scf", "trigger", "create",
         "--function-name", FUNCTION_NAME,
         "--region", REGION,
         "--type", "timer",
         "--trigger-name", "daily-checkin",
         "--cron", TIMER_CRON],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"  ✅ 定时触发器已创建 ({TIMER_CRON} 北京时间)")
    else:
        print(f"  ⚠️ 触发器创建失败: {result.stderr}")
        print(f"  手动: SCF 控制台 → 触发管理 → 创建定时触发器 → {TIMER_CRON}")


def invoke_test() -> None:
    print(f"\n[测试] 手动触发 {FUNCTION_NAME}...")
    result = subprocess.run(
        ["scf", "function", "invoke",
         "--function-name", FUNCTION_NAME,
         "--region", REGION,
         "--invoke-type", "RequestResponse",
         "--client-context", '{"test": true}'],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"  ✅ 调用成功")
        print(f"  返回: {result.stdout[:500]}")
    else:
        print(f"  ❌ 调用失败: {result.stderr}")


def gen_env_json() -> None:
    """从 config.json 生成 SCF 控制台可导入的 JSON 环境变量文件。

    读取 ~/.auto_check_in/config.json 中所有 profiles 的 OpenID 和学号，
    输出 `scf_env.json`，可直接在 SCF 控制台 → 函数配置 → 环境变量 → 导入。

    也支持从 password.txt 回退（兼容旧版）。
    """
    # 尝试从 config.json 读取
    profiles = {}
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            profiles = raw.get("profiles", {})
        except Exception:
            pass

    env_vars = {}

    # 从 profiles 构建环境变量
    if profiles:
        profile_names = ",".join(
            p for p in sorted(profiles.keys())
            if profiles[p].get("openid") or profiles[p].get("username")
        )
        if profile_names:
            env_vars["CHECKIN_PROFILES"] = profile_names

        for name in sorted(profiles.keys()):
            data = profiles[name]
            if data.get("openid"):
                env_vars[f"CHECKIN_OPENID_{name}"] = data["openid"]
            if data.get("username"):
                env_vars[f"CHECKIN_USERNAME_{name}"] = data["username"]

    # 回退：从 password.txt 读取（兼容旧版 + 补充非 profile 变量）
    password_path = PROJECT_DIR / "password.txt"
    if password_path.exists():
        exclude_keys = {"SecretId", "SecretKey", "secret_id", "secret_key"}
        for line in password_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key and val and key not in exclude_keys:
                # 不覆盖 config.json 已有的 profile 变量
                if key not in env_vars and not key.startswith("CHECKIN_OPENID_") and not key.startswith("CHECKIN_USERNAME_"):
                    env_vars[key] = val

    if not env_vars:
        print("[错误] config.json 和 password.txt 均无有效数据")
        print("  请先运行 python scripts/cli.py login-openid 完成登录")
        sys.exit(1)

    output_path = SCRIPT_DIR / "scf_env.json"
    output_path.write_text(
        json.dumps(env_vars, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[完成] 已生成 {output_path.name} ({len(env_vars)} 个变量)")
    print()
    print("  使用方法:")
    print(f"    1. SCF 控制台 -> 函数配置 -> 环境变量 -> 导入")
    print(f"    2. 选择 {output_path.name}")
    print(f"    3. 敏感字段手动勾选「加密」")
    print()
    print("  [注意] JSON 导入后所有变量都是明文，")
    print("  需要手动将 OpenID/密码/ServerKey 逐个勾选「加密」存储")


def main() -> None:
    parser = argparse.ArgumentParser(description="部署 Auto Check-In 到腾讯云 SCF")
    parser.add_argument("--dry-run", action="store_true", help="仅打包，不部署")
    parser.add_argument("--invoke", action="store_true", help="部署后触发测试")
    parser.add_argument("--env-json", type=str, default="",
                        help="从 JSON 文件读取环境变量（SCF 控制台导出的格式）")

    # gen-env 子命令：从 config.json 生成环境变量 JSON
    sub = parser.add_subparsers(dest="command")
    p_gen = sub.add_parser("gen-env", help="从 config.json 生成 SCF 环境变量 JSON")

    args = parser.parse_args()

    # gen-env 子命令先处理
    if getattr(args, "command", None) == "gen-env":
        gen_env_json()
        return

    print("=" * 50)
    print(f"  Auto Check-In → Tencent SCF")
    print(f"  函数名: {FUNCTION_NAME}")
    print(f"  地域:   {REGION}")
    print(f"  运行时: {RUNTIME}")
    print(f"  定时:   {TIMER_CRON} (每天 21:05 北京时间)")
    print("=" * 50)

    # 读取环境变量 JSON
    env_cli_arg = []
    if args.env_json:
        env_path = Path(args.env_json)
        if not env_path.exists():
            print(f"❌ 环境变量文件不存在: {args.env_json}")
            sys.exit(1)
        env_data = json.loads(env_path.read_text(encoding="utf-8"))
        # 转为 SCF CLI 格式: {"Variables": [{"Key": k, "Value": v}]}
        variables = [{"Key": k, "Value": v} for k, v in env_data.items()]
        env_cli_arg = ["--environment", json.dumps({"Variables": variables})]
        print(f"  📦 环境变量: {len(variables)} 个（来自 {args.env_json}）")

    try:
        zip_path = build_package()
        deploy_scf(zip_path, dry_run=args.dry_run, env_cli_arg=env_cli_arg)
    except (RuntimeError, OSError) as e:
        print(f"\n❌ 构建失败: {e}")
        sys.exit(1)

    if not args.dry_run:
        create_timer_trigger()
        if args.invoke:
            invoke_test()

    print(f"\n包路径: {zip_path}")
    print("完成!")


if __name__ == "__main__":
    main()
