# 腾讯云函数（SCF）自动打卡部署指南

将 CSUFT 自动晚点名打卡部署到腾讯云 Serverless Cloud Function（SCF），
每天 21:05 自动执行签到。支持**多账号**一次部署全家桶。

---

## 对比：GitHub Actions vs SCF

| 维度 | GitHub Actions | 腾讯云 SCF ✅ |
|------|---------------|--------------|
| 触发时区 | UTC，需转换 | 北京时间直接配 |
| 保活 | 60 天无活动停用 | 无此限制 |
| 地域 | 海外节点 | 广州，极低延迟 |
| 配置 | 7 个 Secrets | 环境变量（可加密） |
| 费用 | 免费（有限额） | 免费 100 万次/月 |
| 多账号 | 需 matrix 策略 | 原生多用户循环 |

---

## 目录

1. [注册 & 准备](#1-注册--准备)
2. [获取 OpenID](#2-获取-openid)
3. [获取 Server酱 SendKey（可选）](#3-获取-server酱-sendkey可选)
4. [打包代码](#4-打包代码)
5. [创建云函数](#5-创建云函数)
6. [上传代码](#6-上传代码)
7. [配置环境变量](#7-配置环境变量)
8. [配置触发器](#8-配置触发器)
9. [测试验证](#9-测试验证)
10. [更新代码](#10-更新代码)
11. [常见问题](#11-常见问题)

---

## 1. 注册 & 准备

1. 打开 [腾讯云](https://cloud.tencent.com) 注册（新用户有免费额度）
2. 搜索 **云函数 SCF** → 进入控制台
3. 确定地域 — 推荐 **广州**（离学校 API 最近，延迟最低）

---

## 2. 获取 OpenID

每个账号都需要一个 OpenID（微信小程序用户唯一标识）。

方式 A：**自动捕获（推荐）** — 电脑 + 手机同一 WiFi：
```bash
cd auto_check_in
pip install mitmproxy
python scripts/cli.py capture-openid
```
手机设代理到电脑 `IP:8080` → 装 CA 证书 → 打开小程序 → OpenID 自动保存。

方式 B：**模拟器自动方案**（免 root）：
```bash
python scripts/tools/capture_openid_emulator.py
```

方式 C：**手动抓包** — 见 `docs/guides/user/fiddler-抓包获取OpenID.md`

> 多账号：每个微信账号分别操作一次，记下各自的 OpenID。

---

## 3. 获取 Server酱 SendKey（可选）

1. 打开 [Server酱](https://sct.ftqq.com) 微信扫码注册
2. 在「Key & API」页面复制 SendKey（格式 `SCT123456...`）
3. 后续会配到环境变量中

不配也可以，打卡照样执行，只是不发微信通知。

---

## 4. 打包代码

在项目根目录运行：

```bash
python deploy/tencent-scf/deploy.py --dry-run
```

成功输出：
```
[1/4] 复制入口文件...
[2/4] 复制核心库...
[3/4] 安装 pip 依赖...
[4/4] 打包...
  → scf_package.zip (244 KB)
```

生成的 `deploy/tencent-scf/scf_package.zip` 就是上传包。

---

## 5. 创建云函数

SCF 控制台 → **函数服务** → **新建** → **从头开始**：

| 字段 | 值 |
|------|-----|
| 函数类型 | **事件函数** |
| 函数名称 | `CSUFT_AutoCheckIn`（可自定义） |
| 地域 | **广州** |
| 运行环境 | **Python 3.10** |

点 **完成**。

---

## 6. 上传代码

1. 进入刚创建的函数 `CSUFT_AutoCheckIn`
2. 切到 **函数代码** 标签页
3. 下方 **更改代码上传方式** → **本地上传 zip 包**
4. 选择 `deploy/tencent-scf/scf_package.zip` → 点 **部署** 按钮（等待约 10 秒）

---

## 7. 配置环境变量

切到 **函数配置** 标签 → 下方 **环境变量** → **添加环境变量**。

### 多用户模式（推荐，一次部署打多个号）

```bash
# 变量名                   变量值
CHECKIN_PROFILES    =      USER_1,USER_2
CHECKIN_OPENID_USER_1     oHfYy5...（USER_1 的 OpenID）
CHECKIN_USERNAME_USER_1   2023XXXXXX（USER_1 的学号）
CHECKIN_PASSWORD_USER_1   xxxxxx（USER_1 的密码）
CHECKIN_OPENID_USER_2     oHfYy5...（USER_2 的 OpenID）
CHECKIN_USERNAME_USER_2   2023XXXXXX（USER_2 的学号）
# USER_2 如果已绑定点过免密码，可以不设 CHECKIN_PASSWORD_USER_2
SERVERCHAN_KEY            SCT123...（可选，微信推送用）
CHECKIN_TASK_ID           （可选，留空则自动获取）
```

### 单用户模式（兼容旧版，只打一个号）

不设 `CHECKIN_PROFILES`，直接配以下三个即可：

```bash
CHECKIN_OPENID      oHfYy5...（OpenID）
CHECKIN_USERNAME    2023XXXXXX（学号）
CHECKIN_PASSWORD    xxxxxx（密码）
SERVERCHAN_KEY      SCT123...（可选）
```

> **向后兼容说明**：单用户模式之所以能工作，是因为代码会自动将 profile 名设为 `"default"`，
> 先找 `CHECKIN_OPENID_default` 找不到，兜底读取 `CHECKIN_OPENID`（裸变量）。
> 所以不设 `CHECKIN_PROFILES` 时行为与旧版完全一致——不用改任何现有配置。

### 其他配置项

**基础设置**：
- 执行超时时间：**30 秒**（默认 3 秒太短，打卡流程约需要 5–10 秒）
- 内存：**64 MB**（默认 128 MB 也行，多花一毛钱）

**敏感字段**：OpenID、密码、Server酱 Key 全部勾选 **加密存储**（SCF 平台加密，日志不显示明文）。

---

## 8. 配置触发器

1. 切到 **触发管理** 标签 → **创建触发器**
2. 触发器类型：**定时触发**
3. Cron 表达式（选 **自定义**，填入）：

```cron
0 5 21 * * ? *
```

**7 字段格式含义**：

```
秒 分 时  日 月 周 年
0  5  21  *  *  ?  *
```

即每天 **北京时间 21:05** 触发。SCF 控制台默认使用北京时间，无需时区转换。
Cron 格式含秒和年（7 字段），与标准 Linux cron（5 字段）不同。

**创建** → 搞定。

---

## 9. 测试验证

1. 切回 **函数代码** 标签
2. 下方选 **Hello World 事件模板** → 点 **测试**
3. 查看日志输出

预期日志：
```
[通知] SERVERCHAN_KEY 未配置，跳过    ← 没配通知，正常
[结果] status=ok msg=[default] 正常
```

如果配了 Server酱，微信会收到打卡成功通知。

---

## 10. 更新代码

项目代码更新后，重新打包上传：

```bash
# 重新打包
python deploy/tencent-scf/deploy.py --dry-run

# 控制台上传（同第一次）
# 函数代码 → 本地上传 zip 包 → scf_package.zip → 部署
```

---

## 11. 常见问题

### Q: 打卡失败提示"签名错误"？

先检查 `Referer` 和 `User-Agent` 是否完整。SCF 打包已包含正确的环境头，
一般不会出现此问题。如果出现，可能是后端 API 地址变化。

### Q: 多账号怎么加人？

在环境变量中加一组：

```
CHECKIN_OPENID_USER_5=o...
CHECKIN_USERNAME_USER_5=2023XXXXXX
```

然后在 `CHECKIN_PROFILES` 中追加 `,USER_5`。点 **保存** 即生效，无需重新上传代码。

### Q: 密码忘了怎么办？

密码不需要记住。如果账号已绑定（之前点过「绑定」并打卡成功），
直接不设 `CHECKIN_PASSWORD_USER_X` 即可免密码登录。

### Q: OpenID 过期了怎么办？

重新抓包获取新 OpenID → SCF 控制台修改对应环境变量 → 保存。

### Q: 怎么查看打卡日志？

SCF 控制台 → 函数 → **日志查询** → 选时间范围 → 查看每次调用的输出。
日志包含每个 profile 的登录状态、打卡结果、通知状态。

### Q: 同时打卡多个账号，时间够吗？

一个账号约 2-3 秒，5 个账号约 15 秒。超时配 30 秒绰绰有余。
