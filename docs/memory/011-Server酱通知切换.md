# 011 — Server酱通知切换

**日期**：2026-06-08 | **版本**：v0.8.0

## 背景

PushPlus 推送通知要求实名认证（`code:905`），个人使用门槛过高。

## 决策

切换到 **Server酱** 作为主通知渠道：

| 对比 | PushPlus | Server酱 |
|------|----------|----------|
| 实名认证 | ❌ 必需 | ✅ 不需要 |
| 费用 | 免费 | 免费 |
| 接入方式 | 微信扫码 | 微信扫码 |
| API 地址 | pushplus.plus | sctapi.ftqq.com |
| 参数格式 | `token` + `content` | `SendKey` + `desp` |

## 代码变更

- `scripts/auto_checkin.sh`：新增 `send_serverchan()` 函数，API 格式为 `POST https://sctapi.ftqq.com/${SERVERCHAN_KEY}.send`
- 新增统一通知函数 `notify(title, desp, telegram_msg)`，一次调用分发到所有已配置渠道
- `.github/workflows/auto-checkin.yml`：新增 `SERVERCHAN_KEY` 环境变量注入
- `password.txt`：新增 `SERVERCHAN_KEY` 字段

## GitHub Secrets 新增

- `SERVERCHAN_KEY` — Server酱 SendKey（`SCT` 开头）

## 通知渠道优先级

1. Server酱（主）— 免费微信推送，扫码即用
2. Telegram Bot（备用）— 需科学上网
3. GitHub 内置邮件（兜底）— 仅失败通知，零配置

## 用户操作

1. 打开 sct.ftqq.com 微信扫码
2. 复制 SendKey
3. 添加到 GitHub Secrets：`SERVERCHAN_KEY`
4. 关注公众号"方糖"
