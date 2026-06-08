# 005 — OpenID 抓包成功与签名调试

日期：2026-06-07

## 本次成果

### OpenID 抓包
- 使用 MuMu 模拟器 + Fiddler 方案，ADB 直接配置代理 `10.202.2.91:8888`
- 系统分区只读问题通过 bind mount 解决：`mount --bind /data/local/tmp/cacerts /system/etc/security/cacerts`
- 成功抓取 `/api/flySource-base/openApi/getOpenidByJsCode` 响应，获取真实 OpenID
- `login-openid --bind 0` 登录成功（`--bind 0` 用于已绑定账号的重新登录）

### Bug 修复
- `src/core/client.py:_post()` 未转发 `extra_headers` → OpenID 登录时 `Web-Type`/`Tenant-Id` 头丢失
- Windows Python SSL 证书缺失 → 引入 `certifi` 作为 CA bundle
- httpx 检测 Windows 系统代理干扰直连 → `trust_env=False`

### 签名算法
- JS 源码验证：`md5(r + md5(n + d)) + "1." + btoa(n.toString())`
- 其中 `r = url.split("?")[0] + "?sign="`
- 即：`MD5(path + "?sign=" + MD5(timestamp + token)) + "1." + Base64(timestamp)`
- Python 实现与 JS 源码一致，但服务器仍返回"签名错误"——待通过 Fiddler 对比真实请求排查

## 关键发现

### 1. OpenID 登录  [['004-审查修复与OpenID发现']]
- 服务器拒绝 `grant_type=password`，仅接受 `grant_type=wxapp`
- OpenID 首次绑定用 `bindState=1`，已绑定后重新登录用 `bindState=0`
- 重复绑定返回"您已经绑了账号，不能重复绑定"

### 2. MuMu 模拟器系统分区
- MuMu 12 的 `/system` 为 ext4 只读镜像
- 传统 `adb remount` 和 `mount -o rw,remount` 均失败
- bind mount 方案可行：创建证书副本目录 → 挂载到系统证书路径 → 不重启即生效
- 重启后 bind mount 失效，需重新执行

### 3. Windows Python 3.14 证书问题
- Python 3.14 默认查找 `C:\Program Files\Common Files\SSL\cert.pem`（不存在）
- certifi 包提供了跨平台的 CA bundle
- httpx 的 `trust_env=True` 在 Windows 上可能读取到残留代理配置干扰直连

### 4. API 签名要求
- 所有 `/api/flySource-yxgl/*` 接口需要 `FlySource-Auth` + `FlySource-sign` 头
- 缺少签名返回 400"签名错误"，缺少 token 返回 401
- 签名由 client interceptor 统一注入，不区分 GET/POST

## 待解决
- [ ] 签名验证：通过 Fiddler 捕获真实请求对比 Python 生成签名，定位差异
- [ ] 全链路 CLI 测试：tasks → detail → checkin → record
- [ ] bind mount 持久化：重启模拟器后自动恢复

## 后续计划
1. 对比 Fiddler 真实签名 → 修复 Python 实现
2. 验证全链路打卡流程
3. 进入阶段三：FastAPI 后端 + 定时任务
