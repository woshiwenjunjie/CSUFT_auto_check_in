# 后端 API 设计（阶段三）

> RESTful API 规范，基于 FastAPI + SQLAlchemy

## 基础信息

- 基址：`https://checkin.example.com/api/v1`
- 协议：HTTPS
- 格式：JSON（request/response）
- 认证：JWT Bearer Token / X-Admin-Key
- 时区：全部时间使用 UTC+8（Asia/Shanghai）

## 通用响应格式

```json
{
  "code": 200,
  "data": {},
  "message": "ok"
}
```

错误响应：
```json
{
  "code": 400,
  "data": null,
  "message": "错误描述"
}
```

## 用户管理 API

### POST /users/register — 注册新用户

管理员操作，需要 `X-Admin-Key`。

**Request：**
```json
{
  "student_id": "2023****",
  "openid": "o************...",
  "password": "用户密码",
  "tenant_id": "000000"
}
```

**Response：**
```json
{
  "user_id": "uuid...",
  "student_id": "2023****",
  "token_valid": true,
  "dormitory": {
    "name": "QY24",
    "floor": "3F",
    "room": "315",
    "lat": 28.131085,
    "lng": 112.994644,
    "location_accuracy": 1500
  },
  "task": {
    "task_id": "b49ffb3790cfa0fb60661e4b59cdfbc8",
    "task_name": "平安打卡",
    "sign_time": "21:00-22:30"
  }
}
```

### GET /users — 用户列表

**Query：** `?is_active=true&page=1&size=20`

### GET /users/{id} — 用户详情

### PATCH /users/{id} — 更新用户

可更新字段：`is_active`, `settings`, `password`

### DELETE /users/{id} — 删除用户

### POST /users/{id}/refresh-token — 刷新 token

自动用存储的 OpenID + 密码重新调用学校 OAuth 接口。

### POST /users/{id}/sync-tasks — 同步任务信息

从学校 API 获取最新任务列表，更新 task_cache。

## 打卡 API

### POST /checkin/{user_id} — 手动触发打卡

触发指定用户的打卡流程，返回打卡结果。

**Response：**
```json
{
  "status": "ok",
  "task_name": "平安打卡",
  "sign_date": "2026-06-14",
  "sign_time": "21:05:30",
  "coordinate": {
    "lat": 28.131085,
    "lng": 112.994644
  }
}
```

状态说明：`ok` / `duplicate`（已打卡） / `expired`（窗口已过） / `nowindow`（非窗口期） / `error`

### GET /checkin/{user_id}/status — 查询今日状态

### GET /checkin/{user_id}/month/{YYYY-mm} — 月度记录

**Response：**
```json
{
  "month": "2026-06",
  "records": [
    {"date": "2026-06-01", "status": "正常", "sign_time": "21:10:00"},
    {"date": "2026-06-02", "status": "正常", "sign_time": "21:05:00"}
  ],
  "summary": {
    "total": 14,
    "normal": 14,
    "late": 0
  }
}
```

### GET /checkin/{user_id}/history — 打卡历史（分页）

## 调度管理 API

### GET /schedules — 所有定时任务

### POST /schedules — 创建定时任务

**Request：**
```json
{
  "user_id": "uuid...",
  "task_id": "b49ffb...",
  "cron_hour": 21,
  "cron_minute": 5,
  "timezone": "Asia/Shanghai",
  "is_active": true
}
```

### PATCH /schedules/{id} — 修改打卡时间

### DELETE /schedules/{id} — 删除定时任务

## 运维 API

### GET /health — 健康检查

```json
{
  "status": "ok",
  "active_users": 5,
  "today_checkins": 3,
  "db_latency_ms": 2
}
```

## 错误码

| code | 说明 |
|------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未授权（JWT 过期或无效） |
| 403 | 无权限（Admin Key 错误） |
| 404 | 资源不存在 |
| 429 | 请求过于频繁（限流） |
| 500 | 服务器内部错误 |

## 安全设计

- API 全走 HTTPS（Nginx SSL 终结）
- 管理接口验证 `X-Admin-Key`
- JWT 用户鉴权
- 请求限流：认证接口每 IP 5 次/分钟
- 登录凭据 AES-256-CBC 加密存储
- 日志脱敏（不记录完整密码/OpenID）
