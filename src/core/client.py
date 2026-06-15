"""飞源 flySource 统一认证 API 客户端

封装 8 个学校接口（认证/任务/打卡三组），统一处理签名、Basic 认证、
指数退避重试和微信/Web 双模式环境头伪装。
服务器会校验 Referer/User-Agent，缺失时返回误导性的"签名错误"。

Environment variables:
  CHECKIN_BASE_URL    API 基址（默认 https://simp.csuft.edu.cn）
  WX_APP_ID           微信小程序 AppID
  WX_VERSION          小程序版本号
  WX_USER_AGENT       微信客户端 User-Agent（Android 微信）
  WEB_REFERER         WebVPN Referer
  WEB_USER_AGENT      WebVPN User-Agent

Variable naming: All names must be meaningful and context-relevant.
"""
from __future__ import annotations

import atexit
import json
import os
import time
from typing import Any
import certifi
import httpx
from src.utils.crypto import md5
from src.utils.sign import generate_sign, generate_basic_auth, get_credentials


class ApiClient:
    """学校全链路 API 客户端（飞源 flySource 统一认证）

    封装认证、任务、打卡三大类共 8 个接口，统一处理签名、Basic 认证、重试
    支持上下文管理器（with 语句）自动关闭连接池

    服务器会校验 Referer/User-Agent 防止非微信客户端访问，必须伪装小程序环境
    """

    # 微信小程序环境参数（服务器反爬校验，可通过环境变量覆盖）
    WX_APP_ID = os.getenv("WX_APP_ID", "wx0e47c34c9982aa09")
    WX_VERSION = os.getenv("WX_VERSION", "7")
    WX_USER_AGENT = os.getenv("WX_USER_AGENT",
        "Mozilla/5.0 (Linux; Android 12; SM-F926U Build/V417IR; wv) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Version/4.0 Chrome/110.0.5481.154 Safari/537.36 "
        "MMWEBID/8631 MicroMessenger/8.0.72.3100(0x28004850) WeChat/arm64 "
        "Weixin NetType/WIFI Language/zh_CN ABI/arm64 MiniProgramEnv/android"
    )
    WEB_REFERER = os.getenv("WEB_REFERER", "https://simp.csuft.edu.cn/wise/")
    WEB_USER_AGENT = os.getenv("WEB_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0"
    )

    def __init__(self, token: str = "", base_url: str = "", client_mode: str = "wxapp"):
        """初始化客户端

        token: 登录后获得的 access_token（空字符串则只发 Basic 认证）
        base_url: API 基址，默认从环境变量 CHECKIN_BASE_URL 读取，兜底硬编码
        client_mode: 客户端凭据模式，"wxapp"（微信小程序）或 "web"（WebVPN 版）
        """
        if client_mode not in ("wxapp", "web"):
            raise ValueError(f"client_mode must be 'wxapp' or 'web', got: {client_mode}")
        self.token = token
        self.base_url = base_url or os.getenv("CHECKIN_BASE_URL", "https://simp.csuft.edu.cn")
        self.client_mode = client_mode
        self._client_id, self._client_secret = get_credentials(client_mode)
        if client_mode == "web":
            self._referer = self.WEB_REFERER
            self._user_agent = self.WEB_USER_AGENT
        else:
            self._referer = f"https://servicewechat.com/{self.WX_APP_ID}/{self.WX_VERSION}/page-frame.html"
            self._user_agent = self.WX_USER_AGENT
        self._client = httpx.Client(timeout=30, verify=certifi.where(), trust_env=False)
        atexit.register(self.close)  # 确保进程退出时释放连接池（CLI 短生命周期场景）

    def __enter__(self) -> ApiClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self):
        """显式关闭 httpx 连接池"""
        self._client.close()

    def _headers(self, url_path: str, extra: dict | None = None,
                no_auth: bool = False) -> dict:
        """构造请求头：Basic 认证 + 微信环境伪装 + FlySource 签名

        no_auth=True 时跳过 Basic Auth（用于 captcha 等不需要认证的端点）
        """
        ts = int(time.time() * 1000)
        h = {
            "Content-Type": "application/json",
            "charset": "utf-8",
            "Referer": self._referer,
            "User-Agent": self._user_agent,
        }
        if not no_auth:
            h["Authorization"] = generate_basic_auth(self._client_id, self._client_secret)
        if self.token:
            h["FlySource-Auth"] = self.token
            h["FlySource-sign"] = generate_sign(url_path, ts, self.token)
        if extra:
            h.update(extra)
        return h

    def _request(self, method: str, path: str,
                 params: dict | None = None,
                 data: dict | None = None,
                 form: bool = False,
                 extra_headers: dict | None = None,
                 no_auth: bool = False,
                 retry: int = 3) -> dict:
        """底层 HTTP 请求方法

        支持 GET/POST、JSON/form 编码、401 自动检测、指数退避重试（网络/解析错误）
        重试策略：第 1 次等 1s，第 2 次等 2s，第 3 次等 4s（最多 3 次）
        no_auth=True 跳过 Basic Auth（captcha 等不需要认证的端点）
        """
        url = self.base_url + path
        headers = self._headers(path, extra_headers, no_auth=no_auth)
        if form:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        last_error = None
        for attempt in range(retry):
            try:
                if method == "GET":
                    r = self._client.get(url, headers=headers, params=params)
                else:
                    if form:
                        r = self._client.post(url, headers=headers, data=data)
                    else:
                        r = self._client.post(url, headers=headers, json=data)
                if r.status_code == 401:
                    return {"code": 401, "success": False, "msg": "未登录或登录已过期"}
                return r.json()
            except (httpx.RequestError, json.JSONDecodeError) as e:
                last_error = e
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
                continue
        return {"code": 500, "success": False, "msg": f"请求失败: {last_error}"}

    def _get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict | None = None, form: bool = False,
             extra_headers: dict | None = None) -> dict:
        return self._request("POST", path, data=data, form=form, extra_headers=extra_headers)

    # --- 认证接口 ---
    def get_captcha(self, captcha_type: str = "captcha") -> dict:
        """获取登录验证码

        注意：此接口在小程序中 authorization=false，不传 Basic Auth
        """
        return self._request("GET", "/api/flySource-auth/captcha",
                            params={"type": captcha_type}, no_auth=True)

    def sign_in(self, tenant_id: str, username: str, password: str,
                captcha_key: str = "", captcha_code: str = "") -> dict:
        """密码登录（grant_type=password）

        Tenant-Id/Captcha-Key/Captcha-Code 作为请求头发送（与小程序一致）
        密码需做 MD5 后传输
        """
        extra = {"Tenant-Id": tenant_id}
        if captcha_key:
            extra["Captcha-Key"] = captcha_key
        if captcha_code:
            extra["Captcha-Code"] = captcha_code
        return self._post("/api/flySource-auth/oauth/token", data={
            "tenantId": tenant_id, "username": username,
            "password": md5(password), "grant_type": "password", "scope": "all",
        }, form=True, extra_headers=extra)

    def sign_in_openid(self, tenant_id: str, openid: str,
                       username: str = "", password: str = "",
                       bind_state: int = 0) -> dict:
        """OpenID 登录（grant_type=wxapp）

        bind_state=0: 仅自动登录（不绑定账号，小程序首页流程）
        bind_state=1: 绑定账号并登录（在绑定页面使用）
        带密码时做 MD5，空密码传空字符串
        """
        pw = md5(password) if password else ""
        extra = {"Web-Type": "wxapp", "Tenant-Id": tenant_id}
        return self._post("/api/flySource-auth/oauth/token", data={
            "tenantId": tenant_id, "username": username,
            "password": pw, "grant_type": "wxapp",
            "openid": openid, "bindState": str(bind_state), "scope": "all",
        }, form=True, extra_headers=extra)

    # --- 任务接口 ---
    def get_task_list(self, current: int = 1, size: int = 10) -> dict:
        """获取打卡任务列表（分页）"""
        return self._get("/api/flySource-yxgl/dormSignTask/getListForApp",
                         params={"current": current, "size": size})

    def get_task_detail(self, task_id: str) -> dict:
        """获取任务详情（含宿舍坐标 locationLat/locationLng 和精度上限 locationAccuracy）"""
        return self._get("/api/flySource-yxgl/dormSignTask/getTaskByIdForApp",
                         params={"taskId": task_id})

    # --- 打卡记录接口 ---
    def get_one_record(self, task_id: str, sign_date: str | None = None) -> dict:
        """查询当天打卡状态"""
        params = {"taskId": task_id}
        if sign_date:
            params["signDate"] = sign_date
        return self._get("/api/flySource-yxgl/dormSignRecord/getOne", params=params)

    def stu_sign(self, data: dict) -> dict:
        """提交打卡"""
        return self._post("/api/flySource-yxgl/dormSignRecord/stuSign", data=data)

    def stu_late_sign(self, data: dict) -> dict:
        """补签"""
        return self._post("/api/flySource-yxgl/dormSignRecord/stuLateSign", data=data)

    def get_month_records(self, task_id: str, month: str) -> dict:
        """按月查询打卡记录"""
        return self._get("/api/flySource-yxgl/dormSignRecord/getUserListAppByMonth",
                         params={"taskId": task_id, "month": month})
