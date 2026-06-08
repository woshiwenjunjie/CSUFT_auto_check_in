# 004 — 审查修复与 OpenID 发现

日期：2026-06-07

## 本次变更（v0.6.0）

### 代码审查遗留问题修复

按审查报告优先级分五轮完成全部 8 项修复：

| 优先级 | 问题 | 修复 |
|--------|------|------|
| P0 | ApiClient 无上下文管理器 | 新增 `__enter__`/`__exit__`，支持 `with` 语句 |
| P0 | FastAPI 缺 CORS + lifespan | 新增 CORSMiddleware 和 lifespan 管理 ApiClient |
| P1 | BASE_URL 模块级常量 | 改为实例属性，构造函数参数可注入 |
| P1 | 无 pytest 测试 | 20 个测试用例覆盖 crypto/sign/geo |
| P2 | cli.py:49 可读性差 | 三目表达式拆分为 if/else |
| P2 | 无重试机制 | 指数退避重试（最多 3 次，1s/2s/4s） |
| P3 | .env.example 变量被注释 | 取消注释，开箱即用 |
| P3 | requirements.txt 未锁定 | 全部改为固定版本号 |

### OpenID 抓包方案落地

- 创建 `docs/guides/fiddler-抓包获取OpenID.md`（341 行，9 章节）
- 第 2.1 节补充 Fiddler Classic 汉化操作说明（含 GitHub 补丁链接）
- 涵盖 Fiddler 下载安装、HTTPS 解密配置、手机代理设置、抓包定位 OpenID 全流程

### 所有代码添加注释

8 个源码文件全部添加中文模块/类/函数级注释，无行内注释过度。

### 清理

- 删除 `captcha.png`（测试产物）
- 删除 `.pytest_cache`、4 个 `__pycache__` 目录

## 关键发现

### 1. 验证码接口无需 type 参数

`GET /api/flySource-auth/captcha` （不加任何参数）直接返回：
```json
{"key": "...", "image": "data:image/png;base64,..."}
```
如果传 `?type=captcha` 会返回 400"参数类型错误"。无认证头即可调用。

### 2. signIn（密码+验证码）是死代码

深入分析 wxapkg 源码后确认：
- `http/index.js` 中的 `signIn` 函数（密码+验证码版）**在整个小程序代码库中没有任何调用者**
- `getCaptcha` 函数同样**从未被调用**
- 验证码的 `<image>` 和输入框在 WXML 模板中存在但 Vue setup 中没有实现任何事件处理或数据绑定
- **所有实际登录都走微信 OpenID 流程**（`signInOpenId`）

### 3. 服务器拒绝 grant_type=password

测试 `POST /api/flySource-auth/oauth/token` 带 `grant_type=password`：
```
WWW-Authenticate: Bearer error="invalid_client", error_description="Unauthorized grant type: password"
```
该客户端（`flysource_wise_wxapp`）明确不允许 password 授权类型，只能使用 `wxapp`（OpenID）方式。

### 4. 正确登录流程

```
wx.login() → 临时 jsCode
  → GET /api/flySource-base/openApi/getOpenidByJsCode?jsCode=xxx
      → 返回 openid（响应体 data 字段）
  → POST /api/flySource-auth/oauth/token (grant_type=wxapp, openid=xxx, bindState=0/1)
      → 返回 access_token
```

### 5. captcha 验证（API 调试验证）

- 获取验证码：`GET https://simp.csuft.edu.cn/api/flySource-auth/captcha`（无需认证，无需参数）
- 验证码图片可正常获取并保存为 PNG
- 但学校服务器可能已禁用 password 授权类型，导致验证码流程无用

## 结论

要使用本项目必须通过 Fiddler 抓包获取 OpenID，密码+验证码方式不可行。OpenID 获取后通过 `python scripts/cli.py login-openid <OpenID> <学号>` 绑定并登录。

## 后续计划

1. 按 Fiddler 指南抓包获取 OpenID
2. 用 CLI 验证全链路（login-openid → tasks → detail → checkin）
3. 进入阶段三：FastAPI 后端开发
