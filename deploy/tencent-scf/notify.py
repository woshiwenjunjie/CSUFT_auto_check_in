"""Server酱 微信推送通知

将打卡结果通过 Server酱 Turbo（sctapi.ftqq.com）推送到绑定的微信。
可选依赖 — 若 `SERVERCHAN_KEY` 未配置则静默跳过，不影响打卡流程。

重试策略:
    最多 2 次尝试，间隔 3 秒。网络抖动时增加成功率。
    若 2 次均失败，打印错误日志但**不抛出异常**，避免打断主流程。

Server酱 API:
    端点: POST https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send
    参数: title（标题）, desp（Markdown 正文）
    超时: 15 秒
    成功判定: HTTP 200

环境变量:
    SERVERCHAN_KEY    Server酱 SendKey（可选，不设则跳过）
"""
from __future__ import annotations

import os
import time as time_module
import httpx


_MAX_RETRIES = 2
_RETRY_DELAY = 3


def send_serverchan(title: str, content: str) -> bool:
    key = os.environ.get("SERVERCHAN_KEY", "")
    if not key:
        print("[通知] SERVERCHAN_KEY 未配置，跳过")
        return False

    last_err = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = httpx.post(
                f"https://sctapi.ftqq.com/{key}.send",
                data={"title": title, "desp": content},
                timeout=15,
            )
            ok = resp.status_code == 200
            print(f"[通知] Server酱 HTTP {resp.status_code} (尝试 {attempt}/{_MAX_RETRIES})")
            return ok
        except Exception as e:
            last_err = e
            print(f"[通知] 发送失败 (尝试 {attempt}/{_MAX_RETRIES}): {e}")
            if attempt < _MAX_RETRIES:
                time_module.sleep(_RETRY_DELAY)

    print(f"[通知] 重试 {_MAX_RETRIES} 次均失败: {last_err}")
    return False
