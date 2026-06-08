# GitHub Actions 自动打卡部署记录

> 日期：2026-06-08 | 仓库：woshiwenjunjie/CSUFT_auto_check_in

---

## 1. 部署架构

```
GitHub Actions (ubuntu-latest)
  │  cron: "5 13 * * *"  → 每天 21:05 北京时间
  │  workflow_dispatch    → 支持手动触发
  ▼
  ① 写入配置文件（从 GitHub Secrets 注入凭据）
  ② pip install 依赖
  ③ login-openid 登录换取 access_token
  ④ checkin 一键打卡
  ⑤ 结果通知（Server酱微信 + Telegram 备用）
```

---

## 2. 文件清单

| 文件 | 作用 |
|------|------|
| `.github/workflows/auto-checkin.yml` | GitHub Actions 工作流定义 |
| `scripts/auto_checkin.sh` | bash 执行脚本，统一的 `notify()` 多通道分发 |

---

## 3. GitHub Secrets 配置

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 | 必填 |
|-------------|------|:--:|
| `CHECKIN_OPENID` | 微信 OpenID | ✅ |
| `CHECKIN_USERNAME` | 学号 | ✅ |
| `CHECKIN_PASSWORD` | 学校系统密码 | ✅ |
| `SERVERCHAN_KEY` | Server酱 SendKey（微信推送） | 推荐 |
| `CHECKIN_TASK_ID` | 打卡任务 ID（不设自动获取） | |
| `TG_BOT_TOKEN` | Telegram Bot Token（备用） | |
| `TG_CHAT_ID` | Telegram Chat ID（备用） | |

> ⚠️ Secret 值不要加引号，直接粘贴原文。GitHub 存储层 AES-256 加密。

---

## 4. 执行流程

### 4.1 自动触发
- 每天 **21:05**（北京时间）自动执行
- 对应 cron：`5 13 * * *`（UTC 时间）
- 私有仓库 2000 分钟/月（每次约 30 秒，完全够用）

### 4.2 手动触发
Actions 页面 → Auto Check-In → Run workflow → Run workflow

### 4.3 脚本步骤（带进度指示）
```
[1/5] 配置写入完成
[2/5] 安装依赖...
[3/5] 登录校园网...
[4/5] 获取任务...
[5/5] 执行打卡...
```

---

## 5. 打卡结果判断

> **所有结果都会发送 Server酱 微信通知**，包括成功、已打卡、未到时间、失败等，每条通知都写明原因。

| 服务器返回 | 行为 | 退出码 | 通知内容 |
|-----------|------|:--:|------|
| 打卡成功 | 正常退出 | 0 | ✅ 成功，含日期、状态、距离 |
| 已打卡/重复 | 正常退出 | 0 | ⏰ 今日已签到，无需重复 |
| 未到签到时间 | 正常退出 | 0 | ⏳ 不在窗口内（21:00–22:30） |
| 超出打卡范围 | 退出报错 | 1 | ⚠️ GPS 过远，含距离 + 修复建议 |
| Token 过期 | 退出报错 | 1 | ❌ 凭据过期，含续期操作指引 |
| 其他错误 | 退出报错 | 1 | ❌ 服务器返回原文 + 日志链接 |

---

## 6. 通知方式

### Server酱（微信推送）— 推荐

1. 打开 [sct.ftqq.com](https://sct.ftqq.com) 微信扫码登录
2. 复制 SendKey（`SCT` 开头的一串字符）
3. 添加到 GitHub Secrets：Name = `SERVERCHAN_KEY`，Value = 你的 SendKey
4. 关注公众号"方糖"（扫码页面有二维码）
5. 手动触发一次 workflow，在日志中验证 `[通知] Server酱 HTTP 200: {"code":0...}`

#### 通知格式

每条通知都用 Markdown 排版，包含：

- **标题**：一目了然的状态（✅ 成功 / ❌ 失败 / ⏰ 已打卡 / ⏳ 未到时间）
- **详情**：日期、打卡状态、距宿舍距离、执行时间
- **失败时**：额外附带失败原因 + 修复建议 + Actions 日志链接

#### 调试：收不到通知怎么办

在 Actions 日志中搜索 `[通知]`，会看到类似输出：

```
通知渠道:
  ✅ Server酱 (微信) 已配置          ← 确认 Key 已注入
  ⚠️  Telegram 未配置（可选备用渠道）

[通知] 正在发送 Server酱 推送...
[通知] Server酱 HTTP 200: {"code":0,"message":"success"}   ← 成功
```

常见错误码：

| HTTP | code | 含义 | 解决 |
|------|------|------|------|
| 200 | 0 | ✅ 发送成功 | — |
| 200 | 30001 | 内容编码错误 | 更新到最新脚本（已用 `--data-urlencode`） |
| 200 | 40001 | SendKey 无效 | 检查 Secret 值是否完整复制 |
| 000 | — | 网络不通 | GitHub Actions 无法访问 sctapi.ftqq.com（罕见） |

> ⚠️ **旧版脚本的坑**：v0.8.0 初版用 `printf + --data-binary @-` 发送 Markdown，特殊字符未做 URL 编码，且 `> /dev/null 2>&1` 丢弃了 API 响应，导致静默失败。v0.8.1 已修复为 `--data-urlencode` + 响应日志。

### Telegram Bot（备用）

1. `@BotFather` 创建 Bot → 获取 Token
2. 给 Bot 发一条消息，访问 `https://api.telegram.org/bot<TOKEN>/getUpdates` 获取 Chat ID
3. 添加到 Secrets：`TG_BOT_TOKEN` + `TG_CHAT_ID`

### GitHub 内置邮件（兜底）

Settings → Notifications → 勾选 "Email notification for failed workflows"
仅失败时通知，无需额外配置。

---

## 7. 日志与排查

- 每次执行日志保留 7 天（Artifact：`checkin-log`）
- Actions 页面自动生成 Markdown 步骤摘要（打卡报告表）
- 脚本启动时打印通知渠道状态，确认哪些渠道已配置
- 通知发送后打印 HTTP 状态码和 API 响应，方便定位问题

### 常见问题

| 现象 | 可能原因 | 排查步骤 |
|------|----------|----------|
| **收不到微信通知** | Key 未配置/错误 | 日志搜 `[通知]`，看是"未配置"还是 API 报错 |
| **"未到签到时间"** | 正常 | 窗口为 21:00–22:30，21:05 自动触发 |
| **"Token 已过期"** | 不会出现 | 脚本每次全新登录，Token 始终有效 |
| **"超出打卡范围"** | GPS 偏移过大 | 本地执行 `--offset 0.0001` 重试 |
| **日志显示 HTTP 000** | 网络不通 | GitHub Actions 无法访问 sctapi.ftqq.com |
| **关注了公众号但没收到** | 公众号不对 | 确认是"方糖"而非其他公众号 |

---

## 8. 安全说明

- 凭据通过 GitHub Secrets 注入，日志中自动 `***` 屏蔽
- `password.txt` 已加入 `.gitignore`，不会提交
- 仓库为私有，代码 + Secrets 均对外不可见
- 每次 Action 运行于隔离临时容器，结束后销毁
- 脚本中所有 `GITHUB_*` 变量均有默认值，本地也可运行
