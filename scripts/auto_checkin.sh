#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Auto Check-In — CSUFT 自动晚点名打卡
#
# 纯编排脚本：打卡执行 + 日志收集，通知全部交由 Python 模块处理
# 每天 UTC 13:05（北京时间 21:05）自动运行 · GitHub Actions 托管
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

LOG_FILE="/tmp/auto_checkin_output.txt"
PYTHON="python"

echo "========================================" | tee "$LOG_FILE"
echo "  CSUFT Auto Check-In | $(date -u +%Y-%m-%dT%H:%M:%SZ) UTC" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# ── Step 1: 检测是否配置多用户（CHECKIN_PROFILES）──
PROFILES="${CHECKIN_PROFILES:-}"

if [ -n "$PROFILES" ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "  [模式] SCF 多用户模式，账号: $PROFILES" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    # 直接调用 deploy/tencent-scf/checkin.py 的 run_multi_checkin()
    cd "$(dirname "$0")/.."
    $PYTHON -c "
import sys, os
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'deploy', 'tencent-scf'))
from checkin import run_multi_checkin
result = run_multi_checkin()
print(f'CHECKIN_RESULT: status={result.get(\"status\",\"\")} msg={result.get(\"msg\",\"\")}')
sys.exit(0 if result.get('status') == 'ok' else 1)
" 2>&1 | tee -a "$LOG_FILE"
else
    echo "" | tee -a "$LOG_FILE"
    echo "  [模式] 单用户模式" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    # 单用户：用 scripts 下的 token_client + checkin_one 逻辑
    cd "$(dirname "$0")/.."
    $PYTHON -c "
import sys, os
sys.path.insert(0, os.getcwd())
from src.core.token_client import ApiTokenClient
from src.utils.notification import build_notification, send_notifications
from datetime import datetime, timezone

profile = os.environ.get('CHECKIN_PROFILES', 'default').split(',')[0].strip()
api = ApiTokenClient(profile)
ok, msg = api.login()
if not ok:
    result = {'status': 'error', 'detail': msg, 'profile': profile}
else:
    tid = api.task_id or api.fetch_latest_task_id()
    if not tid:
        result = {'status': 'error', 'detail': '无可用task_id', 'profile': profile}
    else:
        check_ok, status, detail = api.do_checkin(tid)
        confirm = api.confirm_checkin(tid) if check_ok else ''
        result = {'status': status, 'detail': detail, 'confirm': confirm, 'profile': profile}

print(f'CHECKIN_RESULT: status={result.get(\"status\",\"\")} detail={result.get(\"detail\",\"\")}')

# 通知
results_map = {profile: result.get('status', 'error') + ': ' + result.get('detail', '')}
title, content = build_notification(results_map)
send_notifications(title, content)
sys.exit(0 if result.get('status') in ('ok', 'duplicate') else 1)
" 2>&1 | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "  完成 $(date -u +%H:%M:%S) UTC" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
