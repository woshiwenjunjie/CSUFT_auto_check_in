#!/usr/bin/env python3
"""wxapkg 解包辅助脚本 — 检查依赖并调用 wxappUnpacker 解包"""

import argparse
import os
import subprocess
import sys


WXAPPUNPACKER_DIRS = [
    os.path.join(os.path.dirname(__file__), '..', '..', 'references', 'wxappUnpacker'),
    os.path.join(os.path.dirname(__file__), '..', '..', 'wxappUnpacker'),
]


def check_dependencies():
    print("检查系统依赖...")
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"  Node.js: {result.stdout.strip()}")
    except FileNotFoundError:
        print("  [FAIL] Node.js 未安装，请先安装 Node.js")
        return False

    unpacker_dir = None
    for d in WXAPPUNPACKER_DIRS:
        if os.path.isdir(d):
            unpacker_dir = d
            break

    if unpacker_dir:
        print(f"  wxappUnpacker: 已找到 ({unpacker_dir})")
    else:
        print("  [FAIL] wxappUnpacker 未找到，请先安装:")
        print("     git clone https://github.com/Kenshin/wxappUnpacker.git references/wxappUnpacker")
        return False

    return True


def decompile(input_path: str, output_dir: str):
    abs_input = os.path.abspath(input_path)
    abs_output = os.path.abspath(output_dir)

    if not os.path.isfile(abs_input):
        print(f"[FAIL] 输入文件不存在: {abs_input}")
        sys.exit(1)

    os.makedirs(abs_output, exist_ok=True)

    unpacker_dir = None
    for d in WXAPPUNPACKER_DIRS:
        if os.path.isdir(d):
            unpacker_dir = d
            break

    wu_package = os.path.join(unpacker_dir, "package.json")
    wu_js = os.path.join(unpacker_dir, "wuWxapkg.js")

    if os.path.isfile(wu_package):
        print("运行 npm install...")
        subprocess.run(["npm", "install"], cwd=unpacker_dir, check=True)

    if not os.path.isfile(wu_js):
        print(f"[FAIL] 未找到 wuWxapkg.js，请检查 wxappUnpacker 安装")
        sys.exit(1)

    print(f"解包中: {abs_input} -> {abs_output}")
    result = subprocess.run(
        ["node", wu_js, abs_input, "-o", abs_output],
        capture_output=True, text=True, cwd=unpacker_dir,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("stderr:", result.stderr)

    list_key_files(abs_output)


def list_key_files(output_dir: str):
    print(f"\n关键产出文件 ({output_dir}):")
    for root, dirs, files in os.walk(output_dir):
        for f in files:
            if f.endswith(('.js', '.json', '.html')):
                rel = os.path.relpath(os.path.join(root, f), output_dir)
                print(f"  {rel}")


def main():
    parser = argparse.ArgumentParser(description="wxapkg 解包辅助脚本")
    parser.add_argument("--input", required=True, help="wxapkg 文件路径")
    parser.add_argument("--output", default="./unpacked", help="输出目录（默认 ./unpacked）")
    args = parser.parse_args()

    if not check_dependencies():
        sys.exit(1)

    decompile(args.input, args.output)


if __name__ == "__main__":
    main()
