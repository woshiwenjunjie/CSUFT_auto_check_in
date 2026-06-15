"""sign_builder — 打卡请求体构建（共享模块，CLI + SCF 共用）"""

from __future__ import annotations

import json
from src.utils.crypto import md5


def compute_stu_task_id(
    latitude: float, longitude: float, location_accuracy: str,
    sign_date: str, task_id: str, file_id: str = "",
) -> str:
    raw = json.dumps(
        {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "locationAccuracy": location_accuracy,
            "signDate": sign_date,
            "taskId": task_id,
            "fileId": file_id or "",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return md5(raw)


def build_stu_sign_data(
    task_detail: dict, cur_lat: float, cur_lng: float,
    loc_accuracy: str, sign_date: str, file_id: str, task_id: str,
) -> dict:
    dorm = task_detail.get("dormitoryRegisterVO", {}) or {}
    stu_data = {
        "taskId": task_id,
        "scanType": task_detail.get("scanType", 1),
        "roomId": dorm.get("roomId", ""),
        "signLat": str(cur_lat),
        "signLng": str(cur_lng),
        "locationAccuracy": loc_accuracy,
        "signType": task_detail.get("signType", 0),
        "scanCode": "",
        "fileId": file_id,
    }
    stu_data["stuTaskId"] = compute_stu_task_id(
        cur_lat, cur_lng, loc_accuracy, sign_date, task_id, file_id,
    )
    return stu_data
