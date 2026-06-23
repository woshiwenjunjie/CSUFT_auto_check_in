# CSUFT 自动晚点名打卡

版本：`v0.15.0`
状态：CLI、腾讯云 SCF、GitHub Actions 均可用；FastAPI 后端仍为预留骨架。

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-114%20passed-green)](tests/)
[![Version](https://img.shields.io/badge/version-0.15.0-blue)]()

这是一个中南林业科技大学自动晚点名打卡工具。项目通过逆向还原微信小程序 API、签名算法和请求头环境，提供命令行打卡、多账号批量打卡、腾讯云 SCF 定时执行、GitHub Actions 轻量托管、Server酱/Telegram 通知等能力。

> 仅供学习交流。使用前请自行确认是否符合学校规定；用户需对自己的使用行为负责。

## 当前能力

| 能力 | 当前状态 |
| --- | --- |
| OpenID 登录 | 可用。小程序密码授权已被服务端拒绝，实际只能走 OpenID / WebVPN token |
| CLI 打卡 | 可用。支持任务查询、打卡、补签、记录查询、月度统计 |
| 多账号 | 可用。`profiles` 配置 + `checkin --profiles` 批量执行 |
| 微信小程序模式 | 可用。自动补齐 Referer、User-Agent、Basic Auth、FlySource-sign |
| WebVPN 模式 | 可用。通过 `client_mode=web` 和 WebVPN token 调用对应环境头 |
| 腾讯云 SCF | 推荐部署方式。北京时间 Cron，独立 zip 包，支持多账号环境变量 |
| GitHub Actions | 轻量备选。UTC Cron，支持多账号/单账号分支和 keepalive |
| 通知 | Server酱 + Telegram 统一由 Python 模块发送 |
| 签名验证 | Python 实现和 `scripts/sign.js` 交叉验证 |
| FastAPI 后端 | 仅骨架预留，阶段三未完成 |

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

python scripts/cli.py setup
python scripts/cli.py status
python scripts/cli.py checkin
```

如果还没有 OpenID，推荐先用模拟器或抓包工具获取：

```powershell
pip install mitmproxy
python scripts/cli.py capture-openid
```

也可以用模拟器自动脚本：

```powershell
python scripts/tools/capture_openid_emulator.py
```

## 常用命令

```powershell
# 首次配置
python scripts/cli.py setup

# OpenID 登录，已绑定账号可免密码
python scripts/cli.py login-openid --profile USER_1 --username 2023XXXXXX --bind 0

# WebVPN token 登录
python scripts/cli.py login-webvpn "bearer eyJ..." 2023XXXXXX

# 查看状态、任务、详情
python scripts/cli.py status
python scripts/cli.py tasks
python scripts/cli.py detail

# 打卡
python scripts/cli.py checkin
python scripts/cli.py checkin --profiles USER_1,USER_2,USER_3

# 查询记录
python scripts/cli.py checkin --record
python scripts/cli.py checkin --record --date 2026-06-01
python scripts/cli.py checkin --month 2026-06

# 配置管理
python scripts/cli.py config
python scripts/cli.py config profile list
python scripts/cli.py config profile USER_2
python scripts/cli.py config sync
```

## 认证说明

### 为什么必须获取 OpenID

反编译小程序后确认：传统 `signIn`、`getCaptcha` 代码路径没有被小程序实际调用。服务端也会返回：

```text
Unauthorized grant type: password
```

因此日常登录应使用：

1. 通过抓包获取微信小程序 OpenID
2. 使用 `grant_type=wxapp` 换取 access token
3. 之后请求带上 `FlySource-Auth` 和 `FlySource-sign`

WebVPN 是备用路径：从浏览器复制 WebVPN 页面请求里的 `flysource-auth`，再用 `login-webvpn` 保存。

### 必要请求头

缺少环境头时，服务端可能返回误导性的“签名错误”。先检查请求头，再怀疑签名算法。

```text
Authorization: Basic <base64(ClientId:ClientSecret)>
FlySource-Auth: <access_token>
FlySource-sign: <签名>
Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html
User-Agent: ...MicroMessenger...MiniProgramEnv/android
```

签名格式：

```text
FlySource-sign = MD5(path + "?sign=" + MD5(ts + token)) + "1." + Base64(ts)
```

验证：

```powershell
python scripts/tools/verify_sign.py --path /api/test --ts 1700000000000 --token test_token --js
python scripts/tools/cross_validate.py
```

## 本地配置

CLI 配置文件位于：

```text
~/.auto_check_in/config.json
```

多账号结构示例：

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
      "task_id": "task-id",
      "client_mode": "wxapp"
    }
  }
}
```

安全约定：

- 终端显示凭据时必须脱敏。
- 密码通过 `secure_input` 输入。
- 本地密码仅 `$obf:<base64>` 混淆保存，不是强加密。
- README 中的 ClientId、ClientSecret 默认值来自反编译源码，是应用级公开常量，不是用户凭据。

## 腾讯云 SCF 部署

推荐使用 SCF 作为生产部署方式。SCF Cron 使用北京时间，表达式无需再做 UTC 换算。

```powershell
# 生成 SCF 环境变量 JSON
python deploy/tencent-scf/deploy.py gen-env

# 生成上传包，不上传
python deploy/tencent-scf/deploy.py --dry-run
```

上传包位置：

```text
deploy/tencent-scf/scf_package.zip
```

当前重新生成的 zip 约 `1.4 MB`。zip 被 `.gitignore` 忽略，不提交到仓库。

SCF 建议配置：

```text
运行时：Python 3.10
入口：handler.main_handler
Cron：0 5 21 * * ? *
```

多账号环境变量示例：

```text
CHECKIN_PROFILES=USER_1,USER_2,USER_3
CHECKIN_OPENID_USER_1=oXXXXXXXX...
CHECKIN_USERNAME_USER_1=2023XXXXXX
CHECKIN_OPENID_USER_2=oXXXXXXXX...
CHECKIN_USERNAME_USER_2=2023XXXXXX
SERVERCHAN_KEY=SCT...
TG_BOT_TOKEN=...
TG_CHAT_ID=...
```

详细教程见 [腾讯云 SCF 部署指南](docs/guides/user/腾讯云SCF部署指南.md) 和 [deploy/tencent-scf/README.md](deploy/tencent-scf/README.md)。

## GitHub Actions

GitHub Actions 是 SCF 的轻量备选方案：

- 定时：每天 UTC 13:05，即北京时间 21:05。
- 手动：支持 `workflow_dispatch`。
- 多账号：设置 `vars.CHECKIN_PROFILES` 后走多账号 Job。
- 单账号：不设置 `vars.CHECKIN_PROFILES` 时走单账号 Job。
- 通知：由 Python 统一发送 Server酱 + Telegram。
- 保活：独立 keepalive Job，避免 60 天无活动导致定时任务停用。

单账号 Secrets：

```text
CHECKIN_OPENID
CHECKIN_USERNAME
CHECKIN_PASSWORD
CHECKIN_TASK_ID
SERVERCHAN_KEY
TG_BOT_TOKEN
TG_CHAT_ID
```

多账号 Secrets：

```text
CHECKIN_OPENID_USER_1
CHECKIN_USERNAME_USER_1
CHECKIN_PASSWORD_USER_1
CHECKIN_OPENID_USER_2
CHECKIN_USERNAME_USER_2
CHECKIN_PASSWORD_USER_2
```

## 时间规则

这是本项目最容易踩坑的地方：

- API 时间判定基于 UTC。
- 打卡窗口是 UTC 13:00-14:30。
- 展示给用户时转换为北京时间 21:00-22:30。
- GitHub Actions Cron 使用 UTC：`5 13 * * *`。
- SCF 控制台 Cron 使用北京时间：`0 5 21 * * ? *`。

## 项目结构

```text
auto_check_in/
├── .github/workflows/        # GitHub Actions 定时任务
├── deploy/tencent-scf/       # 腾讯云 SCF 部署、打包脚本和入口
├── docs/                     # 用户指南、参考文档、开发文档
├── frontend/                 # 阶段三预留前端目录
├── references/               # 逆向分析参考和反编译小程序文件
├── reviews/                  # 代码审查记录
├── scripts/
│   ├── cli.py                # CLI 入口
│   ├── cli_commands/         # 子命令实现
│   ├── tools/                # 签名验证、wxapkg、OpenID 捕获辅助
│   ├── auto_checkin.sh       # GitHub Actions 编排脚本
│   └── sign.js               # JS 签名参考实现
├── src/
│   ├── core/
│   │   ├── client.py         # ApiClient，学校接口封装
│   │   ├── sign_builder.py   # 打卡请求体构建
│   │   └── token_client.py   # SCF 环境变量适配器
│   ├── utils/
│   │   ├── crypto.py         # MD5 / Base64
│   │   ├── geo.py            # 距离和 GPS 偏移
│   │   ├── notification.py   # 通知、窗口提示、汇总文案
│   │   └── sign.py           # FlySource-sign
│   └── main.py               # FastAPI 预留入口
├── tests/                    # 自动化测试
├── .env.example
├── .gitignore
├── requirements.txt
└── requirements-dev.txt
```

根目录只保留项目入口、配置模板、依赖文件和顶层说明。测试临时目录、虚拟环境、zip 包、凭据文件和本地助手配置均由 `.gitignore` 排除。

## 测试

```powershell
# 全量测试
python -m pytest tests/ -q

# Windows 临时目录权限异常时，可指定项目内临时目录
python -m pytest tests/ -q --basetemp .pytest-tmp

# 签名交叉验证
python scripts/tools/cross_validate.py
```

当前验证结果：

```text
114 passed
JS/Python 签名交叉验证 5 组全部通过
```

## 版本状态

`v0.15.0` 聚焦文档和稳定性整理：

- README 完整重写，移除旧版乱码和过期描述。
- 根目录临时文件清理，补充 `.pytest-tmp/`、`.claude/` 忽略规则。
- 当前实际测试数更新为 114。
- 保留现有功能边界：不新增后端功能，不宣称 FastAPI 阶段三已完成。

上一轮代码修复已包含：

- GitHub Actions 脚本导入路径修复。
- 打卡失败/部分失败正确返回非零退出码。
- SCF 全失败返回 `error`，部分成功返回 `partial`。
- 通知成功统计改为状态码白名单。
- Server酱 HTTP 200 内业务失败不再误判成功。
- 通知时间显式使用北京时间。

## 主要文档

| 文档 | 路径 |
| --- | --- |
| 文档总索引 | [docs/README.md](docs/README.md) |
| 快速开始 | [docs/getting-started/快速开始.md](docs/getting-started/快速开始.md) |
| CLI 教程 | [docs/guides/user/CLI教程.md](docs/guides/user/CLI教程.md) |
| 添加新账号 | [docs/guides/user/添加新账号教程.md](docs/guides/user/添加新账号教程.md) |
| 模拟器抓取 OpenID | [docs/guides/user/模拟器自动抓取OpenID.md](docs/guides/user/模拟器自动抓取OpenID.md) |
| 签名算法详解 | [docs/reference/签名算法详解.md](docs/reference/签名算法详解.md) |
| 认证流程与抓包分析 | [docs/reference/认证流程与抓包分析.md](docs/reference/认证流程与抓包分析.md) |
| API 端点参考 | [docs/reference/API端点参考.md](docs/reference/API端点参考.md) |
| SCF 部署指南 | [docs/guides/user/腾讯云SCF部署指南.md](docs/guides/user/腾讯云SCF部署指南.md) |
| 阶段三路线图 | [docs/development/阶段三路线图.md](docs/development/阶段三路线图.md) |

## 开发约定

- 新增 CLI 子命令：`scripts/cli_commands/xxx.py` 实现 `run(args)`，再在 `scripts/cli.py` 注册。
- 修改签名算法时必须同步 `scripts/sign.js`，并运行 `python scripts/tools/cross_validate.py`。
- 涉及请求环境时，优先检查 Referer/User-Agent/Basic Auth，再检查签名算法。
- 架构、功能或部署说明变更时，同步 README、文档索引和变更记录。

## License

MIT License
