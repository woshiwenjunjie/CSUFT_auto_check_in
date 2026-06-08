# 012 — Server酱通知静默失败修复

**日期**：2026-06-08 | **版本**：v0.8.1

## 背景

GitHub Actions 部署完成后，手动/自动触发均收不到 Server酱 微信推送通知。但 `SERVERCHAN_KEY` 已正确添加到 GitHub Secrets。

## 根因分析

`scripts/auto_checkin.sh` 的 `send_serverchan()` 函数存在两个隐蔽 bug：

### Bug 1：Markdown 内容未做 URL 编码

旧代码用 `printf 'title=%s&desp=%s' | curl --data-binary @-` 方式发送表单数据。`desp` 内容为 Markdown，包含换行符、管道符 `|`、井号 `#` 等特殊字符，这些字符在 `application/x-www-form-urlencoded` 格式中必须做百分号编码。未编码导致 Server酱 API 解析表单失败（静默返回错误）。

### Bug 2：API 响应被完全丢弃

`> /dev/null 2>&1 || true` 把 curl 的标准输出和标准错误全部重定向到 `/dev/null`，无论 API 返回成功还是错误码，日志中毫无痕迹。两个 bug 叠加 = **彻头彻尾的盲操作** — 调了 API 但既不知道成功没，也不知道失败原因。

## 修复内容

### 1. URL 编码 → `--data-urlencode`

```bash
# 旧 ❌
printf 'title=%s&desp=%s' "${title}" "${desp}" | curl ... --data-binary @- ...

# 新 ✅
curl ... --data-urlencode "title=${title}" --data-urlencode "desp=${desp}"
```

`--data-urlencode` 让 curl 自动对参数值做百分号编码，无论内容多复杂都能正确传输。

### 2. 响应捕获 → 日志可见

```bash
# 旧 ❌
curl ... > /dev/null 2>&1 || true

# 新 ✅
resp=$(curl -s -w "\n%{http_code}" ... 2>&1) || true
http_code=$(echo "$resp" | tail -1)
body=$(echo "$resp" | sed '$d')
echo "  [通知] Server酱 HTTP ${http_code}: ${body}" | tee -a "$LOG_FILE"
```

### 3. 渠道状态检查

脚本启动时打印通知渠道配置状态，一眼看出 Key 是否注入成功：

```
通知渠道:
  ✅ Server酱 (微信) 已配置
  ⚠️  Telegram 未配置（可选备用渠道）
```

## Server酱 错误码速查

| HTTP | code | 含义 | 解决 |
|------|------|------|------|
| 200 | 0 | 成功 | — |
| 200 | 30001 | 内容编码错误 | 更新到最新脚本 |
| 200 | 40001 | SendKey 无效 | 检查 Secret 值 |
| 000 | — | 网络不通 | 检查 Actions 网络 |

## 教训

1. **API 调用的响应永远不要丢弃** — 至少记录状态码，最好记录响应体
2. **不要假设简单文本 = 不需要编码** — Markdown 含大量需要 URL 编码的字符
3. **静默失败是最坏的失败模式** — 失败不可怕，不知道失败了才可怕

## 关联

- [[010-GitHub-Actions部署上线]] — 部署背景
- [[011-Server酱通知切换]] — PushPlus → Server酱 切换决策
