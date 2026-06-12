# Reqable 抓包获取 OpenID

> 适用环境：安卓手机（热点 / WiFi / 流量均可），不需要电脑
> 难度：⭐⭐（简单）
>
> 注：Reqable 原名 HTTPCanary，现已更名。旧版仍叫 HTTPCanary，用法完全相同。

---

## 1. 概述

**Reqable**（原 HTTPCanary）是一款 Android 抓包工具，利用手机本地 VPN 拦截 HTTP/HTTPS 流量。

**相比 Fiddler 的优势：**
- **不需要电脑** — 手机单机完成
- **不设代理** — VPN 模式，无需改 WiFi 设置
- **热点可用** — 手机自己开热点时也能抓包（Fiddler/mitmproxy 做不到）

**抓包目标：** 打卡小程序登录时会请求 `getOpenidByJsCode` 接口，响应体中的 `data` 字段就是 OpenID。

---

## 2. 下载安装

1. 手机打开浏览器访问 https://httpcanary.com（官网仍沿用旧名）
2. 下载 APK 并安装
3. 或者从 Google Play 搜索 "HTTPCanary" 安装

---

## 3. 安装 CA 证书

Reqable 需要 CA 证书才能解密 HTTPS 流量。

1. 打开 Reqable
2. 点击左上角菜单 → **设置**
3. 找到 **SSL 证书设置** → **安装 CA 证书到系统**
4. 根据提示操作（Android 7+ 会提示去系统设置安装）
   - Android 7-10：通常可直接安装
   - Android 11+：可能需要 ADB 命令推送（Reqable 内点"移动证书"会给出命令）
5. 证书安装成功后返回 Reqable

> ⚠️ 部分高版本 Android 需要 root 才能安装到系统信任区。如果 Reqable 的内置方案不行，可以试试在设置中启用 **"Reqable 根证书"** 的兼容模式。

---

## 4. 开始抓包

1. 回到 Reqable 主界面
2. 点击底部 **开始捕获** 按钮（红色圆点）
3. Reqable 会弹出 VPN 连接请求 — 点 **确定**
4. 状态栏出现钥匙图标表示抓包已启动

---

## 5. 打开打卡小程序

1. 不要关闭 Reqable，直接按 Home 键回到桌面
2. 打开微信
3. 进入「中南林业科技大学平安打卡」小程序
4. 正常使用小程序，让它完成登录流程（加载首页即可）
5. 切回 Reqable

---

## 6. 查找 OpenID

1. 点击底部 **停止捕获** 按钮
2. 在列表顶部搜索栏输入：`getOpenidByJsCode`
3. 点开搜索结果中唯一的那条请求
4. 切换到 **响应体**（Response Body）标签
5. 找到 `"data": "o..."` — 那个 `o` 开头的字符串就是 OpenID

---

## 7. 使用 OpenID

```powershell
python scripts/cli.py setup
```

按提示输入 OpenID + 学号 + 密码，自动完成登录和配置。

或者手动：
```powershell
python scripts/cli.py login-openid <OpenID> <学号>
```

---

## 8. 常见问题

**Q: Reqable 闪退？**
A: 部分国产 ROM 对 VPN 权限有特殊限制。去系统设置中给 Reqable 所有权限（自启、后台运行、省电无限制）。

**Q: 找不到 `getOpenidByJsCode`？**
A: 搜索栏空着先看一眼请求列表 — 小程序请求很多，缩小时间范围。点右上角筛选图标，只显示 `simp.csuft.edu.cn` 的请求。

**Q: 我的 OpenID 看起来不一样？**
A: 正常 OpenID 以 `o` 开头，约 28 位。如果看到 `data: null` 或 `data: ""`，说明小程序还没完成登录，多刷新几下页面再抓。

**Q: 可以不装 CA 证书吗？**
A: 不装证书只能看到 HTTPS 的 CONNECT 请求，看不到具体内容。OpenID 在加密内容中，必须装证书。

**Q: 下载的还是 HTTPCanary 不是 Reqable？**
A: 正常。改名后应用商店和官网推送更新需要时间，旧名 APK 安装后打开就是 Reqable。
