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
  ⑤ 结果通知（PushPlus 微信推送）
```

---

## 2. 文件清单

| 文件 | 作用 |
|------|------|
| `.github/workflows/auto-checkin.yml` | GitHub Actions 工作流定义 |
| `scripts/auto_checkin.sh` | 被 Action 调用的 bash 执行脚本 |

---

## 3. GitHub Secrets 配置

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 | 示例 |
|-------------|------|------|
| `CHECKIN_OPENID` | 微信 OpenID | `o************************U` |
| `CHECKIN_USERNAME` | 学号 | `2023****` |
| `CHECKIN_PASSWORD` | 学校系统密码 | `********` |
| `PUSHPLUS_TOKEN` | PushPlus 推送 Token（可选） | `f4df********************c60a3` |
| `CHECKIN_TASK_ID` | 打卡任务 ID（可选，不设自动获取） | — |

> ⚠️ Secret 值不要加引号，直接粘贴原文。GitHub 存储层 AES-256 加密。

---

## 4. 执行流程

### 4.1 自动触发
- 每天 **21:05**（北京时间）自动执行
- 对应 cron：`5 13 * * *`（UTC 时间）
- 公开仓库无限制免费，私有仓库 2000 分钟/月（每次约 30 秒）

### 4.2 手动触发
Actions 页面 → Auto Check-In → Run workflow → Run workflow

### 4.3 脚本步骤
1. **写入配置** — 从 Secrets 环境变量生成 `~/.auto_check_in/config.json`
2. **安装依赖** — `pip install -r requirements.txt`
3. **登录** — `login-openid --bind 0`，仅登录不绑定
4. **获取任务** — 若未设 `CHECKIN_TASK_ID` 则自动获取
5. **打卡** — `checkin` 一键签到
6. **通知** — PushPlus 微信推送（成功/失败均有通知）

---

## 5. 打卡结果判断

| 服务器返回 | 脚本行为 | 退出码 |
|-----------|---------|:--:|
| 打卡成功 / 已打卡 / 重复 | 发成功通知 | 0 |
| 未到签到时间 | 正常退出（不在 21:00-22:30 窗口） | 0 |
| 超出打卡范围 | 发警告通知 | 1 |
| Token 已过期 | 发失败通知 | 1 |
| 其他错误 | 发失败通知 | 1 |

---

## 6. 通知方式

### PushPlus（微信推送）
1. 打开 [pushplus.plus](http://www.pushplus.plus) 微信扫码
2. 复制 Token
3. 添加到 GitHub Secrets：`PUSHPLUS_TOKEN`

### Telegram（备用）
1. `@BotFather` 创建 Bot → 获取 Token
2. 添加到 Secrets：`TG_BOT_TOKEN` + `TG_CHAT_ID`

### GitHub 内置邮件
Settings → Notifications → 勾选 "Email notification for failed workflows"
（仅失败时通知，无需额外配置）

---

## 7. 日志与排查

- 每次执行日志保留 7 天（Artifact）
- 在 Actions 运行详情页下载 `checkin-log` 查看完整输出
- 常见问题：
  - **"未到签到时间"** — 正常，窗口为 21:00-22:30
  - **"Token 已过期"** — 脚本每次重新登录，不会出现
  - **"超出打卡范围"** — GPS 偏移过大，调整 `--offset` 参数

---

## 8. 安全说明

- 凭据通过 GitHub Secrets 注入，日志中自动 `***` 屏蔽
- `password.txt` 已加入 `.gitignore`，不会提交
- 仓库设为私有，代码 + Secrets 均对外不可见
- 每次 Action 运行在隔离的临时虚拟机，结束后销毁
