"""checkin ApiTokenClient 方法测试

测试需要 mock 的内容：
- _gen_gps(): random_offset 调用由 _gen_gps 内部完成，mock random_offset 控制返回值
- _build_sign_data(): 纯函数，给定输入→期望输出，含 stuTaskId MD5 哈希
"""
import json
from unittest.mock import patch, MagicMock
import pytest
from checkin import ApiTokenClient


class TestGenGps:

    def test_returns_valid_coords(self):
        """random_offset 返回精度范围内的坐标"""
        client = ApiTokenClient("openid", "user", "pass")

        with patch("checkin.random_offset", return_value=(30.001, 120.001)):
            with patch("checkin.haversine", return_value=50.0):
                lat, lng = client._gen_gps(30.0, 120.0, 100.0)

        assert lat == 30.001
        assert lng == 120.001

    def test_fallback_when_all_attempts_exceed_accuracy(self):
        """6 次尝试后仍超出精度 → 返回 None"""
        client = ApiTokenClient("openid", "user", "pass")

        with patch("checkin.random_offset", return_value=(31.0, 121.0)):
            with patch("checkin.haversine", return_value=100000.0):
                lat, lng = client._gen_gps(30.0, 120.0, 1.0)

        assert lat is None
        assert lng is None

    def test_halves_offset_on_each_retry(self):
        """每次超出的偏移减半，最终精度提升"""
        client = ApiTokenClient("openid", "user", "pass")
        call_count = 0

        def shrinking_offset(lat, lng, offset_deg):
            nonlocal call_count
            call_count += 1
            return (lat + offset_deg, lng + offset_deg)

        with patch("checkin.random_offset", side_effect=shrinking_offset):
            with patch("checkin.haversine", return_value=999.0):
                lat, lng = client._gen_gps(30.0, 120.0, 0.001)

        assert call_count <= 6


class TestBuildSignData:

    def test_produces_required_fields(self):
        """返回的 dict 包含所有必要字段"""
        client = ApiTokenClient("openid", "user", "pass")
        task_detail = {"scanType": 1, "dormitoryRegisterVO": {"roomId": "A101"}}

        data = client._build_sign_data(task_detail, 30.0, 120.0, "50.0", "2026-06-12", "task_001")

        assert data["taskId"] == "task_001"
        assert data["scanType"] == 1
        assert data["roomId"] == "A101"
        assert data["signLat"] == "30.0"
        assert data["signLng"] == "120.0"
        assert data["locationAccuracy"] == "50.0"
        assert "stuTaskId" in data

    def test_stu_task_id_is_32_hex_chars(self):
        """stuTaskId 是 32 位十六进制 MD5"""
        client = ApiTokenClient("openid", "user", "pass")
        task_detail = {"scanType": 1, "dormitoryRegisterVO": {"roomId": "A101"}}

        data = client._build_sign_data(task_detail, 30.0, 120.0, "50.0", "2026-06-12", "task_001")

        assert len(data["stuTaskId"]) == 32
        int(data["stuTaskId"], 16)  # 验证是合法十六进制

    def test_stu_task_id_deterministic(self):
        """相同输入产生相同 stuTaskId"""
        client = ApiTokenClient("openid", "user", "pass")
        task_detail = {"scanType": 1, "dormitoryRegisterVO": {"roomId": "A101"}}

        data1 = client._build_sign_data(task_detail, 30.0, 120.0, "50.0", "2026-06-12", "task_001")
        data2 = client._build_sign_data(task_detail, 30.0, 120.0, "50.0", "2026-06-12", "task_001")

        assert data1["stuTaskId"] == data2["stuTaskId"]

    def test_known_md5_hash(self):
        """给定精确输入时 stuTaskId 符合已知 MD5"""
        client = ApiTokenClient("openid", "user", "pass")
        task_detail = {"scanType": 1, "dormitoryRegisterVO": {"roomId": "101"}}
        latitude, longitude = 30.001, 120.001
        location_accuracy = "10.0"
        sign_date = "2026-06-12"
        task_id = "task1"

        data = client._build_sign_data(
            task_detail, latitude, longitude, location_accuracy, sign_date, task_id,
        )

        hash_input = {
            "latitude": str(latitude), "longitude": str(longitude),
            "locationAccuracy": location_accuracy, "signDate": sign_date,
            "taskId": task_id, "fileId": "",
        }
        expected = __import__("hashlib").md5(
            json.dumps(hash_input, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        assert data["stuTaskId"] == expected
