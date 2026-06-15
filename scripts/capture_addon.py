"""mitmproxy addon — 自动捕获小程序 OpenID

工作方式：
  1. 监听所有 HTTP 响应
  2. 当 URL 包含 'getOpenidByJsCode' 时，提取响应 JSON 中的 data 字段（即 OpenID）
  3. 保存到 ~/.auto_check_in/config.json 的指定 profile 中
  4. 自动关闭 mitmproxy

用法：
  mitmdump -s scripts/capture_addon.py --listen-port 8080

或通过 CLI 命令（推荐）：
  python scripts/cli.py capture-openid
  python scripts/cli.py capture-openid --profile USER_2
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from mitmproxy import http, ctx

CONFIG_FILE = Path.home() / ".auto_check_in" / "config.json"


def _load_or_create_config() -> dict[str, Any]:
    """读取现有配置，不存在则返回空字典"""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def _save_openid_to_profile(openid: str, profile_name: str | None = None) -> dict[str, Any]:
    """将 OpenID 保存到指定 profile 的多用户配置中"""
    cfg = _load_or_create_config()

    # 确保用 profiles 字典格式
    if "profiles" not in cfg:
        # 迁移旧版扁平配置
        old = {k: cfg.get(k, "") for k in ("openid", "username", "token", "tenant_id", "task_id")}
        cfg = {"current_profile": "default", "profiles": {"default": old}}

    target = profile_name or cfg.get("current_profile", "default")
    if target not in cfg["profiles"]:
        cfg["profiles"][target] = {}

    cfg["profiles"][target]["openid"] = openid
    cfg["current_profile"] = target

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    return cfg


class OpenIDCapture:
    """捕获 getOpenidByJsCode 响应的 OpenID

    profile 优先级：构造参数 > CAPTURE_PROFILE 环境变量 > config.json current_profile > "default"
    """

    def __init__(self, profile: str | None = None) -> None:
        self.captured = False
        self._profile = profile or os.environ.get("CAPTURE_PROFILE")

    def response(self, flow: http.HTTPFlow) -> None:
        if self.captured:
            return
        if "getOpenidByJsCode" not in flow.request.pretty_url:
            return

        try:
            data = flow.response.json()
            openid = data.get("data", "")
            if not openid or not openid.startswith("o"):
                return

            self.captured = True
            cfg = _save_openid_to_profile(openid, self._profile)
            prof_name = self._profile or cfg.get("current_profile", "default")
            all_profiles = cfg.get("profiles", {})
            prof_count = len(all_profiles)

            print()
            print("=" * 56)
            print(f"  OpenID 已捕获!")
            print(f"  Profile: {prof_name}")
            print(f"  OpenID:  {openid[:4]}***{openid[-4:]}")
            print(f"  已保存到 {CONFIG_FILE}")
            if prof_count > 1:
                print(f"  全部账号: {', '.join(all_profiles.keys())}")
            print(f"\n  下一步: python scripts/cli.py setup --profile {prof_name}")
            print("=" * 56)
            print()

            ctx.master.shutdown()
        except Exception as e:
            print(f"[capture_addon] 解析响应失败: {e}", file=sys.stderr)


addons = [OpenIDCapture()]
