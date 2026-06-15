#!/usr/bin/env python3
"""签名交叉验证 — 生成 5 组随机参数，对比 Python 和 Node.js 签名结果"""

import os
import random
import string
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.sign import generate_sign


def random_path():
    return "/api/" + ''.join(random.choices(string.ascii_lowercase, k=8))


def random_timestamp():
    return random.randint(1600000000000, 1700000000000)


def random_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def js_sign(path, ts, token):
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    result = subprocess.run(
        ["node", "scripts/sign.js", path, str(ts), token],
        capture_output=True, text=True, cwd=project_root,
    )
    return result.stdout.strip()


def main():
    print("=" * 50)
    print("签名交叉验证工具")
    print("=" * 50)

    all_pass = True
    for i in range(5):
        path = random_path()
        ts = random_timestamp()
        token = random_token()

        py_sign = generate_sign(path, ts, token)
        js_sign_val = js_sign(path, ts, token)

        match = py_sign == js_sign_val
        status = "[OK]" if match else "[FAIL]"
        print(f"\n第 {i+1} 组: {status}")
        print(f"  path:      {path}")
        print(f"  ts:        {ts}")
        print(f"  token:     {token[:8]}...{token[-4:]}")
        print(f"  Python:    {py_sign}")
        print(f"  Node.js:   {js_sign_val}")

        if not match:
            all_pass = False

    print(f"\n{'=' * 50}")
    if all_pass:
        print("[OK] 全部 5 组签名交叉验证通过")
    else:
        print("[FAIL] 存在不一致！请检查签名算法")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
