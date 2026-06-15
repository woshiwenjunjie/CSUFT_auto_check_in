# 更新日志

## [0.13.0] — 2026-06-15

### 🏗️ 共享模块重构（CLI + SCF 统一）
- **新建 3 个共享模块**：`src/core/sign_builder.py`（打卡请求体构建）、`src/utils/notification.py`（Server酱 推送+窗口检测+通知构建）、`src/core/token_client.py`（SCF 环境变量→ApiClient 适配器）
- **窗口检测移入共享**：`is_window_open()` / `window_hint()` 从 SCF 专用移至 `notification.py`，CLI + SCF 共用
- **`deploy/tencent-scf/notify.py` 删除**，合并至 `src/utils/notification.py`
- **`ApiTokenClient`** 从 SCF `checkin.py` 提取到 `src/core/token_client.py`
- **SCF `checkin.py` 精简**：从 ~250 行降至 ~80 行（纯编排层，使用共享模块）
- **CLI `checkin.py`**、SCF `checkin.py` 统一调用 `build_notification() + send_serverchan()`

### 🔧 CLI 精简
- **命令 11→9**：删除 `login` 死代码命令；`record`/`month` 合并到 `checkin --record`/`--month`
- **`auth.py`** 删除未使用的 `login()` 函数

### 🤖 capture 一步到位
- `capture_addon.py`：捕获 OpenID 后自动调用 `sign_in_openid` 登录，省去 `login-openid` 第二步
- 添加新账号流程：3 步 → 2 步

### 📬 Server酱 通知增强
- **窗口状态行**：通知正文自动显示 `🪟 距离开窗还有 X 小时 X 分钟` / `🪟 窗口还剩 X 分钟` / `🪟 窗口已关闭`
- **成功/失败分组**：✅ 成功在前，❌ 失败在后，一目了然
- **英文码转中文**：`ok: 0.12` → `正常 (0.12km)`，`error: 登录失败` → `失败: 登录失败`
- **标题带日期**：`打卡汇总 06-15 | 2/3`
- **SCF 错误信息精确化**：`error` 改为 `失败: 具体原因`，不再只有裸 `error`

### 🐛 Bug 修复
- **SCF `sign_date` 格式修复**：`token_client.py:96` 误用 `%H:%M:%S` 带时分秒，导致 `compute_stu_task_id` 签名与服务器不一致，全账号返回"签到失败，请重试！"

### 🎨 体验优化
- GPS 偏移统一为 0.002（CLI 原 0.0003 不一致已修复）
- CLI 报错信息友好化（红色错误 + 灰色修复提示）
- 通知时间标注 `(北京时间)` 避免时区混淆

### 🧪 测试
- test_checkin_core.py：14 → 29（新增 `_map_display` 7 个 + `BuildNotificationDetail` 4 个 + 窗口通知行 4 个）
- 总计 106 测试全部通过
- SCF 打包 1.3 MB，gen-env 正常

## [0.10.0] — 2026-06-14

### 📚 文档体系重构
- **新建 `docs/README.md`** — 文档总索引，统一导航入口
- **新建 `getting-started/`** — 快速开始、配置向导、常见问题 3 篇新手指南
- **新建 `reference/`** — 4 篇深度技术教程重构（签名算法、小程序逆向、认证抓包、wxapkg提取）
- **新建 `development/`** — 阶段三路线图、数据库设计评审、后端 API 设计规范
- **新增 `reference/API端点参考.md`** — 8 个学校 API 接口文档
- **新增 `reference/CLI命令速查表.md`** — 13 个子命令一页速查
- **迁移**：关键词与概念速查从 guides/user 迁入 reference/

### 🛠️ 代码健康检查
- **全模块类型注解** — 覆盖 `src/`、`scripts/`、`deploy/tencent-scf/` 共 18 个文件
- **修复 5 个遗留问题**：
  - `sign.py` 消除全局状态突变（`generate_sign` 参数化）
  - `auth.py` 增加 token 空值显式检测
  - `checkin.py` GPS 阈值配置化（`_DEFAULT_GPS_OFFSET` 等模块常量）
  - `_common.py` / `cli_config.py` 增加 `client_mode` 合法性校验
- **测试增强**：新增 `tests/test_client_integration.py`（7 个 mock 集成测试）
- **边界测试补充**：`test_geo.py` +7 测试（空坐标、极端经纬度、零偏移）
- **边界测试补充**：`test_sign.py` +3 测试（空路径、中文路径、含空格路径）
- **总测试数**：67 → **85**

### 🔧 工具脚本
- **新建 `scripts/tools/verify_sign.py`** — 交互式签名验证，支持 `--js` 对比 Node.js
- **新建 `scripts/tools/cross_validate.py`** — 5 组随机参数自动交叉验证
- **新建 `scripts/tools/decompile_wxapkg.py`** — wxapkg 解包辅助（检查依赖 + 解包 + 列文件）

### 📖 文档
- `AGENTS.md` — 文档目录/tools 路径/工具脚本/85 测试同步
- `README.md` — 徽章 67→85，目录结构同步
- `docs/superpowers/plans/` — 完整实施计划文档

## [0.9.1] — 2026-06-12

### 🎯 SCF 部署优化

**Cron 时区修正**（第三次时区坑）：
- SCF 控制台 Cron 默认北京时间（UTC+8），非 UTC
- 表达式从 `5 13 * * *` → `0 5 21 * * ? *`（7 字段格式，含秒+年）
- 全量文档、代码注释、dry-run 输出同步修正

**通知优化**：
- `_build_notification` 与 GitHub Actions 风格对齐
- 打卡成功时显示 GPS 距离：`**2026-06-12** | 状态：正常 | 距宿舍 15.3m`
- 重复打卡提示次日窗口：`> 次日 **21:00–22:30** 自动执行下次打卡`
- Token 过期增加操作指引：`> CLI: \`capture-openid\` / Fiddler / Reqable`
- `do_checkin` 返回 3 元组 `(bool, str, str)` 传递距离

**窗口检测**：
- 新增 `_is_window_open()` / `_nearest_window_hint()` 检测当前时间
- 窗口外自动返回 `nowindow` 状态而非 `error`
- 提示信息显示小时+分钟：`"还有 8 小时 25 分钟"`
- 窗口内有任务则正常打卡，无任务提示 `"可能今日未发布"`

**函数注释补齐**：
- 全部 9 个函数新增/完善 docstring（`_is_window_open`、`_nearest_window_hint`、`run_checkin`、`_notify_and_return`、`_build_notification`、`get_env_str` 等）

### 📖 文档
- `README.md` — 徽章 31→67，功能列表、测试表、目录结构同步更新
- `CLAUDE.md` — SCF Cron 格式修正，状态描述更新
- `docs/guides/user/腾讯云SCF部署指南.md` — 细化 7 步流程，凭据脱敏，Cron 说明

## [0.12.0] — 2026-06-14

### 🐛 SCF 多用户链路修复

**1. 多用户通知统一走 `_build_notification`**
- `_build_notification` 重构：`detail` 字段对全部状态生效（不仅 `ok`），每条通知末尾统一追加 `🕐 北京时间` 时间戳
- `_do_multi_or_single` 多 profile 分支：汇总结果通过 `_build_notification` 构造通知标题+正文，与单用户路径格式一致
- 新增 `partial` 状态测试 2 个（`test_partial_status`、`test_partial_with_detail`）

**2. 错误消息精确化**
- `_checkin_one` 中 `not openid or not username` 判断拆分为独立检测
- 分别列出 `CHECKIN_OPENID_USER_X` 或 `CHECKIN_USERNAME_USER_X`，不再笼统写一个

**3. 单账号异常隔离**
- 多用户循环中每个 `_checkin_one()` 调用包 try/except
- 任一账号抛出未预期异常不会阻断后续账号执行

**4. 状态码修复**
- 部分成功时 status 从 `"ok"` → `"partial"`（Server酱 标题不再误标 ✅）
- 全失败时 status 从 `all_results[0]["status"]` → 固定 `"error"`
- 单 profile 走 `_notify_and_return`，多 profile 走 `_build_notification` 汇总

### 🚀 SCF 默认多用户 + 部署工具增强

- `handler.py`：移除 `CHECKIN_PROFILES` 检测分支，默认始终调用 `run_multi_checkin()`
- `deploy.py`：新增 `gen-env` 子命令，从 `password.txt` 生成 SCF 控制台可导入的 `scf_env.json`
- `deploy.py`：新增 `--env-json` 参数，部署时通过 SCF CLI 附带环境变量
- `tests/deploy/test_handler.py`：`patch` 目标从 `run_checkin` 改为 `run_multi_checkin`

### 📦 GitHub Actions 多用户支持

- `.github/workflows/auto-checkin.yml`：`timeout-minutes: 5` → `10`
- `scripts/auto_checkin.sh`：新增 `_get_env` 函数 + `CHECKIN_PROFILES` 解析 + 多用户 config.json 写入 + `--profiles` 批量打卡 + 汇总通知

### 📖 文档

- `README.md`：GitHub Secrets 命名 `OPENID`/`USERNAME`/`PASSWORD` → `CHECKIN_OPENID`/`CHECKIN_USERNAME`/`CHECKIN_PASSWORD`
- `deploy/tencent-scf/README.md`：重写为 11 章完整教程，多用户优先，含对比/注册/抓包/打包/配置/触发器/排障
- `password.txt`：环境变量名加 `_USER_X` 后缀，对齐 SCF 多用户格式
- `AGENTS.md`：测试数 85 → 87，SCF 模块表增加 `gen-env` 说明

### 🧪 测试

- 87 测试全部通过（85 原 + 2 新增 `partial` 状态测试）

## [0.11.0] — 2026-06-14

### 👥 多用户打卡系统

**多 profile 配置支持**：
- `cli_config.py` 配置格式升级：`profiles` 字典 + `current_profile` 切换，自动迁移旧版扁平配置
- 新增 `list_profiles()` / `switch_profile()` / `save_config(cfg, profile=...)` 接口
- `load_config(profile=...)` 显式 profile 参数，默认返回 current_profile

**免密码登录**：
- `auth.py` 支持 `--bind 0` 无密码登录（已绑定 OpenID 的账号可跳过密码输入）
- 密码不再必填，base64 混淆存储保留

**全局 --profile 参数**：
- 注入 `setup`、`status`、`config`、`login-openid`、`login-webvpn`、`login`、`tasks`、`detail`、`checkin`、`record`、`month` 全部子命令
- `config profile list` / `config profile <名称>` 查看和切换账号

**批量打卡**：
- `checkin` 新增 `--profiles` 参数，逗号分隔多个账号
- 无参数时默认打卡全部已配置账号
- 每个 profile 独立执行：登录 → 任务 → GPS 偏移 → 提交 → 确认 → 汇总

### 🆕 新账号
- `USER_2`（20234150）：新增第二 WeChat 账号，免密码绑定
- `USER_3`（20234146）：新增第三 WeChat 账号，免密码绑定

### 🔧 工具修复
- `capture_openid_emulator.py`：三大修复 — `mitmdump` 自动搜索 PATH、`cert_hash` 降级 Python cryptography、Android 12 bind mount 替代 remount

### 📖 文档同步
- **新建** `docs/guides/user/模拟器自动抓取OpenID.md` — 模拟器一键捕获专篇，含安全分析
- **更新** `docs/guides/user/CLI教程.md` — 多账号管理章节、模拟器捕获方式
- **更新** `docs/guides/user/完整操作指南.md` — 模拟器方案取代 Fiddler 做首选，新增 4.3 多账号管理
- **更新** `docs/reference/认证流程与抓包分析.md` — 四种方案对比、安全分析"先 root 再登录"
- **更新** `docs/getting-started/快速开始.md` — 推荐方案改为模拟器脚本
- **更新** `docs/getting-started/配置向导.md` — 捕获方式表新增模拟器
- **更新** `docs/getting-started/常见问题.md` — 多账号管理 FAQ
- **更新** `docs/README.md` — 目录索引新增模拟器文档，修复链接
- **更新** `AGENTS.md` — 文档导航新增，模拟器推荐说明

### 🏗️ SCF 多用户支持
- `deploy/tencent-scf/checkin.py`：新增 `_checkin_one()` / `run_multi_checkin()`，`CHECKIN_PROFILES` 环境变量驱动多用户循环
- `deploy/tencent-scf/handler.py`：检测 `CHECKIN_PROFILES` 自动切换多用户模式
- 每个 profile 独立执行登录→任务→打卡→确认，汇总一次性 Server酱 通知
- 后缀环境变量命名：`CHECKIN_OPENID_USER_1` / `CHECKIN_USERNAME_USER_2` 等
- 向后兼容：无后缀 `CHECKIN_OPENID` 作为兜底（单用户旧版无缝升级）

### 🔀 Profile 重命名
- `default` → `USER_1`：配置自动迁移，CLI 命令、文档、帮助文本同步更新
- `deploy/tencent-scf/README.md` — 重写，废弃旧 CLI 方式，统一手动上传流程

## [0.9.0] — 2026-06-12

### 🏗️ SCF 部署模块重构

全模块顶层注释规范化（执行流程图、设计原理、环境变量表、状态码说明）：
- `checkin.py` — 编排流程图、延迟时间函数原理、GPS 退避策略、5 种状态码
- `handler.py` — 异常安全网设计、健康检查支持
- `notify.py` — Server酱 推送流程、2 次重试 3s 间隔
- `deploy.py` — 打包部署架构、错误处理三明治

变量名重构提升可读性：
- `client` → `api_client`、`dorm_lat` → `dormitory_lat`、`cur_offset` → `current_offset_degrees`
- `stu_task_id` → `student_task_id`、`src_dst` → `target_src_dir`

模块级时间冻结修复：`NOW` → `_now()` 延迟函数，避免 warm start 冻结。

运行时版本变量化：`SCF_RUNTIME` 环境变量（默认 Python 3.12）。

`scf_bootstrap` 删除（标准 Python 运行时无需）。

### 🧪 完整测试覆盖（36 新测试）

`tests/deploy/` 目录新建，5 测试文件覆盖全部 SCF 模块：

| 文件 | 测试数 | 覆盖内容 |
|------|--------|----------|
| `test_notify.py` | 4 | 跳过/成功/500/重试 |
| `test_checkin_core.py` | 14 | 时间/环境变量/通知 5 状态 |
| `test_checkin_api.py` | 7 | GPS 退避/sign_data/MD5 |
| `test_handler.py` | 4 | 健康检查/正常/异常捕获 |
| `test_deploy_utils.py` | 4 | _fmt_size KB/MB/0 |

conftest.py 重构：移除模块级 mock，采用 `@patch('checkin.xxx')` 定点拦截。

总计 67 测试（31 原 + 36 新）全部通过。

### 📖 文档
- `docs/memory/017-SCF部署重构与测试完善.md` — 新增
- `AGENTS.md` — 测试数更新 31→67，"Reaple"→"Reqable"，SCF 设计要点表
- `CLAUDE.md` — Four-tier design 含 SCF 层、deploy 命令、状态更新

## [0.8.3] — 2026-06-09

### 🔴 时区修复（第三次，最终方案）

**根因**：v0.8.2 的「UTC 规范化」引入三个连锁 bug：
1. bash `date` + `TZ=Asia/Shanghai` 在 GitHub Actions Ubuntu runner 上不可靠 → 通知时间显示混乱
2. `TZ` 环境变量可能误导 GitHub Actions cron 调度器将 `5 13 * * *` 解释为北京时间 13:05
3. 通知标签全标 UTC，与 date 实际输出时区不一致

**修复**：
- `auto_checkin.sh`：彻底放弃 bash `date`，全部改用 Python `datetime.now(timezone(timedelta(hours=8)))`
- 新增 `_beijing_now()` 函数，`now_ts()` 同步改用 Python
- workflow：**移除 `TZ: Asia/Shanghai`** 环境变量（可能影响 cron 调度器）
- workflow keepalive 步骤改用显式 Beijing 时区
- 通知标签全部改回「北京时间」

### 🟡 状态匹配修复

**根因**：服务器 `signStatusName` 返回「正常」而非 STATUS_MAP 的「已打卡」，导致 `auto_checkin.sh` case 匹配失败，打卡成功却 exit 1 + 发失败通知。

**修复**：
- `auto_checkin.sh`：case 新增 `"正常"` 匹配
- `cli_ui.py`：STATUS_MAP 0 改 `"已打卡"` → `"正常"`，与服务器一致

### 📖 文档
- **新增** `docs/memory/016-时区修复与cron调度排错.md` — 四个 bug 排查全记录
- **更新** `docs/memory/014-UTC时间坑.md` — 修正错误结论
- **更新** `docs/guides/dev/GitHub-Actions部署记录.md` — 补充 cron 调度排错章节

## [0.8.2] — 2026-06-09

### UTC 时间规范化
- 所有通知文案中打卡窗口改为 UTC 时间标注（13:00–14:30 UTC），北京时间放括号
- `auto_checkin.sh` 和 workflow 注释同步改为 `UTC 13:05（北京时间 21:05）`
- 新增 `docs/memory/014-UTC时间坑.md` — 记录服务器基于 UTC 判定时间窗口的根因和教训
- `AGENTS.md` — 新增 "UTC 时间陷阱" 章节

### GPS 自动重试
- `checkin.py`: 超出打卡范围时自动缩小偏移量重试（最多 5 次），不再直接中断
- `auto_checkin.sh`: 移除 GPS 超出范围推送分支（可自动纠正的错误不推送）

### 通知美化
- 所有推送通知文案精简，统一标题格式、引用块突出关键信息、去除冗余表格
- 未知错误改用代码块显示服务器返回

## [0.8.1] — 2026-06-08

### Server酱 通知静默失败修复

**根因**：`send_serverchan()` 两个隐蔽 bug 导致通知静默失败：
1. `printf + --data-binary @-` 发送 Markdown 内容时未做 URL 编码，换行/管道符等特殊字符导致 Server酱 API 解析失败
2. `> /dev/null 2>&1 || true` 丢弃了 curl 的所有输出（包括错误响应），日志毫无痕迹

**修复**：
- `send_serverchan()` — 改用 `--data-urlencode` 自动 URL 编码 `title` 和 `desp`
- `send_serverchan()` — 捕获 HTTP 状态码 + 响应体并写入日志，不再静默丢弃
- `send_telegram()` — 同样改用 `--data-urlencode` + 响应日志
- 脚本启动时新增通知渠道状态检查（✅ 已配置 / ⚠️ 未配置 + 配置指引）

### 时区修复
- Bash: `export TZ='CST-8'`（POSIX 标准格式，不依赖 zoneinfo 文件）→ 之前 `TZ='Asia/Shanghai'` 在部分环境无效
- Python: `datetime.now()` → `datetime.now(timezone(timedelta(hours=8)))` → 硬编码 UTC+8，不受系统时区影响
- Workflow 保活步骤同步使用 `TZ='CST-8'`

### 保活机制
- 新增 `.keepalive` 每日 commit，防止 60 天无活动被 GitHub 停用定时任务
- commit 带 `[skip ci]` 防止递归触发
- Workflow 新增 `permissions: contents: write`

### 文档完善
- **新增** `docs/guides/user/Server酱配置教程.md` — Server酱 从零配置教程
- **新增** `docs/guides/user/GitHub-Actions自动打卡教程.md` — GitHub Actions 用户教程
- **新增** `docs/guides/dev/签名算法详解.md` — FlySource-sign 深入讲解（双语实现、交叉验证、常见陷阱）
- **新增** `docs/guides/dev/项目架构与开发指南.md` — 架构全景、模块设计、数据流、扩展指南
- `docs/guides/user/关键词与概念解释.md` — 新增"通知与自动化"章节（Server酱、GitHub Actions、保活、时区、Telegram）
- `docs/guides/user/完整操作指南.md` — 新增第 5 章 GitHub Actions + 参考资料更新
- `docs/guides/user/CLI教程.md` — 版本更新 + 新指南交叉引用
- `docs/guides/dev/GitHub-Actions部署记录.md` — 新增通知调试章节（错误码表、排查步骤）
- `AGENTS.md` — 文档索引更新（11 份指南）
- `docs/memory/` — 新增 012（通知修复）+ 013（时区修复）

## [0.8.0] — 2026-06-08

### GitHub Actions 自动部署上线
- **新增** `.github/workflows/auto-checkin.yml` — 每天 21:05 北京时间自动触发，支持 workflow_dispatch 手动触发
- **新增** `scripts/auto_checkin.sh` — bash 执行脚本（写配置 → 登录 → 获取任务 → 打卡 → 通知）
- **新增** `docs/guides/dev/GitHub-Actions部署记录.md` — 部署文档（隐私已脱敏）
- **新增** `docs/memory/010-GitHub-Actions部署上线.md` — 部署记忆档案

### 通知系统
- **Server酱** 微信推送（主通道，免费、无需实名、扫码即用）
- **Telegram Bot** 通知（备用通道）
- **GitHub 内置邮件** 兜底（Settings → Notifications）
- 通知函数统一为 `notify()`，自动使用所有已配置渠道
- PushPlus 因实名认证要求弃用

### 脚本健壮性修复
- `grep -oP` 改为 `sed` 提取字段（消除 Ubuntu runner PCRE 兼容性问题）
- `echo -e` 改为 `printf '%b'`（消除跨 shell 兼容性问题）
- 所有 `GITHUB_*` 环境变量添加默认值（本地运行不再崩溃）
- curl 添加 10s 连接超时 + 15s 总超时

### 工作流优化
- 步骤名改为中文，提升可读性
- 添加 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`，消除 Node.js 20 弃用警告
- 分支统一为 `main`

### 隐私安全
- `password.txt` 格式标准化（变量名对应 GitHub Secrets）
- 文档中所有凭据已脱敏处理
- `.gitignore` 确保 `password.txt` 不会被提交

## [0.7.2] — 2026-06-08

### Bug 修复（关键 — cmd_status 已打卡却显示"未打卡"）
三重根因同时修复：
1. `get_one_record` 未传 `sign_date` → 显式传入当天日期
2. 缺少 `_token_expired` 检查 → token 过期被误报为"未打卡" → 添加检测
3. 判断 `rec.get("data")` 在 `data: {}` 时因空字典 falsy → 改为 `d and d.get("signStatus") is not None`

### 代码质量（简洁性提升）
- `scripts/cli.py`: 提取模块级 `STATUS_MAP` 常量 + `_status_display(sc, sn)` 颜色编码函数，消除 3 处重复字典、统一 7 种状态颜色
- `scripts/cli.py`: `_mask()` 改为 None-safe（返回 `""`），4 处调用简化为 `_mask(v, N) or "fallback"`，消除冗余 `if/else` 守卫
- `scripts/cli.py`: 移除 argparse 死参数 `config clear --token`（默认行为已清除 token，`--token` 未在 handler 使用）
- `scripts/cli.py` (`cmd_checkin`): 确认查询增加 `_token_expired` 检测
- `scripts/cli.py` (`cmd_login`): 登录成功补充 masked 学号和 token 显示，与 `cmd_login_openid` 一致

### 安全隐私提升
- `scripts/cli.py`: 学号在 `status`/`config show`/登录成功中应用 `_mask(username, 3)` 脱敏

### 打卡逻辑改进
- `scripts/cli.py` (`cmd_checkin`): 提交打卡后自动调用 `get_one_record` 回查服务器确认实际打卡状态

### 代码审查
- `docs/review/2026-06-08-代码审查.md` — 初次审查（6 个问题）
- `docs/review/2026-06-08-深度审查.md` — 深度审查（全部问题已修复 7/7）

### 文档与规范
- `CLAUDE.md` — 新增"回复必须用中文"约定
- `AGENTS.md` — 新增"回复必须用中文"关键约定（第 6 条），遗留问题表已清空

## [0.7.1] — 2026-06-07

### CLI 用户体验全面升级

**新增 3 个命令：**

- `setup` — 交互式首次配置向导，引导用户输入 OpenID/学号/密码并验证登录
- `status` — 快速状态概览：登录状态、当前任务、今日打卡记录（一次命令替代以往 3 个命令）
- `config` — 管理本地配置：`config show` 查看（凭据自动掩码）、`config clear` 清除 token

**输出美化：**

- ANSI 终端颜色系统（`Style` 类）：绿色=成功 / 红色=错误 / 黄色=警告 / 青色=信息 / 灰色=次要
- `divider()` 分段线、`kv()` 对齐键值行、`bullet()` 图标列表
- `Spinner` 线程动画指示器（`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`），API 调用时自动显示
- `month` 命令新增 ✓/!/− 图标和底部汇总统计
- `tasks` 改为编号列表，任务名称高亮
- 无命令时显示品牌欢迎页

**错误提示改进：**

- Token 过期 → 明确提示 `python scripts/cli.py login-openid`
- 登录绑定冲突 → 提示 `--bind 0`
- 密码错误 → 提示 `--force-input`
- 缺少 task_id → 提示先运行 `tasks`
- 超出打卡范围 → 提示 `--force` 或调整 `--offset`

**技术细节：**

- 零新增依赖，纯 ANSI 转义码（Windows 10+/Unix 通用）
- 尊重 `NO_COLOR` 环境变量 + `isatty()` 管道检测，脚本重定向自动降级为纯文本
- Windows GBK 终端自动 `sys.stdout.reconfigure(encoding='utf-8')`

### 验证

- ✅ 所有 10 个 CLI 命令通过真机 API 测试
- ✅ 20/20 pytest 测试通过
- ✅ `checkin` 正确检测"今日已签到"
- ✅ `month` 月度统计准确（7 天正常）
- ✅ ANSI 颜色在管道输出时自动关闭

## [0.7.0] — 2026-06-07

### 🎯 签名问题终极解决

经过逐字节对比 Fiddler 真实抓包签名，**确认签名算法（MD5 + Base64）自始至终正确**。

真正原因：**服务器反爬校验**，要求请求头包含微信小程序环境特征（`Referer`、`User-Agent`、`charset`）。缺少这些头时服务器直接返回"签名错误"。

### 修复

- `src/core/client.py`: 新增微信小程序伪装头（`charset`、`Referer`、`User-Agent`），AppID/Version/UA 均支持环境变量覆盖
- `src/core/client.py`: `_headers` 新增 `no_auth` 参数（captcha 端点不需要 Basic Auth）
- `src/core/client.py`: `sign_in()` 补齐 `Tenant-Id`/`Captcha-Key`/`Captcha-Code` 请求头
- `scripts/cli.py`: 修复 `tasks` 命令字段名（`t['id']` → `t['taskId']`）
- `scripts/cli.py`: 修复 `record`/`month` 命令状态映射（`signStatus=0` 为"正常/已打卡"，非"未打卡"），优先使用 API 返回的 `signStatusName`

### CLI 联动优化

- `scripts/cli.py`: `getpass` 替换为 `secure_input()`，密码输入回显 `*` 占位符
- `scripts/cli.py`: `login-openid --save-password` 保存密码到配置文件
- `scripts/cli.py`: `login-openid`/`login` 的 openid/username 支持留空从配置文件读取
- `scripts/cli.py`: `tasks` 自动保存任务 ID → `detail`/`checkin`/`record`/`month` 自动读取
- `scripts/cli.py`: 新增 `--force-input`（跳过配置密码）、`tasks --no-save`（不保存任务 ID）
- 日常使用简化：首次 `login-openid --save-password` 后，日常只需 `tasks` → `checkin` 两步

### 验证

- ✅ 全链路 7 个 CLI 命令全部通过真实 API 验证
- ✅ 20/20 pytest 测试通过
- ✅ 签名算法逐字节与微信小程序输出一致
- ✅ `checkin` 命令服务器接受请求（今日已打卡故返回"重复打卡"而非签名错误）
- ✅ 命令联动：`tasks` → `detail` / `checkin` / `record` / `month` 自动传递 task_id

### 文档

- `docs/memory/006-签名问题终极解决.md` — 完整排查记录
- `docs/memory/007-CLI联动与用户体验优化.md` — 联动优化记录
- `docs/guides/user/CLI教程.md` — CLI 详细教程（联动用法）
- `docs/plan/服务器部署规划.md` — 阶段三服务器部署规划
- `docs/guides/user/完整操作指南.md` — 更新至 v0.7.0

## [0.6.1] — 2026-06-07

### Bug 修复
- `src/core/client.py`: `_post()` 修复 `extra_headers` 参数未转发到 `_request()` 的 bug，导致 OpenID 登录无法传递 `Web-Type`/`Tenant-Id` 头
- `src/core/client.py`: httpx 客户端新增 `verify=certifi.where()` 解决 Windows Python SSL 证书缺失问题
- `src/core/client.py`: httpx 客户端新增 `trust_env=False` 解决 Windows 环境代理干扰 HTTPS 直连
- `src/utils/sign.py`: 签名算法更正，移除中间多余的字符串（`path + "?sign=" + inner_hash` 格式经 JS 源码交叉验证确认正确）

### 新增
- `docs/guides/user/完整操作指南.md`: 新增完整操作指南（330 行），覆盖环境准备、OpenID 抓包、CLI 使用、签名算法、安全设计、FAQ
- `requirements.txt`: 新增 `certifi==2025.11.12` 直接依赖

### 验证
- 通过 Fiddler + MuMu 模拟器成功抓包获取真实 OpenID
- 通过 ADB bind mount 方案成功安装系统级 CA 证书到模拟器
- OpenID 登录成功（`login-openid --bind 0`）
- 全部 20 个 pytest 测试通过

## [0.6.0] — 2026-06-07

### 修复（按审查优先级）

**🔴 P0**
- `src/core/client.py`: 新增 `__enter__`/`__exit__` 上下文管理器，支持 `with ApiClient() as c`
- `src/main.py`: 新增 `CORSMiddleware` 跨域支持和 `lifespan` 生命周期事件管理 ApiClient 连接池

**🟡 P1**
- `src/core/client.py`: `BASE_URL` 从模块级常量改为实例属性，构造函数支持 `base_url` 参数，兼容多环境切换
- `tests/`: 新增 20 个 pytest 测试用例（crypto 6 + sign 6 + geo 8），覆盖 MD5/Base64 标准向量、签名算法格式校验、Haversine 已知距离、随机偏移种子可重现性

**🟢 P2**
- `scripts/cli.py:49`: 密码三目表达式改为清晰 `if/else` 分支
- `src/core/client.py`: `_request()` 新增指数退避重试机制（最多 3 次，1s/2s/4s），仅重试网络/解析错误，不影响 401

**⚪ P3**
- `.env.example`: `FLYSOURCE_CLIENT_ID`、`FLYSOURCE_CLIENT_SECRET`、`CHECKIN_BASE_URL` 取消注释，开箱即用
- `requirements.txt`: 所有依赖从 `>=` 改为固定版本号锁定

### 其他
- `src/utils/geo.py`: `random_offset` 新增可选 `seed` 参数，支持测试场景复现
- 所有 8 个源码文件新增中文注释（模块、类、函数级别），提升可读性
- `docs/guides/user/fiddler-抓包获取OpenID.md`: 新增 Fiddler 抓包全流程指南（341 行），含 2.1 节汉化说明
- `docs/memory/004-审查修复与OpenID发现.md`: 本次会话记忆存档
- 清理临时文件（captcha.png、.pytest_cache、4 个 __pycache__）
- `docs/CHANGELOG.md`: 新增 v0.6.0 条目
- `AGENTS.md`: 遗留问题表已清空

## [v0.1 — v0.5] — 2026-06-07 · 早期快速迭代

**v0.1** 项目骨架（FastAPI + APScheduler + SQLAlchemy）、Git 初始化、`.env.example`  
**v0.2** MuMu 12 模拟器 Root + ADB 拉取 6 个 `.wxapkg`  
**v0.3** 反编译确认目标小程序、还原签名算法（FlySource-sign + stuTaskId）、提取 ClientId/ClientSecret  
**v0.4** CLI 工具初版（7 子命令）、核心模块（sign/crypto/geo/client）、凭据安全加固  
**v0.5** 全量代码审查（0 Critical / 5 Important / 6 Minor）
