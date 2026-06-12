# CSUFT 自动晚点名打卡

[![Tests](https://img.shields.io/badge/tests-67%2F67%20%E2%9C%85-green)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)]()

通过逆向工程还原微信小程序 API，实现命令行一键自动打卡。无需每天打开小程序，支持 GitHub Actions 全自动托管打卡。

> ⚠️ **仅供学习交流使用**。使用本工具请遵守学校相关规定，开发者不对因使用本工具产生的任何后果负责。

---

## ✨ 功能特性

| 特性 | 说明 |
|------|------|
| 🔑 一键打卡 | 模拟 GPS 偏移，自动完成晚点名签到 |
| 🤖 全自动托管 | GitHub Actions / 腾讯云 SCF 定时打卡 + 微信通知 |
| 🔒 安全认证 | 基于 OpenID 的 OAuth 登录，密码混淆本地存储 |
| 🧪 算法可验证 | 67 个自动化测试，JS/Python 签名交叉验证 |
| 📱 OpenID 自动捕获 | 内置 mitmproxy 插件，抓包一键获取 OpenID |
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
| `setup` | 交互式首次配置向导 |
| `status` | 查看登录状态、今日任务、打卡记录 |
| `login-openid` | OpenID 登录（推荐） |
| `login` | 密码登录（备用，服务器已禁用） |
| `capture-openid` | 启动 mitmproxy 自动捕获 OpenID |
| `tasks` | 查看打卡任务列表 |
| `login-webvpn` | WebVPN Token 验证+保存（备用方案） |
| `detail` | 查看任务详情（宿舍坐标、精度上限） |
| `checkin` | 一键打卡签到 |
| `record` | 查询当日/指定日期打卡记录 |
| `month` | 按月查询打卡记录（含统计） |
| `config` | 查看或清除本地配置 |

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
  "tenant_id": "000000",
  "username": "2023xxxx",
  "openid": "oEXAMPLE...",
  "password": "$obf:base64encoded...",
  "task_id": "b49ffb3790...",
  "token": "eyJhbGciOiJI..."
}
```

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
├── scripts/                # 可执行脚本
│   ├── cli.py              # CLI 入口
│   ├── cli_commands/       # 子命令实现（10 个命令）
│   ├── cli_config.py       # 配置管理
│   ├── cli_ui.py           # 终端 UI 组件
│   ├── capture_addon.py    # mitmproxy OpenID 捕获插件
│   ├── auto_checkin.sh     # GitHub Actions 执行脚本
│   └── sign.js             # JS 签名参考实现
├── tests/                  # 测试（67 个用例）
├── docs/                   # 文档
│   ├── guides/user/        # 用户指南
│   ├── guides/dev/         # 开发指南
│   ├── memory/             # 里程碑记录
│   └── review/             # 代码审查记录
├── .github/workflows/      # CI/CD 配置
├── wxapkgs/                # 小程序反编译源码
└── references/             # 外部参考资料
```

---

## 🧪 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 签名交叉验证（需 Node.js）
python -m pytest tests/test_cross_validate.py -v
```

| 测试文件 | 用例数 | 覆盖内容 |
|----------|--------|----------|
| `test_crypto.py` | 6 | MD5、Base64 |
| `test_sign.py` | 6 | 签名算法、Basic Auth |
| `test_geo.py` | 8 | Haversine 距离、GPS 随机偏移 |
| `test_config.py` | 6 | 密码混淆、配置读写 |
| `test_cross_validate.py` | 5 | JS vs Python 签名一致性 |
| `tests/deploy/test_notify.py` | 4 | Server酱 推送（跳过/200/500/重试） |
| `tests/deploy/test_checkin_core.py` | 14 | 时间函数、环境变量、通知 5 状态 |
| `tests/deploy/test_checkin_api.py` | 7 | GPS 退避、签名数据、MD5 确定性 |
| `tests/deploy/test_handler.py` | 4 | 健康检查、正常执行、异常捕获 |
| `tests/deploy/test_deploy_utils.py` | 4 | 打包大小格式化 |

**全部 67 个测试通过 ✅**

---

## 🤖 自动化打卡（GitHub Actions）

项目内置完整的 GitHub Actions 工作流，实现零成本全自动托管：

- **触发时间**：每天 UTC 13:05（北京时间 21:05）
- **支持手动触发**：`workflow_dispatch`
- **通知渠道**：Server酱微信推送、Telegram Bot、GitHub Step Summary
- **保活机制**：每日自动 commit，防止仓库因 60 天无活动被停用

### 配置步骤

1. Fork 本仓库
2. 在仓库 Settings → Secrets and variables → Actions 中添加：
   - `OPENID` — 你的微信小程序 OpenID
   - `USERNAME` — 学号
   - `PASSWORD` — 密码
   - `SERVERCHAN_KEY` — Server酱 SendKey（可选，用于微信通知）
3. 在 Actions 页面启用工作流

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

- 中文回复，英文专业术语除外
- 凭据脱敏显示，不写死凭据
- 架构/功能变更时同步更新 CHANGELOG + memory + AGENTS.md

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- 逆向分析参考：[NaHS2 自动打卡文章总结](references/nahs-online-自动打卡文章总结.md)
- 飞源（FlySource）统一认证平台
