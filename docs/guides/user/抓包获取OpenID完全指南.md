# 抓包文件分析 — 读懂微信小程序网络报文

> 适用版本：v0.7.2 | 最后更新：2026-06-08

本文档教你**分析抓到的网络报文**，理解每个请求的含义，从原始数据中找出 OpenID。

---

## 目录

1. [登录全链路报文概览](#1-登录全链路报文概览)
2. [逐条报文分析](#2-逐条报文分析)
3. [关键字段速查](#3-关键字段速查)
4. [真实报文示例（带注释）](#4-真实报文示例带注释)
5. [常见变体与异常报文](#5-常见变体与异常报文)

---

## 1. 登录全链路报文概览

当你在微信中打开「平安打卡」小程序，会发生约 4-8 条 HTTPS 请求。下图是一次完整登录的报文序列：

```
时间轴 →

#1  GET  /api/flySource-base/openApi/getOpenidByJsCode?jsCode=...
         │
         │  用微信临时 code 换取 OpenID
         │  响应: { "data": "oABC123..." }  ← 🔑 OpenID 在这里
         ▼

#2  POST /api/flySource-auth/oauth/token
         │
         │  grant_type=wxapp + OpenID + 学号 + 密码
         │  请求体: ...&openid=oABC123...&...     ← 🔑 OpenID 也在这里
         │  响应: { "access_token": "eyJh..." }   ← 🔑 Token 在这里
         ▼

#3  GET  /api/flySource-yxgl/dormSignTask/getListForApp
         │
         │  带 FlySource-Auth: <token>
         │  带 FlySource-sign: <签名>
         │  响应: 打卡任务列表
         ▼

#4  GET  /api/flySource-yxgl/dormSignRecord/getOne?taskId=...
         │
         │  查询今日打卡状态
         ▼
        ...
```

**重点**：OpenID 只出现在 **#1 的响应体** 和 **#2 的请求体** 中。其他请求里只有 token，没有 OpenID。所以我们只需要分析前两条。

---

## 2. 逐条报文分析

### 2.1 第一条：getOpenidByJsCode — 用临时 code 换 OpenID

这是登录链路的起点。微信 `wx.login()` 生成一个临时 js_code（5 分钟有效），小程序把这个 code 发给学校服务器，学校服务器再转发给微信官方服务器换取真正的 OpenID。

#### 请求（Request）

```
GET /api/flySource-base/openApi/getOpenidByJsCode?jsCode=081xTk0w3abcd1234efgh5i6j7k8l9m0 HTTP/1.1
Host: simp.csuft.edu.cn
User-Agent: Mozilla/5.0 ... MicroMessenger/8.0.72 ...
Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html
```

**逐字段解释：**

| 字段 | 含义 | 从哪里来 |
|------|------|---------|
| `GET` | HTTP 方法，从服务器获取数据 | — |
| `/api/flySource-base/openApi/getOpenidByJsCode` | 飞源平台的"用 js_code 换 OpenID"接口 | 小程序源码中的 API 路径 |
| `?jsCode=081xTk0w...` | `wx.login()` 生成的临时授权码（5分钟有效） | 微信 SDK 自动生成 |
| `Host: simp.csuft.edu.cn` | 目标服务器：中南林业科技大学 | — |
| `User-Agent: ... MicroMessenger/8.0.72 ...` | 声明自己是微信浏览器 | 微信自动设置 |
| `Referer: https://servicewechat.com/wx0e47c34c9982aa09/...` | 声明请求来自哪个小程序页面 | 微信自动设置 |

> 💡 **注意**：这条请求**没有** `Authorization` 头（Basic Auth）和 `FlySource-sign` 头。因为它在小程序中被标记为 `authorization=false`，是公开接口。

#### 响应（Response）

```
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
    "success": true,
    "code": 200,
    "msg": "成功",
    "data": "oABC123XYZ789..."
}
```

**逐字段解释：**

| 字段 | 含义 |
|------|------|
| `success: true` | 请求成功 |
| `code: 200` | HTTP 语义：OK |
| `msg: "成功"` | 中文状态描述 |
| **`data`** | **🎯 这就是 OpenID！** 一个 `o` 开头约 28 位的字符串 |

> 🔑 **OpenID 格式规律**：始终以 `o` 开头，后面是大小写字母+数字混合，约 28 字符。例如 `o6zFv5P7iVQWDISJuCWxIkDNd1U`。

#### Fiddler 中如何找到这条请求

在 Fiddler 会话列表中，它会显示为：
```
#    Result  Protocol  Host              URL
123  200     HTTPS     simp.csuft.edu.cn  /api/flySource-base/openApi/getOpenidByJsCode
```

点击它 → 右侧 **Inspectors** 标签 → 下半部分 **TextView / JSON** → 红色框标注的 `data` 字段。

#### 如果找不到这条请求

说明小程序已登录且 token 未过期，跳过了这步。在微信中**删除小程序**（长按图标 → 删除），重新搜索打开，它会重新走完整登录流程。

---

### 2.2 第二条：oauth/token — 用 OpenID 换取 access_token

拿到 OpenID 后，小程序调用飞源的 OAuth2 接口，用 OpenID + 学号 + 密码换取 `access_token`。之后的打卡请求都靠这个 token。

#### 请求（Request）

```
POST /api/flySource-auth/oauth/token HTTP/1.1
Host: simp.csuft.edu.cn
Content-Type: application/x-www-form-urlencoded
Authorization: Basic Zmx5c291cmNlX3dpc2Vfd3hhcHA6REE3ODhhc2RVRGpuYXNkX2ZseXNvdXJjZV93eGFwcGRzZGFkREFJVWl1d3Fl
charset: utf-8
User-Agent: Mozilla/5.0 ... MicroMessenger/8.0.72 ...
Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html
Web-Type: wxapp
Tenant-Id: 000000

grant_type=wxapp&tenantId=000000&username=2023XXXXXX&password=e10adc3949ba59abbe56e057f20f883e&openid=oABC123XYZ789...&bindState=1&scope=all
```

**逐字段解释：**

| 字段 | 位置 | 含义 |
|------|------|------|
| `POST` | 请求行 | HTTP 方法，向服务器提交数据 |
| `Content-Type: application/x-www-form-urlencoded` | 请求头 | 请求体是 HTML 表单格式（`key=value&key=value`） |
| **`Authorization: Basic ...`** | 请求头 | **客户端认证**。Base64 解码后是 `flysource_wise_wxapp:DA788asdUDjnasd_flysource_wxappdsdadDAIUiuwqe`。每条请求都带，证明自己是官方小程序 |
| `charset: utf-8` | 请求头 | 字符编码 |
| `Web-Type: wxapp` | 请求头 | 声明这是微信小程序端发来的请求 |
| `Tenant-Id: 000000` | 请求头 | 学校/租户 ID。中南林业科技大学固定为 `000000` |
| — | — | **以下是请求体（body）** |
| `grant_type=wxapp` | 请求体 | OAuth2 授权类型。`wxapp` = 微信小程序登录 |
| `tenantId=000000` | 请求体 | 租户 ID（与请求头重复，飞源的设计如此） |
| `username=2023XXXXXX` | 请求体 | 学号 |
| `password=e10adc39...` | 请求体 | **密码的 MD5 哈希**（32位十六进制小写） |
| **`openid=oABC123...`** | 请求体 | **🎯 OpenID！** 第一条响应拿到的值 |
| `bindState=1` | 请求体 | 绑定模式：`1`=绑定并登录，`0`=仅登录不绑定 |
| `scope=all` | 请求体 | OAuth2 权限范围 |

> 🔑 **如果方法 A（getOpenidByJsCode）抓不到，这里就是备选方案**。`openid=xxx` 在请求体中明文传输，直接复制即可。

#### 响应（Response）

```json
{
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 2592000,
    "scope": "all",
    "tenant_id": "000000",
    "username": "2023XXXXXX",
    "openid": "oABC123XYZ789..."
}
```

**逐字段解释：**

| 字段 | 含义 |
|------|------|
| `access_token` | JWT 格式的访问令牌。之后的打卡/查询请求都要带这个 |
| `token_type: "bearer"` | OAuth2 标准：Bearer 令牌 |
| `expires_in: 2592000` | token 有效期 2592000 秒 = **30 天** |
| `scope: "all"` | 权限范围：全部 |
| `tenant_id` | 租户 ID |
| `username` | 学号（服务器回传确认） |
| `openid` | OpenID（服务器回传确认） |

#### 响应中的常见错误

| 错误响应 | 原因 | 解决 |
|---------|------|------|
| `{"error": "invalid_grant", "error_description": "绑定失败..."}` | 该 OpenID 已绑定过学号 | 用 `--bind 0` 仅登录不绑定 |
| `{"error": "invalid_grant", "error_description": "密码错误"}` | 密码不正确 | 重新输入密码 |
| `{"code": 401, "msg": "未登录或登录已过期"}` | — | token 过期后的正常返回，不是登录时的错误 |

---

## 3. 关键字段速查

### 请求头（Headers）每字段作用

```
Authorization    → 证明"我是官方小程序客户端"（每条请求必带）
FlySource-Auth   → 证明"我是已登录用户"（登录后才出现，值为 access_token）
FlySource-sign   → 防止请求伪造（登录后才出现，值为签名哈希）
Referer          → 伪装微信小程序环境（服务器反爬校验）
User-Agent       → 伪装微信浏览器（同上）
Tenant-Id        → 标识学校（000000 = 中南林业科技大学）
Web-Type         → 标识客户端类型（wxapp = 微信小程序）
charset          → 字符编码声明（utf-8）
Content-Type     → 请求体格式（json / form）
```

### 请求体中每种 grant_type 的字段

```
grant_type=wxapp (微信登录):
  tenantId   — 学校 ID
  username   — 学号
  password   — 密码 MD5
  openid     — 微信 OpenID  ← 🔑
  bindState  — 0=登录 / 1=绑定并登录
  scope      — all

grant_type=password (密码登录):
  tenantId   — 学校 ID
  username   — 学号
  password   — 密码 MD5
  scope      — all
```

### 响应体统一格式

飞源所有接口遵循相同的 JSON 外壳：

```json
{
    "success": true/false,
    "code": 200/401/500,
    "msg": "状态描述（中文）",
    "data": { ... } 或 "字符串" 或 null
}
```

- `success` = 业务是否成功
- `code` = HTTP 语义状态码。`401` = 未登录/token 过期
- `msg` = 人类可读的状态消息
- `data` = 实际数据，可能是对象、字符串、null

---

## 4. 真实报文示例（带注释）

下面是一份完整的抓包记录，逐条标注。← 表示重要/需要关注的字段。

### 报文 #1：获取 OpenID

```
┌── REQUEST ────────────────────────────────────────────
│ GET /api/flySource-base/openApi/getOpenidByJsCode?jsCode=081abc123def456gh
│ Host: simp.csuft.edu.cn
│ User-Agent: ... MicroMessenger/8.0.72 ... MiniProgramEnv/android
│ Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html
│
│ (无请求体 — GET 方法参数在 URL 中)
└──────────────────────────────────────────────────────

┌── RESPONSE ───────────────────────────────────────────
│ 200 OK
│ Content-Type: application/json
│
│ {
│   "success": true,
│   "code": 200,
│   "msg": "成功",
│   "data": "oABC123XYZ789abcdefghijklmn"     ← 🔑 OpenID！
│ }
└──────────────────────────────────────────────────────
```

### 报文 #2：登录换取 Token

```
┌── REQUEST ────────────────────────────────────────────
│ POST /api/flySource-auth/oauth/token
│ Host: simp.csuft.edu.cn
│ Content-Type: application/x-www-form-urlencoded
│ Authorization: Basic Zmx5c291cmNlX3dpc2Vfd3hhcHA6REE3ODhhc2... ← 客户端认证
│ Tenant-Id: 000000                                       ← 学校 ID
│ Web-Type: wxapp                                         ← 微信端标识
│ Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html
│
│ grant_type=wxapp&                                       ← OAuth2 授权类型
│ tenantId=000000&
│ username=2023XXXXXX&                                     ← 学号
│ password=e10adc3949ba59abbe56e057f20f883e&              ← 密码 MD5
│ openid=oABC123XYZ789abcdefghijklmn&                     ← 🔑 OpenID！
│ bindState=1&                                             ← 绑定 + 登录
│ scope=all
└──────────────────────────────────────────────────────

┌── RESPONSE ───────────────────────────────────────────
│ 200 OK
│
│ {
│   "access_token": "eyJhbGciOiJSUzI1NiJ9.eyJ1c2Vy...",  ← 🔑 Token！
│   "token_type": "bearer",
│   "expires_in": 2592000,                                 ← 30 天有效
│   "scope": "all",
│   "tenant_id": "000000",
│   "username": "2023XXXXXX",
│   "openid": "oABC123XYZ789abcdefghijklmn"
│ }
└──────────────────────────────────────────────────────
```

### 报文 #3：获取任务列表（登录后）

```
┌── REQUEST ────────────────────────────────────────────
│ GET /api/flySource-yxgl/dormSignTask/getListForApp?current=1&size=10
│ Host: simp.csuft.edu.cn
│ Authorization: Basic Zmx5c291cmNlX3dpc2Vfd3hhcHA6REE3ODhhc2...
│ FlySource-Auth: eyJhbGciOiJSUzI1NiJ9.eyJ1c2Vy...         ← 🔑 Token！
│ FlySource-sign: a1b2c3d4e5f6789...1.MTcwMDAwMDAwMDAwMA==  ← 签名
│ Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html
└──────────────────────────────────────────────────────

┌── RESPONSE ───────────────────────────────────────────
│ 200 OK
│
│ {
│   "success": true,
│   "code": 200,
│   "data": {
│     "records": [
│       {
│         "taskId": "b49ffb3790cfa0fb60661e4b59cdfbc8",    ← 用于后续打卡
│         "taskName": "平安打卡",
│         "signStartTime": "21:00",
│         "signEndTime": "22:30"
│       }
│     ]
│   }
│ }
└──────────────────────────────────────────────────────
```

---

## 5. 常见变体与异常报文

### 变体 1：getOpenidByJsCode 未触发

**现象**：抓包中直接出现 `oauth/token`，没有 `getOpenidByJsCode`。

**原因**：小程序已登录，token 未过期，直接进入首页。OpenID 从本地缓存读取，不再向服务器请求。

**怎么办**：在 `oauth/token` 请求体的 `openid=` 字段取 OpenID（见报文 #2）。

### 变体 2：bindState=0（仅登录不绑定）

**现象**：`oauth/token` 请求体中 `bindState=0`，`username` 和 `password` 为空。

```
grant_type=wxapp&tenantId=000000&username=&password=&openid=oABC123...&bindState=0&scope=all
```

**含义**：小程序首页加载，仅用 OpenID 登录获取 token（查看公告等不需要绑定学号的操作）。

**怎么办**：OpenID 仍然在 `openid=` 字段中，照常使用。之后用 `--bind 1` 重新登录绑定即可。

### 变体 3：401 Token 过期

**现象**：除了 `oauth/token` 之外的请求返回：

```json
{
    "code": 401,
    "success": false,
    "msg": "未登录或登录已过期"
}
```

**含义**：access_token 已过期（30 天到期）。

**怎么办**：重新执行 `login-openid`（OpenID 永久有效，不需要重新抓包）。

### 变体 4：签名错误（实际是环境头缺失）

**现象**：带 `FlySource-sign` 的请求返回：

```json
{
    "code": 500,
    "success": false,
    "msg": "签名错误"
}
```

**真实原因**：99% 的情况不是签名算法算错，而是请求头缺少 `Referer` 或 `User-Agent`（没有伪装微信环境）。

**检查**：确认请求头包含 `Referer: https://servicewechat.com/wx0e47c34c9982aa09/7/page-frame.html` 和 `User-Agent: ... MicroMessenger ... MiniProgramEnv/android`。

---

## 总结：拿到 OpenID 的最短路径

```
抓包 → 过滤 simp.csuft.edu.cn
     → 找到 GET /getOpenidByJsCode → 响应 data 字段 = OpenID（首选）
     → 或  找到 POST /oauth/token → 请求体 openid= 字段 = OpenID（备选）
     → 复制 OpenID
     → python scripts/cli.py setup
     → 完成
```
