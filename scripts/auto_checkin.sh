#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Auto Check-In — GitHub Actions 执行脚本
#
# 通知渠道（按优先级）：
#   1. Server酱 · 免费微信推送（仅需扫码关注公众号）
#   2. Telegram Bot
#   3. GitHub Actions 页面 Summary
# ═══════════════════════════════════════════════════════════

set -euo pipefail

LOG_FILE="/tmp/auto_checkin_output.txt"
RUN_DATE=$(date '+%Y-%m-%d %H:%M:%S')
RUN_DATE_SHORT=$(date '+%Y-%m-%d')

# GitHub Actions 环境变量（本地运行时不存在）
GITHUB_SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-unknown}"
GITHUB_RUN_ID="${GITHUB_RUN_ID:-0}"
GITHUB_STEP_SUMMARY="${GITHUB_STEP_SUMMARY:-}"


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

# 从 CLI 输出中提取字段
extract_field() {
    local text="$1" label="$2"
    echo "$text" | sed -n "s/.*${label}:\s*//p" | head -1
}

# Server酱 · 微信推送（免费，扫码即用）
send_serverchan() {
    local title="$1" desp="$2"
    if [ -n "${SERVERCHAN_KEY:-}" ]; then
        curl -s --connect-timeout 10 --max-time 15 \
            -X POST "https://sctapi.ftqq.com/${SERVERCHAN_KEY}.send" \
            -d "title=${title}" \
            -d "desp=${desp}" \
            > /dev/null 2>&1 || true
    fi
}

# Telegram 通知（备用）
send_telegram() {
    local text="$1"
    if [ -n "${TG_BOT_TOKEN:-}" ] && [ -n "${TG_CHAT_ID:-}" ]; then
        curl -s --connect-timeout 10 --max-time 15 \
            -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TG_CHAT_ID}" \
            -d "text=${text}" \
            > /dev/null 2>&1 || true
    fi
}

# 统一通知：所有已配置的渠道同时发送
notify() {
    local title="$1" desp="$2" telegram_msg="$3"
    send_serverchan "${title}" "${desp}"
    send_telegram "${telegram_msg}"
}

# GitHub Step Summary
write_github_summary() {
    if [ -n "${GITHUB_STEP_SUMMARY}" ]; then
        printf '%b\n' "$1" >> "$GITHUB_STEP_SUMMARY"
    fi
}


# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

echo "========================================" | tee "$LOG_FILE"
echo "  CSUFT 自动晚点名打卡" | tee -a "$LOG_FILE"
echo "  时间: ${RUN_DATE}" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

SUMMARY="## 🏠 打卡报告 | ${RUN_DATE_SHORT}\n\n"

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

echo "[1/5] 配置写入完成" | tee -a "$LOG_FILE"

# ── 2. 安装依赖 ──────────────────────────────────────
echo "[2/5] 安装依赖..." | tee -a "$LOG_FILE"
pip install -q -r requirements.txt 2>&1 | tee -a "$LOG_FILE"

# ── 3. 登录 ──────────────────────────────────────────
echo "[3/5] 登录校园网..." | tee -a "$LOG_FILE"

LOGIN_OUTPUT=$(python scripts/cli.py login-openid \
  "${CHECKIN_OPENID}" \
  "${CHECKIN_USERNAME}" \
  --bind 0 \
  2>&1) || true

echo "$LOGIN_OUTPUT" | tee -a "$LOG_FILE"

if echo "$LOGIN_OUTPUT" | grep -q "登录成功"; then
    echo "  => 登录成功" | tee -a "$LOG_FILE"
    SUMMARY+="| 登录 | ✅ 成功 |\n"
else
    echo "  => 登录失败" | tee -a "$LOG_FILE"
    SUMMARY+="| 登录 | ❌ 失败 |\n"
    ERR=$(echo "$LOGIN_OUTPUT" | grep "登录失败\|error" || echo "凭据无效或网络不通")

    NOTIFY="❌ 打卡失败 — 登录阶段\n========\n时间：${RUN_DATE}\n原因：${ERR}"
    notify "❌ 打卡失败" "${NOTIFY}" "❌ CSUFT 打卡失败 — 登录阶段"

    SUMMARY+="\n**结果**：❌ 登录失败，未执行打卡\n"
    write_github_summary "${SUMMARY}"
    exit 1
fi

# ── 4. 获取任务 ──────────────────────────────────────
echo "[4/5] 获取任务..." | tee -a "$LOG_FILE"

if [ -z "${CHECKIN_TASK_ID:-}" ]; then
    TASKS_OUTPUT=$(python scripts/cli.py tasks 2>&1) || true
    echo "$TASKS_OUTPUT" | tee -a "$LOG_FILE"
fi

# ── 5. 打卡 ──────────────────────────────────────────
echo "[5/5] 执行打卡..." | tee -a "$LOG_FILE"

CHECKIN_OUTPUT=$(python scripts/cli.py checkin 2>&1) || true
echo "$CHECKIN_OUTPUT" | tee -a "$LOG_FILE"

# 提取字段
CHECKIN_DATE=$(extract_field "$CHECKIN_OUTPUT" "日期")
CHECKIN_DATE="${CHECKIN_DATE:-${RUN_DATE_SHORT}}"
STATUS_RAW=$(extract_field "$CHECKIN_OUTPUT" "状态")
STATUS_RAW="${STATUS_RAW:-未知}"
DISTANCE=$(extract_field "$CHECKIN_OUTPUT" "与宿舍距离")
DISTANCE="${DISTANCE:--}"
COORDS=$(extract_field "$CHECKIN_OUTPUT" "坐标")

# ── 判断结果 ────────────────────────────────────────

if echo "$CHECKIN_OUTPUT" | grep -qE "打卡成功"; then
    echo "  => 打卡成功！" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ✅ ${STATUS_RAW} |\n"
    SUMMARY+="\n### 🎉 打卡成功\n"
    SUMMARY+="| 项目 | 详情 |\n|------|------|\n"
    SUMMARY+="| 日期 | ${CHECKIN_DATE} |\n"
    SUMMARY+="| 状态 | ${STATUS_RAW} |\n"
    [ "${DISTANCE}" != "-" ] && SUMMARY+="| 距宿舍 | ${DISTANCE} |\n"
    [ -n "${COORDS}" ] && SUMMARY+="| 坐标 | ${COORDS} |\n"

    # 纯文本通知
    NOTIFY="✅ 打卡成功\n========\n📅 日期：${CHECKIN_DATE}\n📊 状态：${STATUS_RAW}"
    [ "${DISTANCE}" != "-" ] && NOTIFY+="\n📍 距宿舍：${DISTANCE}"
    NOTIFY+="\n⏰ 执行时间：${RUN_DATE}"
    notify "✅ 打卡成功" "${NOTIFY}" "✅ CSUFT 打卡成功 | ${CHECKIN_DATE} | ${STATUS_RAW}"

elif echo "$CHECKIN_OUTPUT" | grep -qE "已打卡|重复"; then
    echo "  => 今日已打卡" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ⚠️ 已打卡 |\n"
    SUMMARY+="\n**结果**：今日已签过到，无需重复 ✌️\n"

    NOTIFY="⏰ 今日已打卡\n========\n📅 ${CHECKIN_DATE}\n📊 ${STATUS_RAW}\n\n今天已经打过卡了，不用重复操作~"
    notify "⏰ 已打卡" "${NOTIFY}" ""

elif echo "$CHECKIN_OUTPUT" | grep -q "超出打卡范围"; then
    echo "  => 超出范围" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ⚠️ 超出范围 |\n"
    SUMMARY+="| 距宿舍 | ${DISTANCE} |\n"
    SUMMARY+="\n**结果**：⚠️ GPS 距离超出精度范围\n"

    NOTIFY="⚠️ 打卡失败 — GPS 超出范围\n========\n📅 ${CHECKIN_DATE}\n📍 距宿舍：${DISTANCE}\n\n💡 本地尝试：python scripts/cli.py checkin --offset 0.0001"
    notify "⚠️ GPS 超出范围" "${NOTIFY}" "⚠️ CSUFT 超出范围 | ${DISTANCE}"

    write_github_summary "${SUMMARY}"
    exit 1

elif echo "$CHECKIN_OUTPUT" | grep -q "Token 已过期"; then
    echo "  => Token 过期" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ❌ 凭据过期 |\n"
    SUMMARY+="\n**结果**：❌ Token 已过期，需更新凭据\n"

    NOTIFY="❌ 打卡失败 — 凭据过期\n========\n时间：${RUN_DATE}\n\n需在本地重新登录：\npython scripts/cli.py login-openid"
    notify "❌ 凭据过期" "${NOTIFY}" "❌ CSUFT Token 过期，需手动续期"

    write_github_summary "${SUMMARY}"
    exit 1

elif echo "$CHECKIN_OUTPUT" | grep -qE "未到签到时间|不在"; then
    echo "  => 不在签到窗口（21:00-22:30，正常）" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ⏳ 未到时间 |\n"
    SUMMARY+="\n**结果**：⏳ 尚未到签到时间（窗口：21:00–22:30）\n"
    # 非错误，不发通知

else
    echo "  => 未知错误" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ❌ 失败 |\n"
    SUMMARY+="\n**结果**：❌ 打卡失败\n"

    LAST_LINES=$(echo "$CHECKIN_OUTPUT" | tail -8)
    NOTIFY="❌ 打卡失败\n========\n⏰ ${RUN_DATE}\n\n错误信息：\n${LAST_LINES}"
    notify "❌ 打卡失败" "${NOTIFY}" "❌ CSUFT 打卡失败 | ${RUN_DATE}"

    write_github_summary "${SUMMARY}"
    exit 1
fi

# ── 写入 GitHub Summary ──────────────────────────────
SUMMARY+="\n---\n⏰ ${RUN_DATE} · [查看日志](${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID})\n"
write_github_summary "${SUMMARY}"

echo "========================================" | tee -a "$LOG_FILE"
echo "  完成: ${RUN_DATE}" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
