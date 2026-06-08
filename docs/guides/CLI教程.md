# Auto Check-In CLI 使用教程

> 适用版本：v0.7.1+  
> 项目：中南林业科技大学自动晚点名打卡工具

---

## 目录

1. [快速开始](#1-快速开始)
2. [命令速查表](#2-命令速查表)
3. [首次配置](#3-首次配置)
4. [日常使用流程](#4-日常使用流程)
5. [命令详解](#5-命令详解)
6. [高级用法](#6-高级用法)
7. [配置与凭据管理](#7-配置与凭据管理)
8. [故障排查](#8-故障排查)

---

## 1. 快速开始

```powershell
# 激活虚拟环境
.\.venv\Scripts\activate

# 方式一：交互式向导（推荐新用户）
python scripts/cli.py setup

# 方式二：手动输入
python scripts/cli.py login-openid <你的OpenID> <学号>
# 输入密码（显示 * 占位符）

# 查看状态
python scripts/cli.py status

# 一键打卡
python scripts/cli.py checkin
```

---

## 2. 命令速查表

| 命令 | 功能 | 频率 | 示例 |
|------|------|------|------|
| `setup` | 🆕 交互式配置向导 | 首次 | `python scripts/cli.py setup` |
| `status` | 🆕 状态概览（登录+任务+今日记录） | 每天 | `python scripts/cli.py status` |
| `config` | 🆕 查看/管理本地配置 | 偶尔 | `python scripts/cli.py config` |
| `login-openid` | OpenID 登录（推荐） | 首次 / token 过期 | `python scripts/cli.py login-openid oEXAMPLE... 2023****` |
| `login` | 密码登录（备用） | 极少 | `python scripts/cli.py login 2023****` |
| `tasks` | 查看任务 + 自动记住ID | 每天 | `python scripts/cli.py tasks` |
| `detail` | 任务详情（task_id 可选） | 首次 | `python scripts/cli.py detail` |
| `checkin` | 一键打卡（task_id 可选） | 每天 | `python scripts/cli.py checkin` |
| `record` | 查询打卡状态（task_id 可选） | 确认用 | `python scripts/cli.py record` |
| `month <YYYY-mm>` | 月度记录 + 统计（task_id 可选） | 偶尔 | `python scripts/cli.py month 2026-06` |

> `tasks` 运行后自动记住任务 ID，后续 `detail`/`checkin`/`record`/`month` 可直接省略 task_id。终端支持 ANSI 彩色输出（绿色=成功，红色=错误，黄色=警告）。

---

## 3. 首次配置

### 3.1 获取 OpenID

OpenID 是微信用户在小程序中的唯一标识，需要通过抓包获取。详见 `docs/guides/完整操作指南.md` 第 3 节。

简化步骤：
1. MuMu 模拟器 + Fiddler 抓包
2. 模拟器打开打卡小程序
3. 在 Fiddler 中找到 `getOpenidByJsCode` 请求
4. 响应体 `data` 字段即为 OpenID（`o` 开头，约 28 位）

### 3.2 使用交互式向导（推荐）

```powershell
# 启动向导，按提示输入即可
python scripts/cli.py setup
```

向导会引导你完成 4 步：OpenID → 学号 → 密码 → 自动验证登录。成功后所有凭据自动保存。

### 3.3 手动登录（高级用户）

```powershell
# 首次：保存所有凭据到配置文件
python scripts/cli.py login-openid <OpenID> <学号> --bind 1 --save-password
# 输入密码 → 学号/OpenID/密码全保存到 ~/.auto_check_in/config.json

# 之后 token 过期重新登录（无需再输 OpenID 和学号）
python scripts/cli.py login-openid --bind 0
# 密码自动从配置读取（如果用了 --save-password）
```

成功后 token 自动保存至 `~/.auto_check_in/config.json`，后续命令无需重复登录。

### 3.4 确认环境正常

```powershell
# 运行测试
python -m pytest tests/ -v

# 检查登录状态（一键查看所有关键信息）
python scripts/cli.py status
```

---

## 4. 日常使用流程

首次配置后，每天打卡只需两步（无需输入任何参数）：

```powershell
# 激活环境
.\.venv\Scripts\activate

# Step 1: 查看状态（登录状态 + 任务 + 今日打卡记录）
python scripts/cli.py status
# 输出:
#  ─── 系统状态 ───
#  ✓  登录状态: 已登录 ✓
#  当前任务
#    名称: 本科生2026年春季学期平安打卡
#    时间: 21:00 — 22:30
#  今日打卡
#    日期: 2026-06-07
#    状态: 正常              ← 绿色高亮

# Step 2: 一键打卡（自动用已保存的任务ID和宿舍坐标）
python scripts/cli.py checkin
# 输出:
#  ─── 打卡签到 ───
#  任务: 本科生2026年春季学期平安打卡
#  坐标: (28.130978, 112.994662) — 模拟偏移 ±0.0003°
#  与宿舍距离: 12.0m
#  精度上限: 1500.0m
#  打卡成功！              ← 绿色高亮
```

---

## 5. 命令详解

### 5.1 `setup` — 交互式配置向导（🆕 推荐）

```powershell
python scripts/cli.py setup
```

交互式 4 步向导，适合首次使用：
1. 输入 OpenID（附获取说明）
2. 输入学号
3. 选择是否保存密码（安全提示）
4. 自动验证登录并保存配置

登录失败时仍保存凭据，方便排查后重试。

### 5.2 `status` — 状态概览（🆕）

```powershell
python scripts/cli.py status
```

一键查看所有关键信息：
- 配置文件路径 + 凭据摘要
- Token 有效性验证（实时调用 API）
- 当前活跃任务 + 打卡时间窗口
- 今日打卡记录（日期/状态/坐标）
- Token 过期时提示重新登录

### 5.3 `config` — 配置管理（🆕）

```powershell
python scripts/cli.py config              # 查看配置（凭据自动掩码）
python scripts/cli.py config clear        # 清除 token
python scripts/cli.py config clear --all  # 清除全部配置（需确认）
python scripts/cli.py config clear --password  # 仅清除密码
```

敏感信息用掩码显示：`ocrJ********************Nd1U`。`clear` 子命令支持精确控制清除范围。

### 5.4 `login-openid` — OpenID 登录

```powershell
python scripts/cli.py login-openid [--tenant 000000] <openid> [username] [password] [--bind 0|1]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `openid` | ✅ | 微信 OpenID（抓包获取） |
| `username` | 首次绑定时 | 学号 |
| `password` | 留空交互输入 | 密码（不回显） |
| `--bind 0` | — | 仅登录不绑定（已绑定后使用） |
| `--bind 1` | — | 绑定并登录（首次，默认） |
| `--tenant` | — | 租户 ID，默认 `000000` |

**常见场景**：

```powershell
# 首次使用：绑定学号
python scripts/cli.py login-openid oEXAMPLE... 2023**** --bind 1

# token 过期后重新登录
python scripts/cli.py login-openid oEXAMPLE... --bind 0

# 更换学号
python scripts/cli.py login-openid oEXAMPLE... 新学号 --bind 1
```

### 5.5 `tasks` — 任务列表

```powershell
python scripts/cli.py tasks [--page 1] [--size 10]
```

输出示例：
```
[b49ffb3790cfa0fb60661e4b59cdfbc8] 中南林2026年春季学期平安打卡  21:00-22:30
共 1 条
```

**提示**：`任务ID`（方括号内的长字符串）是后续 `detail`/`checkin`/`record`/`month` 命令的必填参数。建议记下或写入脚本。

### 5.6 `detail` — 任务详情

```powershell
python scripts/cli.py detail <任务ID>
```

输出示例：
```
任务: 中南林2026年春季学期平安打卡
时间: 21:00:00 - 22:30:00
宿舍: QY24 3F 315
坐标: (28.1310851493253, 112.994643653515)
精度: 1500m
定位校验: 开启
```

**关键信息解读**：

| 字段 | 含义 | 影响 |
|------|------|------|
| `坐标` | 宿舍 GPS 坐标 | CLI 自动以此为中心生成模拟定位 |
| `精度` | 允许的最远距离（米） | 模拟定位必须在此范围内 |
| `定位校验: 开启` | 服务端验证 GPS | 必须传合理坐标 |
| `定位校验: 关闭` | 服务端不验证 | 随便传坐标 |

### 5.7 `checkin` — 打卡签到（核心命令）

```powershell
python scripts/cli.py checkin <任务ID> [选项]
```

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--lat <纬度>` | float | 自动 | 手动指定纬度 |
| `--lng <经度>` | float | 自动 | 手动指定经度 |
| `--offset <值>` | float | `0.0003` | GPS 随机偏移量（度），约 ±30m |
| `--force` | flag | 关闭 | 超出精度范围仍强制提交 |
| `--late-date <YYYY-mm-dd>` | string | 今天 | 补签日期 |
| `--file-id <文件ID>` | string | 无 | 上传照片的文件 ID |

**使用场景**：

```powershell
# 正常打卡（自动从宿舍坐标 + 随机偏移模拟）
python scripts/cli.py checkin b49ffb3790cfa0fb60661e4b59cdfbc8

# 手动指定坐标（如用真实手机 GPS）
python scripts/cli.py checkin b49ffb37... --lat 28.133235 --lng 112.993898

# 增大偏移范围（更逼真）
python scripts/cli.py checkin b49ffb37... --offset 0.0008

# 补签昨天的
python scripts/cli.py checkin b49ffb37... --late-date 2026-06-06

# 超出范围强制提交（慎用）
python scripts/cli.py checkin b49ffb37... --lat 28.5 --lng 113.0 --force
```

**工作原理**：

```
1. 从 API 获取宿舍坐标 (locationLat, locationLng)
2. 用 random_offset() 在宿舍坐标基础上加随机偏移
   → 默认 ±0.0003° ≈ ±30m，模拟真实 GPS 漂移
3. 用 haversine() 计算模拟位置与宿舍的距离
4. 距离 < 精度上限 → 提交打卡
   距离 > 精度上限 → 警告，需 --force 强制提交
5. 服务端再次校验坐标合理性
```

### 5.8 `record` — 查询今日打卡状态

```powershell
python scripts/cli.py record <任务ID> [--date YYYY-mm-dd]
```

输出示例：
```
日期: 2026-06-07  状态: 正常
坐标: (28.13167182074653, 112.99509819878472)
```

**状态说明**：状态直接使用服务端返回的 `signStatusName` 中文值。

| signStatus | 含义 |
|-----------|------|
| 0 | 正常（已打卡） |
| 1 | 迟到 |
| 2 | 请假中 |
| 3 | 未归 |
| 4 | 走读中 |
| 5 | 离校中 |
| 6 | 外宿中 |

### 5.9 `month` — 月度打卡记录

```powershell
python scripts/cli.py month <任务ID> <YYYY-mm>
```

输出示例：
```
2026-06-01: 正常
2026-06-02: 正常
2026-06-03: 正常
2026-06-04: 正常
2026-06-05: 正常
2026-06-06: 正常
2026-06-07: 正常
```

**注意**：API 仅返回有打卡记录的日期，无记录日期不显示。

### 5.10 `login` — 密码登录（备用）

```powershell
python scripts/cli.py login [--tenant 000000] <学号> [密码]
```

小程序实际不使用此方式登录，保留作备用。需要验证码，但验证码接口可用性不稳定。

---

## 6. 高级用法

### 6.1 定时自动打卡（Windows 计划任务）

将打卡命令保存为脚本 `auto_checkin.ps1`：

```powershell
# auto_checkin.ps1
Set-Location "D:\A_Learn\Vibe coding\Project\auto_check_in"
.\.venv\Scripts\Activate.ps1
python scripts/cli.py checkin b49ffb3790cfa0fb60661e4b59cdfbc8 >> checkin.log 2>&1
```

创建计划任务（每天 21:05 执行）：

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File D:\A_Learn\Vibe coding\Project\auto_check_in\auto_checkin.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "21:05"
Register-ScheduledTask -TaskName "AutoCheckIn" -Action $action -Trigger $trigger
```

### 6.2 Linux cron 定时打卡

```bash
# crontab -e
5 21 * * * cd /path/to/auto_check_in && .venv/bin/python scripts/cli.py checkin TASK_ID >> checkin.log 2>&1
```

### 6.3 批量脚本

```bash
#!/bin/bash
# daily_checkin.sh — 完整每日流程
cd /path/to/auto_check_in
source .venv/bin/activate

echo "=== $(date) ==="
python scripts/cli.py tasks
python scripts/cli.py checkin TASK_ID
python scripts/cli.py record TASK_ID
```

### 6.4 环境变量配置

所有敏感和可变参数均支持环境变量覆盖：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `CHECKIN_BASE_URL` | `https://simp.csuft.edu.cn` | API 基址 |
| `FLYSOURCE_CLIENT_ID` | `flysource_wise_wxapp` | OAuth 客户端 ID |
| `FLYSOURCE_CLIENT_SECRET` | `DA788asdUDjnasd...` | OAuth 客户端密钥 |
| `WX_APP_ID` | `wx0e47c34c9982aa09` | 微信小程序 AppID |
| `WX_VERSION` | `7` | 小程序版本号 |
| `WX_USER_AGENT` | `Mozilla/5.0 ...` | 微信 User-Agent |

---

## 7. 配置与凭据管理

### 配置文件位置

```
~/.auto_check_in/config.json
```

### 配置文件内容

```json
{
  "token": "eyJhbGciOiJI...",
  "tenant_id": "000000",
  "username": "2023xxxx",
  "openid": "xxxxxx..."
}
```

### 安全建议

```powershell
# Windows: 限制配置文件权限
icacls "$env:USERPROFILE\.auto_check_in\config.json" /inheritance:r /grant "$env:USERNAME:(R)"

# Linux/macOS:
chmod 600 ~/.auto_check_in/config.json
```

### Token 过期处理

Token 有效期约 20~30 天。过期后（API 返回 401）重新登录即可：

```powershell
python scripts/cli.py login-openid <你的OpenID> --bind 0
# 输入密码
```

---

## 8. 故障排查

| 错误 | 原因 | 解决 |
|------|------|------|
| `SSL: CERTIFICATE_VERIFY_FAILED` | Windows 证书缺失 | 已内置 certifi 修复 |
| `签名错误 (code 400)` | 时间偏差过大 | 同步系统时间 |
| `未登录或登录已过期 (code 401)` | token 过期 | 重新 `login-openid` |
| `打卡失败: 超出打卡范围` | 模拟坐标偏移过大 | 减小 `--offset` 或用 `--force` |
| `今天已签到无需重复` | 已打过卡 | 无需操作 |
| `获取任务失败` | 网络不通或 token 过期 | 检查网络，重新登录 |

---

## 参考资料

- `docs/guides/完整操作指南.md` — 完整操作教程（含抓包环境搭建）
- `docs/CHANGELOG.md` — 版本更新记录
- `AGENTS.md` — 项目整体指南
