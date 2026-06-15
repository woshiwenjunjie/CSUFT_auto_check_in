"""token_client — 从环境变量读取凭据并登录（SCF 专用适配器）"""

from __future__ import annotations

import os
import math
from datetime import datetime, timezone
from src.core.client import ApiClient
from src.utils.geo import generate_gps_with_retry, haversine
from src.core.sign_builder import build_stu_sign_data


def _get_profile_env(profile: str, prefix: str) -> str:
    suffix = f"{prefix}_{profile}"
    val = os.environ.get(suffix, "")
    if val:
        return val
    return os.environ.get(prefix, "")


class ApiTokenClient:
    """从环境变量读取凭据的 ApiClient 包装器"""

    def __init__(self, profile: str):
        self.profile = profile
        self.openid = _get_profile_env(profile, "CHECKIN_OPENID")
        self.username = _get_profile_env(profile, "CHECKIN_USERNAME")
        self.password = _get_profile_env(profile, "CHECKIN_PASSWORD")
        self.task_id_str = _get_profile_env(profile, "CHECKIN_TASK_ID")
        self.client: ApiClient | None = None
        self._task_id: str | None = None

    @property
    def task_id(self) -> str | None:
        if self._task_id is None:
            tid = self.task_id_str
            if tid and tid.strip():
                self._task_id = tid.strip()
        return self._task_id

    def login(self) -> tuple[bool, str]:
        try:
            self.client = ApiClient()
            resp = self.client.sign_in_openid(
                tenant_id="000000",
                openid=self.openid,
                username=self.username,
                password=self.password,
                bind_state=0,
            )
            token = resp.get("access_token", "")
            if token:
                self.client.token = token
                return True, "登录成功"
            err = resp.get("error_description") or resp.get("msg", "登录失败")
            return False, f"登录失败: {err}"
        except Exception as e:
            return False, f"登录异常: {e}"

    def fetch_latest_task_id(self) -> str | None:
        if not self.client:
            return None
        try:
            resp = self.client.get_task_list(current=1, size=10)
            if not resp.get("success"):
                return None
            records = resp.get("data", {}).get("records", [])
            for task in records:
                tid = task.get("taskId", "")
                if tid:
                    self._task_id = tid
                    return tid
        except Exception:
            return None
        return None

    def do_checkin(self, task_id: str) -> tuple[bool, str, str]:
        if not self.client:
            return False, "no_login", ""
        try:
            resp = self.client.get_task_detail(task_id)
            if not resp.get("success"):
                return False, "task_detail_failed", ""
            task_info = resp.get("data", {})
            dorm = task_info.get("dormitoryRegisterVO", {}) or {}
            dorm_lat = float(dorm.get("locationLat", 0))
            dorm_lng = float(dorm.get("locationLng", 0))
            accuracy_limit = float(task_info.get("locationAccuracy", 1000))

            gps = generate_gps_with_retry(dorm_lat, dorm_lng, accuracy_limit)
            if gps is None:
                return False, "out_of_range", ""
            cur_lat, cur_lng = gps

            distance_m = haversine(dorm_lat, dorm_lng, cur_lat, cur_lng)
            sign_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            stu_data = build_stu_sign_data(
                task_info, cur_lat, cur_lng, f"{distance_m:.1f}",
                sign_date, "", task_id,
            )

            resp2 = self.client.stu_sign(stu_data)
            if resp2.get("success"):
                return True, "ok", f"{distance_m / 1000:.2f}"
            msg = resp2.get("msg", "")
            if "重复" in msg:
                return True, "duplicate", msg
            if "已过期" in msg or "已结束" in msg:
                return False, "expired", msg
            return False, "error", msg
        except Exception as e:
            return False, "error", str(e)

    def confirm_checkin(self, task_id: str) -> str:
        if not self.client:
            return "no_login"
        try:
            sign_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            record = self.client.get_one_record(task_id, sign_date)
            data = record.get("data", {})
            if data:
                status = data.get("status", "")
                return "正常" if status in ("1", 1) else f"异常({status})"
            return "无记录"
        except Exception:
            return "查询异常"
