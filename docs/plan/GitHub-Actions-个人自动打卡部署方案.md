# GitHub Actions 个人自动打卡部署方案

> 适用版本：v0.7.2 | 日期：2026-06-08
> 适用场景：个人使用，无需购买服务器，免费自动打卡

---

## 目录

1. [为什么选 GitHub Actions？](#1-为什么选-github-actions)
2. [架构总览](#2-架构总览)
3. [前置准备](#3-前置准备)
4. [文件清单](#4-文件清单)
5. [步骤一：配置 GitHub Secrets](#5-步骤一配置-github-secrets)
6. [步骤二：创建工作流文件](#6-步骤二创建工作流文件)
7. [步骤三：推送并验证](#7-步骤三推送并验证)
8. [通知方案](#8-通知方案)
9. [故障排查](#9-故障排查)
10. [安全注意事项](#10-安全注意事项)

---

## 1. 为什么选 GitHub Actions？

| 方案 | 成本 | 可靠性 | 维护量 | 适用 |
|------|------|--------|--------|------|
| **GitHub Actions** | 免费 | 高（微软托管） | 零 | ✅ 个人使用 |
| 自有服务器 + cron | ¥50-100/月 | 中 | 需维护系统 | 多用户 |
| Windows 计划任务 | 电费 | 低（关机就停） | 低 | 电脑常开 |
| 手机定时脚本 | 免费 | 低 | 高 | 临时 |

GitHub Actions 对个人使用来说**零成本、零维护**：
- 公开仓库完全免费，私有仓库每月 2000 分钟（约 33 小时）
- 每次打卡只需 ~30 秒，每月消耗约 15 分钟
- 凭据加密存储在 GitHub Secrets 中，日志可配置隐藏

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────┐
│                GitHub Actions                    │
│                                                 │
│  cron: "5 13 * * *"  每天 21:05 (UTC+8) 触发    │
│       │                                         │
│       ▼                                         │
│  ┌──────────────┐                               │
│  │ checkout 代码 │  ← 从仓库拉取最新代码           │
│  └──────┬───────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐                               │
│  │ 安装 Python   │  Python 3.14 + pip install    │
│  └──────┬───────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐                               │
│  │ 注入 Secrets  │  OPENID / USERNAME / PASSWORD │
│  │ 写入 config   │  → 生成 ~/.auto_check_in/    │
│  └──────┬───────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐                               │
│  │ login-openid  │  换取 access_token            │
│  └──────┬───────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐                               │
│  │   checkin     │  一键打卡签到                   │
│  └──────┬───────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐                               │
│  │  推送通知     │  成功/失败 → Telegram/微信/邮件  │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

---

## 3. 前置准备

在开始之前，确保你已经有：

- [ ] 一个 GitHub 账号
- [ ] 本项目的代码已推送到 GitHub 仓库
- [ ] 通过 Fiddler 抓包拿到了 OpenID
- [ ] 学号和密码
- [ ] 至少成功用过一次 `python scripts/cli.py checkin`（验证链路通畅）

---

## 4. 文件清单

部署需要新增 3 个文件：

```
auto_check_in/
├── .github/
│   └── workflows/
│       └── auto-checkin.yml          ← GitHub Actions 工作流定义
├── scripts/
│   └── auto_checkin.sh              ← 被 Action 调用的执行脚本
└── docs/
    └── plan/
        └── GitHub-Actions-个人自动打卡部署方案.md  ← 本文件
```

### 4.1 工作流文件：`.github/workflows/auto-checkin.yml`

```yaml
name: Auto Check-In

on:
  # 定时触发：每天北京时间 21:05（UTC 13:05）
  schedule:
    - cron: "5 13 * * *"

  # 允许手动触发（在 GitHub 页面点按钮执行）
  workflow_dispatch:

  # 允许 push 触发（仅用于测试，正式运行时注释掉）
  # push:
  #   branches: [main]

env:
  # Python 版本
  PYTHON_VERSION: "3.14"

jobs:
  checkin:
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      # ── Step 1: 检出代码 ──
      - name: Checkout code
        uses: actions/checkout@v4

      # ── Step 2: 安装 Python ──
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      # ── Step 3: 安装依赖 ──
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      # ── Step 4: 执行打卡 ──
      - name: Run auto check-in
        env:
          CHECKIN_OPENID: ${{ secrets.CHECKIN_OPENID }}
          CHECKIN_USERNAME: ${{ secrets.CHECKIN_USERNAME }}
          CHECKIN_PASSWORD: ${{ secrets.CHECKIN_PASSWORD }}
          CHECKIN_TASK_ID: ${{ secrets.CHECKIN_TASK_ID }}
          # 可选：通知相关
          TG_BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
        run: |
          bash scripts/auto_checkin.sh

      # ── Step 5: 上传日志（无论成功失败都保留） ──
      - name: Upload check-in log
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: checkin-log
          path: /tmp/auto_checkin_output.txt
          retention-days: 7
```

### 4.2 执行脚本：`scripts/auto_checkin.sh`

```bash
#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Auto Check-In — GitHub Actions 执行脚本
# 
# 功能：
#   1. 从 GitHub Secrets 写入配置文件
#   2. 登录并获取 token
#   3. 执行打卡
#   4. 记录日志
#   5. 可选：发送 Telegram 通知
# ═══════════════════════════════════════════════════════════

set -euo pipefail

LOG_FILE="/tmp/auto_checkin_output.txt"
echo "=== Auto Check-In $(date '+%Y-%m-%d %H:%M:%S') ===" | tee "$LOG_FILE"

# ── 1. 写入配置文件 ──────────────────────────────────
CONFIG_DIR="$HOME/.auto_check_in"
mkdir -p "$CONFIG_DIR"

# 从环境变量构建临时配置文件
# 注意：GitHub Actions 环境由 Secrets 注入，不会在日志中暴露
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

# ── 2. 安装依赖（已在 workflow 中完成，这里仅为安全重试） ──
pip install -q -r requirements.txt 2>&1 | tee -a "$LOG_FILE"

# ── 3. 登录并获取 token ──────────────────────────────
echo "--- Login ---" | tee -a "$LOG_FILE"

LOGIN_OUTPUT=$(python scripts/cli.py login-openid \
  "${CHECKIN_OPENID}" \
  "${CHECKIN_USERNAME}" \
  --bind 0 \
  2>&1) || true

echo "$LOGIN_OUTPUT" | tee -a "$LOG_FILE"

# 检查是否登录成功
if echo "$LOGIN_OUTPUT" | grep -q "登录成功"; then
    echo "[OK] Login success" | tee -a "$LOG_FILE"
else
    echo "[FAIL] Login failed" | tee -a "$LOG_FILE"
    # 提取错误信息
    ERROR_MSG=$(echo "$LOGIN_OUTPUT" | grep "登录失败" || echo "未知登录错误")
    send_notification "❌ 打卡失败 — 登录" "$ERROR_MSG"
    exit 1
fi

# ── 4. 获取任务列表（自动记住 task_id） ──────────────
echo "--- Get Tasks ---" | tee -a "$LOG_FILE"

# 如果未设置 task_id，先运行 tasks 获取
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
    # 提取打卡确认信息
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
else
    echo "[FAIL] Unknown error" | tee -a "$LOG_FILE"
    send_notification "❌ 打卡失败" "$(echo "$CHECKIN_OUTPUT" | tail -5)"
    exit 1
fi

echo "=== Done $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$LOG_FILE"


# ═══════════════════════════════════════════════════════
# 通知函数（可选：取消注释以启用 Telegram 通知）
# ═══════════════════════════════════════════════════════
send_notification() {
    local title="$1"
    local message="$2"

    # ── Telegram 通知 ──
    if [ -n "${TG_BOT_TOKEN:-}" ] && [ -n "${TG_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TG_CHAT_ID}" \
            -d "text=${title}%0A${message}" \
            -d "parse_mode=HTML" \
            > /dev/null 2>&1 || true
    fi

    # ── 微信通知（通过 Server酱 / PushPlus） ──
    # if [ -n "${PUSHPLUS_TOKEN:-}" ]; then
    #     curl -s -X POST "http://www.pushplus.plus/send" \
    #         -d "token=${PUSHPLUS_TOKEN}" \
    #         -d "title=${title}" \
    #         -d "content=${message}" \
    #         > /dev/null 2>&1 || true
    # fi
}
```

---

## 5. 步骤一：配置 GitHub Secrets

在 GitHub 仓库页面：**Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 值 | 说明 |
|-------------|-----|------|
| `CHECKIN_OPENID` | `oABC123XYZ...` | 微信 OpenID（28 位字符串） |
| `CHECKIN_USERNAME` | `2023XXXXXX` | 学号 |
| `CHECKIN_PASSWORD` | `你的密码` | 学校系统密码（明文，GitHub 加密存储） |
| `CHECKIN_TASK_ID` | `b49ffb37...` | 打卡任务 ID（可选，不设则自动获取） |
| `TG_BOT_TOKEN` | `123456:ABC...` | Telegram Bot Token（可选，用于通知） |
| `TG_CHAT_ID` | `-100123456` | Telegram Chat ID（可选） |

> 📌 **添加方法**：每个 Secret 逐个添加。值**不要加引号**，直接粘贴。

完成后，Secrets 页面应显示 4-6 个条目。

---

## 6. 步骤二：创建工作流文件

在项目根目录创建目录和文件：

```bash
mkdir -p .github/workflows
```

将 [4.1 节](#41-工作流文件githubworkflowsauto-checkinyml) 的内容保存为 `.github/workflows/auto-checkin.yml`。

将 [4.2 节](#42-执行脚本scriptsauto_checkinsh) 的内容保存为 `scripts/auto_checkin.sh`。

给脚本添加执行权限：

```bash
chmod +x scripts/auto_checkin.sh
git add .github/ scripts/auto_checkin.sh
git commit -m "Add GitHub Actions auto check-in workflow"
git push
```

---

## 7. 步骤三：推送并验证

### 7.1 手动测试

推送到 GitHub 后，进入仓库的 **Actions** 标签页：

1. 点击左侧 **Auto Check-In** 工作流
2. 点击 **Run workflow** 下拉按钮
3. 选择分支（main/master）
4. 点击 **Run workflow**

等待约 30-60 秒，观察每一步的输出：

```
✅ Checkout code          → 拉取代码
✅ Setup Python           → Python 3.14 就绪
✅ Install dependencies   → pip install 完成
✅ Run auto check-in      → 登录 → 打卡 → 确认
✅ Upload check-in log    → 日志上传
```

### 7.2 查看日志

点击 `Run auto check-in` 步骤展开输出，确认看到：

```
[OK] Config written
[OK] Login success
[OK] Check-in successful
```

### 7.3 验证定时触发

首次推送后，定时任务会在**北京时间每晚 21:05** 自动执行。

在 Actions 页面，下次触发时间会显示在定时触发行。

---

## 8. 通知方案

### 方案 A：Telegram Bot（推荐，免费）

1. 在 Telegram 搜索 `@BotFather`，发送 `/newbot`，跟着提示创建一个 bot
2. 拿到 Bot Token（如 `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`）
3. 搜索你创建的 bot，发送一条消息
4. 访问 `https://api.telegram.org/bot<TOKEN>/getUpdates`，从 JSON 中找到 `chat.id`
5. 将 Token 和 Chat ID 添加到 GitHub Secrets：
   - `TG_BOT_TOKEN` = Bot Token
   - `TG_CHAT_ID` = Chat ID

### 方案 B：Server酱 / PushPlus（微信推送）

1. 访问 https://www.pushplus.plus 注册
2. 获取 Token
3. 在 `auto_checkin.sh` 中取消 PushPlus 通知的注释
4. 将 Token 添加到 GitHub Secrets：`PUSHPLUS_TOKEN`

### 方案 C：GitHub Actions 内置通知

无需额外配置。在 Actions 页面可以设置 workflow 失败时发送邮件通知：
- 仓库 **Settings → Notifications** → 勾选 **Email notification for failed workflows**

---

## 9. 故障排查

### Q: 手动触发成功但定时没跑

**原因**：GitHub Actions 的 cron 使用 **UTC 时间**，北京时间 21:00 = UTC 13:00。

**检查**：
- `cron: "5 13 * * *"` 表示 UTC 13:05，即北京时间 21:05
- GitHub 对公开仓库的定时任务可能有 ±15 分钟的延迟

### Q: "Token 已过期" 如何处理？

Token 有效期约 30 天。CLI 会检测到过期并报错。收到通知后：
1. 在本地运行 `python scripts/cli.py login-openid` 重新登录
2. 新的 token 会自动保存到本地 config
3. **GitHub Action 不会自动续期** — 这是设计上的限制

**解决**：在 Action 中每次都执行 `login-openid`（已包含在脚本中），每次都是全新登录，不依赖持久化的 token。

### Q: 日志报 "OpenID 不能为空"

检查 GitHub Secrets 是否配置正确：
- Secret 名称是否完全一致（区分大小写）：`CHECKIN_OPENID`
- Secret 值是否包含多余空格或引号

### Q: 打卡失败但不清楚原因

在 Actions 运行详情页下载 **checkin-log** artifact（保留 7 天），查看完整日志。

### Q: 每天消耗多少 Actions 额度？

- 每次打卡约 30 秒
- 每月 30 次 = 约 15 分钟
- GitHub 免费额度：公开仓库无限，私有仓库 2000 分钟/月
- **完全不需要担心超额**

---

## 10. 安全注意事项

### Secrets 的安全性

- GitHub Secrets 在存储层是**加密的**（AES-256）
- 只有通过 workflow 才能读取，**任何人（包括仓库管理员）无法在 GitHub 页面上看到 Secret 的明文值**
- Secrets 在日志中**自动被屏蔽** — 如果 Secret 值意外出现在输出中，GitHub 会用 `***` 替换
- Secrets **不会**传递给 fork 仓库的 workflow

### 最佳实践

```
✅ DO:
  - 所有凭据通过 Secrets 传入
  - 定期检查 Actions 日志确认正常运行
  - Token 过期后及时更新

❌ DON'T:
  - 不要在 workflow YAML 中硬编码凭据
  - 不要在代码注释中写真实学号和密码
  - 不要将 config.json 提交到仓库
  - 不要在公开 issue 中贴 OpenID
```

### 仓库可见性

| 仓库类型 | Actions 免费额度 | 安全性 |
|---------|-----------------|--------|
| 公开仓库 | 无限 | Secrets 仍加密，但代码可见。确保代码中无硬编码凭据 |
| 私有仓库 | 2000 分钟/月 | 代码 + Secrets 均不可见，更安全 |

建议：**使用私有仓库**（免费），安全性最佳。

---

## 附录：快速部署清单

```
□ 1. 确保本地 CLI 打卡成功至少一次
□ 2. 代码推送到 GitHub 仓库
□ 3. 配置 4-6 个 GitHub Secrets
□ 4. 创建 .github/workflows/auto-checkin.yml
□ 5. 创建 scripts/auto_checkin.sh 并 chmod +x
□ 6. git add + commit + push
□ 7. Actions 页面手动触发测试
□ 8. 确认日志输出"打卡成功"
□ 9. （可选）配置 Telegram 通知
□ 10. 等待今晚 21:05 自动执行验证
```
