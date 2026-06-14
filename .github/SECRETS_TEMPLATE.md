# 凭据配置模板

克隆本仓库后，按需配置以下凭据。

---

## 目录

- [A. GitHub Actions 自动打卡](#a-github-actions-自动打卡)
- [B. 腾讯云 SCF 部署](#b-腾讯云-scf-部署)
- [C. 本地 CLI 配置文件](#c-本地-cli-配置文件)

---

## A. GitHub Actions 自动打卡

### 单用户（最简）

仓库 → Settings → Secrets and variables → Actions → New repository secret：

| Name | Value |
|------|-------|
| `CHECKIN_OPENID` | `o` 开头约 28 位（抓包获取） |
| `CHECKIN_USERNAME` | 你的学号 |
| `CHECKIN_PASSWORD` | 学校系统密码 |
| `CHECKIN_TASK_ID` | 打卡任务 ID（可选，不设则自动获取） |
| `SERVERCHAN_KEY` | Server酱 SendKey（可选，用于微信通知） |
| `TG_BOT_TOKEN` | Telegram Bot Token（可选） |
| `TG_CHAT_ID` | Telegram 聊天 ID（可选） |

### 多用户

额外添加带后缀的 Secrets，并在 Actions 页面的 workflow 文件中扩展 env 段：

| Name | Value |
|------|-------|
| `CHECKIN_OPENID_USER_2` | 第二个账号的 OpenID |
| `CHECKIN_USERNAME_USER_2` | 第二个账号的学号 |
| `CHECKIN_OPENID_USER_3` | 第三个账号的 OpenID |
| … | … |

然后在仓库根目录创建 Environment Variables（非 Secrets，不带加密）：

| Name | Value |
|------|-------|
| `CHECKIN_PROFILES` | `USER_1,USER_2,USER_3` |

---

## B. 腾讯云 SCF 部署

SCF 控制台 → 函数配置 → 环境变量 → 添加（敏感字段勾选「加密」）：

### 多用户模式（推荐）

```
CHECKIN_PROFILES  =  USER_1,USER_2,USER_3                 # 要打卡的账号列表
CHECKIN_OPENID_USER_1  =  o开头28位                       ← 加密
CHECKIN_USERNAME_USER_1  =  2023XXXXXX                    ← 加密
CHECKIN_PASSWORD_USER_1  =  xxxxxx                        ← 加密（免密码可不设）
CHECKIN_OPENID_USER_2  =  o开头28位                       ← 加密
CHECKIN_USERNAME_USER_2  =  2023XXXXXX                    ← 加密
# 更多账号追加 USER_3 / USER_4 ...
SERVERCHAN_KEY  =  SCT123456789ABCDEF                     ← 加密（可选）
```

### 单用户模式（不设 CHECKIN_PROFILES 时自动回退）

```
CHECKIN_OPENID    =  o开头28位                            ← 加密
CHECKIN_USERNAME  =  2023XXXXXX                           ← 加密
CHECKIN_PASSWORD  =  xxxxxx                               ← 加密
SERVERCHAN_KEY    =  SCT123456789ABCDEF                   ← 加密（可选）
CHECKIN_TASK_ID   =  任务 ID（可选，不设则自动获取）
```

### 快速生成 JSON（用本地 password.txt）

```bash
python deploy/tencent-scf/deploy.py gen-env
# 生成 deploy/tencent-scf/scf_env.json → SCF 控制台导入
```

---

## C. 本地 CLI 配置文件

路径：`~/.auto_check_in/config.json`

### 单用户

```json
{
  "tenant_id": "000000",
  "username": "2023XXXXXX",
  "openid": "oXXXXXXXX...",
  "password": "$obf:<base64 混淆密码>",
  "task_id": "b49ffb37..."
}
```

### 多用户

```json
{
  "current_profile": "USER_1",
  "profiles": {
    "USER_1": {
      "tenant_id": "000000",
      "username": "2023XXXXXX",
      "openid": "oXXXXXXXX...",
      "password": "$obf:<base64 混淆密码>",
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

> 密码通过 `login-openid --save-password` 自动写入，无需手写。
> `$obf:<base64>` 混淆防止肩窥，非加密。

### 交互式配置（推荐）

```bash
python scripts/cli.py setup                      # 首次配置
python scripts/cli.py setup --profile USER_2      # 添加第二个账号
python scripts/cli.py config profile list        # 查看所有账号
python scripts/cli.py config profile USER_2      # 切换到 USER_2
```
