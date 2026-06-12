# 腾讯云函数（SCF）自动打卡部署方案

将 CSUFT 自动晚点名打卡部署到腾讯云 Serverless Cloud Function（SCF），替代 GitHub Actions。

> 完整图文教程见 `docs/guides/user/腾讯云SCF部署指南.md`

## 架构

```
timer (21:05 北京时间) → SCF Function → 登录校园网 → 获取任务 → 打卡 → Server酱通知
```

| 组件 | 说明 |
|------|------|
| 触发器 | 定时触发器，每天 21:05（Cron 默认北京时间，7 字段格式） |
| 运行时 | Python 3.10 |
| 入口 | `handler.main_handler` |
| 通知 | Server酱 微信推送（可选） |
| 配置 | SCF 控制台环境变量（平台默认加密存储） |

## 前置工作

### 1. 注册腾讯云账号

1. 打开 [腾讯云](https://cloud.tencent.com) 注册（新用户有免费额度和代金券）
2. 搜索 **云函数 SCF** → 进入控制台
3. 确定地域（推荐 **广州**，离中南林科大 API 最近）

### 2. 获取 OpenID

抓包获取微信 OpenID，参考：

- `docs/guides/user/fiddler-抓包获取OpenID.md`（PC + 同一 WiFi）
- `docs/guides/user/Reqable-抓包获取OpenID.md`（手机端 VPN）

### 3. 获取 Server酱 SendKey（可选）

1. 打开 [Server酱](https://sct.ftqq.com) 扫码注册
2. 在「Key & API」页面复制 SendKey（格式：`SCT123456...`）

## 手动部署步骤

### 步骤 1：创建函数

1. SCF 控制台 → **函数服务** → **新建**
2. 选择 **从头开始**

| 字段 | 值 |
|------|-----|
| 函数类型 | 事件函数 |
| 函数名称 | `CSUFT_AutoCheckIn` |
| 地域 | 广州 |
| 运行环境 | Python 3.10 |

### 步骤 2：打包代码

在项目根目录运行：

```bash
# 生成 scf_package.zip
python deploy/tencent-scf/deploy.py --dry-run

# Windows (PowerShell) 手动打包
python -m pip install httpx certifi -t deploy/tencent-scf/
# 然后手动复制 src/ 模块

# Linux/Mac
bash deploy/tencent-scf/package.sh
```

### 步骤 3：上传代码

1. 进入函数 `CSUFT_AutoCheckIn` → **函数代码**
2. 下方 **更改代码上传方式** → 选 **本地上传 zip 包**
3. 选择 `scf_package.zip` → 点 **部署** 按钮

### 步骤 4：配置环境变量

SCF 控制台 → **函数配置** → 环境变量：

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `CHECKIN_OPENID` | 是 | 微信 OpenID |
| `CHECKIN_USERNAME` | 是 | 学号 |
| `CHECKIN_PASSWORD` | 是 | 密码 |
| `CHECKIN_TASK_ID` | 否 | 任务 ID（不设则自动获取） |
| `SERVERCHAN_KEY` | 否 | Server酱 SendKey |

基础设置：**执行超时时间** 30 秒，**启动类/方法** `handler.main_handler`。

### 步骤 5：配置触发器

1. **触发管理** → **创建触发器**
2. **定时触发** → Cron 表达式：`0 5 21 * * ? *`（7 字段格式，北京时间）

### 步骤 6：测试

1. **函数代码** → 点击下方 **测试** 按钮
2. 选 **Hello World 事件** → **运行**
3. 查看日志

---

## 与 GitHub Actions 对比

| 对比项 | GitHub Actions | 腾讯云 SCF |
|--------|---------------|------------|
| 费用 | 免费（有限额） | 免费额度 100 万次调用/月 |
| 配置复杂度 | 低（只需 Secrets） | 中（需上传代码） |
| 执行时长 | 最多 6 小时 | 最多 900 秒（足够） |
| 网络 | 海外节点（需访问内地 API） | 广州节点（极低延迟） |
| 持久化 | 无（每次全新环境） | 无（无状态） |
| 通知 | Server酱 + Telegram | Server酱 |

## 注意事项

1. **密钥安全**：SCF 环境变量由平台加密存储
2. **超时设置**：建议函数超时设为 **30 秒**（打卡流程通常 < 10 秒）
3. **内存设置**：**64 MB** 足够
4. **Cron 时区**：SCF 控制台默认北京时间，`0 5 21 * * ? *` 即 21:05 触发
5. **OpenID 过期**：OpenID 通常长期有效，但如果微信账号异常需重新抓包
