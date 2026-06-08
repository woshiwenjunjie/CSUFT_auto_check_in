# AGENTS.md — Auto Check-In 项目指南

## 项目概述

中南林业科技大学自动晚点名打卡系统。模拟微信小程序网络请求，通过逆向还原的签名算法和接口调用链实现命令行打卡。

## 技术栈

Python 3.14 + httpx + FastAPI（待阶段三） + APScheduler（待阶段三）

## 关键约定

1. **回复必须用中文** — 所有最终回复使用简体中文
2. **先跑通再扩展** — 先 CLI 验证，再搭后端
3. **交叉验证** — 签名算法用 JS 原版（`scripts/sign.js`）和 Python 实现互验
4. **凭据安全** — 所有显示均脱敏（`_mask`），密码用 `secure_input`，环境变量覆盖硬编码
5. **文档同步** — 涉及架构/功能变更时，同步更新 CHANGELOG + memory + 本文件
6. **逆向源码在 wxapkgs/** — `_-250202245_7` 为中南林业科技大学平安打卡小程序

## 快速命令

```powershell
.\.venv\Scripts\activate               # 激活虚拟环境
python -m pytest tests/ -v             # 运行测试（20 用例）
python scripts/cli.py setup            # 首次配置
python scripts/cli.py status           # 状态概览
python scripts/cli.py checkin          # 一键打卡
node scripts/sign.js /api/test 1700000000000 test_token  # 签名交叉验证
```

## 核心架构

### src/ — Python 源码

| 模块 | 文件 | 职责 |
|------|------|------|
| **API 客户端** | `src/core/client.py` | 封装 8 个学校接口，统一处理签名/认证/重试 |
| **签名算法** | `src/utils/sign.py` | `FlySource-sign`: `MD5(path+"?sign="+MD5(ts+token))+"1."+Base64(ts)` |
| **工具函数** | `src/utils/crypto.py` | MD5、Base64 |
| **定位计算** | `src/utils/geo.py` | Haversine 距离 + GPS 随机偏移 |
| **Web 入口** | `src/main.py` | FastAPI 脚手架（阶段三） |

### scripts/ — CLI 工具 + GitHub Actions

**模块化 CLI 架构**（v0.9+）：

| 文件 | 行数 | 职责 |
|------|------|------|
| `scripts/cli.py` | 248 | 入口 + argparse 骨架 + dispatch 路由 |
| `scripts/cli_ui.py` | 160 | ANSI 样式 / Spinner / 终端输出辅助 |
| `scripts/cli_config.py` | 149 | 配置持久化 / 密码混淆(base64) / 安全输入 |
| `scripts/cli_commands/_common.py` | 36 | 共享工具：get_client / token_expired |
| `scripts/cli_commands/setup.py` | 101 | 交互式首次配置向导 |
| `scripts/cli_commands/status.py` | 99 | 登录状态 + 今日打卡概况 |
| `scripts/cli_commands/config_cmd.py` | 64 | 本地配置查看/清除 |
| `scripts/cli_commands/auth.py` | 103 | OpenID 登录 + 密码登录 |
| `scripts/cli_commands/tasks.py` | 112 | 任务列表 + 任务详情 |
| `scripts/cli_commands/checkin.py` | 289 | 打卡/补签/记录查询/月度统计 |

**新增命令只需 3 步**：新建 `cli_commands/xxx.py` → 实现 `run(args)` → 在 `cli.py` 中 import + 注册 dispatch + 添加 argparse 声明。

**密码存储**：`$obf:<base64>` 前缀混淆格式，`load_config()` 自动还原为 `_password_raw`，`save_config()` 自动混淆写入。向后兼容明文密码。

`scripts/auto_checkin.sh` — GitHub Actions 执行脚本，编排：写配置 → 登录 → 获取任务 → 打卡 → 通知。每次 Action 从 GitHub Secrets 注入凭据全新登录。通知通过 `notify()` 统一分发到 Server酱（微信）和 Telegram（可选）。

### .github/workflows/ — CI/CD

`auto-checkin.yml` — 每天 UTC 13:05（北京时间 21:05）自动触发，支持 workflow_dispatch 手动触发。ubuntu-latest 环境，Python 3.14。

### 请求必须携带的头

```
Authorization: Basic <base64(ClientId:ClientSecret)>  ← 客户端认证
FlySource-Auth: <access_token>                         ← 用户认证
FlySource-sign: <签名>                                  ← 防伪造
Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html  ← 伪装微信
User-Agent: ...MicroMessenger...MiniProgramEnv/android  ← 伪装微信
```

> ⚠️ 缺少 Referer/User-Agent 时服务器返回 **"签名错误"**（误导），先检查环境头再怀疑签名算法。

### 关键凭据

| 凭据 | 来源 | 可覆盖 |
|------|------|--------|
| `FLYSOURCE_CLIENT_ID` | `flysource_wise_wxapp`（硬编码默认） | 环境变量 |
| `FLYSOURCE_CLIENT_SECRET` | 硬编码默认 | 环境变量 |
| `CHECKIN_BASE_URL` | `https://simp.csuft.edu.cn`（硬编码默认） | 环境变量 |
| OpenID | Fiddler 抓包获取 | `~/.auto_check_in/config.json` |
| access_token | OAuth2 登录后获取 | config.json |

## 项目状态

- ✅ 阶段一/二完成：逆向分析 + CLI 工具（全部功能可用，31 测试通过）
- ✅ GitHub Actions 部署：每天 21:05 自动打卡 + Server酱微信通知
- ✅ CLI 模块化重构：命令拆分 + 密码混淆 + 签名跨语言验证
- ⏳ 阶段三待开始：FastAPI 后端 + 多用户支持 + 定时任务
- 📋 所有计划见 `docs/plan/`

## 文档同步说明

**同步时机**：仅在阶段/里程碑完成时更新 `AGENTS.md`、`CLAUDE.md`、`CHANGELOG.md` 和 memory 文件。日常小修小改（bug fix、格式调整）只提交代码，不触发文档更新。重大功能（新命令、新部署方式、架构变更）才补齐文档记录。

**同步清单**：
- `AGENTS.md` — 架构、项目状态、文档索引
- `CLAUDE.md` — 命令、架构、约定
- `docs/CHANGELOG.md` — 新增版本条目
- `docs/memory/` — 新建里程碑记忆文件

## 文档索引

### 使用指南 `docs/guides/user/`

| 文件 | 内容 |
|------|------|
| `完整操作指南.md` | 从零到打卡的完整教程 |
| `CLI教程.md` | CLI 详细用法（10 个子命令） |
| `GitHub-Actions自动打卡教程.md` | GitHub Actions 自动打卡部署教程 |
| `Server酱配置教程.md` | Server酱 微信推送配置详解 |
| `抓包获取OpenID完全指南.md` | 抓包报文分析与获取流程 |
| `fiddler-抓包获取OpenID.md` | Fiddler 抓包工具配置 |
| `关键词与概念解释.md` | 术语速查 |

### 开发指南 `docs/guides/dev/`

| 文件 | 内容 |
|------|------|
| `提取小程序wxapkg.md` | 微信小程序反编译与源码提取 |
| `GitHub-Actions部署记录.md` | GitHub Actions 自动打卡部署文档 |
| `签名算法详解.md` | FlySource-sign 签名算法深入讲解 |
| `项目架构与开发指南.md` | 项目架构、模块设计、数据流、扩展指南 |

### 计划 `docs/plan/`

| 文件 | 内容 |
|------|------|
| `项目整体实施计划.md` | 五阶段路线图 |
| `GitHub-Actions-个人自动打卡部署方案.md` | GitHub Actions 部署方案 |
| `服务器部署规划.md` | 多用户服务器方案 |

### 其他

| 类型 | 文件 | 内容 |
|------|------|------|
| 日志 | `docs/CHANGELOG.md` | 版本更新记录 |
| 逆向 | `docs/memory/003-逆向分析结果.md` | 小程序源码逆向分析 |
| 审查 | `docs/review/` | 代码审查报告（4 份） |
| 记忆 | `docs/memory/` | 项目里程碑（001–013） |
