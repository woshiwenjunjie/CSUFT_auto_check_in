# wxapkg 提取教程：从安卓模拟器获取微信小程序包体

本文档详细说明如何从安卓模拟器中提取微信小程序的 .wxapkg 包体文件，涵盖 MuMu 模拟器、雷电模拟器、蓝叠模拟器的操作差异，以及 ADB 工具的使用方法。提取的 wxapkg 文件是后续反编译分析的基础。

---

## 目录

1. [前置准备](#1-前置准备)
2. [提取步骤详细（MuMu 模拟器）](#2-提取步骤详细mumu-模拟器)
3. [多模拟器方案差异](#3-多模拟器方案差异)
4. [自动化解包](#4-自动化解包)
5. [疑难排解表](#5-疑难排解表)
6. [参考：反编译后的文件解读](#6-参考反编译后的文件解读)

---

## 1. 前置准备

### 1.1 硬件与软件要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10+ / macOS / Linux |
| 模拟器 | MuMu 12 / MuMu 5.0 / 雷电模拟器 / 蓝叠模拟器（任选其一） |
| ADB 工具 | 模拟器自带（位于安装目录下）或独立安装 |
| 微信 | 模拟器中安装的微信 APK |
| 文件管理器 | MT 管理器（推荐）或 RE 文件管理器 |
| 反编译工具 | wxappUnpacker（Node.js 项目） |

### 1.2 相关工具下载

| 工具 | 获取方式 |
|------|---------|
| MuMu 模拟器 | https://mumu.163.com/ |
| 雷电模拟器 | https://www.ldmnq.com/ |
| 蓝叠模拟器 | https://www.bluestacks.com/ |
| MT 管理器 | https://mt2.cn/ |
| wxappUnpacker | git clone https://github.com/xuedingmiaojun/wxappUnpacker.git |

### 1.3 核心概念

wxapkg 是微信小程序的包体文件格式，存放于微信应用的数据目录中。由于 Android 系统限制，普通用户无法直接访问 /data/data/com.tencent.mm/ 目录，需要 root 权限或使用模拟器。

提取路径：

```
/data/data/com.tencent.mm/MicroMsg/{32位hash文件夹}/appbrand/pkg/general/xxx.wxapkg
```

---

## 2. 提取步骤详细（MuMu 模拟器）

### 2.1 确定模拟器版本

模拟器安装目录下：
- 有 MuMuPlayer-12.0 字样为 MuMu 12（安卓 12）
- 其他为 MuMu 5.0（安卓 6）

### 2.2 开启 Root 权限

方式 A：图形界面设置（推荐）

MuMu 12：
1. 右上角 菜单 -> 设置中心
2. 左侧 磁盘 -> 磁盘共享改为 可写系统盘
3. 左侧 其他 -> 开启 手机 Root 权限
4. 保存设置，重启模拟器

MuMu 5.0：
1. 右上角 菜单 -> 设置中心
2. 基本设置 -> 勾选 root 权限
3. 保存设置

方式 B：ADB 命令（无 root 选项时）

```bash
# 1. 进入模拟器 adb 所在目录（通常在模拟器安装目录下）
cd <模拟器安装目录>

# 2. 连接模拟器 ADB
.\adb.exe connect 127.0.0.1:7555

# 3. 进入 shell 确认 root 状态
.\adb.exe shell
```

- 提示符为 # 表示已 root
- 提示符为 $ 表示未 root，执行 .\adb.exe root 授权

### 2.3 安装微信并进入目标小程序

1. 拖拽微信 APK 到模拟器窗口安装，或打开应用商店搜索微信
2. 登录微信
3. 从聊天记录或搜索中打开学校的小程序
4. 随意点几个页面，确保小程序已完全加载（缓存写入磁盘）

### 2.4 安装文件管理器

推荐 MT 管理器：
1. 打开模拟器内置浏览器，搜索 MT 管理器下载 APK
2. 或访问 https://mt2.cn/ 下载后拖拽安装
3. 安装后打开，弹出授权窗口时勾选"永久记住选择" -> "允许"

备选：RE 文件管理器（模拟器应用商店中搜索安装）

### 2.5 提取 wxapkg 文件

1. 打开 MT 管理器
2. 切换到根目录 /，进入：
   ```
   /data/data/com.tencent.mm/MicroMsg/
   ```
3. 找到 32 位 hash 命名的文件夹（只登了一个微信就只有一个，多个则选体积最大或时间最新的）
4. 继续进入：
   ```
   appbrand/pkg/
   ```
5. 该目录下可能有多个子目录：
   - general/ -- 通用小程序包体（目标在此）
   - firstParty/ -- 官方小程序
   - commLib/ -- 公共依赖库（体积很大，如 37MB）
6. 进入 general/，按修改时间排序，最近修改的 .wxapkg 就是目标小程序

### 2.6 复制到电脑

方式 A：共享文件夹（推荐）

1. MT 管理器中长按目标文件 -> 复制
2. 导航到 /mnt/shared/ 下带 MuMu 字样的文件夹，粘贴
3. 在电脑上打开对应的 MuMu 共享文件夹取出文件

方式 B：adb pull

```bash
# 先确认连接设备并已 root
.\adb.exe connect 127.0.0.1:7555
.\adb.exe root

# 拉取整个 general 目录（推荐）
.\adb.exe pull /data/data/com.tencent.mm/MicroMsg/{hash}/appbrand/pkg/general/ "D:\目标路径"

# 或拉取指定文件
.\adb.exe pull /data/data/com.tencent.mm/MicroMsg/{hash}/appbrand/pkg/general/xxx.wxapkg "D:\目标路径"
```

{hash} 替换为第 2.5 步中看到的 32 位文件夹名称。

方式 C：复制到 /sdcard/ 后拖拽

1. MT 管理器中把文件复制到 /sdcard/（手机存储根目录）
2. 在模拟器桌面把文件直接拖拽到电脑窗口

### 2.7 判断哪个包是正确的

| 特征 | 说明 |
|------|------|
| 体积 | 主包 1MB ~ 5MB，分包几百 KB |
| 时间 | 按修改时间排序，最新的就是 |
| 不确定 | 把所有 .wxapkg 都复制出来 |

---

## 3. 多模拟器方案差异

### 3.1 MuMu 12 vs MuMu 5.0

| 特性 | MuMu 12 | MuMu 5.0 |
|------|---------|----------|
| 安卓版本 | 12 | 6 |
| Root 设置 | 设置中心 -> 其他 -> Root 权限 | 设置中心 -> 基本设置 |
| ADB 端口 | 7555 | 7555 |
| 共享文件夹路径 | /mnt/shared/MuMu共享文件夹/ | 类似 |
| 证书安装 | 需 ADB 推送 | 可直接安装 |

### 3.2 雷电模拟器

| 项目 | 说明 |
|------|------|
| ADB 端口 | 5555 |
| Root 开启 | 模拟器设置 -> 其他设置 -> 开启 Root 权限 |
| 共享文件夹 | 模拟器右侧工具栏 -> 文件传输 |
| 特殊注意 | 雷电 9（安卓 9）的 root 方式与雷电 5 不同 |

连接命令：

```bash
.\adb.exe connect 127.0.0.1:5555
```

### 3.3 蓝叠模拟器

| 项目 | 说明 |
|------|------|
| ADB 端口 | 5555 |
| Root 开启 | 需要额外安装 Root 包（蓝叠默认不带 root） |
| 共享文件夹 | 通过 BlueStacks Multi-Instance Manager 的"媒体管理器" |
| 特殊注意 | 蓝叠 5 的 Pie64 实例（安卓 9）需要开启"允许 ADB Root" |

连接命令：

```bash
.\adb.exe connect 127.0.0.1:5555
```

### 3.4 ADB 端口速查

| 模拟器 | ADB 端口 | 备注 |
|-------|---------|------|
| MuMu 12 / 5.0 | 7555 | 需在设置中开启 ADB 调试 |
| 雷电模拟器 | 5555 | 默认开启 |
| 蓝叠模拟器 | 5555 | 需在设置中开启 ADB |
| 逍遥模拟器 | 21503 | 较少使用 |
| 真机（USB） | -- | 使用 adb devices 确认 |

---

## 4. 自动化解包

### 4.1 获取 wxapkg 后的反编译

wxappUnpacker 的完整解包流程：

```bash
# 安装依赖
cd wxappUnpacker
npm install

# 解包 wxapkg
node wuWxapkg.js <文件.wxapkg>

# 反编译 JS
node wuJs.js app-service.js

# 反编译模板
node wuWxml.js <页面目录>
```

### 4.2 一键反编译脚本

项目中暂无自动化解包脚本（scripts/tools/decompile_wxapkg.py 不存在），但可使用以下批处理命令：

```powershell
# PowerShell 批量解包当前目录下所有 wxapkg
Get-ChildItem "*.wxapkg" | ForEach-Object {
    node wuWxapkg.js $_.Name
}
```

### 4.3 推荐的完整工作流

```
1. MuMu 模拟器中打开微信和小程序   <- 生成 wxapkg
2. MT 管理器复制 wxapkg 到共享目录  <- 提取
3. 从共享文件夹复制到项目目录       <- 传到 PC
4. wxappUnpacker 解包             <- 反编译
5. 分析 app-service.js            <- 逆向分析
```

---

## 5. 疑难排解表

| 问题 | 原因 | 解决 |
|------|------|------|
| ADB 连接失败 | 模拟器未开启 ADB 调试 | 模拟器设置中开启 USB 调试 / ADB 调试 |
| 无法访问 /data/data/ | 未获取 root 权限 | 检查 root 是否开启，adb root 重新授权 |
| 找不到 appbrand/pkg/ 目录 | 未打开过任何小程序 | 打开目标小程序并加载几个页面后再试 |
| general/ 目录为空 | 小程序使用分包加载 | 检查 firstParty/ 或其他子目录 |
| 文件复制失败 | 权限不足或路径错误 | 使用 adb pull 替代 MT 管理器复制 |
| 模拟器卡顿 | 未开启 VT（虚拟化技术） | BIOS 中开启 Intel VT-x / AMD-V |
| MT 管理器闪退 | 未授予 root 权限 | 重新打开，在权限弹窗中点允许 |
| wxapkg 解包报错 SyntaxError | Node.js 版本过低 | 升级到 Node.js 14+ |
| 解包后 app-service.js 为空 | 分包未合并 | 同时解包主包和所有分包 |

### 5.1 Android 真机 vs 模拟器

| 维度 | 模拟器 | 真机（root） | 真机（免 root adb backup） |
|------|-------|------------|--------------------------|
| 操作难度 | 低 | 中（需 root） | 高（成功率低） |
| 成功率 | 高 | 高 | 低 |
| 环境一致 | 不同模拟器有差异 | 与实际一致 | -- |
| 推荐度 | 推荐 | 可选 | 不推荐 |

---

## 6. 参考：反编译后的文件解读

### 6.1 目录结构

```
decompiled/
+-- app-config.json          # 小程序配置文件（页面路径、窗口样式）
+-- app-service.js           # 主逻辑包（uni-app 编译产物，~310KB）
+-- page-frame.html          # 页面框架
+-- app-wxss.js              # 全局样式
+-- pages/                   # 页面文件
|   +-- index/
|   |   +-- shouye.js        # 首页逻辑
|   +-- views/
|   |   +-- stusign.js       # 打卡页面逻辑
|   +-- login/
|       +-- binding.js       # 绑定页面逻辑
+-- utils/                   # 工具模块（如果是分包解包出来的独立文件）
```

### 6.2 什么是 wxapkg

wxapkg 是微信小程序的专有包格式，本质上是多个 JS/JSON/WXML/WXSS 文件的压缩归档。微信小程序的执行流程：

```
wxapkg 文件
    |
    +-> app-config.json   -> 读取页面配置和路由
    +-> app-service.js    -> JS 引擎执行（核心业务逻辑）
    +-> page-frame.html   -> WebView 渲染框架
    +-> 各个页面.wxml/wxss -> UI 渲染
```

### 6.3 uni-app 编译产物的特征

CSUFT 平安打卡小程序使用 uni-app 框架开发，其编译产物特征：

1. 所有模块合并到一个文件：app-service.js 包含所有页面逻辑和公共模块（约 310KB）
2. Vue SFC 转为 JS：.vue 文件被编译为 createPage() 调用，data/methods/lifecycle 以对象字面量形式嵌入
3. minified 但非 obfuscated：变量名被缩短（如 n, d, r），但控制流和字符串常量清晰可读

### 6.4 下一步

获取 wxapkg 后，建议按以下顺序阅读源码：

1. 搜索字符串常量（API 路径、ClientId、ClientSecret）了解全局配置
2. 分析 HTTP 拦截器（search "FlySource-sign"）理解签名算法
3. 查找所有 authorization=false 的请求，定位公开接口
4. 分析页面入口文件，理解登录流程（search "bindState"、"jsCode"）
5. 对照本项目的 Python 实现，逐函数验证正确性
