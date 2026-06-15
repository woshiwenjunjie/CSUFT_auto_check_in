"""腾讯云 SCF 函数入口

默认多用户入口。所有流程通过 `run_multi_checkin()` 执行，即使只打一个账号。
无需单独设 `CHECKIN_PROFILES`：不设时自动回退 bare 变量 `CHECKIN_OPENID` 等。
异常安全网确保未预期异常也能通过 Server酱 通知。

触发器:
    定时触发器（每天 21:05，SCF 控制台默认北京时间）

环境变量:
    ─ 多用户模式 ─
    CHECKIN_PROFILES=USER_1,USER_2           profile 列表（逗号分隔，缺省="default"）
    CHECKIN_OPENID_USER_1                    账号 1 的 OpenID
    CHECKIN_USERNAME_USER_1                  账号 1 的学号
    CHECKIN_PASSWORD_USER_1                  账号 1 的密码（免密码可不设）
    CHECKIN_OPENID_USER_2 / USERNAME_USER_2  账号 2
    ...
    ─ 单用户模式（不设 CHECKIN_PROFILES 时自动回退）─
    CHECKIN_OPENID           OpenID
    CHECKIN_USERNAME         学号
    CHECKIN_PASSWORD         密码
    ─ 通用 ─
    CHECKIN_TASK_ID          任务 ID（可选，不设则自动获取）
    SERVERCHAN_KEY           Server酱 SendKey（可选，建议加密）
"""
from __future__ import annotations

from checkin import run_multi_checkin, _date_str
from src.utils.notification import send_serverchan


def main_handler(event: dict, context: dict) -> dict:
    if not event:
        return {"status": "healthy"}
    try:
        # 默认多用户入口 — 兼容单用户（无后缀变量回退到 bare 变量）
        # 设 CHECKIN_PROFILES=USER_1,USER_2 打卡指定账号
        # 不设 CHECKIN_PROFILES 则打卡 "default"，回退读取 CHECKIN_OPENID/USERNAME
        result = run_multi_checkin()
    except Exception as e:
        err_msg = f"未捕获异常: {e}"
        print(f"[错误] {err_msg}")
        result = {"status": "error", "msg": err_msg, "date": _date_str()}
        send_serverchan(f"❌ 打卡失败 · {_date_str()}", f"## {err_msg}")
    print(f"[结果] status={result['status']} msg={result.get('msg', '')}")
    return result
