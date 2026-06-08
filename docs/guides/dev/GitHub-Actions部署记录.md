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

| 服务器返回 | 行为 | 退出码 | 通知 |
|-----------|------|:--:|------|
| 打卡成功 | 正常退出 | 0 | ✅ 微信通知 |
| 已打卡/重复 | 正常退出 | 0 | ⏰ 微信告知 |
| 未到签到时间 | 正常退出 | 0 | 不发通知 |
| 超出打卡范围 | 退出报错 | 1 | ⚠️ 微信 + 建议 |
| Token 过期 | 退出报错 | 1 | ❌ 微信 + 指引 |
| 其他错误 | 退出报错 | 1 | ❌ 微信 + 日志 |

---

## 6. 通知方式

### Server酱（微信推送）— 推荐
1. 打开 [sct.ftqq.com](https://sct.ftqq.com) 微信扫码
2. 复制 SendKey（`SCT` 开头）
3. 添加到 GitHub Secrets：`SERVERCHAN_KEY`
4. 关注公众号"方糖"（扫码页面有）

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
- 常见问题：
  - **"未到签到时间"** — 正常，窗口为 21:00-22:30
  - **"Token 已过期"** — 脚本每次重新登录，不会出现
  - **"超出打卡范围"** — GPS 偏移过大，调整 `--offset` 参数
  - **"收不到通知"** — 检查 Secrets 拼写 + 公众号是否关注

---

## 8. 安全说明

- 凭据通过 GitHub Secrets 注入，日志中自动 `***` 屏蔽
- `password.txt` 已加入 `.gitignore`，不会提交
- 仓库为私有，代码 + Secrets 均对外不可见
- 每次 Action 运行于隔离临时容器，结束后销毁
- 脚本中所有 `GITHUB_*` 变量均有默认值，本地也可运行
