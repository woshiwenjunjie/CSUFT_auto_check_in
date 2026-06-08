# GitHub Actions 自动打卡教程

> 适用版本：v0.8.1 | 最后更新：2026-06-08

配置一次，每天自动打卡 + 微信通知，**无需开电脑、无需服务器、完全免费**。

---

## 目录

1. [概述](#1-概述)
2. [前置准备](#2-前置准备)
3. [部署步骤](#3-部署步骤)
4. [日常使用](#4-日常使用)
5. [手动触发与监控](#5-手动触发与监控)
6. [通知解读](#6-通知解读)
7. [故障处理](#7-故障处理)
8. [进阶配置](#8-进阶配置)

---

## 1. 概述

### 对比：本地 CLI vs GitHub Actions

| | 本地 CLI | GitHub Actions |
|------|----------|----------------|
| 执行方式 | 手动敲命令 | 每天 21:05 自动触发 |
| 需要开电脑 | ✅ | ❌ |
| 需要联网 | ✅ | ❌（云端执行） |
| 通知方式 | 终端文字 | 微信推送 |
| 费用 | 免费 | 免费（2000 分钟/月） |
| 寒假/暑假回家 | 需改坐标 | 自动（云端不变） |

### 执行原理

```
每天 21:05（北京时间）
  → GitHub 租用一台虚拟机（ubuntu-latest）
  → 拉取你的仓库代码
  → 从 GitHub Secrets 读取密码/token/OpenID
  → 写入配置文件
  → Python 脚本登录 + 打卡
  → 结果推送到微信（Server酱）
  → 虚拟机销毁（全程约 30 秒）
```

---

## 2. 前置准备

在开始部署前，确保你已具备：

| 准备项 | 说明 | 从哪里获取 |
|--------|------|-----------|
| ✅ GitHub 账号 | 免费注册 | [github.com](https://github.com) |
| ✅ OpenID | 微信小程序唯一标识 | [抓包获取OpenID完全指南](./抓包获取OpenID完全指南.md) |
| ✅ 学号 | 学校学号 | — |
| ✅ 密码 | 学校系统密码 | — |
| ✅ Server酱 SendKey | 微信推送通道 | [Server酱配置教程](./Server酱配置教程.md) |

> 如果还没有 OpenID，先看 [抓包获取OpenID完全指南](./抓包获取OpenID完全指南.md)。如果还没有 SendKey，先看 [Server酱配置教程](./Server酱配置教程.md)。

---

## 3. 部署步骤

### 3.1 Fork 仓库

打开 `https://github.com/woshiwenjunjie/CSUFT_auto_check_in`，点击右上角 **Fork** → **Create fork**。

> ⚠️ 建议 Fork 后设为 **私有仓库**（Settings → General → Danger Zone → Change visibility → Make private），保护你的凭据。

### 3.2 配置 Secrets

进入你的仓库 → Settings → Secrets and variables → Actions → **New repository secret**。

逐个添加以下 4 个必填 Secret（全部严格区分大小写）：

| Name | Value 示例 | 说明 |
|------|-----------|------|
| `CHECKIN_OPENID` | `oABC123XYZ...` | 微信 OpenID，约 28 位，`o` 开头 |
| `CHECKIN_USERNAME` | `20234152` | 学号 |
| `CHECKIN_PASSWORD` | `Wenjunjie123!` | 学校系统密码（明文，加密存储） |
| `SERVERCHAN_KEY` | `SCT361140TMTI8...` | Server酱 SendKey |

可选 Secret（不设也行）：

| Name | 说明 |
|------|------|
| `CHECKIN_TASK_ID` | 打卡任务 ID，不设则自动获取 |
| `TG_BOT_TOKEN` | Telegram 备用通知 |
| `TG_CHAT_ID` | Telegram 备用通知 |

> ⚠️ Value 直接粘贴原文，**不要加引号**。

### 3.3 手动测试

1. 仓库页面 → **Actions** 标签
2. 左侧选择 **Auto Check-In**
3. 点击 **Run workflow** → 绿色 **Run workflow** 按钮
4. 等待约 30 秒，刷新页面查看结果

展开运行记录，确认：

```
[3/5] 登录校园网 21:05:01
  => 登录成功

[5/5] 执行打卡 21:05:15
  打卡成功！

通知渠道:
  ✅ Server酱 (微信) 已配置

[通知] Server酱 HTTP 200: {"code":0,"message":"success"}
```

同时微信"方糖"公众号应收到打卡成功推送。

### 3.4 确认自动触发

部署完成后**不需要任何额外操作**。每天 21:05 自动执行，默认 cron 为：

```
"5 13 * * *"  ← UTC 时间，等于北京时间 21:05
```

---

## 4. 日常使用

### 你什么都不用做

配置完成后，系统每天自动：

1. 21:05 触发打卡
2. 微信推送打卡结果
3. 如果失败，通知里会写明原因和解决办法

### 需要你介入的情况

| 通知标题 | 含义 | 你需要做什么 |
|----------|------|-------------|
| ✅ CSUFT 打卡成功 | 正常 | 无视 |
| ⏰ CSUFT 已打卡 | 今天打过了 | 无视 |
| ⏳ CSUFT 未到签到时间 | 还不到 21:00 | 无视（21:05 才执行） |
| ⚠️ CSUFT GPS 超出范围 | GPS 偏移太大 | 手动触发一次，或不管（下次随机可能正好） |
| ❌ CSUFT Token 过期 | 登录凭据过期 | 本地跑一次 `login-openid`，更新 Secrets |
| ❌ CSUFT 打卡失败 | 登录/网络失败 | 检查 Secrets 凭据，查看 Actions 日志 |

### 假期/离校

- 打卡系统根据你的 GPS 坐标判断是否在校
- GitHub Actions 云端坐标不受你实际位置影响，始终使用模拟坐标
- 寒暑假回家后正常自动打卡，无需修改任何配置

---

## 5. 手动触发与监控

### 随时手动打卡

Actions → Auto Check-In → Run workflow → Run workflow

### 查看历史日志

Actions → Auto Check-In → 点击任意一次运行 → 展开"执行打卡"步骤

每次日志保留 7 天（作为 Artifact），可在运行页面底部下载 `checkin-log`。

### GitHub 邮件兜底

Settings → Notifications → 勾选 **"Email notification for failed workflows"**

即使 Server酱 出问题，失败的打卡也能收到 GitHub 邮件通知。

---

## 6. 通知解读

所有通知均为 **Markdown 格式**，包含完整的日期、状态、失败原因等信息。

### 成功通知

```
✅ CSUFT 打卡成功

| 项目 | 详情 |
|------|------|
| 日期 | 2026-06-08 |
| 状态 | 正常 |
| 距宿舍 | 12.0m |

⏰ 2026-06-08 21:05:23
```

### 失败通知（含解决办法）

```
⚠️ CSUFT GPS 超出范围

日期：2026-06-08
距宿舍：156.0m

原因：随机生成的模拟坐标距离宿舍太远，超过了学校要求的精度范围。

解决办法：在本地用减小偏移量的方式重试：
`python scripts/cli.py checkin --offset 0.0001`
```

---

## 7. 故障处理

### 通用排查流程

1. **看微信**：收到通知了吗？标题是什么？
2. **看 Actions 日志**：搜索 `[通知]`，看 Server酱 返回了什么？
3. **看 Actions 摘要**：运行页面底部有 Markdown 打卡报告表
4. **下载日志**：Artifact `checkin-log` 包含完整执行日志

### 常见问题

**Q: 连续几天没收到任何通知？**

A: 
1. 打开 Actions 页面，看是否还有运行记录
2. 如果 60 天内没有任何运行记录 → workflow 可能被停用了（GitHub 规则）
3. 手动触发一次即可唤醒（项目已内置每日保活 commit，一般不会触发停用）

**Q: 提示"未到签到时间"？**

A: 正常。打卡窗口 21:00-22:30，工作流 21:05 触发。如果是手动触发（比如下午 3 点），就会看到这个提示。

**Q: 提示"超出打卡范围"？**

A: 随机 GPS 偏移恰好偏远了。通常下次自动打卡就能正常。如果连续出现，可以手动触发一次或减小 offset。

**Q: 微信收得到推送但 Telegram 收不到？**

A: Telegram 需要科学上网。GitHub Actions 的 runner 通常在海外，访问 Telegram API 没问题。检查 `TG_BOT_TOKEN` 和 `TG_CHAT_ID` 是否正确，Bot 是否被 block。

**Q: 学校更换了打卡系统怎么办？**

A: 拉取上游仓库最新代码合并。如果 API 协议有重大变更，项目会更新适配。

---

## 8. 进阶配置

### 修改打卡时间

编辑 `.github/workflows/auto-checkin.yml`：

```yaml
on:
  schedule:
    - cron: "5 13 * * *"   # 改这里
```

Cron 表达式是 **UTC 时间**，5 个字段：`分 时 日 月 星期`。北京时间 = UTC + 8。

| 想设置的时间 | cron |
|-------------|------|
| 每天 21:05 | `5 13 * * *` |
| 每天 21:30 | `30 13 * * *` |
| 每天 07:00 | `0 23 * * *`（前一天 23:00 UTC） |

> ⚠️ 修改 cron 后需等待 GitHub 重新调度，可能需要几分钟到几小时生效。

### 调整 GPS 偏移量

默认偏移 `±0.0003°`（约 30 米）。如果经常超出范围，可以在 workflow 中修改：

编辑 `.github/workflows/auto-checkin.yml`，在"执行打卡"步骤的 `run` 中添加：

```yaml
run: bash scripts/auto_checkin.sh --offset 0.0001
```

然后同步修改 `scripts/auto_checkin.sh` 中 `checkin` 命令的参数。

### 同步上游更新

当原始仓库（woshiwenjunjie/CSUFT_auto_check_in）有更新时：

```bash
# 本地添加 upstream 远程
git remote add upstream https://github.com/woshiwenjunjie/CSUFT_auto_check_in.git

# 拉取并合并
git fetch upstream
git merge upstream/main

# 推送到你的仓库
git push origin main
```

---

## 参考资料

- `docs/guides/dev/GitHub-Actions部署记录.md` — 开发者视角的部署记录（含技术细节）
- `docs/guides/user/Server酱配置教程.md` — Server酱 详细配置
- `docs/guides/user/CLI教程.md` — 本地 CLI 详细用法
- `docs/guides/user/完整操作指南.md` — 从零开始的完整指南
- `docs/memory/010-GitHub-Actions部署上线.md` — 部署里程碑记录
