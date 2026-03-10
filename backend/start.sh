#!/bin/bash
# AI麻将助手后端启动脚本

set -e

cd "$(dirname "$0")"

echo "========================================="
echo "  AI麻将助手 - 后端启动"
echo "========================================="

# 检查Docker是否可用
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "检测到Docker环境，使用Docker部署..."
    docker-compose up -d --build
    echo ""
    echo "✅ 后端已启动!"
    echo "   API地址: http://localhost:8088"
    echo "   API文档: http://localhost:8088/docs"
    echo "   健康检查: http://localhost:8088/health"
else
    echo "未检测到Docker，使用本地Python环境..."
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo "创建虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装依赖
    pip install -r requirements.txt
    
    # 启动服务
    echo "启动后端服务..."
    uvicorn main:app --host 0.0.0.0 --port 8088 --reload
fi
