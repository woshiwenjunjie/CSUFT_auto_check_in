# CSUFT 自动晚点名 — 文档目录

> 中南林业科技大学自动晚点名打卡工具
> v0.13.0 — 共享模块、SCF 精简、通知增强

## 快速入口

| 文档 | 适合读者 |
|------|---------|
| [快速开始](getting-started/快速开始.md) | 新用户首次配置 |
| [配置向导](getting-started/配置向导.md) | 首次 setup 向导 |
| [常见问题](getting-started/常见问题.md) | 遇到问题时查阅 |

## 操作指南

| 文档 | 说明 |
|------|------|
| [CLI 命令详解](guides/user/CLI教程.md) | 全部子命令用法 + 多账号管理 |
| [添加新账号教程](guides/user/添加新账号教程.md) | 从 OpenID 抓取到一键打卡，完整的新账号接入流程 |
| [模拟器自动抓取 OpenID](guides/user/模拟器自动抓取OpenID.md) | ✅ 推荐方案：一键自动捕获 |
| [Fiddler 抓包方案](guides/user/fiddler-抓包获取OpenID.md) | 传统 PC + 手机方案 |
| [Reqable 手机抓包](guides/user/Reqable-抓包获取OpenID.md) | VPN 模式，无需电脑 |
| [完整操作指南](guides/user/完整操作指南.md) | 从零开始的完整图文教程 |
| [Server酱配置](guides/user/Server酱配置教程.md) | 微信通知设置 |
| [GitHub Actions 部署](guides/user/GitHub-Actions自动打卡教程.md) | 自动打卡方案一 |
| [腾讯云 SCF 部署](guides/user/腾讯云SCF部署指南.md) | 自动打卡方案二 |

## 技术参考

| 文档 | 说明 |
|------|------|
| [签名算法详解](reference/签名算法详解.md) | FlySource-sign 完整推导 |
| [认证流程与抓包分析](reference/认证流程与抓包分析.md) | OAuth 全链路 + 三种抓包方案 |
| [小程序逆向分析](reference/小程序逆向分析.md) | wxapkg 源码级分析 |
| [wxapkg 提取教程](reference/wxapkg提取教程.md) | 从模拟器提取小程序包体 |
| [API 端点参考](reference/API端点参考.md) | 8 个学校 API 接口文档 |
| [CLI 命令速查表](reference/CLI命令速查表.md) | 全部子命令一览 |
| [关键词与概念速查](reference/关键词与概念速查.md) | 项目术语表 |

## 开发文档

| 文档 | 说明 |
|------|------|
| [项目架构](guides/dev/项目架构与开发指南.md) | 整体架构与扩展指南 |
| [数据库设计](development/数据库设计.md) | 阶段三数据库规划 |
| [后端 API 设计](development/后端API设计.md) | 阶段三 REST API 规范 |
| [阶段三路线图](development/阶段三路线图.md) | 优先级与里程碑 |
| [CHANGELOG](CHANGELOG.md) | 版本更新记录 |

## 项目记忆

- [reviews/](../../reviews/) — 代码审查记录
