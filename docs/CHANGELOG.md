# 更新日志

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
