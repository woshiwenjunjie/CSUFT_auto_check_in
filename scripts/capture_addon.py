"""mitmproxy addon — 自动捕获小程序 OpenID

工作方式：
  1. 监听所有 HTTP 响应
  2. 当 URL 包含 'getOpenidByJsCode' 时，提取响应 JSON 中的 data 字段（即 OpenID）
  3. 保存到 ~/.auto_check_in/config.json
  4. 自动关闭 mitmproxy

用法：
  mitmdump -s scripts/capture_addon.py --listen-port 8080

或通过 CLI 命令：
  python scripts/cli.py capture-openid
"""

import json
import sys
from pathlib import Path
from mitmproxy import http, ctx

CONFIG_FILE = Path.home() / ".auto_check_in" / "config.json"


class OpenIDCapture:
    """捕获 getOpenidByJsCode 响应的 OpenID"""

    def __init__(self):
        self.captured = False

    def response(self, flow: http.HTTPFlow):
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

            cfg = {}
            if CONFIG_FILE.exists():
                cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg["openid"] = openid

            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            print()
            print("=" * 50)
            print(f"  OpenID 已捕获!")
            print(f"  OpenID: {openid[:4]}***{openid[-4:]}")
            print(f"  已保存到 {CONFIG_FILE}")
            print("=" * 50)
            print()
            print("  下一步: python scripts/cli.py setup")
            print()

            ctx.master.shutdown()
        except Exception as e:
            print(f"[capture_addon] 解析响应失败: {e}", file=sys.stderr)


addons = [OpenIDCapture()]
