# 016 — 时区修复与 cron 调度排错（2026-06-09）

## 背景

v0.8.2 做了一个「UTC 时间规范化」改动：
- 通知文案全部改为 UTC 标注（如 `🕐 13:05 UTC`）
- 但 `RUN_DATE` 使用 bash `date` + `TZ=Asia/Shanghai` 获取
- 同时 `TZ` 环境变量在 workflow 中设置

结果引发三个连锁 bug，花了一整天才全部修完。

---

## Bug 1：通知时间标注混乱

**现象**：通知里显示的时间用户完全看不懂，不知道是 UTC 还是北京时间。

**根因**：
- bash `date` + `TZ=Asia/Shanghai` 在 GitHub Actions Ubuntu runner 上**不可靠**
- `date` 输出可能是 UTC 也可能是北京时间，无法预测
- 通知硬编码 `UTC` 标签，与 `date` 实际输出不一致

**修复**：
- `auto_checkin.sh`：放弃 bash `date`，全部改用 Python `datetime.now(timezone(timedelta(hours=8)))`
- `_beijing_now()` 函数输出三个值：完整日期时间、短日期、时间
- `now_ts()` 同样改用 Python
- 通知标签全部改为「北京时间」
- workflow keepalive 步骤同步改用显式时区

**关键代码**：
```bash
_beijing_now() {
    python -c "
from datetime import datetime, timezone, timedelta
tz = timezone(timedelta(hours=8))
n = datetime.now(tz)
print(n.strftime('%Y-%m-%d %H:%M:%S'), n.strftime('%Y-%m-%d'), n.strftime('%H:%M:%S'))
"
}
read -r RUN_DATE RUN_DATE_SHORT _NOW_TIME <<< "$(_beijing_now)"

now_ts() { python -c "from datetime import datetime,timezone,timedelta;print(datetime.now(timezone(timedelta(hours=8))).strftime('%H:%M:%S'))"; }
```

---

## Bug 2：TZ 环境变量可能影响 cron 调度器

**现象**：用户反馈 action 在北京时间 13:00 触发（而非预期的 21:05）。

**推测**：`TZ=Asia/Shanghai` 可能导致 GitHub Actions 的 cron 调度器将 `5 13 * * *` 解释为北京时间 13:05（而非 UTC 13:05）。

**修复**：
- 从 workflow `env` 中移除 `TZ: Asia/Shanghai`
- 所有时间显示已由 Python 显式处理，不再需要系统时区变量

**教训**：
- GitHub Actions cron **应为 UTC**（官方文档明确），不要设 TZ 环境变量
- 所有时间转换统一在 Python 代码中完成，不依赖系统时区
- [[015-beijing-timezone-fix-final]]

---

## Bug 3：状态名称不匹配 — 成功误判为失败

**现象**：打卡明明成功，但脚本 exit code 1，通知发"打卡失败"。

**根因**：
- 服务器 `signStatusName` 返回的是 **"正常"**（不是 STATUS_MAP 的 "已打卡"）
- `auto_checkin.sh` 的 case 只匹配 `"已打卡"|"迟到"`，匹配不到就落到 `*` 分支当失败处理
- CLI 代码：`info.get("signStatusName", "") or STATUS_MAP.get(sc, "未知")` — 优先用服务器返回值

**修复**：
- `auto_checkin.sh`：case 新增 `"正常"` 匹配
- `cli_ui.py`：STATUS_MAP 0 改 `"已打卡"` → `"正常"`，与服务器一致

**教训**：
- **不要假设服务器返回的状态名称**，实际抓一次输出确认
- bash case 语句应包含所有可能的服务器返回值
- [[004-CLI工具开发完成]]

---

## Bug 4：Cron 不触发 / 没显示 "Next scheduled run"

**现象**：新仓库的 schedule 没有显示下一次运行时间，cron 从未自动触发。

**可能原因**：
1. 仓库太新（创建不到 24 小时），GitHub 调度器尚未注册
2. 同一天内频繁修改 workflow 文件（今天改了 5 次），导致调度器不断重置
3. `TZ` 环境变量干扰（已移除）

**当前状态**：手动触发正常，等待明天北京时间 21:05 验证 cron 是否自动触发。

**排查步骤**：
1. 仓库 → Actions → Auto Check-In → 查看是否有"Next scheduled run"
2. 如果没有 → Settings → Actions → General → 确认 "Allow all actions"
3. 停止修改 workflow 文件 24 小时，等待调度器稳定

---

## 关键教训总结

| # | 教训 | 影响 |
|---|------|------|
| 1 | bash `date` + TZ 不可靠 → 用 Python 显式时区 | 时间显示 |
| 2 | TZ 环境变量不能设在 workflow → 可能影响 cron | 触发时间 |
| 3 | 状态名称必须与服务器返回值一致 | 通知内容 |
| 4 | 新仓库 workflow 不要频繁修改 → 影响 cron 注册 | 调度 |

## 关联

- [[015-beijing-timezone-fix-final]] — 北京时间修复最终方案
- [[014-UTC时间坑]] — UTC 时间陷阱（部分结论已被本记录修正）
- [[013-GitHub-Actions时区修复]]
- [[004-CLI工具开发完成]]
