#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Auto Check-In — GitHub Actions 执行脚本
#
# 功能：
#   1. 从 GitHub Secrets 写入配置文件
#   2. 登录并获取 token
#   3. 执行打卡
#   4. 记录日志
#   5. 可选：发送通知（PushPlus 微信 / Telegram）
# ═══════════════════════════════════════════════════════════

set -euo pipefail

LOG_FILE="/tmp/auto_checkin_output.txt"


# ═══════════════════════════════════════════════════════════
# 通知函数（必须在调用前定义）
# ═══════════════════════════════════════════════════════════
send_notification() {
    local title="$1"
    local message="$2"

    # ── 微信通知（PushPlus，免费微信推送） ──
    if [ -n "${PUSHPLUS_TOKEN:-}" ]; then
        curl -s -X POST "http://www.pushplus.plus/send" \
            -d "token=${PUSHPLUS_TOKEN}" \
            -d "title=${title}" \
            -d "content=${message}" \
            > /dev/null 2>&1 || true
    fi

    # ── Telegram 通知 ──
    if [ -n "${TG_BOT_TOKEN:-}" ] && [ -n "${TG_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TG_CHAT_ID}" \
            -d "text=${title}%0A${message}" \
            -d "parse_mode=HTML" \
            > /dev/null 2>&1 || true
    fi
}


# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

echo "=== Auto Check-In $(date '+%Y-%m-%d %H:%M:%S') ===" | tee "$LOG_FILE"

# ── 1. 写入配置文件 ──────────────────────────────────
CONFIG_DIR="$HOME/.auto_check_in"
mkdir -p "$CONFIG_DIR"

cat > "$CONFIG_DIR/config.json" << EOF
{
  "tenant_id": "000000",
  "username": "${CHECKIN_USERNAME}",
  "openid": "${CHECKIN_OPENID}",
  "password": "${CHECKIN_PASSWORD}",
  "task_id": "${CHECKIN_TASK_ID:-}"
}
EOF

echo "[OK] Config written" | tee -a "$LOG_FILE"

# ── 2. 安装依赖 ──────────────────────────────────────
pip install -q -r requirements.txt 2>&1 | tee -a "$LOG_FILE"

# ── 3. 登录并获取 token ──────────────────────────────
echo "--- Login ---" | tee -a "$LOG_FILE"

LOGIN_OUTPUT=$(python scripts/cli.py login-openid \
  "${CHECKIN_OPENID}" \
  "${CHECKIN_USERNAME}" \
  --bind 0 \
  2>&1) || true

echo "$LOGIN_OUTPUT" | tee -a "$LOG_FILE"

if echo "$LOGIN_OUTPUT" | grep -q "登录成功"; then
    echo "[OK] Login success" | tee -a "$LOG_FILE"
else
    echo "[FAIL] Login failed" | tee -a "$LOG_FILE"
    ERROR_MSG=$(echo "$LOGIN_OUTPUT" | grep "登录失败" || echo "未知登录错误")
    send_notification "❌ 打卡失败 — 登录" "$ERROR_MSG"
    exit 1
fi

# ── 4. 获取任务列表（自动记住 task_id） ──────────────
echo "--- Get Tasks ---" | tee -a "$LOG_FILE"

if [ -z "${CHECKIN_TASK_ID:-}" ]; then
    TASKS_OUTPUT=$(python scripts/cli.py tasks 2>&1) || true
    echo "$TASKS_OUTPUT" | tee -a "$LOG_FILE"
fi

# ── 5. 执行打卡 ──────────────────────────────────────
echo "--- Check In ---" | tee -a "$LOG_FILE"

CHECKIN_OUTPUT=$(python scripts/cli.py checkin 2>&1) || true
echo "$CHECKIN_OUTPUT" | tee -a "$LOG_FILE"

# 判断结果
if echo "$CHECKIN_OUTPUT" | grep -qE "打卡成功|已打卡|重复"; then
    echo "[OK] Check-in successful" | tee -a "$LOG_FILE"
    STATUS_LINE=$(echo "$CHECKIN_OUTPUT" | grep -A1 "状态" | tail -1 || echo "已打卡")
    send_notification "✅ 打卡成功" "$STATUS_LINE"

elif echo "$CHECKIN_OUTPUT" | grep -q "超出打卡范围"; then
    echo "[WARN] Out of range" | tee -a "$LOG_FILE"
    send_notification "⚠️ 打卡失败 — 超出范围" "尝试减小 --offset 参数"
    exit 1

elif echo "$CHECKIN_OUTPUT" | grep -q "Token 已过期"; then
    echo "[FAIL] Token expired" | tee -a "$LOG_FILE"
    send_notification "❌ 打卡失败 — Token 过期" "需要手动重新登录"
    exit 1

elif echo "$CHECKIN_OUTPUT" | grep -qE "未到签到时间|不在"; then
    echo "[OK] Not check-in time yet (expected outside 21:00-22:30)" | tee -a "$LOG_FILE"
    # 不在窗口内是正常的，不算失败

else
    echo "[FAIL] Unknown error" | tee -a "$LOG_FILE"
    send_notification "❌ 打卡失败" "$(echo "$CHECKIN_OUTPUT" | tail -5)"
    exit 1
fi

echo "=== Done $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$LOG_FILE"
