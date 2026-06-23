"""checkin ApiTokenClient 方法测试

测试来自共享模块的 ApiTokenClient、sign_builder、geo 功能。
"""
import json
import os
from unittest.mock import patch, MagicMock
import pytest
from src.core.token_client import ApiTokenClient, _get_profile_env
from src.core.sign_builder import build_stu_sign_data, compute_stu_task_id
from src.utils.geo import generate_gps_with_retry


class TestGetProfileEnv:

    def test_prefers_suffixed_env(self):
        with patch.dict(os.environ, {"CHECKIN_OPENID_USER_1": "suffixed", "CHECKIN_OPENID": "bare"}):
            assert _get_profile_env("USER_1", "CHECKIN_OPENID") == "suffixed"

    def test_falls_back_to_bare_env(self):
        with patch.dict(os.environ, {"CHECKIN_OPENID": "bare"}):
            assert _get_profile_env("USER_1", "CHECKIN_OPENID") == "bare"

    def test_empty_when_not_set(self):
        assert _get_profile_env("USER_1", "CHECKIN_NONEXIST") == ""


class TestApiTokenClientLogin:

    def test_login_success(self):
        with patch.dict(os.environ, {"CHECKIN_OPENID": "test_openid", "CHECKIN_USERNAME": "test_user"}):
            client = ApiTokenClient("default")
            with patch.object(client, "client", None):
                with patch("src.core.token_client.ApiClient") as MockApi:
                    mock_instance = MagicMock()
                    MockApi.return_value = mock_instance
                    mock_instance.sign_in_openid.return_value = {"access_token": "test_token"}

                    ok, msg = client.login()

        assert ok is True
        assert mock_instance.token == "test_token"

    def test_login_failure(self):
        with patch.dict(os.environ, {"CHECKIN_OPENID": "test_openid", "CHECKIN_USERNAME": "test_user"}):
            client = ApiTokenClient("default")
            with patch.object(client, "client", None):
                with patch("src.core.token_client.ApiClient") as MockApi:
                    mock_instance = MagicMock()
                    MockApi.return_value = mock_instance
                    mock_instance.sign_in_openid.return_value = {"error_description": "bad token"}

                    ok, msg = client.login()

        assert ok is False
        assert "bad token" in msg

    def test_login_reports_missing_required_env_without_api_call(self):
        with patch.dict(os.environ, {}, clear=True):
            client = ApiTokenClient("USER_1")
            with patch("src.core.token_client.ApiClient") as MockApi:
                ok, msg = client.login()

        assert ok is False
        assert "CHECKIN_OPENID_USER_1" in msg
        assert "CHECKIN_USERNAME_USER_1" in msg
        MockApi.assert_not_called()


class TestApiTokenClientFetchTask:

    def test_fetch_returns_task_id(self):
        with patch.dict(os.environ, {"CHECKIN_OPENID": "oid", "CHECKIN_USERNAME": "u"}):
            client = ApiTokenClient("default")
            client.client = MagicMock()
            client.client.get_task_list.return_value = {
                "success": True,
                "data": {"records": [{"taskId": "task_001"}, {"taskId": "task_002"}]},
            }
            tid = client.fetch_latest_task_id()
            assert tid == "task_001"

    def test_fetch_returns_none_when_no_records(self):
        with patch.dict(os.environ, {"CHECKIN_OPENID": "oid", "CHECKIN_USERNAME": "u"}):
            client = ApiTokenClient("default")
            client.client = MagicMock()
            client.client.get_task_list.return_value = {
                "success": True,
                "data": {"records": []},
            }
            assert client.fetch_latest_task_id() is None

    def test_fetch_returns_none_when_not_logged_in(self):
        with patch.dict(os.environ, {"CHECKIN_OPENID": "oid", "CHECKIN_USERNAME": "u"}):
            client = ApiTokenClient("default")
            assert client.fetch_latest_task_id() is None


class TestApiTokenClientDoCheckin:

    def test_successful_checkin(self):
        with patch.dict(os.environ, {"CHECKIN_OPENID": "oid", "CHECKIN_USERNAME": "u"}):
            client = ApiTokenClient("default")
            client.client = MagicMock()
            client.client.get_task_detail.return_value = {
                "success": True,
                "data": {
                    "scanType": 1,
                    "dormitoryRegisterVO": {"locationLat": "30.0", "locationLng": "120.0", "id": "A101"},
                    "locationAccuracy": 1000,
                },
            }
            client.client.stu_sign.return_value = {"success": True, "msg": "打卡成功"}

            ok, status, detail = client.do_checkin("task_001")

            assert ok is True
            assert status == "ok"

    def test_duplicate_checkin(self):
        with patch.dict(os.environ, {"CHECKIN_OPENID": "oid", "CHECKIN_USERNAME": "u"}):
            client = ApiTokenClient("default")
            client.client = MagicMock()
            client.client.get_task_detail.return_value = {
                "success": True,
                "data": {
                    "scanType": 1,
                    "dormitoryRegisterVO": {"locationLat": "30.0", "locationLng": "120.0", "id": "A101"},
                    "locationAccuracy": 1000,
                },
            }
            client.client.stu_sign.return_value = {"success": False, "msg": "重复签到"}

            ok, status, detail = client.do_checkin("task_001")

            assert ok is True
            assert status == "duplicate"


class TestGenerateGpsWithRetry:

    def test_returns_valid_coords(self):
        result = generate_gps_with_retry(30.0, 120.0, 1000, start_offset=0.002)
        assert result is not None
        lat, lng = result
        assert 29.9 <= lat <= 30.1
        assert 119.9 <= lng <= 120.1

    def test_returns_none_when_accuracy_too_tight(self):
        result = generate_gps_with_retry(30.0, 120.0, 0.0001, start_offset=0.002, max_retries=2)
        assert result is None


class TestBuildSignData:

    def test_produces_required_fields(self):
        task_detail = {"scanType": 1, "dormitoryRegisterVO": {"roomId": "A101"}, "signType": 0}
        data = build_stu_sign_data(task_detail, 30.0, 120.0, "50.0", "2026-06-12", "", "task_001")

        assert data["taskId"] == "task_001"
        assert data["scanType"] == 1
        assert data["roomId"] == "A101"
        assert data["signLat"] == "30.0"
        assert data["signLng"] == "120.0"
        assert data["locationAccuracy"] == "50.0"
        assert "stuTaskId" in data

    def test_stu_task_id_is_32_hex_chars(self):
        task_detail = {"scanType": 1, "dormitoryRegisterVO": {"roomId": "A101"}, "signType": 0}
        data = build_stu_sign_data(task_detail, 30.0, 120.0, "50.0", "2026-06-12", "", "task_001")
        assert len(data["stuTaskId"]) == 32
        int(data["stuTaskId"], 16)

    def test_stu_task_id_deterministic(self):
        task_detail = {"scanType": 1, "dormitoryRegisterVO": {"roomId": "A101"}, "signType": 0}
        data1 = build_stu_sign_data(task_detail, 30.0, 120.0, "50.0", "2026-06-12", "", "task_001")
        data2 = build_stu_sign_data(task_detail, 30.0, 120.0, "50.0", "2026-06-12", "", "task_001")
        assert data1["stuTaskId"] == data2["stuTaskId"]

    def test_known_md5_hash(self):
        task_detail = {"scanType": 1, "dormitoryRegisterVO": {"roomId": "101"}, "signType": 0}
        latitude, longitude = 30.001, 120.001
        location_accuracy = "10.0"
        sign_date = "2026-06-12"
        task_id = "task1"

        data = build_stu_sign_data(
            task_detail, latitude, longitude, location_accuracy, sign_date, "", task_id,
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


class TestRunMultiCheckinStatus:

    def test_all_failed_profiles_return_error_status(self):
        import checkin

        fake_results = [
            {"profile": "USER_1", "status": "error", "detail": "login failed"},
            {"profile": "USER_2", "status": "expired", "detail": "token expired"},
        ]
        with patch.dict(os.environ, {"CHECKIN_PROFILES": "USER_1,USER_2"}):
            with patch.object(checkin, "is_window_open", return_value=True):
                with patch.object(checkin, "_do_multi_or_single", return_value=fake_results):
                    with patch.object(checkin, "send_notifications"):
                        result = checkin.run_multi_checkin()

        assert result["status"] == "error"
