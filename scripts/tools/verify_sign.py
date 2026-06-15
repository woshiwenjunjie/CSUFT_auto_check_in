#!/usr/bin/env python3
"""交互式签名验证工具 — 调用 Python/Node.js 生成 FlySource-sign 并对比"""

import argparse
import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.sign import generate_sign, generate_basic_auth, get_credentials


def get_js_sign(path: str, ts: int, token: str) -> str:
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    result = subprocess.run(
        ["node", "scripts/sign.js", path, str(ts), token],
        capture_output=True, text=True, cwd=project_root,
    )
    if result.returncode != 0:
        print("Node.js 调用失败:", result.stderr)
        sys.exit(1)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="FlySource 签名验证工具")
    parser.add_argument("--path", help="API 路径，如 /api/test")
    parser.add_argument("--ts", type=int, help="13 位毫秒时间戳")
    parser.add_argument("--token", default="", help="access_token（可选）")
    parser.add_argument("--js", action="store_true", help="同时用 Node.js 计算并对比")
    args = parser.parse_args()

    path = args.path
    ts = args.ts
    token = args.token

    if not path or ts is None:
        print("=== 交互式签名验证 ===\n")
        path = input("API 路径: ").strip() or "/api/test"
        ts_input = input("13 位毫秒时间戳: ").strip()
        ts = int(ts_input) if ts_input else 1700000000000
        token = input("access_token（可为空）: ").strip() or ""
        if not args.js:
            js_prompt = input("同时用 Node.js 对比? (y/N): ").strip().lower()
            args.js = js_prompt == "y"

    py_sign = generate_sign(path, ts, token)
    client_id, client_secret = get_credentials()
    basic_auth = generate_basic_auth(client_id, client_secret)

    print("\n=== 签名验证结果 ===")
    print(f"路径:          {path}")
    print(f"时间戳:        {ts}")
    print(f"token:         {token[:12] + '...' if len(token) > 15 else token}")
    print(f"Client ID:     {client_id}")
    print("---")
    print(f"Basic Auth:    {basic_auth}")
    print(f"Python 签名:   {py_sign}")

    if args.js:
        js_sign = get_js_sign(path, ts, token)
        print(f"Node.js 签名:  {js_sign}")
        if py_sign == js_sign:
            print("[OK] 签名一致")
        else:
            print("[FAIL] 签名不一致！")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
