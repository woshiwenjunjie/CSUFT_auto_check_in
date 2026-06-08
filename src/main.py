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
