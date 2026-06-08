# Fiddler 抓包获取 OpenID

> 适用环境：Windows PC + 真实安卓手机（同一 WiFi）

---

## 1. 概述

**Fiddler Classic** 是 Telerik 出品的免费 HTTP/HTTPS 抓包调试工具，可以拦截、查看和修改电脑和手机上的网络请求。

**为什么要抓 OpenID？**

本项目的目标小程序「平安打卡」使用**飞源统一认证 + 微信 OpenID** 登录流程。逆向分析表明：

- 小程序**从不使用**密码+验证码登录（`signIn` 函数虽存在但**未被任何页面调用**，是死代码）
- 所有登录走 `wx.login()` → `getOpenidByJsCode` → `signInOpenId` 链路
- OpenID 是调用 CLI 所有命令的**前置条件**

**登录流程（源码层面）：**

```
wx.login() → 临时 code
    → GET /api/flySource-base/openApi/getOpenidByJsCode?jsCode=xxx
        → 返回 openid
    → POST /api/flySource-auth/oauth/token (grant_type=wxapp, openid=xxx)
        → 返回 access_token
```

抓包的目标就是捕获**第一次 HTTP 请求的响应体**（内含 OpenID），或者**第二次请求的请求体**。

---

## 2. 下载和安装 Fiddler Classic

1. 访问 https://www.telerik.com/download/fiddler
2. 点击 **Free Download** 下载 Fiddler Classic（不是 Fiddler Everywhere）
3. 运行安装程序，一路 **Next → I Agree → Install → Finish**
4. 安装后自动启动 Fiddler Classic
5. （可选）汉化界面：
   - 下载汉化补丁（`FiddlerTexts.txt` + `FdToChinese.dll`）：https://github.com/pumpkin-nbc/FiddlerSinicization
   - 将 `FiddlerTexts.txt` 复制到 Fiddler 安装根目录（如 `C:\Program Files (x86)\Fiddler\`）
   - 将 `FdToChinese.dll` 复制到 `Scripts\` 子目录
   - 重启 Fiddler，菜单即显示中文；想切回英文则删除这两个文件

> Fiddler Classic 是免费软件，无需注册或许可证。

---

## 3. 配置 Fiddler 解密 HTTPS

小程序的所有 API 走 HTTPS，必须配置 Fiddler 解密才能看到明文：

1. 打开 Fiddler Classic
2. 菜单栏 **Tools → Options → HTTPS** 选项卡
3. 勾选：
   - **Capture HTTPS CONNECTs**
   - **Decrypt HTTPS traffic**
4. 下拉选择 **from all processes**
5. 弹出证书安全警告，点击 **Yes**（Windows）→ 再次点击 **Yes**（确认安装根证书）
6. 切到 **Connections** 选项卡
7. 勾选 **Allow remote computers to connect**
8. 记下端口号（默认 **8888**）
9. 点击 **OK** 保存
10. **重启 Fiddler**

---

## 4. 设置手机代理

### 确认同网段

确保电脑和手机连接**同一个 WiFi**。

### 查看电脑 IP

在 Fiddler 右上角可以看 `Online` 指示器的 IP，或者在命令行执行：

```powershell
ipconfig
```

找到当前网络的 IPv4 地址（如 `192.168.1.100`）。

### 设置手机 WiFi 代理

**Android：**
1. 打开 **设置 → WLAN / Wi-Fi**
2. 长按当前连接的 WiFi → **修改网络**
3. 展开 **高级选项**
4. 代理设为 **手动**
5. 填入：
   - **主机名**：电脑 IP（如 `192.168.1.100`）
   - **端口**：`8888`
6. 点击 **保存**

**iOS：**
1. **设置 → 无线局域网**
2. 点击当前 WiFi 右侧的 **(i)**
3. 向下滚动找到 **HTTP 代理 → 配置代理**
4. 选 **手动**
5. 填入相同的 IP 和端口
6. 点击 **存储**

### 安装 Fiddler 根证书

手机浏览器访问：

```
http://<电脑IP>:8888
```

页面底部点击 **FiddlerRoot certificate** 链接，下载并安装证书。

**Android：**
- 下载后到 **设置 → 安全 → 加密与凭据 → 从存储设备安装**
- 选择下载的 `FiddlerRoot.cer` 文件

**iOS：**
- 下载后会自动跳转描述文件安装界面，点击 **安装**
- 再到 **设置 → 通用 → 关于本机 → 证书信任设置**，找到 **Fiddler Root Certificate**，开启开关

> **Android 7+ 注意事项**：系统只信任系统级 CA，用户安装的证书对非调试应用（如微信）无效。可选方案：
> - 使用已 root 的手机，用 Magisk 模块将证书移动到系统级
> - 使用安卓 7 以下设备或模拟器
> - 部分定制 ROM（如 MIUI、EMUI）可能不需要额外操作，实测为准

### 验证连接

手机浏览器访问任意 HTTPS 网站（如 `https://www.baidu.com`），如果 Fiddler 中出现请求记录且能解密，说明配置成功。

---

## 5. 开始抓包

1. 在手机上**关闭所有后台应用**，减少干扰请求
2. 在 Fiddler 中按 **Ctrl + X** 清空当前会话列表
3. 在手机上打开 **微信**
4. 进入 **发现 → 小程序**，搜索或从聊天记录中打开 **平安打卡**
5. 小程序会**自动触发登录流程**（调用 `wx.login()` → 获取 OpenID → 登录/绑定）
6. 观察 Fiddler 中出现的请求

### 过滤请求

在 Fiddler 左下角的过滤器输入框中输入：

```
simp.csuft.edu.cn
```

或点击 **Filters** 选项卡 → 勾选 **Use Filters** → **Hosts** → **Show only the following Hosts** → 输入 `simp.csuft.edu.cn` → **Actions → Run Filterset now**。

---

## 6. 定位 OpenID

有两种方法，推荐使用方法 A。

### 方法 A：从 getOpenidByJsCode 的响应中获取（推荐）

登录流程中，小程序先调用 `wx.login()` 拿到临时 code，然后用这个 code 向服务端换取真正的 OpenID。

在 Fiddler 会话列表中查找：

```
GET /api/flySource-base/openApi/getOpenidByJsCode?jsCode=xxxxxxxxxx
```

**点击这条请求 → 右侧 Inspectors 选项卡 → TextView（或 JSON）查看响应体。**

响应结构示例：

```json
{
    "success": true,
    "code": 200,
    "msg": "成功",
    "data": "oEXAMPLE_abc123def456"
}
```

`data` 字段的值（如 `oEXAMPLE_abc123def456`）就是 **OpenID**。

> **说明**：`getOpenidByJsCode` 只有在小程序**首次加载或 token 过期**时才会调用。如果抓不到，可以在微信中删除小程序（长按图标 → 删除），重新进入触发完整的登录流程。

### 方法 B：从 oauth/token 请求参数中获取

`getOpenidByJsCode` 拿到 OpenID 后，小程序接着调用 `signInOpenId` 进行登录/绑定。

查找：

```
POST /api/flySource-auth/oauth/token
```

**点击这条请求 → Inspectors 选项卡 → WebForms（或 TextView），查看请求体。**

请求体内容（格式为 `application/x-www-form-urlencoded`）：

```
grant_type=wxapp
&tenantId=000000
&username=
&password=
&openid=oEXAMPLE_abc123def456
&bindState=0
&scope=all
```

`openid` 参数的值就是你要找的 OpenID。

如果小程序还未绑定学号，这个请求会返回 `invalid_grant` 错误，**但 OpenID 已经在请求体中暴露了**，直接复制即可。

---

## 7. 保存 OpenID 到本地配置

拿到 OpenID 后，用项目 CLI 工具绑定账号：

```powershell
cd D:\A_Learn\Vibe coding\Project\auto_check_in
.\.venv\Scripts\Activate.ps1
python scripts/cli.py login-openid <你的OpenID> <学号>
```

命令行会提示输入密码（交互式输入，安全不回显）：

```
密码:
```

输入密码后，CLI 会调用 `signInOpenId` 绑定并登录，将 `access_token`、`tenant_id`、`username`、`openid` 保存到 `~/.auto_check_in/config.json`。

**完整示例：**

```powershell
PS D:\A_Learn\Vibe coding\Project\auto_check_in> .\.venv\Scripts\Activate.ps1
PS D:\A_Learn\Vibe coding\Project\auto_check_in> python scripts/cli.py login-openid oEXAMPLE_abc123def456 2024XXXXXX
密码:
OpenID 登录成功，token: eyJhbGciOiJSUzI1NiIsI...
```

> 也可以一次性提供密码（不安全，会留在 PowerShell 历史记录中）：
> ```
> python scripts/cli.py login-openid oEXAMPLE_abc123def456 2024XXXXXX mypassword
> ```

### 命令参数说明

| 参数 | 说明 |
|------|------|
| `openid` | （必填）第 6 步抓到的 OpenID |
| `username` | （可选）学号，留空则不绑定 |
| `password` | （可选）密码，留空则交互式输入 |
| `--tenant` | 租户 ID，默认 `000000`（不用改） |
| `--bind` | 绑定状态，`1`=绑定（默认），`0`=仅登录不绑定 |

---

## 8. 验证登录成功

执行任务列表命令检验 token 是否有效：

```powershell
python scripts/cli.py tasks
```

成功输出示例：

```
  [1] 晚点名打卡  21:00-23:00
  [2] 晨检打卡    07:00-09:00

共 2 条
```

说明 OpenID 绑定成功、token 有效，可以正常使用所有 CLI 命令了。

---

## 9. 常见问题

### Q: 手机上安装证书后仍然无法解密 HTTPS

**原因**：Android 7+ 默认不信任用户安装的 CA 证书，微信作为非调试应用不会使用用户证书。

**解决**：
- 使用已 root 手机，用 Magisk 模块 `Move Certificates` 将 Fiddler 证书移到系统级
- 使用安卓 6 或更低版本的设备/模拟器
- 使用 VirtualXposed 等工具在虚拟环境中运行微信

### Q: Fiddler 无法远程连接

**原因**：Windows 防火墙阻止了 8888 端口。

**解决**：
1. 临时关闭防火墙测试是否是此原因：
   ```powershell
   # 管理员 PowerShell
   New-NetFirewallRule -DisplayName "Fiddler" -Direction Inbound -Protocol TCP -LocalPort 8888 -Action Allow
   ```
2. 或完全退出防火墙/杀毒软件测试

### Q: 抓不到 simp.csuft.edu.cn 的请求

**原因分析**：
- 小程序已登录且 token 未过期：`getOpenidByJsCode` 不会再次触发
- 微信代理设置未生效
- 小程序使用了强制 HTTPS 证书校验（certificate pinning）

**解决**：
1. 在微信中删除小程序（首页下拉 → 长按小程序图标 → 删除），重新进入
2. 确认手机代理 IP 和端口正确
3. 在 Fiddler 中尝试清空缓存：**Tools → Clear → All sessions**
4. 如果小程序做了证书锁定，需使用 Frida + objection 绕过 SSL Pinning（超出本文范围，参见 Xposed 或 Frida 相关教程）

### Q: 电脑和手机不在同一网络

**方案 A**：电脑开启**移动热点**，手机连接热点。

**方案 B**：使用 Fiddler 的 **Online Proxy** 功能（需登录 Telerik 账号）。

### Q: OpenID 保存后还能用多久？

OpenID 本身不失效，只要微信账号不解绑。保存到配置文件中后可以重复使用。只有 `access_token` 会过期（约 30 天），但 CLI 工具会自动刷新。

---

## 下一步

OpenID 和 token 就绪后，可以：

```powershell
# 查看任务列表
python scripts/cli.py tasks

# 查看任务详情（含宿舍坐标和精度上限）
python scripts/cli.py detail <task_id>

# 打卡签到（模拟 GPS 偏移）
python scripts/cli.py checkin <task_id>

# 查询当天打卡状态
python scripts/cli.py record <task_id>
```

详情参见 `docs/plan.md`。
