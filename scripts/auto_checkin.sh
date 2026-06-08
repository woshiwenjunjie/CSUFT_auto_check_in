#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Auto Check-In — GitHub Actions 执行脚本
#
# 功能：
#   1. 从 GitHub Secrets 写入配置文件
#   2. 登录并获取 token
#   3. 执行打卡
#   4. 生成可读摘要（GitHub + PushPlus 微信推送）
# ═══════════════════════════════════════════════════════════

set -euo pipefail

LOG_FILE="/tmp/auto_checkin_output.txt"
SUMMARY=""

# ── 元数据 ──────────────────────────────────────────
RUN_DATE=$(date '+%Y-%m-%d %H:%M:%S')
RUN_DATE_SHORT=$(date '+%Y-%m-%d')


# ═══════════════════════════════════════════════════════════
# 通知函数
# ═══════════════════════════════════════════════════════════

# PushPlus 微信推送（支持 HTML 格式模板）
send_pushplus() {
    local title="$1"
    local content="$2"
    if [ -n "${PUSHPLUS_TOKEN:-}" ]; then
        curl -s -X POST "http://www.pushplus.plus/send" \
            -d "token=${PUSHPLUS_TOKEN}" \
            -d "title=${title}" \
            -d "content=${content}" \
            -d "template=html" \
            > /dev/null 2>&1 || true
    fi
}

# Telegram 通知
send_telegram() {
    local text="$1"
    if [ -n "${TG_BOT_TOKEN:-}" ] && [ -n "${TG_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TG_CHAT_ID}" \
            -d "text=${text}" \
            -d "parse_mode=HTML" \
            > /dev/null 2>&1 || true
    fi
}

# 写入 GitHub Actions 步骤摘要（Actions 页面可见的富文本）
write_github_summary() {
    if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
        echo "$1" >> "$GITHUB_STEP_SUMMARY"
    fi
}


# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

echo "=== Auto Check-In ${RUN_DATE} ===" | tee "$LOG_FILE"
SUMMARY+="## 🏠 自动晚点名打卡报告\n\n"
SUMMARY+="**执行时间**：${RUN_DATE}\n\n"

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

echo "[OK] Config ready" | tee -a "$LOG_FILE"

# ── 2. 安装依赖 ──────────────────────────────────────
pip install -q -r requirements.txt 2>&1 | tee -a "$LOG_FILE"

# ── 3. 登录并获取 token ──────────────────────────────
echo "--- 登录 ---" | tee -a "$LOG_FILE"

LOGIN_OUTPUT=$(python scripts/cli.py login-openid \
  "${CHECKIN_OPENID}" \
  "${CHECKIN_USERNAME}" \
  --bind 0 \
  2>&1) || true

echo "$LOGIN_OUTPUT" | tee -a "$LOG_FILE"

if echo "$LOGIN_OUTPUT" | grep -q "登录成功"; then
    echo "[OK] 登录成功" | tee -a "$LOG_FILE"
    TOKEN_MASKED=$(echo "$LOGIN_OUTPUT" | grep -oP 'Token:\s+\K\S+' || echo "***")
    SUMMARY+="| 项目 | 状态 |\n|------|------|\n"
    SUMMARY+="| 校园网登录 | ✅ 成功 |\n"
else
    echo "[FAIL] 登录失败" | tee -a "$LOG_FILE"
    SUMMARY+="| 项目 | 状态 |\n|------|------|\n"
    SUMMARY+="| 校园网登录 | ❌ 失败 |\n"
    ERROR_MSG=$(echo "$LOGIN_OUTPUT" | grep "登录失败" || echo "凭据无效或网络不通")

    # 失败通知
    FAIL_BODY="<h2>❌ 打卡失败 — 登录阶段</h2>"
    FAIL_BODY+="<p><b>时间</b>：${RUN_DATE}</p>"
    FAIL_BODY+="<p><b>原因</b>：${ERROR_MSG}</p>"
    FAIL_BODY+="<hr><p style='color:#999;font-size:12px'>中南林业科技大学 · 自动晚点名</p>"
    send_pushplus "❌ 打卡失败" "${FAIL_BODY}"
    send_telegram "❌ 打卡失败 — ${ERROR_MSG}"

    SUMMARY+="\n**结果**：❌ 登录失败，未执行打卡\n"
    write_github_summary "$(echo -e "${SUMMARY}")"
    exit 1
fi

# ── 4. 获取任务列表 ──────────────────────────────────
echo "--- 获取任务 ---" | tee -a "$LOG_FILE"

if [ -z "${CHECKIN_TASK_ID:-}" ]; then
    TASKS_OUTPUT=$(python scripts/cli.py tasks 2>&1) || true
    echo "$TASKS_OUTPUT" | tee -a "$LOG_FILE"

    # 提取任务名称
    TASK_NAME=$(echo "$TASKS_OUTPUT" | grep -oP '\[\d+\]\s+\K\S+' | head -1 || echo "未知")
else
    TASK_NAME="已预设"
fi

# ── 5. 执行打卡 ──────────────────────────────────────
echo "--- 打卡 ---" | tee -a "$LOG_FILE"

CHECKIN_OUTPUT=$(python scripts/cli.py checkin 2>&1) || true
echo "$CHECKIN_OUTPUT" | tee -a "$LOG_FILE"

# ── 提取关键字段 ────────────────────────────────────
CHECKIN_DATE=$(echo "$CHECKIN_OUTPUT" | grep -oP '日期:\s+\K\S+' | head -1 || echo "${RUN_DATE_SHORT}")
STATUS_RAW=$(echo "$CHECKIN_OUTPUT" | grep -oP '状态:\s+\K.*' | head -1 || echo "未知")
DISTANCE=$(echo "$CHECKIN_OUTPUT" | grep -oP '与宿舍距离:\s+\K\S+' | head -1 || echo "-")
COORDS=$(echo "$CHECKIN_OUTPUT" | grep -oP '坐标:\s+\(.*?\)' | head -1 || echo "")

# ── 判断结果并生成通知 ──────────────────────────────

if echo "$CHECKIN_OUTPUT" | grep -qE "打卡成功"; then
    echo "[OK] 打卡成功" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ✅ ${STATUS_RAW} |\n"
    SUMMARY+="\n**结果**：🎉 打卡成功\n"

    # 成功通知（PushPlus HTML）
    SUCCESS_BODY="<h2>✅ 打卡成功</h2>"
    SUCCESS_BODY+="<table border='0' cellpadding='4' style='font-size:15px'>"
    SUCCESS_BODY+="<tr><td>📅 日期</td><td><b>${CHECKIN_DATE}</b></td></tr>"
    SUCCESS_BODY+="<tr><td>📊 状态</td><td><span style='color:#22c55e;font-weight:bold'>${STATUS_RAW}</span></td></tr>"
    if [ -n "${DISTANCE}" ] && [ "${DISTANCE}" != "-" ]; then
        SUCCESS_BODY+="<tr><td>📍 距离</td><td>${DISTANCE}</td></tr>"
    fi
    if [ -n "${COORDS}" ]; then
        SUCCESS_BODY+="<tr><td>🗺️ 坐标</td><td style='font-size:12px;color:#666'>${COORDS}</td></tr>"
    fi
    SUCCESS_BODY+="<tr><td>⏰ 执行</td><td style='color:#666'>${RUN_DATE}</td></tr>"
    SUCCESS_BODY+="</table>"
    SUCCESS_BODY+="<hr><p style='color:#999;font-size:12px'>中南林业科技大学 · 自动晚点名</p>"

    send_pushplus "✅ 打卡成功" "${SUCCESS_BODY}"
    send_telegram "✅ CSUFT 晚点名打卡成功%0A📅 ${CHECKIN_DATE} | ${STATUS_RAW}%0A📍 距离：${DISTANCE}%0A⏰ ${RUN_DATE}"

elif echo "$CHECKIN_OUTPUT" | grep -qE "已打卡|重复"; then
    echo "[OK] 今日已打卡" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ⚠️ ${STATUS_RAW} |\n"
    SUMMARY+="\n**结果**：✅ 今日已打过卡，无需重复\n"

    DUP_BODY="<h2>⚠️ 今日已打卡</h2>"
    DUP_BODY+="<p><b>日期</b>：${CHECKIN_DATE}</p>"
    DUP_BODY+="<p><b>状态</b>：<span style='color:#f59e0b'>${STATUS_RAW}</span></p>"
    DUP_BODY+="<p style='color:#666'>今天已经签过到了，无需重复操作 ✌️</p>"
    DUP_BODY+="<hr><p style='color:#999;font-size:12px'>中南林业科技大学 · 自动晚点名</p>"
    send_pushplus "⏰ 已打卡" "${DUP_BODY}"

elif echo "$CHECKIN_OUTPUT" | grep -q "超出打卡范围"; then
    echo "[WARN] 超出范围" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ⚠️ GPS 超出范围 |\n"
    SUMMARY+="| 距离 | ${DISTANCE} |\n"
    SUMMARY+="\n**结果**：⚠️ 模拟坐标超出精度范围\n"

    RANGE_BODY="<h2>⚠️ 打卡失败 — GPS 超出范围</h2>"
    RANGE_BODY+="<table border='0' cellpadding='4' style='font-size:15px'>"
    RANGE_BODY+="<tr><td>📅 日期</td><td><b>${CHECKIN_DATE}</b></td></tr>"
    RANGE_BODY+="<tr><td>📍 距离</td><td><span style='color:#ef4444;font-weight:bold'>${DISTANCE}</span></td></tr>"
    RANGE_BODY+="</table>"
    RANGE_BODY+="<p style='color:#666'>建议：在本地用 <code>--offset 0.0001</code> 减小偏移量</p>"
    RANGE_BODY+="<hr><p style='color:#999;font-size:12px'>中南林业科技大学 · 自动晚点名</p>"
    send_pushplus "⚠️ 超出范围" "${RANGE_BODY}"
    send_telegram "⚠️ CSUFT 打卡失败 — GPS 超出范围%0A📅 ${CHECKIN_DATE} | 📍 ${DISTANCE}"

    SUMMARY+="\n"
    write_github_summary "$(echo -e "${SUMMARY}")"
    exit 1

elif echo "$CHECKIN_OUTPUT" | grep -q "Token 已过期"; then
    echo "[FAIL] Token 过期" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ❌ Token 已过期 |\n"
    SUMMARY+="\n**结果**：❌ 登录凭据已过期\n"

    TOKEN_BODY="<h2>❌ 打卡失败 — 登录过期</h2>"
    TOKEN_BODY+="<p><b>时间</b>：${RUN_DATE}</p>"
    TOKEN_BODY+="<p style='color:#ef4444'>Token 已过期，需要在本地重新登录更新凭据。</p>"
    TOKEN_BODY+="<p style='color:#666'>操作：<code>python scripts/cli.py login-openid</code></p>"
    TOKEN_BODY+="<hr><p style='color:#999;font-size:12px'>中南林业科技大学 · 自动晚点名</p>"
    send_pushplus "❌ 凭据过期" "${TOKEN_BODY}"
    send_telegram "❌ CSUFT 打卡失败 — Token 过期，需手动续期"

    SUMMARY+="\n"
    write_github_summary "$(echo -e "${SUMMARY}")"
    exit 1

elif echo "$CHECKIN_OUTPUT" | grep -qE "未到签到时间|不在"; then
    echo "[OK] 不在签到窗口（正常）" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ⏳ 未到签到时间 |\n"
    SUMMARY+="\n**结果**：⏳ 尚未到签到时间（窗口：21:00–22:30）\n"
    # 窗口外不发通知，避免骚扰

else
    echo "[FAIL] 未知错误" | tee -a "$LOG_FILE"

    SUMMARY+="| 打卡 | ❌ 未知错误 |\n"
    SUMMARY+="\n**结果**：❌ 打卡失败\n"

    ERR_BODY="<h2>❌ 打卡失败 — 未知错误</h2>"
    ERR_BODY+="<p><b>时间</b>：${RUN_DATE}</p>"
    ERR_BODY+="<p><b>详情</b>：</p>"
    ERR_BODY+="<pre style='background:#f3f4f6;padding:8px;border-radius:4px;font-size:12px'>$(echo "$CHECKIN_OUTPUT" | tail -10)</pre>"
    ERR_BODY+="<hr><p style='color:#999;font-size:12px'>中南林业科技大学 · 自动晚点名</p>"
    send_pushplus "❌ 打卡失败" "${ERR_BODY}"
    send_telegram "❌ CSUFT 打卡失败%0A${RUN_DATE}%0A$(echo "$CHECKIN_OUTPUT" | tail -3)"

    SUMMARY+="\n"
    write_github_summary "$(echo -e "${SUMMARY}")"
    exit 1
fi

# ── 写入 GitHub Actions 步骤摘要 ──────────────────
SUMMARY+="\n---\n📋 [查看完整日志](${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID})\n"
write_github_summary "$(echo -e "${SUMMARY}")"

echo "=== 完成 $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$LOG_FILE"
