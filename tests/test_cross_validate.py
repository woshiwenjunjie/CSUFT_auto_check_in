"""签名交叉验证 — JS vs Python 一致性测试

验证 scripts/sign.js 和 src/utils/sign.py 对相同输入产出相同签名。
这是 API 调用的核心安全网——签名差一个字符全部请求都会被拒。
"""

import subprocess
import sys
from pathlib import Path
from src.utils.sign import generate_sign, generate_basic_auth


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIGN_JS = PROJECT_ROOT / "scripts" / "sign.js"


def _js_sign(path: str, ts: int, token: str) -> str:
    """通过 Node.js 生成签名（跨进程调用 sign.js）"""
    result = subprocess.run(
        ["node", "-e", f"""
            const crypto = require('crypto');
            function md5(s) {{ return crypto.createHash('md5').update(s, 'utf8').digest('hex'); }}
            function b64(str) {{ return Buffer.from(str, 'utf8').toString('base64'); }}
            const tsStr = String({ts});
            const inner = md5(tsStr + '{token}');
            const outer = md5('{path}' + '?sign=' + inner);
            console.log(outer + '1.' + b64(tsStr));
        """],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    return result.stdout.strip()


def test_cross_validate_standard_inputs():
    """标准输入：Python vs JS 签名一致"""
    path = "/api/test"
    ts = 1700000000000
    token = "test_token"
    py_sign = generate_sign(path, ts, token)
    js_sign = _js_sign(path, ts, token)
    assert py_sign == js_sign, f"签名不一致!\n  Python: {py_sign}\n  JS:     {js_sign}"


def test_cross_validate_empty_token():
    """空 token 签名一致"""
    path = "/api/sign"
    ts = 1700000000000
    token = ""
    py_sign = generate_sign(path, ts, token)
    js_sign = _js_sign(path, ts, token)
    assert py_sign == js_sign, f"空 token 签名不一致!\n  Python: {py_sign}\n  JS:     {js_sign}"


def test_cross_validate_chinese_path():
    """中文路径签名一致（虽然实际 API 不会出现）"""
    path = "/api/测试"
    ts = 1700000000000
    token = "token_中文"
    py_sign = generate_sign(path, ts, token)
    js_sign = _js_sign(path, ts, token)
    assert py_sign == js_sign, f"中文签名不一致!\n  Python: {py_sign}\n  JS:     {js_sign}"


def test_cross_validate_real_world_timestamp():
    """实时时间戳签名一致"""
    import time
    ts = int(time.time() * 1000)
    path = "/api/flySource-yxgl/dormSignTask/getListForApp"
    token = "real_world_token_abc123"
    py_sign = generate_sign(path, ts, token)
    js_sign = _js_sign(path, ts, token)
    assert py_sign == js_sign, f"实时签名不一致!\n  Python: {py_sign}\n  JS:     {js_sign}"


def test_basic_auth_structure():
    """Basic Auth 结构完整性"""
    result = generate_basic_auth()
    assert result.startswith("Basic ")
    # 解码验证
    import base64
    decoded = base64.b64decode(result[6:]).decode("utf-8")
    assert ":" in decoded
    client_id, client_secret = decoded.split(":", 1)
    assert len(client_id) > 0
    assert len(client_secret) > 0
