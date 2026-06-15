# 腾讯云 SCF 自动打卡部署指南

将 CSUFT 自动晚点名打卡部署到腾讯云 Serverless Cloud Function（SCF），替代 GitHub Actions。

## 架构

```
定时触发 (每天 21:05 北京时间) → SCF 函数 → 登录校园网 → 获取任务 → 打卡 → Server酱通知
```

## 前置条件

- [ ] 腾讯云账号（已实名认证）
- [ ] 微信 OpenID（抓包获取，参考 `fiddler-抓包获取OpenID.md` 或 `Reqable-抓包获取OpenID.md`）
- [ ] Server酱 SendKey（可选，参考 `Server酱配置教程.md`）

## 第一步：领取免费额度

1. 打开 [SCF 控制台](https://console.cloud.tencent.com/scf)
2. 首次进入时按提示完成服务授权
3. 进入 **套餐包** 页面，**0 元购买个人标准版套餐包**
   - 额度：50 万次调用/月 + 10 万 GBs/月 + 2 GB 外网出流量
   - 本项目每月仅需 ~30 次调用、~19 GBs，绰绰有余

## 第二步：打包代码

在项目根目录执行：

```bash
python deploy/tencent-scf/deploy.py --dry-run
```

生成 `deploy/tencent-scf/scf_package.zip`（约 1.3 MB）。

### 生成环境变量 JSON

部署前，先用 `gen-env` 子命令从本地配置生成环境变量文件：

```bash
python deploy/tencent-scf/deploy.py gen-env
```

该命令读取 `~/.auto_check_in/config.json`（CLI 生成的用户配置），输出 `deploy/tencent-scf/scf_env.json`。后续在 SCF 控制台直接导入即可，无需手动逐条填写。

## 第三步：创建函数

1. 进入 [SCF 函数服务](https://console.cloud.tencent.com/scf/list) → **新建**
2. 选 **从头开始**

| 字段 | 值 |
|------|-----|
| 函数类型 | **事件函数** |
| 函数名称 | `CSUFT_AutoCheckIn` |
| 地域 | **广州** |
| 运行环境 | **Python 3.10**（SCF 最高版本） |

> 创建页的「高级配置」不用动，环境变量在后面配。

3. 点击 **完成**

## 第四步：上传代码

1. 点函数名 `CSUFT_AutoCheckIn` 进入详情
2. **函数代码** 标签页 → 下方 **更改代码上传方式** → 选 **本地上传 zip 包**
3. 选择 `deploy/tencent-scf/scf_package.zip`
4. 点击 **部署**（等待部署完成，约 10-20 秒）

> 每次修改代码后重新打包上传，zip 覆盖 + 点部署即可更新。

## 第五步：配置函数

进入 **函数配置** 标签页，往下翻：

### 环境变量

有两种方式配置：

**方式一：导入生成的 JSON（推荐）**

1. 在 **环境变量** 区域点击 **导入**
2. 选择上一步生成的 `scf_env.json`
3. 导入后，手动将 OpenID/密码/ServerKey 等敏感字段勾选「加密存储」

**方式二：手动逐个添加**

| 键 | 值 |
|------|------|
| `CHECKIN_PROFILES` | `USER_1,USER_2,...`（profile 列表，逗号分隔） |
| `CHECKIN_OPENID_USER_1` | 账号 1 的 OpenID（`o` 开头约 28 位） |
| `CHECKIN_USERNAME_USER_1` | 账号 1 的学号 |
| `CHECKIN_PASSWORD_USER_1` | 账号 1 的密码（选填，免密码可不设） |
| `CHECKIN_OPENID_USER_2` | 账号 2 的 OpenID |
| `CHECKIN_USERNAME_USER_2` | 账号 2 的学号 |
| ... | ...（按实际账号数扩展） |
| `SERVERCHAN_KEY` | Server酱 SendKey（选填，建议加密） |

> `PASSWORD` 变量仅在 `PASSWORD` 模式使用；如果使用 `login-openid` 登录（推荐），`OPENID` + `USERNAME` 足够，无需密码。
>
> 不设 `CHECKIN_PROFILES` 时自动回退单用户模式，读取 bare 变量 `CHECKIN_OPENID` / `CHECKIN_USERNAME` / `CHECKIN_PASSWORD`。

### 基础设置
| 字段 | 值 |
|------|-----|
| 启动类/方法 | `handler.main_handler` |
| 执行超时时间 | **30 秒**（默认 3 秒不够） |
| 内存 | **64 MB**（绰绰有余） |

点击 **保存**。

## 第六步：配置定时触发器

1. **触发管理** 标签页 → **创建触发器**
2. SCF 使用 **7 字段 Cron** 格式：`秒 分 时 日 月 周 年`

| 字段 | 值 |
|------|-----|
| 触发方式 | 定时触发 |
| 触发周期 | 自定义 Cron 表达式 |
| Cron 表达式 | `0 5 21 * * ? *` |
| 名称 | `daily-checkin` |

> Cron 含义：每天 21:05:00 触发。`?` 表示不指定星期几。
> SCF 控制台默认使用北京时间，无需时区转换。

3. 点击 **保存**

## 第七步：测试验证

1. 回到 **函数代码** 标签页
2. 点下方 **测试** 按钮
3. 弹窗中 **测试事件模板** 选 **Hello World 事件**（或空 `{}`），点 **运行**
4. 等待 5-15 秒，看下方 **日志** 输出：

```
[信息] OpenID 登录成功
[信息] 打卡任务: 晚点名 (ID: b49f...)
[信息] 打卡提交成功
[信息] 确认打卡状态: 正常
```

5. 正常的话手机会收到 Server酱 微信推送通知

### 测试结果说明

| 状态 | 含义 | 处理 |
|------|------|------|
| `ok` | 打卡成功 | ✅ 正常 |
| `duplicate` | 今日已打卡 | ✅ 正常 |
| `expired` | OpenID 过期 | 重新抓包 |
| `nowindow` | 不在打卡窗口 | 等到 21:00-22:30 再测 |
| `error` | 其他错误 | 看日志详情 |

## 后续维护

- **查看日志**：函数代码页 → 日志标签
- **更新代码**：`--dry-run` 重新打包 → 本地上传 zip 覆盖 → 测试验证
- **修改环境变量**：函数配置页直接改，无需重新部署
- **停用打卡**：触发管理 → 禁用触发器，下次不会自动触发

## 添加新用户（无需重新部署）

SCF 函数已支持根据环境变量自动适配新用户，添加步骤如下：

1. **本地配置**：运行 `python scripts/cli.py login-openid --profile USER_N` 完成新账号登录
2. **生成环境变量**：再次运行 `python deploy/tencent-scf/deploy.py gen-env`，更新后的 `scf_env.json` 会包含新账号
3. **导入更新**：SCF 控制台 → 函数配置 → 环境变量 → 导入 `scf_env.json`（覆盖现有变量）
4. **测试**：函数代码页 → 测试按钮验证

> 不需要重新打包或重新部署函数。环境变量覆盖后，下次定时触发自动生效。

如果在 SCF 控制台手动添加变量：

| 新增变量 | 示例值 |
|---------|--------|
| `CHECKIN_OPENID_USER_N` | 新用户的 OpenID |
| `CHECKIN_USERNAME_USER_N` | 新用户的学号 |
| 更新 `CHECKIN_PROFILES` | 追加 `USER_N`，如 `USER_1,USER_2,USER_3,USER_4` |

## 常见问题

### 函数执行超时
执行超时时间改 30 秒。如果学校 API 响应慢可改 60 秒。

### 打卡失败 "签名错误"
检查环境变量是否填写正确，特别是 OpenID。OpenID 过期需重新抓包。

### 没有收到通知
- 检查 `SERVERCHAN_KEY` 是否配置
- Server酱 免费版每日限 5 条
- 查看函数日志确认通知是否成功发送

### 如何更新代码
```bash
python deploy/tencent-scf/deploy.py --dry-run
```
SCF 控制台 → 函数代码 → 本地上传 zip 覆盖。

