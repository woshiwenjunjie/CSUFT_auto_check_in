# Server酱 微信推送配置教程

> 适用版本：v0.8.1 | 最后更新：2026-06-08

将 GitHub Actions 打卡结果推送到微信，**免费、无需实名、扫码即用**。

---

## 目录

1. [什么是 Server酱](#1-什么是-server酱)
2. [获取 SendKey](#2-获取-sendkey)
3. [配置 GitHub Secrets](#3-配置-github-secrets)
4. [验证推送](#4-验证推送)
5. [通知内容说明](#5-通知内容说明)
6. [故障排查](#6-故障排查)
7. [进阶：多通道通知](#7-进阶多通道通知)

---

## 1. 什么是 Server酱

Server酱（原名"方糖推送"）是一个免费的消息推送服务，通过微信企业号"方糖"将服务器消息推送到你的微信。

| 特性 | 说明 |
|------|------|
| 费用 | 免费（个人版无限制） |
| 实名认证 | **不需要** |
| 接入方式 | 微信扫码 → 获取 SendKey → POST API |
| 支持格式 | 纯文本 / Markdown |
| API 地址 | `https://sctapi.ftqq.com/{SendKey}.send` |

> 本项目弃用了 PushPlus（需付费实名认证），选用 Server酱 作为主通知渠道。

---

## 2. 获取 SendKey

### 步骤 1：打开 Server酱 官网

用 **手机微信** 扫描下方流程操作：

1. 手机浏览器打开 [sct.ftqq.com](https://sct.ftqq.com)
2. 点击页面上的 **"微信扫码登录"**
3. 用微信扫描二维码
4. 页面自动跳转到控制台

### 步骤 2：复制 SendKey

登录后在控制台页面找到 **SendKey**（以 `SCT` 开头的一长串字符）：

```
SCT361140TMTI8GjqdEV2UHMyjWUSjHXEe  ← 示例格式，实际值完全不同
```

点击复制按钮，保存好这个值。**不要泄露给任何人**，拥有 SendKey 就能给你发推送。

### 步骤 3：关注公众号

在同一页面扫描 **"方糖"公众号** 二维码并关注。不关注的话消息发不出去（企业号限制）。

> ⚠️ 关键：必须关注公众号"方糖"，不是其他公众号。Server酱 通过企业微信应用推送，未关注则收不到消息。

---

## 3. 配置 GitHub Secrets

### 步骤 1：打开仓库 Secrets 页面

```
https://github.com/你的用户名/CSUFT_auto_check_in/settings/secrets/actions
```

或手动导航：仓库主页 → Settings → Secrets and variables → Actions

### 步骤 2：新建 Secret

点击绿色按钮 **New repository secret**：

| 字段 | 填写内容 |
|------|----------|
| **Name** | `SERVERCHAN_KEY`（严格区分大小写，必须一模一样） |
| **Value** | 粘贴你的 SendKey（如 `SCT361140TMTI8GjqdEV2UHMyjWUSjHXEe`） |

点击 **Add secret** 保存。

### 步骤 3：确认 Secret 列表

确保 Actions secrets 列表中出现：

```
SERVERCHAN_KEY    *** (已隐藏)
```

---

## 4. 验证推送

### 方式 1：手动触发 GitHub Actions

1. 打开 Actions 页面 → 左侧选 **Auto Check-In**
2. 点击 **Run workflow** → **Run workflow**
3. 等待约 30 秒
4. 点击进入运行记录 → 展开"执行打卡"步骤
5. 搜索日志中的 `[通知]` 关键字：

```
通知渠道:
  ✅ Server酱 (微信) 已配置

[通知] 正在发送 Server酱 推送...
[通知] Server酱 HTTP 200: {"code":0,"message":"success"}
```

6. 检查微信 → "方糖"公众号 → 应收到打卡结果推送

### 方式 2：本地测试

```bash
# 替换为你的 SendKey 测试
curl -X POST "https://sctapi.ftqq.com/你的SendKey.send" \
  --data-urlencode "title=测试" \
  --data-urlencode "desp=如果你看到这条消息，说明 Server酱 配置成功！"
```

---

## 5. 通知内容说明

本项目发出的所有通知均为 **Markdown 格式**，包含完整的打卡结果信息：

### 成功示例

```
标题: ✅ CSUFT 打卡成功

内容:
## ✅ 打卡成功

| 项目 | 详情 |
|------|------|
| 日期 | 2026-06-08 |
| 状态 | 正常 |
| 距宿舍 | 12.0m |

⏰ 2026-06-08 21:05:23
```

### 其他结果类型

| 标题 | 含义 | 是否需要处理 |
|------|------|:--:|
| ✅ CSUFT 打卡成功 | 打卡正常 | 不用 |
| ⏰ CSUFT 已打卡 | 今日已签过到了 | 不用 |
| ⏳ CSUFT 未到签到时间 | 还未到 21:00 | 不用（21:05 自动执行） |
| ⚠️ CSUFT GPS 超出范围 | 随机偏移过大 | 需要（本地重试减小 offset） |
| ❌ CSUFT Token 过期 | 凭据过期 | 需要（重新登录更新 Secrets） |
| ❌ CSUFT 打卡失败 | 登录失败/网络问题 | 需要（检查凭据或网络） |

---

## 6. 故障排查

### 日志搜索法（最重要）

在 GitHub Actions 运行日志中 **搜索 `[通知]`**：

```
[通知] SERVERCHAN_KEY 未配置，跳过 Server酱
  → 未配置 Secret，回到第 3 节配置

[通知] Server酱 HTTP 200: {"code":0,"message":"success"}
  → API 调用成功，检查微信"方糖"公众号

[通知] Server酱 HTTP 200: {"code":30001,...}
  → 编码错误，更新脚本到最新版本（v0.8.1+）

[通知] Server酱 HTTP 200: {"code":40001,...}
  → SendKey 无效，重新从 sct.ftqq.com 复制

[通知] Server酱 HTTP 000:
  → 网络不通，GitHub Actions 无法访问 sctapi.ftqq.com
```

### 错误码速查

| HTTP | code | 含义 | 解决办法 |
|------|------|------|----------|
| 200 | 0 | ✅ 成功 | 检查微信是否收到 |
| 200 | 30001 | 内容编码错误 | 更新到最新脚本 |
| 200 | 40001 | SendKey 无效 | 重新复制 SendKey |
| 200 | 40002 | 消息内容过长 | 简化通知内容 |
| 000 | — | curl 连接失败 | GitHub Actions 网络问题（罕见） |

### 常见问题

**Q: 日志显示成功但微信没收到？**

A: 确认关注了公众号"方糖"（不是"方糖推送"或其他）。打开微信 → 通讯录 → 公众号 → 搜索"方糖"。

**Q: 公众号里看不到历史消息？**

A: Server酱 是企业微信应用推送，没有历史记录。每条消息独立推送，推送时就能看到。

**Q: 能同时推送到多个微信吗？**

A: SendKey 绑定一个微信。如需多人接收，可配置 Telegram 备用通道（见第 7 节）。

---

## 7. 进阶：多通道通知

项目支持 3 层通知，`notify()` 函数自动分发到所有已配置渠道：

| 渠道 | 配置 | 优先级 |
|------|------|:--:|
| Server酱 | `SERVERCHAN_KEY` | 主（微信推送） |
| Telegram | `TG_BOT_TOKEN` + `TG_CHAT_ID` | 备用 |
| GitHub 邮件 | Settings → Notifications | 兜底（仅失败） |

### Telegram 配置（可选）

1. 在 Telegram 搜索 `@BotFather`，发送 `/newbot`
2. 按提示创建 Bot，获得 Token
3. 给新 Bot 发任意一条消息
4. 浏览器访问 `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. 从返回的 JSON 中找到 `"chat":{"id":123456789}`
6. 在 GitHub Secrets 中添加：
   - `TG_BOT_TOKEN` = Bot Token
   - `TG_CHAT_ID` = Chat ID

配置后，打卡结果会同时推送到微信和 Telegram。

---

## 参考资料

- Server酱 官网：[sct.ftqq.com](https://sct.ftqq.com)
- `docs/guides/dev/GitHub-Actions部署记录.md` — 部署详细记录含通知调试章节
- `docs/guides/user/GitHub-Actions自动打卡教程.md` — GitHub Actions 完整教程
- `docs/memory/011-Server酱通知切换.md` — PushPlus → Server酱 切换记录
- `docs/memory/012-Server酱通知静默失败修复.md` — 通知修复记录
