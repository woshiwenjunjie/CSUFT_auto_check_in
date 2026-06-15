"""notification — Server酱 微信推送（共享模块，CLI + SCF 共用）"""

from __future__ import annotations

import os
import time as time_module
from datetime import datetime


_SERVERCHAN_URL = "https://sctapi.ftqq.com/{key}.send"
_MAX_RETRIES = 2
_RETRY_DELAY = 3


def send_serverchan(title: str, content: str, key: str = "") -> bool:
    if not key:
        key = os.environ.get("SERVERCHAN_KEY", "")
    if not key:
        return False
    try:
        import httpx
    except ImportError:
        return False
    last_err = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = httpx.post(
                _SERVERCHAN_URL.format(key=key),
                data={"title": title, "desp": content},
                timeout=15,
            )
            return resp.status_code == 200
        except Exception as e:
            last_err = e
            if attempt < _MAX_RETRIES:
                time_module.sleep(_RETRY_DELAY)
    return False


def _is_success(status: str) -> bool:
    fail_keywords = ("error", "失败", "过期", "超出", "未登录", "无任务", "异常", "退出")
    for kw in fail_keywords:
        if kw in status.lower():
            return False
    return bool(status.strip())


def build_notification(results: dict[str, str]) -> tuple[str, str]:
    ok_count = sum(1 for s in results.values() if _is_success(s))
    total = len(results)
    title = f"打卡汇总 {ok_count}/{total}"
    content_lines = [f"## 自动打卡结果", f"共 {total} 个账号，成功 {ok_count} 个", ""]
    for pname, status in results.items():
        content_lines.append(f"- **{pname}**: {status}")
    content_lines.append("")
    content_lines.append(f"---")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content_lines.append(f"🕐 {ts} (北京时间)")
    return title, "\n".join(content_lines)
