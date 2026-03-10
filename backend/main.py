"""
AI麻将后端服务入口
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.majiang import router as majiang_router
from app.api.realtime import router as realtime_router

app = FastAPI(
    title="AI麻将助手 API",
    description="麻将AI策略服务后端 | 包含图像识别和WebSocket实时通信",
    version="1.1.0",
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
app.include_router(realtime_router, prefix="/api/v1", tags=["实时通信", "图像识别"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "AI麻将助手 API",
        "version": "1.1.0",
        "features": [
            "麻将牌效计算",
            "胡牌判定（支持长沙麻将）",
            "图像识别（YOLO模型预留）",
            "WebSocket实时通信"
        ],
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "1.1.0"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088)
