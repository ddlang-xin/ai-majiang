"""
AI麻将后端服务入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.majiang import router as majiang_router

app = FastAPI(
    title="AI麻将助手 API",
    description="麻将AI策略服务后端",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(majiang_router, prefix="/api/v1", tags=["麻将分析"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "AI麻将助手 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
