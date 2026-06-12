"""SCF deploy 测试共用配置

将 deploy/tencent-scf/ 加入 sys.path，使测试文件能 import notify/checkin/handler。
src/ 已在项目根目录，pytest 自动在 sys.path 中。

注意：不在模块级 mock 任何函数。checkin 引入 ApiClient 是类定义引用，不触发构造。
需要 mock 的测试用例用 `@patch('checkin.xxx')` 定点拦截。
"""
import sys
from pathlib import Path

DEPLOY_DIR = Path(__file__).resolve().parents[2] / "deploy" / "tencent-scf"
if str(DEPLOY_DIR) not in sys.path:
    sys.path.insert(0, str(DEPLOY_DIR))
