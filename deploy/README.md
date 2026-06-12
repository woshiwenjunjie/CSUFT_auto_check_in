# Auto Check-In 部署方案

将 CSUFT 自动晚点名打卡部署到不同平台。

| 方案 | 位置 | 说明 |
|------|------|------|
| GitHub Actions | `.github/workflows/auto-checkin.yml` | 现有方案，免费，需 PushPlus/Server酱 |
| **腾讯云 SCF** | `deploy/tencent-scf/` | 替代方案，国内节点低延迟，免费额度高 |

## 腾讯云函数（推荐替代方案）

详细指南：[tencent-scf/README.md](tencent-scf/README.md)

**优势**：
- 广州节点，API 延迟低
- 每月 100 万次免费调用
- 不依赖 GitHub 服务状态
- 环境变量加密存储
