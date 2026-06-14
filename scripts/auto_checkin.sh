#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Auto Check-In — CSUFT 自动晚点名打卡
#
# 每天 UTC 13:05（北京时间 21:05）自动运行 · GitHub Actions 托管
# 通知：Server酱微信推送（主） + Telegram（备用）
# ═══════════════════════════════════════════════════════════

set -euo pipefail

# ═══════════════════════════════════════════════════════════
# 时间统一用 Python timezone(timedelta(hours=8)) 获取北京时间
# bash date + TZ 环境变量在 GitHub Actions Ubuntu runner 上不可靠
# 参考: docs/memory/014-UTC时间坑.md, 015-beijing-timezone-fix-final.md
# ═══════════════════════════════════════════════════════════

LOG_FILE="/tmp/auto_checkin_output.txt"

# 用 Python 获取北京时间（纯数学偏移，不依赖 OS 时区数据库）
_beijing_now() {
    python -c "
from datetime import datetime, timezone, timedelta
tz = timezone(timedelta(hours=8))
n = datetime.now(tz)
print(n.strftime('%Y-%m-%d %H:%M:%S'), n.strftime('%Y-%m-%d'), n.strftime('%H:%M:%S'))
"
}
read -r RUN_DATE RUN_DATE_SHORT _NOW_TIME <<< "$(_beijing_now)"

now_ts() { python -c "from datetime import datetime,timezone,timedelta;print(datetime.now(timezone(timedelta(hours=8))).strftime('%H:%M:%S'))"; }

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

# 从 CHECKIN_RESULT 行提取字段（比 extract_field 更可靠，不受 ANSI 颜色影响）
parse_result_field() {
    local text="$1" field="$2"
    echo "$text" | grep -oP "${field}=\K[^ ]*" | head -1
}

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
# 多用户 profile 支持
# ═══════════════════════════════════════════════════════════

_get_env() {
    local key="$1" profile="$2" default="${3:-}"
    local val=""
    if [ -n "$profile" ] && [ "$profile" != "default" ]; then
        eval "val=\"\${${key}_${profile}:-}\""
    fi
    if [ -z "$val" ]; then
        eval "val=\"\${${key}:-}\""
    fi
    echo "${val:-$default}"
}

# 解析 profiles（逗号分隔，默认 default）
PROFILES_STR="${CHECKIN_PROFILES:-default}"
IFS=',' read -ra PROFILE_NAMES <<< "$PROFILES_STR"
# trim whitespace
PROFILE_NAMES_CLEAN=()
for pname in "${PROFILE_NAMES[@]}"; do
    pname=$(echo "$pname" | xargs)
    [ -n "$pname" ] && PROFILE_NAMES_CLEAN+=("$pname")
done
PROFILE_NAMES=("${PROFILE_NAMES_CLEAN[@]}")
unset PROFILE_NAMES_CLEAN

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

# 写入多 profile 格式 config.json
{
  echo '{'
  echo '  "current_profile": "'"${PROFILE_NAMES[0]}"'",'
  echo '  "profiles": {'
  first=true
  for pname in "${PROFILE_NAMES[@]}"; do
    openid=$(_get_env "CHECKIN_OPENID" "$pname")
    username=$(_get_env "CHECKIN_USERNAME" "$pname")
    password=$(_get_env "CHECKIN_PASSWORD" "$pname")
    [ -z "$openid" ] && echo "  ⚠️  [$pname] CHECKIN_OPENID 缺失，跳过" | tee -a "$LOG_FILE" && continue
    [ -z "$username" ] && echo "  ⚠️  [$pname] CHECKIN_USERNAME 缺失，跳过" | tee -a "$LOG_FILE" && continue
    $first || echo ','
    first=false
    printf '    "%s": {\n      "tenant_id": "000000",\n      "username": "%s",\n      "openid": "%s"' "$pname" "$username" "$openid"
    if [ -n "$password" ]; then
      printf ',\n      "password": "%s"' "$password"
    fi
    printf '\n    }'
  done
  echo ''
  echo '  }'
  echo '}'
} > "$CONFIG_DIR/config.json"

echo "[1/5] 配置完成（${#PROFILE_NAMES[@]} 个 profile） $(now_ts)" | tee -a "$LOG_FILE"

# ── [2/5] 依赖 ────────────────────────────────────────
echo "[2/5] 安装依赖  $(now_ts)" | tee -a "$LOG_FILE"
pip install -q -r requirements.txt 2>&1 | tee -a "$LOG_FILE"

# ── [3/5] 登录第一个账号 ─────────────────────────────
FIRST_PROFILE="${PROFILE_NAMES[0]}"
FIRST_OPENID=$(_get_env "CHECKIN_OPENID" "$FIRST_PROFILE")
FIRST_USERNAME=$(_get_env "CHECKIN_USERNAME" "$FIRST_PROFILE")

echo "[3/5] 登录 ${FIRST_PROFILE}  $(now_ts)" | tee -a "$LOG_FILE"

LOGIN_OUTPUT=$(python scripts/cli.py login-openid \
  "${FIRST_OPENID}" "${FIRST_USERNAME}" --bind 0 2>&1) || true
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
echo "[5/5] 执行打卡（${#PROFILE_NAMES[@]} 个账号） $(now_ts)" | tee -a "$LOG_FILE"

PROFILES_ARG=$(IFS=,; echo "${PROFILE_NAMES[*]}")
CHECKIN_OUTPUT=$(python scripts/cli.py checkin --profiles "$PROFILES_ARG" 2>&1) || true
echo "$CHECKIN_OUTPUT" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════════════════
# 结果判断
# ═══════════════════════════════════════════════════════════

SUMMARY+="\n### 📋 打卡详情\n"

if echo "$CHECKIN_OUTPUT" | grep -q "打卡汇总"; then
    # ── 多用户模式：提取汇总表格 ──
    SUMMARY+="\n\`\`\`\n"
    SUMMARY+="$(echo "$CHECKIN_OUTPUT" | grep -E '^\s+[✓✗]' | sed 's/^  //' || echo '')"
    SUMMARY+="\n\`\`\`\n"

    # 统计成功/失败
    SUCCESS_COUNT=$(echo "$CHECKIN_OUTPUT" | grep -c '✓')
    FAIL_COUNT=$(echo "$CHECKIN_OUTPUT" | grep -c '✗')
    TOTAL_COUNT=$((SUCCESS_COUNT + FAIL_COUNT))

    echo "  => 结果: ${SUCCESS_COUNT}/${TOTAL_COUNT} 成功" | tee -a "$LOG_FILE"

    SUMMARY+="\n**汇总**：${SUCCESS_COUNT}/${TOTAL_COUNT} 个账号打卡成功\n"

    DETAILS=$(echo "$CHECKIN_OUTPUT" | grep -E '^\s+[✓✗]' | sed 's/^  //')

    if [ "$FAIL_COUNT" -eq 0 ]; then
        NOTIFY_TITLE="✅ CSUFT 打卡成功 · ${RUN_DATE_SHORT}"
        NOTIFY_BODY="## ✅ 全部 ${TOTAL_COUNT} 个账号打卡成功\n\n${DETAILS}\n\n🕐 ${RUN_DATE} 北京时间"
        TELEGRAM_MSG="✅ ${SUCCESS_COUNT}/${TOTAL_COUNT} 打卡成功"
    elif [ "$FAIL_COUNT" -lt "$TOTAL_COUNT" ]; then
        NOTIFY_TITLE="⚠️ CSUFT 部分打卡成功 · ${RUN_DATE_SHORT}"
        NOTIFY_BODY="## ⚠️ 部分打卡成功（${SUCCESS_COUNT}/${TOTAL_COUNT}）\n\n${DETAILS}\n\n🕐 ${RUN_DATE} 北京时间"
        TELEGRAM_MSG="⚠️ ${SUCCESS_COUNT}/${TOTAL_COUNT} 部分成功"
    else
        NOTIFY_TITLE="❌ CSUFT 打卡失败 · ${RUN_DATE_SHORT}"
        NOTIFY_BODY="## ❌ 全部 ${TOTAL_COUNT} 个账号均失败\n\n${DETAILS}\n\n🕐 ${RUN_DATE} 北京时间"
        TELEGRAM_MSG="❌ ${SUCCESS_COUNT}/${TOTAL_COUNT} 全部失败"
    fi

    notify "$NOTIFY_TITLE" "$NOTIFY_BODY" "$TELEGRAM_MSG"

else
    # ── 单用户模式：保持原有逻辑 ──
    RESULT_LINE=$(echo "$CHECKIN_OUTPUT" | grep -oP 'CHECKIN_RESULT:.*' | head -1)
    if [ -n "${RESULT_LINE}" ]; then
        STATUS_RAW=$(parse_result_field "$RESULT_LINE" "status")
        CHECKIN_DATE=$(parse_result_field "$RESULT_LINE" "date")
    else
        STATUS_RAW=$(extract_field "$CHECKIN_OUTPUT" "状态")
        CHECKIN_DATE=$(extract_field "$CHECKIN_OUTPUT" "日期")
    fi
    STATUS_RAW="${STATUS_RAW:-未知}"
    CHECKIN_DATE="${CHECKIN_DATE:-${RUN_DATE_SHORT}}"
    DISTANCE=$(extract_field "$CHECKIN_OUTPUT" "与宿舍距离")
    DISTANCE="${DISTANCE:--}"

    case "$STATUS_RAW" in
        "已打卡"|"正常"|"迟到")
            SUMMARY+="| 打卡 | ✅ 成功 |\n"
            SUMMARY+="| 日期 | ${CHECKIN_DATE} |\n| 状态 | ${STATUS_RAW} |\n"
            [ "${DISTANCE}" != "-" ] && SUMMARY+="| 位置 | 距宿舍 ${DISTANCE} |\n"

            BODY="## ✅ 晚点名打卡 · 成功\n\n**${CHECKIN_DATE}** | 状态：${STATUS_RAW}"
            [ "${DISTANCE}" != "-" ] && BODY+=" | 距宿舍 ${DISTANCE}"
            BODY+="\n\n---\n🕐 ${RUN_DATE} 北京时间"

            notify "✅ CSUFT 打卡成功 · ${CHECKIN_DATE}" "${BODY}" "✅ 打卡成功 ${CHECKIN_DATE} | ${STATUS_RAW}"
            ;;

        "请假中"|"未归"|"走读中"|"离校中"|"外宿中")
            SUMMARY+="| 打卡 | ⚠️ ${STATUS_RAW} |\n"
            SUMMARY+="\n**结果**：${STATUS_RAW}\n"
            BODY="## ⚠️ 打卡状态：${STATUS_RAW}\n\n**${CHECKIN_DATE}** — 状态：${STATUS_RAW}"
            notify "⚠️ CSUFT 状态 ${STATUS_RAW} · ${CHECKIN_DATE}" "${BODY}" "⚠️ 状态 ${STATUS_RAW} ${CHECKIN_DATE}"
            ;;

        *)
            if echo "$CHECKIN_OUTPUT" | grep -q "Token 已过期"; then
                SUMMARY+="| 打卡 | ❌ 凭据过期 |\n"
                SUMMARY+="\n**失败原因**：Token 已过期\n"
                BODY="## ❌ 登录凭据已过期\n\n**${RUN_DATE}**\n\n> 学校系统 Token 已过期，需在本地重新登录：\n> \`login-openid\` → 更新 GitHub Secrets"
                notify "❌ CSUFT Token 过期" "${BODY}" "❌ Token 过期"
                write_github_summary "${SUMMARY}"
                exit 1

            elif echo "$CHECKIN_OUTPUT" | grep -qE "未到签到时间|不在"; then
                SUMMARY+="| 打卡 | ⏳ 未到时间 |\n"
                SUMMARY+="\n**说明**：不在签到窗口内\n"
                BODY="## ⏳ 未到签到时间\n\n**${RUN_DATE}** — 不在打卡窗口内\n\n> 窗口：**21:00–22:30 北京时间**（UTC 13:00–14:30）\n> 任务定时 21:05 北京时间 自动执行"
                notify "⏳ CSUFT 未到签到时间 · ${RUN_DATE}" "${BODY}" "⏳ 未到签到时间 ${RUN_DATE}"

            else
                SUMMARY+="| 打卡 | ❌ 失败 |\n"
                LAST_LINES=$(echo "$CHECKIN_OUTPUT" | tail -8)
                SUMMARY+="\n**失败原因**：服务器返回未知错误\n\`\`\`\n${LAST_LINES}\n\`\`\`\n"
                BODY="## ❌ 打卡失败\n\n**${RUN_DATE}**\n\n\`\`\`\n${LAST_LINES}\n\`\`\`\n\n🔍 请在 Actions 页面查看完整日志"
                notify "❌ CSUFT 打卡失败 · ${RUN_DATE}" "${BODY}" "❌ 打卡失败 ${RUN_DATE}"
                write_github_summary "${SUMMARY}"
                exit 1
            fi
            ;;
    esac
fi

# ── 成功路径收尾 ────────────────────────────────────
SUMMARY+="\n---\n⏰ ${RUN_DATE} 北京时间 · [查看日志](${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID})\n"
write_github_summary "${SUMMARY}"

echo "========================================" | tee -a "$LOG_FILE"
echo "  完成 $(now_ts)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
