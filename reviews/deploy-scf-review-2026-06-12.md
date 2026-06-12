# 部署方案审查：腾讯云 SCF 自动打卡

**日期：** 2026-06-12
**审查文件：** `deploy/tencent-scf/`（9 个文件）

---

## 结构完整性

| 文件 | 用途 | 状态 |
|------|------|------|
| `handler.py` | SCF 入口 `main_handler(event, context)` | ✅ |
| `checkin.py` | 核心流程：login → task → checkin → notify | ✅ |
| `notify.py` | Server酱 微信推送（httpx） | ✅ |
| `requirements.txt` | 最小依赖（httpx, certifi） | ✅ |
| `scf_bootstrap` | 自定义运行时引导脚本 | ✅ |
| `deploy.py` | 自动部署脚本（支持 --dry-run / --invoke） | ✅ |
| `package.sh` | Linux 打包脚本 | ✅ |
| `.env.example` | 环境变量模板 | ✅ |
| `README.md` | 完整部署指南（手动 + 自动） | ✅ |
| `deploy/README.md` | 顶部索引页 | ✅ |

## 架构评估

- **无状态设计**：所有配置从环境变量读取，没有本地文件依赖
- **错误处理**：登录失败、token 过期、重复打卡、超出窗口均有对应通知文案
- **兼容性**：复用 `src/core/client.py` + `src/utils/*.py`，与 CLI 共用核心库
- **通知**：Server酱 推送覆盖成功/失败/重复/过期/窗口外 5 种场景
- **GPS**：随机偏移重试机制与 CLI 的 checkin.py 一致（最大 5 次，1e-6 阈值）

## 风险点

1. **OpenID 过期无自愈**：SCF 无交互式 CLI，OpenID 过期后只能更新环境变量，无自动重试
2. **无定时失败重试**：单次执行失败即通知，没有指数退避重试（但 SCF 可配置重试策略）
3. **Python 版本兼容**：Python 3.14 尚未稳定，SCF 可能只支持 3.6-3.12，需降级部署

## 结论

适合部署，建议手动上传方式先行测试。
