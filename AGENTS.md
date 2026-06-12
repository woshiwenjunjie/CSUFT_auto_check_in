# AGENTS.md — Auto Check-In

中南林业科技大学自动晚点名打卡。模拟微信小程序 API，通过逆向还原的签名算法和接口链实现命令行打卡。

## 关键约定

1. **回复用中文**，英文专业术语（API/JSON/HTTP）除外
2. **凭据安全** — 显示脱敏（`_mask`），密码用 `secure_input`，不写死凭据
3. **交叉验证** — 签名算法用 JS 原版（`scripts/sign.js`）和 Python 实现互验
4. **文档同步** — 架构/功能变更时更新 CHANGELOG + memory + AGENTS.md
5. **两个客户端模式** — `wxapp`（微信小程序）和 `web`（WebVPN），通过 `client_mode` 切换，Referer/User-Agent/Basic Auth 自动匹配

## 快速命令

```powershell
.\.venv\Scripts\activate               # 激活虚拟环境
python -m pytest tests/ -v             # 运行全部 67 个测试
python scripts/cli.py <setup|status|tasks|checkin|config|detail|record|month|login|login-openid|login-webvpn|capture-openid>
python scripts/cli.py login-webvpn     # WebVPN token 验证+保存（绕过 OpenID）
python scripts/cli.py capture-openid   # 一键启动 mitmproxy 自动捕获 OpenID
node scripts/sign.js /api/test 1700000000000 test_token  # 签名交叉验证
pip install mitmproxy                  # 首次使用 capture-openid 前先装依赖
fastapi dev src/main.py                # 启动 FastAPI 后端
```

## 架构

### 认证：只有 OpenID 方式有效

- 小程序源码分析确认：`signIn`（密码+验证码）和 `getCaptcha` 函数**从未被调用**，是死代码
- 服务器返回 `"Unauthorized grant type: password"`，拒绝密码授权
- **必须通过抓包获取 OpenID**，推荐用 `capture-openid` CLI 命令自动捕获（mitmproxy），也可用 Fiddler/HTTPCanary 手动抓包
- ```python scripts/cli.py capture-openid``` — 一键启动 mitmproxy，手机设代理后打开小程序即可自动捕获 OpenID
- 正确流程：`wx.login()` → `getOpenidByJsCode` → `oauth/token` (`grant_type=wxapp`)
- 手机开热点时手机本身无法设代理，需用 **Reqable**（原名 HTTPCanary，本地 VPN 抓包，不需代理）或 **USB 反向共享**（电脑开 Fiddler，手机 USB 连电脑开 USB 网络共享后再设代理）

### 请求头（缺任意一个都可能被拒）

```
Authorization: Basic <base64(ClientId:ClientSecret)>  客户端认证
FlySource-Auth: <access_token>                        用户认证
FlySource-sign: <签名>                                 防伪造
Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html
User-Agent: ...MicroMessenger...MiniProgramEnv/android
```
⚠️ 缺 Referer/User-Agent 时服务器返回 **"签名错误"**（误导性报错），先检查环境头再怀疑签名算法。

### 源码结构

| 路径 | 职责 |
|------|------|
| `src/core/client.py` | ApiClient — 封装 8 个学校接口，统一签名/认证/指数退避重试 |
| `src/utils/sign.py` | FlySource-sign: `MD5(path+"?sign="+MD5(ts+token))+"1."+Base64(ts)` |
| `src/utils/crypto.py` | MD5、Base64 封装 |
| `src/utils/geo.py` | Haversine 距离 + 带 seed 的 GPS 随机偏移 |
| `src/main.py` | FastAPI 脚手架（阶段三） |
| `scripts/cli.py` | argparse 入口，dispatch 到 cli_commands/ |
| `scripts/capture_addon.py` | mitmproxy addon — 自动捕获 OpenID |
| `scripts/cli_commands/` | 子命令：`auth.py`（含 login-openid/login/login-webvpn） `checkin.py` `tasks.py` `status.py` `config_cmd.py` `setup.py` `capture.py` + `_common.py` |
| `scripts/cli_config.py` | 配置 ~/.auto_check_in/config.json，密码 `$obf:<base64>` 混淆存储 |
| `scripts/cli_ui.py` | ANSI 样式、Spinner、彩色终端输出 |
| `tests/` | 6 个文件 31 个测试（crypto 6 + sign 6 + geo 8 + config 6 + cross_validate 5） |
| `tests/deploy/` | SCF 部署测试 36 个（notify 4 + checkin_core 14 + checkin_api 7 + handler 4 + deploy 4 + conftest） |
| `deploy/tencent-scf/` | 腾讯云 SCF 部署方案：入口 handler.py、编排 checkin.py、通知 notify.py、打包脚本 deploy.py/package.sh、README |
| `reviews/` | 代码审查记录 |
| `docs/review/` | 子代理审查结果 |

新增子命令：新建 `cli_commands/xxx.py` → 实现 `run(args)` → cli.py import + dispatch + argparse

### 凭据默认值（均可被环境变量覆盖）

| 凭据 | 默认值 |
|------|--------|
| `FLYSOURCE_CLIENT_ID` | `flysource_wise_wxapp`（微信小程序）/ `flysource_wise_app`（WebVPN） |
| `FLYSOURCE_CLIENT_SECRET` | `DA788asdUDjnasd_flysource_wxappdsdadDAIUiuwqe`（小程序）/ `DA788asdUDjnasd_flysource_dsdadDAIUiuwqe`（WebVPN） |
| `CHECKIN_BASE_URL` | `https://simp.csuft.edu.cn` |

### 腾讯云 SCF 部署

`deploy/tencent-scf/` 文件夹包含完整的 SCF 部署方案。核心模块：

| 模块 | 职责 |
|------|------|
| `handler.py` | SCF 入口 `main_handler(event, context)`，含异常安全网（try/except + 通知） |
| `checkin.py` | 编排层：登录 → 任务 → 打卡 → 确认 → 通知；`ApiTokenClient` 适配器包装 `ApiClient` |
| `notify.py` | Server酱 推送，2 次重试 + 3s 间隔 |
| `deploy.py` | 一键打包部署，运行时通过 `SCF_RUNTIME` 环境变量指定（默认 Python3.10） |
| `package.sh` | Linux/macOS 打包脚本 |
| `requirements.txt` | 仅 httpx + certifi（宽松版本约束） |

设计要点：
- 所有时间变量为延迟函数（`_now()`/`_now_str()`/`_date_str()`），避免 warm start 冻结
- 无 `scf_bootstrap`，使用标准 Python 运行时
- 错误状态 5 种：`ok`/`duplicate`/`expired`/`nowindow`/`error`
- GPS 偏移退避：0.002° 起始 → 折半 → 最多 6 次 → 1e-6° 最小阈值
- `handler.py` 中空 event 返回 `{"status": "healthy"}` 支持健康检查

### ⚠️ UTC 时间陷阱（重要）

flySource 服务器所有时间判定基于 **UTC**。`signStartTime`/`signEndTime` 是 UTC 时刻，窗口实际为 **UTC 13:00–14:30**（对应北京时间 21:00–22:30）。不要假设 API 返回的时间是本地时间，任何需要时区的显示都要做 UTC+8 转换。

### GitHub Actions

`.github/workflows/auto-checkin.yml` — 每天 UTC 13:05（北京时间 21:05）触发，从 Secrets 注入凭据全新登录 → 打卡 → Server酱通知。支持 `workflow_dispatch` 手动触发。

## 项目状态

- ✅ 阶段一/二：逆向分析 + CLI 工具（67 测试通过，全部功能可用）
- ✅ GitHub Actions 自动打卡 + 微信通知
- ✅ 腾讯云 SCF 部署方案（`deploy/tencent-scf/`）— 替代 GitHub Actions，独立文件夹，手动+自动双部署方式
- ⏳ 阶段三：FastAPI 后端 + 多用户 + 定时任务

## 关键文档

| 文档 | 位置 |
|------|------|
| Fiddler 抓包获取 OpenID 完整指南 | `docs/guides/user/fiddler-抓包获取OpenID.md` |
| Reqable 抓包获取 OpenID 指南 | `docs/guides/user/Reqable-抓包获取OpenID.md` |
| CLI 详细用法 | `docs/guides/user/CLI教程.md` |
| 签名算法详解 | `docs/guides/dev/签名算法详解.md` |
| 逆向分析结果 | `docs/memory/003-逆向分析结果.md` |
| 参考文章（NaHS2） | `references/nahs-online-自动打卡文章总结.md` |
| 腾讯云 SCF 部署指南 | `docs/guides/user/腾讯云SCF部署指南.md` |
