# 模拟器自动抓取 OpenID

> 一键脚本 + MuMu 模拟器，自动捕获微信小程序 OpenID

## 安全声明

本方案使用 mitmproxy 对模拟器的 HTTP/HTTPS 流量做中间人拦截（MITM），提取微信小程序向校园 API 发起的 `getOpenidByJsCode` 请求中的 OpenID。

**关于微信账号风险：**

| 风险点 | 说明 | 防护措施 |
|--------|------|---------|
| MITM 拦截 | 脚本解析的是小程序→学校 API 的流量，不修改任何请求/响应 | 纯被动监听，不改包 |
| 微信风控 | mitmproxy 代理可能触发微信的安全检测 | 在**模拟器**中操作，不在真实手机上运行 |
| 密码泄露 | 抓包过程不涉及微信登录密码 | 无需任何微信凭据 |
| 证书锁定 | 微信核心通信自带 SSL Pinning | 脚本只监听小程序→学校的明文 API，不触碰微信内部通信 |

**结论**：在模拟器中操作比在真实手机上更安全。模拟器被风控标记时只需重置镜像，微信账号不受影响。v0.11.0 已通过此方式完成 3 个账号的 OpenID 捕获，无一触发风控。

---

## 方案对比

| 方案 | 难度 | 安全 | 适用场景 |
|------|------|------|---------|
| ✅ **模拟器自动脚本**（本文） | ⭐ | 高 | 多账号批量捕获、无 root 真实手机 |
| Fiddler（真实手机 + 电脑同 WiFi） | ⭐⭐⭐ | 中 | 有 root 手机 |
| Reqable（手机 VPN 抓包） | ⭐⭐ | 中 | 手机开热点时、无电脑时 |

---

## 前置条件

- 一台运行中的 Android 模拟器（推荐 **MuMu 12**，自带 root）
- ADB 可连接（MuMu 自带 ADB，路径通常 `MuMu12/shell/adb.exe`）
- Python 3.10+
- mitmproxy 已安装

```powershell
pip install mitmproxy
```

---

## 使用步骤

### 第 1 步：启动模拟器

打开 MuMu 12，确认 ADB 可连接：

```powershell
adb devices
# 输出: 127.0.0.1:7555  device
```

如果模拟器刚安装，需要先打开微信登录一次（首次手动扫二维码）。登录成功后，可以在模拟器中切换不同微信账号。

### 第 2 步：启动自动捕获

```powershell
python scripts/tools/capture_openid_emulator.py --port 8899
```

脚本自动完成 4 个阶段：

```
1. 环境检查
   ✓ ADB 可连接
   ✓ mitmproxy 已安装
   ✓ CA 证书存在
   ✓ 插件脚本存在

2. 安装 CA 证书
   → adb root (模拟器有 root 权限)
   → 创建 /data/local/tmp/cacerts/
   → 生成 mitmproxy CA 哈希文件名
   → bind mount 到 /system/etc/security/cacerts/
   （MuMu 12 的 /system 只读，无法 remount，使用 mount -o bind）

3. 设置代理
   → adb shell settings put global http_proxy 10.202.2.91:8899

4. 启动 mitmproxy
   → 加载 capture_addon.py
   → 监听 8899 端口
```

### 第 3 步：打开微信小程序

脚本输出 **"已打开微信小程序"** 后，确认模拟器中：

1. 微信已打开
2. 小程序"平安打卡"已启动
3. 小程序执行 `wx.login()` → 调用 `getOpenidByJsCode` API

捕获到 OpenID 后脚本自动退出：

```
========================================================
  OpenID 已捕获!
  OpenID: ocrJ***xxxx
  已保存到: C:\Users\xxx\.auto_check_in\config.json
========================================================
```

### 第 4 步：配置 CLI 并登录

```powershell
# 查看捕获的 OpenID
python scripts/cli.py config

# 免密码登录（推荐，绑定后无需重复密码）
python scripts/cli.py login-openid --bind 0

# 查看任务
python scripts/cli.py tasks
```

---

## 多账号捕获流程

需要捕获第二个/第三个微信账号的 OpenID：

1. 在 MuMu 微信中 → **我 → 设置 → 退出登录**
2. 登录另一个微信账号
3. **重新运行**脚本（模拟器重启后证书 bind mount 丢失，脚本会自动重新安装）

```powershell
python scripts/tools/capture_openid_emulator.py --port 8899
```

每个新 OpenID 捕获后，手动创建对应 profile：

```powershell
# 查看当前配置
python scripts/cli.py config profile list

# 创建新 profile（手动编辑或通过 setup 交互式配置）
# 切换 profile
python scripts/cli.py config profile USER_2

# 登录绑定
python scripts/cli.py login-openid --bind 0 --profile USER_2
```

---

## 脚本工作原理详解

### 证书安装策略

Android 7+ 默认不信任用户级 CA 证书，需要将 mitmproxy CA 装到系统区。MuMu 12 的 `/system` 分区是只读的：

```powershell
# ❌ 传统 remount 失败
adb shell mount -o rw,remount /system   # 报错: Permission denied

# ✅ bind mount 方案
adb shell mkdir -p /data/local/tmp/cacerts
adb push mitmproxy-ca-cert.cer /data/local/tmp/cacerts/<hash>.0
adb shell mount -o bind /data/local/tmp/cacerts /system/etc/security/cacerts
```

bind mount 在模拟器重启后失效，需重新执行脚本。

### OpenID 提取

`capture_addon.py` 监听所有经过 mitmproxy 的响应，匹配 `getOpenidByJsCode` 路径：

```python
def response(flow: HTTPFlow) -> None:
    if "getOpenidByJsCode" in flow.request.pretty_url:
        data = flow.response.text
        openid = extract_openid(data)
        if openid:
            save_to_config(openid)
```

### 代理清理

脚本退出时（或 `Ctrl+C`）自动清理代理设置：

```python
adb shell settings delete global http_proxy
```

如代理未清理导致模拟器断网，手动执行：

```powershell
python scripts/tools/capture_openid_emulator.py --cleanup
```

---

## 常见问题

### 脚本找不到 adb / mitmdump

脚本自动搜索常见安装路径，包括系统 PATH、Python Scripts 目录、MuMu 安装目录。如搜索失败，手动指定：

```powershell
# 环境变量
$env:ADB_PATH = "D:\Program Files\adb\adb.exe"

# 或添加到 PATH
$env:Path += ";D:\Program Files\adb"
```

### 微信小程序打开后没有流量

检查代理设置：

```powershell
adb shell settings get global http_proxy
# 应输出: 10.202.2.91:8899
```

确认 mitmproxy 监听端口未被占用。

### OpenID 捕获为空（假阳性）

脚本可能输出 `OpenID 已捕获` 但打开配置文件发现 OpenID 为空。这是因为小程序加载阶段发起的其他请求被误匹配。重启模拟器后重试。

### 模拟器重启后脚本失败

每次模拟器重启后需要重新执行整个脚本（bind mount 丢失、代理设置重置）：

```powershell
python scripts/tools/capture_openid_emulator.py --port 8899
```

### 不想每次重启都重装证书

将脚本封装为开机自启动，或保持模拟器休眠状态不关机。

---

## 与其他抓包方案对比

| 对比项 | 模拟器自动脚本 | Fiddler | Reqable |
|--------|--------------|---------|---------|
| 是否需要电脑 | ✅ 需要 | ✅ 需要 | ❌ 不需要 |
| 是否需要 root | ❌ 模拟器自带 | ❌ 可无 root | ❌ 不需要 |
| 是否需要同 WiFi | ❌ 不需要 | ✅ 需要 | ❌ 不需要 |
| 热点环境可用 | ✅ 是 | ❌ 否 | ✅ 是 |
| 手机开热点时 | ✅ 模拟器不受影响 | ❌ 无法使用 | ✅ VPN 模式 |
| 多账号切换 | ✅ 模拟器切换微信 | ⚠️ 需多次绑定 | ⚠️ 需多次绑定 |
| 微信风控风险 | ✅ 低（模拟器隔离） | ⚠️ 中 | ⚠️ 中 |
| 操作步骤 | 1 条命令 | 10+ 步 | 5 步 |
| 自动化程度 | 全自动 | 手动 | 手动 |

---

## 参考

- 脚本源码：`scripts/tools/capture_openid_emulator.py`
- mitmproxy addon：`scripts/capture_addon.py`
- CLI 命令：`scripts/cli_commands/capture.py`
