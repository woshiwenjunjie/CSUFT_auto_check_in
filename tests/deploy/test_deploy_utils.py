"""deploy.py 工具函数测试

测试内容：
- _fmt_size() 格式化（KB 和 MB 两种模式）
"""
import pytest
from pathlib import Path
from deploy import _fmt_size


class TestFmtSize:

    def test_kilobytes_below_1024(self, tmp_path):
        """1023 KB → "1023 KB" """
        f = tmp_path / "test.zip"
        f.write_bytes(b"x" * (1023 * 1024))
        assert _fmt_size(f) == "1023 KB"

    def test_megabytes_at_exactly_1024(self, tmp_path):
        """1024 KB → "1.0 MB" """
        f = tmp_path / "test.zip"
        f.write_bytes(b"x" * (1024 * 1024))
        assert _fmt_size(f) == "1.0 MB"

    def test_megabytes_large(self, tmp_path):
        """3072 KB → "3.0 MB" """
        f = tmp_path / "test.zip"
        f.write_bytes(b"x" * (3072 * 1024))
        assert _fmt_size(f) == "3.0 MB"

    def test_zero_bytes(self, tmp_path):
        """0 字节 → "0 KB" """
        f = tmp_path / "empty.zip"
        f.write_bytes(b"")
        assert _fmt_size(f) == "0 KB"
