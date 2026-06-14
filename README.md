# CSUFT 自动晚点名打卡 — v0.12.0

[![Tests](https://img.shields.io/badge/tests-87%2F87%20%E2%9C%85-green)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Version](https://img.shields.io/badge/version-0.12.0-blue)]()

通过逆向工程还原微信小程序 API，实现命令行一键自动打卡。无需每天打开小程序，支持 GitHub Actions 全自动托管打卡。

> ⚠️ **仅供学习交流使用**。使用本工具请遵守学校相关规定，开发者不对因使用本工具产生的任何后果负责。

---

## ✨ 功能特性

| 特性 | 说明 |
|------|------|
| 🔑 一键打卡 | 模拟 GPS 偏移，自动完成晚点名签到 |
| 👥 多账号批量 | `checkin --profiles` 一次命令打多个号，SCF 原生多用户循环 |
| 🤖 全自动托管 | GitHub Actions / 腾讯云 SCF 定时打卡 + 微信通知 |
| 🔒 安全认证 | 基于 OpenID 的 OAuth 登录，密码混淆本地存储 |
| 🧪 算法可验证 | 87 个自动化测试，JS/Python 签名交叉验证 |
| 📱 OpenID 自动捕获 | 内置 mitmproxy 插件 / 模拟器一键脚本 |
| 🛠️ 交互式配置 | `setup` 向导式首次配置，零门槛上手 |
| ⏰ 窗口检测 | 自动检测打卡窗口（21:00–22:30），非窗口期友好提示 |

---

## 📋 目录

- [快速开始](#-快速开始)
- [安装](#-安装)
- [使用方法](#-使用方法)
- [配置说明](#-配置说明)
- [项目架构](#-项目架构)
- [测试](#-测试)
- [自动化打卡](#-自动化打卡github-actions)
- [技术原理](#-技术原理)
- [常见问题](#-常见问题)
- [开发指南](#-开发指南)
- [许可证](#-许可证)

---

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url>
cd auto_check_in

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .\.venv\Scripts\activate  # Windows PowerShell

# 3. 安装依赖
pip install -r requirements.txt

# 4. 首次配置（交互式向导）
python scripts/cli.py setup

# 5. 一键打卡
python scripts/cli.py checkin
```

---

## 📦 安装

### 环境要求

- Python 3.10+
- Node.js（可选，用于签名交叉验证）
- mitmproxy（可选，用于自动捕获 OpenID）

### 依赖安装

```bash
pip install -r requirements.txt
```

生产环境依赖：

| 包 | 版本 | 用途 |
|----|------|------|
| `httpx` | 0.28.1 | 异步 HTTP 客户端 |
| `fastapi` | 0.115.6 | Web 框架（阶段三预留） |
| `uvicorn` | 0.34.0 | ASGI 服务器 |
| `python-dotenv` | 1.1.0 | 环境变量加载 |
| `pytest` | 8.3.4 | 测试框架 |

---

## 🎯 使用方法

### CLI 命令一览

```bash
python scripts/cli.py <command>
```

| 命令 | 功能 |
|------|------|
| `setup` | 交互式首次配置向导（支持 `--profile` 多账号） |
| `status` | 查看登录状态、今日任务、打卡记录 |
| `login-openid` | OpenID 登录（`--bind 0` 免密码，`--profile` 多账号） |
| `login` | 密码登录（备用，服务器已禁用） |
| `capture-openid` | 启动 mitmproxy 自动捕获 OpenID |
| `tasks` | 查看打卡任务列表 |
| `login-webvpn` | WebVPN Token 验证+保存（备用方案） |
| `detail` | 查看任务详情（宿舍坐标、精度上限） |
| `checkin` | 一键打卡签到（`--profiles` 批量多个账号） |
| `record` | 查询当日/指定日期打卡记录 |
| `month` | 按月查询打卡记录（含统计） |
| `config` | 管理配置（`config profile list` 列出账号，`config profile <名称>` 切换） |

### 首次使用流程

#### Step 1: 获取 OpenID（必需）

OpenID 是微信小程序用户的唯一标识，必须通过抓包获取。

**方式 A：自动捕获（推荐）**

```bash
# 安装 mitmproxy（首次）
pip install mitmproxy

# 启动自动捕获
python scripts/cli.py capture-openid
```

然后：
1. 手机与电脑连接同一 WiFi
2. 手机设置代理为 `电脑IP:8080`
3. 访问 `mitm.it` 安装 CA 证书
4. 打开微信小程序，OpenID 自动保存到配置

**方式 B：手动抓包（Fiddler）**

参考详细教程：[Fiddler 抓包获取 OpenID 完整指南](docs/guides/user/fiddler-抓包获取OpenID.md)

#### Step 2: 配置登录

```bash
python scripts/cli.py setup
# 按提示输入：OpenID → 学号 → 密码
```

#### Step 3: 日常打卡

```bash
# 查看状态
python scripts/cli.py status

# 一键打卡（自动模拟 GPS 偏移）
python scripts/cli.py checkin

# 批量打卡多个账号
python scripts/cli.py checkin --profiles USER_1,USER_2
```

### 查看打卡记录

```bash
# 今日记录
python scripts/cli.py record

# 指定日期
python scripts/cli.py record --date 2026-06-01

# 整月统计
python scripts/cli.py month --month 2026-06
```

---

## ⚙️ 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CHECKIN_BASE_URL` | `https://simp.csuft.edu.cn` | API 基地址 |
| `FLYSOURCE_CLIENT_ID` | `flysource_wise_wxapp` | OAuth 客户端 ID |
| `FLYSOURCE_CLIENT_SECRET` | `DA788asdUDjnasd_flysource_wxappdsdadDAIUiuwqe` | OAuth 客户端密钥 |
| `WX_APP_ID` | `wx0e47c34c9982aa09` | 微信小程序 AppID |
| `WX_VERSION` | `7` | 小程序版本号 |

### 本地配置文件

路径：`~/.auto_check_in/config.json`

```json
{
  "current_profile": "USER_1",
  "profiles": {
    "USER_1": {
      "tenant_id": "000000",
      "username": "2023XXXXXX",
      "openid": "oXXXXXXXX...",
      "password": "$obf:base64...",
      "token": "eyJhbGciOi...",
      "task_id": "b49ffb37..."
    },
    "USER_2": {
      "tenant_id": "000000",
      "username": "2023XXXXXX",
      "openid": "oXXXXXXXX...",
      "token": "eyJhbGciOi..."
    }
  }
}
```

- 多账号通过 `profiles` 字典管理，`config profile list` 查看全部
- `config profile USER_2` 切换当前账号
- `checkin --profiles USER_1,USER_2` 批量打卡多个账号
- 密码采用 `$obf:<base64>` 混淆存储（防明文，非加密）
- 凭据显示时自动脱敏，仅显示首尾字符

---

## 🏗️ 项目架构

```
┌─────────────────────────────────────────┐
│           用户交互层                     │
│  ┌──────────────┐  ┌──────────────┐    │
│  │  CLI 工具     │  │  微信通知     │    │
│  │ scripts/cli   │  │ Server酱     │    │
│  └──────────────┘  └──────────────┘    │
├─────────────────────────────────────────┤
│           自动化层                       │
│  ┌──────────────────────────────────┐   │
│  │  GitHub Actions                  │   │
│  │  cron → bash → login → checkin  │   │
│  │  → notify                        │   │
│  └──────────────────────────────────┘   │
├─────────────────────────────────────────┤
│           核心引擎                       │
│  ┌─────────────────────────────────┐    │
│  │  ApiClient (src/core/client)    │    │
│  │  ├─ 8 个学校 API 端点            │    │
│  │  ├─ 自动签名 / 认证 / 重试       │    │
│  │  └─ 微信环境伪装                 │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │  工具模块 (src/utils/)           │    │
│  │  ├─ sign.py   签名算法           │    │
│  │  ├─ crypto.py MD5/Base64        │    │
│  │  └─ geo.py    GPS计算           │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│           阶段三（规划中）               │
│  ┌─────────────────────────────────┐    │
│  │  FastAPI + SQLAlchemy           │    │
│  │  + APScheduler 多用户 Web 后端   │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### 目录结构

```
auto_check_in/
├── src/                    # Python 源码
│   ├── core/client.py      # ApiClient — 核心 API 客户端
│   ├── utils/              # 工具模块（sign / crypto / geo）
│   ├── api/                # (预留) FastAPI 路由
│   ├── models/             # (预留) 数据模型
│   ├── services/           # (预留) 业务服务
│   └── main.py             # FastAPI 入口
├── scripts/                # CLI 工具 + GitHub Actions 脚本
│   ├── cli.py              # CLI 入口（13 个子命令）
│   ├── cli_commands/       # 子命令实现
│   ├── cli_config.py       # 配置管理
│   ├── cli_ui.py           # 终端 UI 组件
│   ├── capture_addon.py    # mitmproxy OpenID 捕获插件
│   ├── tools/              # 工具脚本（verify_sign / cross_validate / decompile_wxapkg）
│   ├── auto_checkin.sh     # GitHub Actions 执行脚本
│   └── sign.js             # JS 签名参考实现
├── deploy/                 # 非 GitHub 部署方案
│   └── tencent-scf/        # 腾讯云 SCF 部署（推荐，含 deploy.py gen-env）
├── tests/                  # 测试（87 个用例）
├── docs/                   # 文档体系：getting-started / guides / reference / development / memory
├── references/             # 外部参考资料 + 小程序反编译源码
├── reviews/                # 代码审查记录
├── frontend/               # (预留) 前端页面
└── .github/workflows/      # GitHub Actions CI/CD
```

---

## 🧪 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 签名交叉验证（需 Node.js）
python -m pytest tests/test_cross_validate.py -v

# 工具：JS/Python 交叉验证（5 组随机）
python scripts/tools/cross_validate.py

# 工具：交互式签名验证
python scripts/tools/verify_sign.py --path /api/test --ts 1700000000000 --token test_token
```

| 测试文件 | 用例数 | 覆盖内容 |
|----------|--------|----------|
| `test_crypto.py` | 6 | MD5、Base64 |
| `test_sign.py` | 9 | 签名算法、Basic Auth、空路径/中文路径 |
| `test_geo.py` | 15 | Haversine 距离、GPS 随机偏移、极端坐标、零偏移 |
| `test_config.py` | 6 | 密码混淆、明文/混淆/空密码读取 |
| `test_cross_validate.py` | 5 | JS vs Python 签名一致性 |
| `test_client_integration.py` | 7 | 401 检测、签名格式、重试机制 |
| `tests/deploy/test_notify.py` | 4 | Server酱 推送（跳过/200/500/重试） |
| `tests/deploy/test_checkin_core.py` | 16 | 时间函数、环境变量、通知 6 状态（含 partial） |
| `tests/deploy/test_checkin_api.py` | 7 | GPS 退避、签名数据、MD5 确定性 |
| `tests/deploy/test_handler.py` | 4 | 健康检查、正常执行、异常捕获 |
| `tests/deploy/test_deploy_utils.py` | 4 | 打包大小格式化 |

**全部 87 个测试通过 ✅**

---

## ☁️ 腾讯云 SCF 部署（推荐）

项目同时提供腾讯云云函数（SCF）部署方案，作为 GitHub Actions 的升级替代。

### 对比：GitHub Actions vs SCF

| 维度 | GitHub Actions | 腾讯云 SCF ✅ |
|------|---------------|--------------|
| 触发 | UTC 时间，需考虑时区转换 | 北京时间，Cron 直接配置 |
| 保活 | 需人工保持仓库活跃（60 天规则） | 无此限制，配置即用 |
| 通知 | Server酱 + Telegram + Step Summary | Server酱微信推送 |
| 日志 | GitHub Actions 日志界面 | SCF 控制台日志，保留更久 |
| 费用 | 免费（但有使用配额） | 免费额度远超打卡需求 |
| 维护 | 需维护仓库 fork | 一次配置，上传即用 |
| 依赖 | 自动安装环境 | 打包上传，环境固化 |
| 稳定性 | 依赖 GitHub 服务可用性 | 腾讯云 SLA 保障 |
| 配置 | Secrets 环境变量 | SCF 控制台环境变量（可加密） |

**推荐使用 SCF**：无保活困扰、北京时间原生支持、配置一次长期稳定运行。

SCF 默认以多用户模式运行。不设 `CHECKIN_PROFILES` 时自动回退单用户（`CHECKIN_OPENID` 兜底），新旧配置无缝兼容。

### 快速部署

```bash
# 1. 生成环境变量 JSON（从 password.txt）
python deploy/tencent-scf/deploy.py gen-env

# 2. 打包代码
python deploy/tencent-scf/deploy.py --dry-run

# 3. SCF 控制台：
#    ① 函数代码 → 本地上传 zip → 选 scf_package.zip → 部署
#    ② 函数配置 → 环境变量 → 导入 scf_env.json
#    ③ 敏感字段逐行勾选「加密」
#    ④ 触发管理 → 创建触发器 → 0 5 21 * * ? *（每天 21:05 北京时间）
```

### 多用户环境变量（SCF 控制台配置）

```
CHECKIN_PROFILES=USER_1,USER_2,USER_3
CHECKIN_OPENID_USER_1=o开头28位    → 加密
CHECKIN_USERNAME_USER_1=2023XXXXXX → 加密
# USER_1 免密码，不设 PASSWORD_USER_1
CHECKIN_OPENID_USER_2=o开头28位    → 加密
CHECKIN_USERNAME_USER_2=2023XXXXXX → 加密
SERVERCHAN_KEY=SCT123...           → 加密（可选，微信推送用）
```

详细教程：[腾讯云 SCF 部署指南](docs/guides/user/腾讯云SCF部署指南.md) | `deploy/tencent-scf/README.md`

---

项目内置完整的 GitHub Actions 工作流，实现零成本全自动托管：

- **触发时间**：每天 UTC 13:05（北京时间 21:05）
- **支持手动触发**：`workflow_dispatch`
- **通知渠道**：Server酱微信推送、Telegram Bot、GitHub Step Summary
- **保活机制**：每日自动 commit，防止仓库因 60 天无活动被停用

### 单用户配置（最简）

1. Fork 本仓库
2. 仓库 Settings → Secrets and variables → Actions 中添加：
   - `CHECKIN_OPENID` — 你的微信小程序 OpenID
   - `CHECKIN_USERNAME` — 学号
   - `CHECKIN_PASSWORD` — 密码
   - `SERVERCHAN_KEY` — Server酱 SendKey（可选）
3. Actions 页面启用工作流

### 多用户配置

多账号需额外配 `CHECKIN_PROFILES` 和带后缀的凭据，工作流 env 段自行扩展。

---

## 🔬 技术原理

### 签名算法

飞源（FlySource）平台使用自定义签名防止请求伪造：

```
FlySource-sign = MD5(path + "?sign=" + MD5(ts + token)) + "1." + Base64(ts)
```

- `path`：URL 路径（不含 query）
- `ts`：13 位毫秒时间戳
- `token`：OAuth access_token

### 认证流程

```
wx.login() → getOpenidByJsCode → oauth/token (grant_type=wxapp)
```

> 注意：密码登录（`grant_type=password`）已被服务器禁用，必须使用 OpenID 方式。
> 另提供 WebVPN 客户端模式（`client_mode: web`），通过 CAS SSO 登录 WebVPN 后调用办公版 API。

### 请求头要求

```
Authorization: Basic <base64(ClientId:ClientSecret)>
FlySource-Auth: <access_token>
FlySource-sign: <签名>
Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html
User-Agent: ...MicroMessenger...MiniProgramEnv/android
```

缺少 `Referer` 或 `User-Agent` 时，服务器会返回误导性的"签名错误"。

### GPS 偏移算法

以宿舍坐标为中心，使用带 seed 的伪随机生成偏移量（保留 6 位小数），确保每次打卡位置在合理范围内波动。

---

## ❓ 常见问题

**Q: 为什么必须用 OpenID，不能直接用密码登录？**

A: 小程序源码分析确认 `signIn` 和 `getCaptcha` 函数从未被调用，是死代码。服务器返回 `"Unauthorized grant type: password"`，拒绝密码授权。必须通过抓包获取 OpenID。

**Q: 手机开热点时怎么抓包？**

A: 手机本身无法设代理时，可用：
- **Reqable**（原 HTTPCanary）：本地 VPN 抓包，无需代理
- **USB 反向共享**：电脑开 Fiddler，手机 USB 连接电脑并开启 USB 网络共享，再设置代理

**Q: 打卡失败提示"签名错误"怎么办？**

A: 先检查请求头是否完整，特别是 `Referer` 和 `User-Agent`。这两个头缺失时服务器会返回误导性的签名错误，实际签名算法可能没问题。

**Q: 如何验证签名算法正确性？**

A: 运行交叉验证测试：
```bash
node scripts/sign.js /api/test 1700000000000 test_token
python -m pytest tests/test_cross_validate.py -v
```

---

## 🛠️ 开发指南

### 添加新 CLI 子命令

1. 新建 `scripts/cli_commands/xxx.py`，实现 `run(args)` 函数
2. 在 `scripts/cli.py` 中 import + dispatch + argparse

### 修改签名算法

- 必须同步更新 `scripts/sign.js`
- 运行 `python -m pytest tests/test_cross_validate.py -v` 验证一致性

### 代码规范

**凭据安全**
- README 中展示的默认值（`FLYSOURCE_CLIENT_ID`、`FLYSOURCE_CLIENT_SECRET`、`WX_APP_ID` 等）均来自小程序反编译源码，属于应用级公开常量，**不构成敏感信息**。真正的用户级凭据（OpenID、密码、token）不会出现在任何文档中。
- 所有凭据在终端显示时自动脱敏（`_mask`），仅展示首尾字符。
- 密码本地存储使用 `$obf:<base64>` 混淆，禁止明文。
- 环境变量中的敏感字段建议在部署平台（SCF/CI）中勾选加密存储。

**代码风格**
- 模块化设计，单文件不超过 300 行。
- 函数职责单一，命名体现用途（如 `_build_notification`、`_is_window_open`）。
- 新增子命令：`scripts/cli_commands/xxx.py` → 实现 `run(args)` → cli.py import + dispatch + argparse。
- 变量名拒绝缩写（`dorm_lat` → `dormitory_lat`、`cur_offset` → `current_offset_degrees`）。

**验证纪律**
- 变更签名算法时同步更新 `scripts/sign.js`，并运行交叉验证测试。
- 测试覆盖率目标：核心模块 90%+，部署模块 80%+。
- 提交前确保 `python -m pytest tests/ -v` 全部通过。

**文档同步**
- 架构/功能变更时同步更新 README 目录结构、AGENTS.md（本地）、CHANGELOG。
- 关键决策记录在 `reviews/` 审查记录中，包含决策理由与备选方案。

**时区陷阱**
- 所有 API 时间基于 **UTC**，显示时做 UTC+8 转换。
- 打卡窗口为 UTC 13:00–14:30（北京时间 21:00–22:30）。
- SCF Cron 使用北京时间直接配置（`0 5 21 * * ? *`），无需时区转换。

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- 逆向分析参考：[NaHS2 自动打卡文章总结](references/nahs-online-自动打卡文章总结.md) · [nahsit.com](https://nahsit.com)
- 飞源（FlySource）统一认证平台
