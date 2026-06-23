# CSUFT 自动晚点名打卡文档

> v0.15.0 — README 重写、根目录整理、自动化链路稳定性修复。

## 快速入口

| 文档 | 适合读者 |
| --- | --- |
| [快速开始](getting-started/快速开始.md) | 新用户首次配置 |
| [配置向导](getting-started/配置向导.md) | 首次 setup 细节 |
| [常见问题](getting-started/常见问题.md) | 排障 |

## 用户指南

| 文档 | 说明 |
| --- | --- |
| [CLI 教程](guides/user/CLI教程.md) | CLI 子命令、多账号、记录查询 |
| [添加新账号教程](guides/user/添加新账号教程.md) | 新账号接入流程 |
| [模拟器自动抓取 OpenID](guides/user/模拟器自动抓取OpenID.md) | 推荐 OpenID 捕获方案 |
| [抓包获取 OpenID 完全指南](guides/user/抓包获取OpenID完全指南.md) | 多种抓包方案对比 |
| [Reqable 抓包获取 OpenID](guides/user/Reqable-抓包获取OpenID.md) | 手机本地 VPN 抓包 |
| [Fiddler 抓包获取 OpenID](guides/user/fiddler-抓包获取OpenID.md) | PC 代理抓包 |
| [Server酱配置教程](guides/user/Server酱配置教程.md) | 微信通知 |
| [GitHub Actions 自动打卡教程](guides/user/GitHub-Actions自动打卡教程.md) | Actions 轻量托管 |
| [腾讯云 SCF 部署指南](guides/user/腾讯云SCF部署指南.md) | 推荐生产部署 |

## 技术参考

| 文档 | 说明 |
| --- | --- |
| [签名算法详解](reference/签名算法详解.md) | FlySource-sign 推导与验证 |
| [小程序逆向分析](reference/小程序逆向分析.md) | wxapkg 源码级分析 |
| [认证流程与抓包分析](reference/认证流程与抓包分析.md) | OAuth/OpenID/WebVPN |
| [wxapkg 提取教程](reference/wxapkg提取教程.md) | 从模拟器提取小程序包 |
| [API 端点参考](reference/API端点参考.md) | 学校接口说明 |

## 开发文档

| 文档 | 说明 |
| --- | --- |
| [项目架构与开发指南](guides/dev/项目架构与开发指南.md) | 模块边界和扩展方式 |
| [数据库设计](development/数据库设计.md) | 阶段三规划 |
| [后端 API 设计](development/后端API设计.md) | 阶段三 API 规划 |
| [阶段三路线图](development/阶段三路线图.md) | FastAPI 后端计划 |
| [CHANGELOG](CHANGELOG.md) | 版本记录 |

## 代码审查

- [reviews/](../reviews/)：代码审查记录。
