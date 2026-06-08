# 002 — 获取 wxapkg 文件

日期：2026-06-07

## 背景
项目进入逆向阶段，需要从微信小程序提取 `.wxapkg` 包体以还原签名算法和接口调用链。

## 使用环境
- 模拟器：MuMu 12（安卓 12），实际版本路径 `nx_device\12.0`
- 用户此前以为用的是 MuMu 5.011，实际是 MuMu 12
- ADB 工具位于 `nx_main\adb.exe`

## 关键发现

### 1. Root 权限
- MuMu 12 设置中有「开启手机 Root 权限」开关（在设置中心 → 其他）
- 如果找不到 root 选项，`adb root` 可用
- 执行 `adb root` 后 shell 提示符从 `$` 变为 `#`，显示 `adbd is already running as root`
- `su` 命令不可用（`not found`），但 `adb root` 方式已足够

### 2. 目录结构
- 微信缓存路径：`/data/data/com.tencent.mm/MicroMsg/`
- `.wxapkg` 文件位于 `appbrand/pkg/` 下，分 3 个子目录：
  - `general/` — 通用包体（包含目标小程序）
  - `firstParty/` — 官方小程序
  - `commLib/` — 公共库（37MB 大文件）
- 目标文件在 `general/` 中，共 6 个 `.wxapkg`，最大 6.4MB

### 3. 文件命名
- 文件名格式：`_{数字}_{数字}.wxapkg`（如 `_1233860900_344.wxapkg`）
- 非 `wx_` 前缀格式，需逐个反编译确认

## 拉取方式
使用 `adb pull` 拉取整个 `general/` 目录到项目 `wxapkgs/` 下。

## 后续步骤
1. 用 wxapp-unpacker 反编译每个 `.wxapkg` 文件
2. 找到学校小程序的包，分析源码还原签名算法
