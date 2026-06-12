# 审查：腾讯云 SCF 部署方案

**日期：** 2026-06-12
**审查范围：** `deploy/tencent-scf/`（共 10 文件）
**审查方式：** AI Code Reviewer (subagent)

---

## Strengths（亮点）

- **清晰的关注点分离**：`handler.py`（入口）→ `checkin.py`（编排）→ `notify.py`（通知）
- **完备的错误分类**：`run_checkin()` 区分 5 种状态（`ok`/`duplicate`/`expired`/`nowindow`/`error`），通知信息友好
- **环境变量驱动**：严格遵循 SCF 无状态原则；`.env.example` 与代码实际读取的变量完全一致
- **GPS 退避正确**：`_gen_gps` 从 0.002 起始，折半重试最多 6 次，有 1e-6 最小阈值
- **打包脚本完整**：`package.sh`（Linux）和 `deploy.py`（Windows/Python native）双路径覆盖
- **README 质量高**：手动 + 自动两种部署方式、环境变量对照表、与 GitHub Actions 对比、注意事项齐全

---

## Issues（问题）

### Critical（必须修复）

#### 1. `checkin.py:16-18` — 模块级时间变量在 import 时冻结

```python
NOW = datetime.now(BEJING_TZ)
NOW_STR = NOW.strftime("%Y-%m-%d %H:%M:%S")
DATE_STR = NOW.strftime("%Y-%m-%d")
```

这些值在模块导入时计算一次。SCF 容器可能 warm start 复用，第二次调用时使用旧时间。连续手动测试会导致日期滞后。

**影响**：日触发场景概率低，但多次「测试」点击时会出问题。

**修复**：改为函数延迟计算：

```python
def _now() -> datetime: return datetime.now(BEJING_TZ)
def _now_str() -> str: return _now().strftime("%Y-%m-%d %H:%M:%S")
def _date_str() -> str: return _now().strftime("%Y-%m-%d")
```

---

### Important（应该修复）

#### 2. `handler.py:10-13` — 无异常安全网

`run_checkin()` 内若抛出未捕获异常（网络不通、JSON 解析异常），SCF 调用直接失败，**通知不会发送**。

**修复**：`main_handler` 外层 try/except，异常时也发通知。

#### 3. `checkin.py:16` — `BEJING_TZ` 拼写错误

`BEJING` 少了一个 `i`，应为 `BEIJING_TZ`。不影响功能，但 IDE 搜索时困惑。

#### 4. `deploy.py:106` — 运行时硬编码 `Python3.14`

2026 年中 SCF 是否支持 Python 3.14 不确定。

**修复**：改为变量 + 降级默认值（`Python3.10`），README 注明可覆盖。

#### 5. `requirements.txt` — `certifi==2025.11.12` 版本过于固定

CA 证书包应允许小版本更新。

**修复**：`certifi>=2024.0.0`。

#### 6. `notify.py` — Server酱 API 无重试/降级

API 临时不可用时通知静默失败，用户不知晓。

**修复**：添加重试或 fallback print。

#### 7. `scf_bootstrap` 与标准 Python 运行时冲突

README 选择「Python 运行环境」时应删除 `scf_bootstrap`（仅 Custom Runtime 需要），反之亦然。当前配置两者并存造成用户困惑。

**修复**：二选一 — 删除 `scf_bootstrap`（推荐纯 Python 运行时），或改用 Custom Runtime 并修改 README。

---

### Minor（建议优化）

| # | 文件 | 问题 | 建议 |
|---|------|------|------|
| 8 | `checkin.py:206` | `from src.utils.crypto import md5` 写在方法内部 | 移到文件顶部 |
| 9 | `deploy.py:50-53` | `subprocess.run(check=True)` 无 try/except/net 清理 | 加异常处理 + `finally` 清理临时目录 |
| 10 | `package.sh:43` | `pip install --quiet` 隐藏错误输出 | 去掉 `--quiet` 或加 `|| exit 1` |
| 11 | `deploy.py:62` | 包大小仅 KB 单位，大包显示 >1000KB | 自动切换 KB/MB |
| 12 | `checkin.py:6` | `import time` 未使用 | 删除 |
| 13 | `README.md` | 未提及需先通过 `capture-openid` 获取 OpenID | 前置条件中补充说明 |

---

## Recommendations（改进建议）

1. **结构化日志**：`print("[INFO] ...")` 前缀方便 SCF 日志控制台过滤
2. **OpenID 过期自动通知替代方案**：考虑企业微信/钉钉 webhook 补充
3. **健康检查**：event 为空时返回 `{"status": "healthy"}`，支持 SCF 健康检查
4. **VPC 参数**：`deploy.py` 增加 `--no-vpc` 参数

---

## Assessment（结论）

**Ready to merge?** 需要修复 Critical + Important 共 7 项后合并

**Reasoning:** 代码架构扎实、与现有 `src/` 包兼容、README 文档质量高。模块级时间冻结是真正的 bug（虽日触发概率低），运行时版本和 bootstrap 冲突是高风险的配置错误。修复后即可上线部署。
