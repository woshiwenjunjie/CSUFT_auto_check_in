"""腾讯云 SCF 函数入口

该模块是 SCF 定时触发器的主入口。SCF 运行时调用 `main_handler(event, context)`
启动一次完整打卡流程。异常安全网确保即使 `run_checkin()` 抛出未预期异常，
也能通过 Server酱 通知用户。

触发器:
    定时触发器（每天 21:05，SCF 控制台默认北京时间）

事件来源:
    - 定时触发器: event 为 {}（空字典）
    - 手动测试: event 可含任意键（当前忽略）
    - 健康检查: event 为空时返回 {"status": "healthy"}

安全边界:
    `main_handler` 内 try/except 捕获所有 Exception，异常时构造
    `{"status": "error", "msg": "未捕获异常: ..."}` 并发送通知。
    避免 SCF 调用失败时用户完全不知情。

环境变量（由 SCF 控制台配置，全部敏感字段勾选加密）:
    CHECKIN_OPENID     微信 OpenID（必填，建议加密）
    CHECKIN_USERNAME   学号（必填，建议加密）
    CHECKIN_PASSWORD   密码（必填，必须加密）
    CHECKIN_TASK_ID    打卡任务 ID（可选）
    SERVERCHAN_KEY     Server酱 SendKey（可选，建议加密）
"""
from checkin import run_checkin, _build_notification, _date_str
from notify import send_serverchan


def main_handler(event: dict, context: dict) -> dict:
    if not event:
        return {"status": "healthy"}
    try:
        result = run_checkin()
    except Exception as e:
        print(f"[错误] 未捕获异常: {e}")
        result = {"status": "error", "msg": f"未捕获异常: {e}", "date": _date_str()}
        title, body = _build_notification(result)
        send_serverchan(title, body)
    print(f"[结果] status={result['status']} msg={result['msg']}")
    return result
