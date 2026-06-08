# 010 — GitHub Actions 自动打卡部署上线

**日期**：2026-06-08 | **版本**：v0.8.0

## 背景

用户 woshiwenjunjie（学号 20234152）完成本地 CLI 验证后，需要将打卡迁移到云端自动执行。

## 技术决策

- **平台**：GitHub Actions（免费、零维护、无需服务器）
- **触发**：每天 UTC 13:05（北京时间 21:05）+ 手动 workflow_dispatch
- **通知**：PushPlus（微信推送）+ GitHub 内置邮件兜底
- **凭据管理**：GitHub Secrets（AES-256 加密存储）

## 新增文件

| 文件 | 用途 |
|------|------|
| `.github/workflows/auto-checkin.yml` | GitHub Actions 工作流定义 |
| `scripts/auto_checkin.sh` | bash 执行脚本（登录→获取任务→打卡→通知） |
| `docs/guides/dev/GitHub-Actions部署记录.md` | 部署文档（隐私已脱敏） |

## 执行链路

```
GitHub Secrets 注入
  → 写 config.json
  → pip install
  → login-openid --bind 0（每次全新登录）
  → tasks（自动获取任务 ID）
  → checkin（一键打卡）
  → 结果判断 → PushPlus 微信通知
```

## 打卡结果处理

| 服务器返回 | 行为 | 通知 |
|-----------|------|------|
| 打卡成功 | 正常退出 | ✅ 卡片式 HTML 推送 |
| 已打卡/重复 | 正常退出 | ⚠️ 告知无需重复 |
| 未到签到时间 | 正常退出 | 不推送（避免骚扰） |
| 超出范围 | 退出码 1 | ⚠️ 含距离和建议 |
| Token 过期 | 退出码 1 | ❌ 含续期操作指引 |
| 未知错误 | 退出码 1 | ❌ 含日志片段 |

## PushPlus 通知格式

采用 `template=html`，成功时推送表格卡片（日期、状态、距离、坐标、执行时间），失败时推送错误原因和修复建议。所有通知底部带"中南林业科技大学 · 自动晚点名"品牌标识。

## 安全措施

- 密码和凭据仅存储在 GitHub Secrets 中
- `password.txt` 已在 `.gitignore`，不会被提交
- 仓库为私有
- 日志中敏感信息自动被 GitHub 屏蔽（`***`）
- 每次 Action 运行于隔离临时容器

## 分支设置

- 默认分支：`main`
- 仓库地址：https://github.com/woshiwenjunjie/CSUFT_auto_check_in

## 待验证

- ⏳ 今晚 21:05 自动触发首次打卡
- ⏳ PushPlus 推送实际效果
- ⏳ 一个月后验证 token 自动续期是否有效（每次全新 login-openid）
