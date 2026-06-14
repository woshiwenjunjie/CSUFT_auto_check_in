"""CSUFT 自动晚点名打卡 — SCF 编排模块

该模块是腾讯云 SCF（Serverless Cloud Function）的核心编排层，负责将登录、任务获取、
打卡提交、结果确认和 Server酱 通知串联为单一事务。不依赖本地配置文件，所有敏感信息
通过 SCF 环境变量注入。

执行流程:
    run_checkin()
      ├─ 读取环境变量（OpenID、学号、密码、任务 ID）
      ├─ ApiTokenClient.auth()      → 获取 access_token（OAuth2）
      ├─ ApiTokenClient.fetch_latest_task_id()  → 自动发现打卡任务
      ├─ ApiTokenClient.do_checkin() → 构造签名、GPS 偏移、提交打卡
      │   ├─ get_task_detail()       → 获取宿舍 GPS 坐标 + 精度限制
      │   ├─ _gen_gps()             → 带退避的随机 GPS 偏移（6 次重试）
      │   ├─ _build_sign_data()      → 构造 stuTaskId（MD5 签名）
      │   └─ stu_sign()             → 提交签到 API
      ├─ ApiTokenClient.confirm_checkin() → 确认打卡状态
      └─ _notify_and_return()       → Server酱 推送 + 返回结果

时间处理:
    flySource 服务器使用 UTC 判定打卡窗口（UTC 13:00–14:30）。该模块内所有时间
    `_now()`/`_now_str()`/`_date_str()` 均为延迟计算函数，而非模块级常量，避免
    SCF 容器 warm start 时时间冻结导致日期滞后。

状态码:
    ok         打卡成功（含确认记录或 fallback）
    duplicate  今日已打卡（服务器返回重复/已签）
    expired    OpenID/token 过期（需重新抓包）
    nowindow   不在打卡窗口内
    error      其他错误（网络、凭据缺失、登录失败等）

环境变量（由 SCF 控制台配置，全部敏感字段勾选加密）:
    CHECKIN_OPENID     微信 OpenID（必填，建议加密）
    CHECKIN_USERNAME   学号（必填，建议加密）
    CHECKIN_PASSWORD   密码（必填，必须加密）
    CHECKIN_TASK_ID    打卡任务 ID（可选，不设则自动获取第一条）
    SERVERCHAN_KEY     Server酱 SendKey（可选，建议加密）
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from src.core.client import ApiClient
from src.utils.crypto import md5
from src.utils.geo import haversine, random_offset
from notify import send_serverchan


BEIJING_TZ = timezone(timedelta(hours=8))
WINDOW_START_T = timedelta(hours=21)
WINDOW_END_T = timedelta(hours=22, minutes=30)


def _now() -> datetime:
    return datetime.now(BEIJING_TZ)


def _now_str() -> str:
    return _now().strftime("%Y-%m-%d %H:%M:%S")


def _date_str() -> str:
    return _now().strftime("%Y-%m-%d")


def _is_window_open() -> bool:
    """当前北京时间是否在 21:00–22:30 打卡窗口内"""
    now_bj = _now()
    start = now_bj.replace(hour=21, minute=0, second=0, microsecond=0)
    end = now_bj.replace(hour=22, minute=30, second=0, microsecond=0)
    return start <= now_bj <= end


def _nearest_window_hint() -> str:
    """返回距下次窗口的友好提示（如"还有 8 小时 25 分钟"）"""
    now_bj = _now()
    start_today = now_bj.replace(hour=21, minute=0, second=0, microsecond=0)
    if now_bj < start_today:
        delta = int((start_today - now_bj).total_seconds())
        hours, minutes = divmod(delta // 60, 60)
        if hours > 0:
            return f"距下次打卡窗口还有 {hours} 小时 {minutes} 分钟"
        return f"距下次打卡窗口还有 {minutes} 分钟"
    return "下次打卡窗口为今晚 21:00–22:30"


def get_env_str(key: str, default: str = "") -> str:
    """读取环境变量，不存在时返回 default"""
    return os.environ.get(key, default)


def _build_notification(result: dict) -> tuple[str, str]:
    """根据 result 状态构造推送标题+正文，与 GitHub Actions 通知风格保持一致"""
    status = result["status"]
    msg = result["msg"]
    date = result.get("date", _date_str())
    detail = result.get("detail", "")
    distance = result.get("distance", "")
    now = _now_str()

    if status == "ok":
        title = f"✅ CSUFT 打卡成功 · {date}"
        body = f"## ✅ 晚点名打卡 · 成功\n\n**{date}** | 状态：{msg}"
        if distance:
            body += f" | 距宿舍 {distance}"
    elif status == "duplicate":
        title = f"⏰ CSUFT 今日已打卡 · {date}"
        body = (f"## ⏰ 今日已打卡\n\n**{date}** — 今日已签过到，无需重复操作\n\n"
                f"> 次日 **21:00–22:30** 自动执行下次打卡")
    elif status == "expired":
        title = "❌ CSUFT Token 过期"
        body = (f"## ❌ 登录凭据已过期\n\n**{now}**\n\n"
                f"> OpenID 过期，需重新抓包更新\n"
                f"> CLI: `capture-openid` / Fiddler / Reqable")
    elif status == "nowindow":
        title = f"⏳ CSUFT 未到签到时间 · {now}"
        body = f"## ⏳ 未到签到时间\n\n**{now}** — {msg}\n\n> 窗口：**21:00–22:30 北京时间**（UTC 13:00–14:30）\n> 定时任务每天 21:05 自动执行"
    elif status == "partial":
        title = f"⚠️ CSUFT 部分打卡成功 · {now}"
        body = f"## ⚠️ 部分打卡成功\n\n**{now}** — {msg}"
    else:
        title = f"❌ CSUFT 打卡失败 · {now}"
        body = f"## ❌ 打卡失败\n\n**{now}**\n\n```\n{msg}\n```"
    if detail:
        body += f"\n\n{detail}"
    body += f"\n\n---\n🕐 {now} 北京时间"
    return title, body


def _notify_and_return(result: dict) -> dict:
    """打印结果、发 Server酱 通知、返回 result"""
    print(f"[结果] {json.dumps(result, ensure_ascii=False)}")
    title, body = _build_notification(result)
    send_serverchan(title, body)
    return result


def _get_profile_env(profile_name: str, key: str, default: str = "") -> str:
    """读取 profile 环境变量，优先带后缀，兜底无后缀（兼容旧版单用户配置）。"""
    val = get_env_str(f"{key}_{profile_name}")
    if val:
        return val
    return get_env_str(key, default)


def _checkin_one(profile_name: str) -> dict:
    """为一个账号执行登录→任务→打卡→确认，返回结果字典。"""
    openid = _get_profile_env(profile_name, "CHECKIN_OPENID")
    username = _get_profile_env(profile_name, "CHECKIN_USERNAME")
    password = _get_profile_env(profile_name, "CHECKIN_PASSWORD", "")
    task_id = _get_profile_env(profile_name, "CHECKIN_TASK_ID")
    date = _date_str()

    label = f"[{profile_name}]"
    if not openid or not username:
        suffix = f"_{profile_name}"
        missing = []
        if not openid:
            missing.append(f"CHECKIN_OPENID{suffix}")
        if not username:
            missing.append(f"CHECKIN_USERNAME{suffix}")
        return {"status": "error", "msg": f"{label} 环境变量缺失：{'、'.join(missing)}", "date": date}

    print(f"{label} 登录 openid={openid[:8]}... username={username}")
    api_client = ApiTokenClient(openid, username, password)
    login_ok, token = api_client.login()
    if not login_ok:
        msg = f"登录失败: {token}"
        print(f"{label} {msg}")
        return {"status": "error", "msg": f"{label} {msg}", "date": date}
    print(f"{label} 登录成功")

    if not task_id:
        task_id = api_client.fetch_latest_task_id()
        if not task_id:
            if _is_window_open():
                msg = "窗口内无可用任务"
                status = "error"
            else:
                msg = f"不在窗口（{_nearest_window_hint()}）"
                status = "nowindow"
            return {"status": status, "msg": f"{label} {msg}", "date": date}
    print(f"{label} task_id={task_id}")

    checkin_ok, checkin_msg, distance = api_client.do_checkin(task_id)
    if not checkin_ok:
        if "重复" in checkin_msg or "已签" in checkin_msg:
            status = "duplicate"
        elif "过期" in checkin_msg:
            status = "expired"
        elif "签到时间" in checkin_msg or "不在" in checkin_msg:
            status = "nowindow"
        else:
            status = "error"
        return {"status": status, "msg": f"{label} {checkin_msg}", "date": date}

    record = api_client.confirm_checkin(task_id)
    if record:
        status_name = record.get("signStatusName", "未知")
        sign_date = record.get("signDate", date)
        return {"status": "ok", "msg": f"{label} {status_name}", "date": sign_date, "distance": distance}
    return {"status": "ok", "msg": f"{label} 打卡成功（无法确认）", "date": date}


def run_checkin() -> dict:
    """SCF 打卡主入口：单用户模式（向后兼容）。"""
    return _do_multi_or_single(profiles=None)


def run_multi_checkin() -> dict:
    """SCF 打卡默认入口：多用户模式（同时也是 handler 默认调用入口）。

    环境变量约定:
      CHECKIN_PROFILES=USER_1,USER_2           profile 列表（缺省="default"）
      CHECKIN_OPENID_USER_1 / USERNAME_USER_1  每个 profile 的凭据
      不设 CHECKIN_PROFILES 时自动回退 bare 变量 CHECKIN_OPENID/USERNAME（兼容单用户）
    """
    profiles_str = get_env_str("CHECKIN_PROFILES", "")
    return _do_multi_or_single(profiles=profiles_str)


def _do_multi_or_single(profiles: str | None) -> dict:
    """根据 profiles 参数决定单用户或多用户流程。"""
    if profiles:
        profile_names = [p.strip() for p in profiles.split(",") if p.strip()]
    else:
        profile_names = ["default"]

    if len(profile_names) == 1:
        return _notify_and_return(_checkin_one(profile_names[0]))

    all_results: list[dict] = []
    for pname in profile_names:
        try:
            result = _checkin_one(pname)
        except Exception as e:
            print(f"[错误] {pname} 异常: {e}")
            result = {"status": "error", "msg": f"[{pname}] 未捕获异常: {e}", "date": _date_str()}
        all_results.append(result)
        print(f"[结果] {pname}: {result['status']} {result.get('msg', '')}")

    date = _date_str()
    ok_count = sum(1 for r in all_results if r["status"] == "ok")
    total = len(all_results)

    if ok_count == total:
        summary = {"status": "ok", "msg": f"全部 {total} 个账号打卡成功", "date": date}
    elif ok_count > 0:
        summary = {"status": "partial", "msg": f"{ok_count}/{total} 个账号打卡成功", "date": date}
    else:
        summary = {"status": "error", "msg": f"{total} 个账号均失败", "date": date}

    detail_lines = []
    for r in all_results:
        icon = "✅" if r["status"] == "ok" else "⏰" if r["status"] == "duplicate" else "❌"
        detail_lines.append(f"{icon} {r.get('msg', '')}")
    summary["detail"] = "\n".join(detail_lines)

    title, body = _build_notification(summary)
    send_serverchan(title, body)
    print(f"[结果] {summary['msg']}")
    return summary


class ApiTokenClient:
    """SCF 环境下的 ApiClient 适配器。

    包装 `src.core.client.ApiClient`，剥离 CLI 依赖（cli_config、cli_ui），
    通过构造函数注入凭据，以纯 API 方式完成登录 OAuth2 流程。

    不支持 WebVPN 模式，仅使用 `wxapp` 客户端模式。若需 WebVPN 认证，
    请参考 `scripts/cli_commands/auth.login_webvpn()`。
    """

    def __init__(self, openid: str, username: str, password: str) -> None:
        self.openid = openid
        self.username = username
        self.password = password
        self.token = ""
        self.tenant_id = "000000"
        self._client: ApiClient | None = None

    def login(self) -> tuple[bool, str]:
        self._client = ApiClient(client_mode="wxapp")
        resp = self._client.sign_in_openid(
            tenant_id=self.tenant_id,
            openid=self.openid,
            username=self.username,
            password=self.password,
            bind_state=0,
        )
        token = resp.get("access_token", "")
        if token:
            self.token = token
            self._client.token = token
            return True, token
        err = resp.get("error_description") or resp.get("msg", "未知错误")
        return False, err

    def fetch_latest_task_id(self) -> str:
        if not self._client or not self.token:
            return ""
        resp = self._client.get_task_list(current=1, size=5)
        if not resp.get("success"):
            return ""
        records = resp.get("data", {}).get("records", [])
        for task in records:
            task_identifier = task.get("taskId", "")
            if task_identifier:
                return task_identifier
        return ""

    def do_checkin(self, task_id: str) -> tuple[bool, str, str]:
        """返回 (成功, 消息, 距离描述)"""
        if not self._client or not self.token:
            return False, "未登录", ""
        detail = self._client.get_task_detail(task_id)
        if not detail.get("success"):
            return False, detail.get("msg", "获取任务详情失败"), ""
        task_detail = detail.get("data", {})
        dorm_registration = task_detail.get("dormitoryRegisterVO", {}) or {}
        dormitory_lat = float(dorm_registration.get("locationLat", 0))
        dormitory_lng = float(dorm_registration.get("locationLng", 0))
        accuracy_limit = float(task_detail.get("locationAccuracy", 100))
        sign_date = _now().strftime("%Y-%m-%d")

        # generate GPS with random offset
        current_lat, current_lng = self._gen_gps(dormitory_lat, dormitory_lng, accuracy_limit)
        if current_lat is None:
            return False, f"重试5次后仍超出打卡范围（精度上限{accuracy_limit}m）", ""

        distance_m = haversine(current_lat, current_lng, dormitory_lat, dormitory_lng)
        location_accuracy = f"{distance_m:.1f}"
        signature_payload = self._build_sign_data(
            task_detail, current_lat, current_lng, location_accuracy, sign_date, task_id,
        )

        resp = self._client.stu_sign(signature_payload)
        if resp.get("success"):
            return True, "打卡成功", f"{distance_m:.1f}m"
        msg = resp.get("msg", "未知错误")
        return False, msg, ""

    def _gen_gps(self, dormitory_lat: float, dormitory_lng: float, accuracy_limit: float) -> tuple:
        """生成带偏移的 GPS 坐标，使 Haversine 距离 ≤ accuracy_limit。

        策略：从 0.002° 起始，每次折半偏移量，最多 6 次尝试。若精度上限极小（< 1e-6°），
        直接以 dormitory 坐标返回。避免原地打卡（服务器防作弊检测）。
        """
        current_offset_degrees = 0.002
        for _ in range(6):
            latitude, longitude = random_offset(dormitory_lat, dormitory_lng, current_offset_degrees)
            distance = haversine(latitude, longitude, dormitory_lat, dormitory_lng)
            if distance <= accuracy_limit:
                return latitude, longitude
            if current_offset_degrees < 1e-6:
                break
            current_offset_degrees /= 2
        return None, None

    def _build_sign_data(self, task_detail: dict, latitude: float, longitude: float,
                         location_accuracy: str, sign_date: str, task_id: str) -> dict:
        """构造打卡请求体，含 stuTaskId（MD5 防篡改哈希）。

        哈希算法：
            hash_input = {latitude, longitude, locationAccuracy, signDate, taskId, fileId}
            stuTaskId = MD5(json.dumps(hash_input, sorted keys, no spaces))
        """
        dorm_registration = task_detail.get("dormitoryRegisterVO", {}) or {}
        data = {
            "taskId": task_id,
            "scanType": task_detail.get("scanType", 1),
            "roomId": dorm_registration.get("roomId", ""),
            "signLat": str(latitude),
            "signLng": str(longitude),
            "locationAccuracy": location_accuracy,
            "signType": 0,
            "scanCode": "",
            "fileId": "",
        }
        hash_input = {
            "latitude": str(latitude), "longitude": str(longitude),
            "locationAccuracy": location_accuracy, "signDate": sign_date,
            "taskId": task_id, "fileId": "",
        }
        data["stuTaskId"] = md5(
            json.dumps(hash_input, ensure_ascii=False, separators=(",", ":"))
        )
        return data

    def confirm_checkin(self, task_id: str) -> dict | None:
        if not self._client or not self.token:
            return None
        sign_date = _now().strftime("%Y-%m-%d")
        resp = self._client.get_one_record(task_id, sign_date)
        if resp.get("success"):
            return resp.get("data")
        return None
