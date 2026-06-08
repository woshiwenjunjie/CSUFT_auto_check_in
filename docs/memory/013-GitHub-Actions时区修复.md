# 013 — GitHub Actions 时区修复（UTC → 北京时间）

**日期**：2026-06-08 | **版本**：v0.8.1

## 问题

Server酱通知中显示的时间是 UTC 时间（如 05:54），而非北京时间（如 13:54），相差 8 小时。

## 根因

GitHub Actions `ubuntu-latest` runner 默认时区为 **UTC**。`scripts/auto_checkin.sh` 中所有 `date` 命令未指定时区，输出均为 UTC 时间：
- `RUN_DATE` / `RUN_DATE_SHORT` — 写入通知标题和内容
- `now_ts()` — 写入步骤进度日志
- 所有通知（Server酱、Telegram、GitHub Summary）中的时间均受影响

## 修复

3 处 `date` 调用全部添加 `TZ='Asia/Shanghai'` 前缀：

```bash
# 修复前
RUN_DATE=$(date '+%Y-%m-%d %H:%M:%S')
RUN_DATE_SHORT=$(date '+%Y-%m-%d')
now_ts() { date '+%H:%M:%S'; }

# 修复后
RUN_DATE=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')
RUN_DATE_SHORT=$(TZ='Asia/Shanghai' date '+%Y-%m-%d')
now_ts() { TZ='Asia/Shanghai' date '+%H:%M:%S'; }
```

## 关键信息

- `Asia/Shanghai` = 北京时间（UTC+8），中国全境统一
- GitHub Actions cron `"5 13 * * *"` = UTC 13:05 = 北京时间 21:05
- 不要在 workflow YAML 里设 `TZ` 环境变量，会影响整个 runner 的行为，在脚本内局部使用 `TZ=` 前缀更安全

## 关联

- [[010-GitHub-Actions部署上线]]
- [[012-Server酱通知静默失败修复]]
