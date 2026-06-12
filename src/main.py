"""Auto Check-In FastAPI 服务入口（阶段三脚手架）

全局 ApiClient 单例通过 FastAPI lifespan 管理生命周期。
load_dotenv() 必须在导入其他业务模块之前执行，确保环境变量优先加载。

Important caveats:
  - 当前仅提供根路径健康检查，多用户/定时任务功能待开发
  - CORS 配置允许所有来源（开发阶段），生产环境应限制

Variable naming: All names must be meaningful and context-relevant.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 加载 .env 环境变量（在导入其他模块之前执行）
load_dotenv()

from src.core.client import ApiClient

# 全局 ApiClient 实例，通过 lifespan 管理生命周期
api_client: ApiClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期：启动时创建 ApiClient，关闭时释放连接池"""
    global api_client
    api_client = ApiClient()
    yield
    api_client.close()


app = FastAPI(title="Auto Check-In", version="0.1.0", lifespan=lifespan)

# 允许跨域访问（开发调试用，生产环境应限制来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Auto Check-In Service"}
