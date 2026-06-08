# 提取微信小程序 .wxapkg 文件

> 推荐方案：使用安卓模拟器（PC 上操作）

---

## 原理
在 PC 上运行安卓模拟器，开启 Root 权限后直接访问微信缓存目录 `/data/data/com.tencent.mm/`，提取小程序包体。

---

## 方法一：MuMu 模拟器（通用，适配 MuMu 5.0 / MuMu 12）

### 1. 确定模拟器版本

模拟器根目录下有 `MuMuPlayer-12.0` 字样的为 **MuMu 12**（安卓 12），反之为 **MuMu 5.0**（安卓 6）。两个版本的设置界面不同。

### 2. 开启 Root 权限

**方式 A：图形界面设置（推荐，优先试）**

MuMu 12：
1. 右上角 **≡ 菜单 → 设置中心**
2. 左侧 **磁盘** → 磁盘共享改为 **可写系统盘**
3. 左侧 **其他** → 开启 **「开启手机 Root 权限」**
4. 保存设置，重启模拟器

MuMu 5.0：
1. 右上角 **≡ 菜单 → 设置中心**
2. **基本设置** → 勾选 **root 权限**
3. 保存设置

> 如果找不到 root 选项，说明模拟器已默认开启 root，跳过此步。

**方式 B：ADB 命令（无 root 选项时用）**

1. 进入模拟器安装目录下的 adb 所在文件夹
2. 连接设备：
   ```bash
   .\adb.exe connect 127.0.0.1:7555
   ```
3. 进入 shell 看是否已 root：
   ```bash
   .\adb.exe shell
   ```
   - 提示符为 `#` → 已 root
   - 提示符为 `$` → 未 root，继续以下步骤
4. 退出 shell（输入 `exit`）后执行：
   ```bash
   .\adb.exe root
   ```
5. 看模拟器屏幕有没有弹出授权窗口，有则点「允许」
6. 重新进入 shell 确认已变成 `#`：
   ```bash
   .\adb.exe shell
   ```

### 3. 安装微信并进入目标小程序

1. 拖拽微信 APK 到模拟器窗口安装，或打开应用商店搜索微信
2. 登录微信
3. 从聊天记录/搜索中打开 **学校的小程序**
4. 随意点几个页面，确保小程序已完全加载（缓存落地磁盘）

### 4. 安装文件管理器

**推荐：MT 管理器**
1. 打开模拟器内置浏览器，搜索 MT 管理器下载 APK
2. 或访问 https://mt2.cn/ 下载后拖拽安装
3. 安装后打开，弹出授权窗口时勾选 **「永久记住选择」→「允许」**

**备选：RE 文件管理器**
1. 打开模拟器「应用商店」搜索 RE 文件管理器并安装
2. 打开后授予 Root 权限

### 5. 提取 .wxapkg 文件

1. 打开 MT 管理器
2. 切换到根目录 `/`，进入：
   ```
   /data/data/com.tencent.mm/MicroMsg/
   ```
3. 找到 32 位 hash 命名的文件夹（只登了一个微信就只有一个，多个则选体积最大/时间最新的）
4. 继续进入：
   ```
   appbrand/pkg/
   ```
5. 该目录下可能有多个子目录，常见的有：
   - `general/` — 通用小程序包体（**目标在此**）
   - `firstParty/` — 官方小程序
   - `commLib/` — 公共依赖库（体积很大，如 37MB）
6. 进入 `general/`，按修改时间排序，**最近修改的** `.wxapkg` 就是你的目标小程序

### 6. 复制到电脑

**方式 A：共享文件夹（推荐）**
1. MT 管理器中长按目标文件 → 复制
2. 导航到 `/mnt/shared/` 下带「MuMu」字样的文件夹，粘贴
3. 在电脑上打开对应的「MuMu共享文件夹」取出文件

**方式 B：adb pull（实测可行）**
1. 进入模拟器 adb 所在目录
2. 先确认已连接设备并已 root：
   ```bash
   .\adb.exe connect 127.0.0.1:7555
   .\adb.exe root
   ```
3. 拉取指定文件：
   ```bash
   .\adb.exe pull /data/data/com.tencent.mm/MicroMsg/{hash}/appbrand/pkg/general/xxx.wxapkg "D:\目标路径"
   ```
   或拉取整个 `general/` 目录（推荐，一次性获取所有包体）：
   ```bash
   .\adb.exe pull /data/data/com.tencent.mm/MicroMsg/{hash}/appbrand/pkg/general/ "D:\目标路径"
   ```
   `{hash}` 替换为第 3 步中看到的 32 位文件夹名称
4. 拉取成功后验证：
   ```bash
   Get-ChildItem "D:\目标路径"
   ```

**方式 C：复制到 /sdcard/ 后拖拽**
1. MT 管理器中把文件复制到 `/sdcard/`（手机存储根目录）
2. 在模拟器桌面把文件直接拖拽到电脑窗口

### 判断哪个包是正确的

| 特征 | 说明 |
|------|------|
| 体积 | 主包 **1MB ~ 5MB**，分包几百 KB |
| 时间 | 按修改时间排序，最新的就是 |
| 不确定 | 把所有 `.wxapkg` 都复制出来 |

---

## 方法二：已 root 安卓手机

1. 安装 MT 管理器
2. 导航到 `/data/data/com.tencent.mm/MicroMsg/{32位hash}/appbrand/pkg/`
3. 复制 `.wxapkg` 到 SD 卡或发送到电脑

---

## 方法三：免 root 安卓手机（adb backup，成功率较低）

1. 手机开启 USB 调试，连接电脑
2. 执行：
   ```bash
   adb backup -f wechat.ab com.tencent.mm
   ```
3. 手机上点「备份」，**不要设密码**
4. 用 `android-backup-extractor` 工具解压 `.ab` 文件
5. 在 `apps/com.tencent.mm/root/data/data/.../appbrand/pkg/` 中找到 `.wxapkg`

---

## 下一步
拿到 `.wxapkg` 文件后，放在项目根目录，运行反编译：
```bash
node node_modules\wxapp-unpacker\wuWxapkg.js <文件.wxapkg>
```
输出在 `decompiled/` 目录下。
