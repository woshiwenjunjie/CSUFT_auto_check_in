#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Auto Check-In — CSUFT 自动晚点名打卡
#
# 每天 21:05 自动运行 · GitHub Actions 托管
# 通知：Server酱微信推送（主） + Telegram（备用）
# ═══════════════════════════════════════════════════════════

set -euo pipefail

# ═══════════════════════════════════════════════════════════
# 统一时区：北京时间 (UTC+8)
# 用 POSIX TZ 格式：CST-8（不需要 zoneinfo 文件，100% 兼容）
# date 命令和 Python datetime.now() 均受此环境变量影响
# ═══════════════════════════════════════════════════════════
export TZ='CST-8'

LOG_FILE="/tmp/auto_checkin_output.txt"
RUN_DATE=$(date '+%Y-%m-%d %H:%M:%S')
RUN_DATE_SHORT=$(date '+%Y-%m-%d')

GITHUB_SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-unknown}"
GITHUB_RUN_ID="${GITHUB_RUN_ID:-0}"
GITHUB_STEP_SUMMARY="${GITHUB_STEP_SUMMARY:-}"


# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════

extract_field() {
    local text="$1" label="$2"
    echo "$text" | sed -n "s/.*${label}:\s*//p" | head -1
}

now_ts() { date '+%H:%M:%S'; }


# ═══════════════════════════════════════════════════════════
# Server酱 微信推送
# 使用 --data-urlencode 确保内容正确编码（支持 Markdown/换行/特殊字符）
# ═══════════════════════════════════════════════════════════
send_serverchan() {
    local title="$1" desp="$2"
    if [ -z "${SERVERCHAN_KEY:-}" ]; then
        echo "  [通知] SERVERCHAN_KEY 未配置，跳过 Server酱" | tee -a "$LOG_FILE"
        return
    fi

    echo "  [通知] 正在发送 Server酱 推送..." | tee -a "$LOG_FILE"
    local resp http_code
    resp=$(curl -s -w "\n%{http_code}" --connect-timeout 10 --max-time 15 \
        -X POST "https://sctapi.ftqq.com/${SERVERCHAN_KEY}.send" \
        --data-urlencode "title=${title}" \
        --data-urlencode "desp=${desp}" \
        2>&1) || true
    http_code=$(echo "$resp" | tail -1)
    local body=$(echo "$resp" | sed '$d')

    echo "  [通知] Server酱 HTTP ${http_code}: ${body}" | tee -a "$LOG_FILE"
}

send_telegram() {
    local text="$1"
    if [ -z "${TG_BOT_TOKEN:-}" ] || [ -z "${TG_CHAT_ID:-}" ]; then return; fi
    echo "  [通知] 正在发送 Telegram..." | tee -a "$LOG_FILE"
    local resp
    resp=$(curl -s --connect-timeout 10 --max-time 15 \
        -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${TG_CHAT_ID}" \
        --data-urlencode "text=${text}" \
        2>&1) || true
    echo "  [通知] Telegram 响应: ${resp}" | tee -a "$LOG_FILE"
}

notify() {
    local title="$1" desp="$2" telegram_msg="${3:-}"
    send_serverchan "${title}" "${desp}"
    [ -n "${telegram_msg}" ] && send_telegram "${telegram_msg}"
}

write_github_summary() {
    if [ -n "${GITHUB_STEP_SUMMARY}" ]; then
        printf '%b\n' "$1" >> "$GITHUB_STEP_SUMMARY"
    fi
}


# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

echo "========================================" | tee "$LOG_FILE"
echo "  CSUFT 自动晚点名 · $(now_ts)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

SUMMARY="## 🏠 CSUFT 晚点名 · ${RUN_DATE_SHORT}\n\n"

# ── 通知渠道检查 ──────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "  通知渠道:" | tee -a "$LOG_FILE"
if [ -n "${SERVERCHAN_KEY:-}" ]; then
    echo "    ✅ Server酱 (微信) 已配置" | tee -a "$LOG_FILE"
else
    echo "    ⚠️  Server酱 未配置 — 不会发送微信推送" | tee -a "$LOG_FILE"
    echo "    配置方法: GitHub Secrets → SERVERCHAN_KEY → sct.ftqq.com 扫码获取" | tee -a "$LOG_FILE"
fi
if [ -n "${TG_BOT_TOKEN:-}" ] && [ -n "${TG_CHAT_ID:-}" ]; then
    echo "    ✅ Telegram 已配置" | tee -a "$LOG_FILE"
else
    echo "    ⚠️  Telegram 未配置（可选备用渠道）" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# ── [1/5] 配置 ────────────────────────────────────────
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
echo "[1/5] 配置完成  $(now_ts)" | tee -a "$LOG_FILE"

# ── [2/5] 依赖 ────────────────────────────────────────
echo "[2/5] 安装依赖  $(now_ts)" | tee -a "$LOG_FILE"
pip install -q -r requirements.txt 2>&1 | tee -a "$LOG_FILE"

# ── [3/5] 登录 ────────────────────────────────────────
echo "[3/5] 登录校园网  $(now_ts)" | tee -a "$LOG_FILE"

LOGIN_OUTPUT=$(python scripts/cli.py login-openid \
  "${CHECKIN_OPENID}" "${CHECKIN_USERNAME}" --bind 0 2>&1) || true
echo "$LOGIN_OUTPUT" | tee -a "$LOG_FILE"

if ! echo "$LOGIN_OUTPUT" | grep -q "登录成功"; then
    SUMMARY+="| 登录 | ❌ 失败 |\n"
    REASON=$(echo "$LOGIN_OUTPUT" | grep -o "登录失败.*" | head -1 || echo "网络不通或凭据无效")
    SUMMARY+="\n**失败原因**：${REASON}\n"

    notify \
        "❌ CSUFT 打卡失败" \
        "## ❌ 打卡失败 — 登录失败

**时间**：${RUN_DATE}
**原因**：${REASON}

> 请检查学号、密码、OpenID 是否正确
> 或确认校园网/VPN 是否连通" \
        "❌ CSUFT 登录失败 | ${REASON}"

    write_github_summary "${SUMMARY}"
    exit 1
fi

echo "  => 登录成功" | tee -a "$LOG_FILE"
SUMMARY+="| 登录 | ✅ 成功 |\n"

# ── [4/5] 任务 ────────────────────────────────────────
echo "[4/5] 获取任务  $(now_ts)" | tee -a "$LOG_FILE"
if [ -z "${CHECKIN_TASK_ID:-}" ]; then
    TASKS_OUTPUT=$(python scripts/cli.py tasks 2>&1) || true
    echo "$TASKS_OUTPUT" | tee -a "$LOG_FILE"
fi

# ── [5/5] 打卡 ────────────────────────────────────────
echo "[5/5] 执行打卡  $(now_ts)" | tee -a "$LOG_FILE"

CHECKIN_OUTPUT=$(python scripts/cli.py checkin 2>&1) || true
echo "$CHECKIN_OUTPUT" | tee -a "$LOG_FILE"

CHECKIN_DATE=$(extract_field "$CHECKIN_OUTPUT" "日期")
CHECKIN_DATE="${CHECKIN_DATE:-${RUN_DATE_SHORT}}"
STATUS_RAW=$(extract_field "$CHECKIN_OUTPUT" "状态")
STATUS_RAW="${STATUS_RAW:-未知}"
DISTANCE=$(extract_field "$CHECKIN_OUTPUT" "与宿舍距离")
DISTANCE="${DISTANCE:--}"


# ═══════════════════════════════════════════════════════════
# 结果判断 → 全部发送通知，写明原因
# ═══════════════════════════════════════════════════════════

if echo "$CHECKIN_OUTPUT" | grep -qE "打卡成功"; then
    # ── 🎉 成功 ──
    SUMMARY+="| 打卡 | ✅ 成功 |\n"
    SUMMARY+="\n### 🎉 打卡成功\n"
    SUMMARY+="| 项目 | 详情 |\n|------|------|\n"
    SUMMARY+="| 日期 | ${CHECKIN_DATE} |\n"
    SUMMARY+="| 状态 | ${STATUS_RAW} |\n"
    [ "${DISTANCE}" != "-" ] && SUMMARY+="| 距宿舍 | ${DISTANCE} |\n"

    BODY="## ✅ 打卡成功

| 项目 | 详情 |
|------|------|
| 日期 | ${CHECKIN_DATE} |
| 状态 | ${STATUS_RAW} |"
    [ "${DISTANCE}" != "-" ] && BODY+="
| 距宿舍 | ${DISTANCE} |"
    BODY+="

⏰ ${RUN_DATE}"

    notify "✅ CSUFT 打卡成功" "${BODY}" "✅ CSUFT 打卡成功 | ${CHECKIN_DATE} | ${STATUS_RAW}"

elif echo "$CHECKIN_OUTPUT" | grep -qE "已打卡|重复"; then
    # ── 已打过 ──
    SUMMARY+="| 打卡 | ⚠️ 已打卡 |\n"
    SUMMARY+="\n**结果**：今日已签过到\n"

    BODY="## ⏰ 今日已打卡

**日期**：${CHECKIN_DATE}
**状态**：${STATUS_RAW}

今天已经签过到了，无需重复操作"

    notify "⏰ CSUFT 已打卡" "${BODY}" ""

elif echo "$CHECKIN_OUTPUT" | grep -q "超出打卡范围"; then
    # ── GPS 超出 ──
    SUMMARY+="| 打卡 | ⚠️ GPS 超出范围 |\n"
    SUMMARY+="| 距宿舍 | ${DISTANCE} |\n"
    SUMMARY+="\n**失败原因**：模拟坐标距离宿舍过远\n"

    BODY="## ⚠️ 打卡失败 — GPS 超出范围

**日期**：${CHECKIN_DATE}
**距宿舍**：${DISTANCE}

**原因**：随机生成的模拟坐标距离宿舍太远，
超过了学校要求的精度范围。

**解决办法**：在本地用减小偏移量的方式重试：
\`python scripts/cli.py checkin --offset 0.0001\`"

    notify "⚠️ CSUFT GPS 超出范围" "${BODY}" "⚠️ CSUFT GPS 超出范围 | ${DISTANCE}"
    write_github_summary "${SUMMARY}"
    exit 1

elif echo "$CHECKIN_OUTPUT" | grep -q "Token 已过期"; then
    # ── Token 过期 ──
    SUMMARY+="| 打卡 | ❌ 凭据过期 |\n"
    SUMMARY+="\n**失败原因**：Token 已过期\n"

    BODY="## ❌ 打卡失败 — Token 过期

**时间**：${RUN_DATE}

**原因**：学校系统的登录凭据（Token）已过期。

**解决办法**：在本地电脑上重新登录一次：
\`python scripts/cli.py login-openid\`
然后更新 GitHub Secrets。"

    notify "❌ CSUFT Token 过期" "${BODY}" "❌ CSUFT Token 过期"
    write_github_summary "${SUMMARY}"
    exit 1

elif echo "$CHECKIN_OUTPUT" | grep -qE "未到签到时间|不在"; then
    # ── 不在窗口 ──
    SUMMARY+="| 打卡 | ⏳ 未到时间 |\n"
    SUMMARY+="\n**说明**：不在签到窗口内（21:00–22:30）\n"

    BODY="## ⏳ 未到签到时间

**时间**：${RUN_DATE}
**状态**：尚未到签到时间

CSUFT 打卡窗口为 **每晚 21:00–22:30**
定时任务会在 21:05 自动执行。"

    notify "⏳ CSUFT 未到签到时间" "${BODY}" ""

else
    # ── 未知错误 ──
    SUMMARY+="| 打卡 | ❌ 失败 |\n"
    LAST_LINES=$(echo "$CHECKIN_OUTPUT" | tail -8)
    SUMMARY+="\n**失败原因**：服务器返回未知错误\n\`\`\`\n${LAST_LINES}\n\`\`\`\n"

    BODY="## ❌ 打卡失败 — 未知错误

**时间**：${RUN_DATE}

**服务器返回**：
${LAST_LINES}

请在 Actions 页面查看完整日志。"

    notify "❌ CSUFT 打卡失败" "${BODY}" "❌ CSUFT 打卡失败 | ${RUN_DATE}"
    write_github_summary "${SUMMARY}"
    exit 1
fi

# ── 成功路径收尾 ────────────────────────────────────
SUMMARY+="\n---\n⏰ ${RUN_DATE} · [Actions](${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID})\n"
write_github_summary "${SUMMARY}"

echo "========================================" | tee -a "$LOG_FILE"
echo "  完成 $(now_ts)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
