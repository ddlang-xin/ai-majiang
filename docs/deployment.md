# AI麻将助手 - 部署方案

## 项目概述

- **后端**: Python FastAPI (端口: 8088)
- **前端**: Flutter APP (Android/iOS)
- **功能**: 实时捕捉麻将画面 → AI分析策略

---

## 1. 后端部署

### 1.1 技术栈
- Python 3.10+
- FastAPI + Uvicorn
- 依赖: fastapi, uvicorn, pydantic

### 1.2 部署方式选择

| 方式 | 优点 | 缺点 |
|------|------|------|
| **Docker** | 环境隔离、一键部署、可移植 | 需要Docker环境 |
| **PM2** | 简单、性能好、进程管理 | 需手动配置环境 |
| **直接运行** | 最简单 | 不利于维护 |

**推荐**: Docker 方式（环境一致性好）

### 1.3 Docker 部署

```dockerfile
# backend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8088

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8088"]
```

```yaml
# backend/docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8088:8088"
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
```

### 1.4 启动脚本

```bash
#!/bin/bash
# backend/start.sh

cd "$(dirname "$0")"

# 使用Docker
if command -v docker &> /dev/null; then
    docker-compose up -d --build
    echo "后端已启动: http://localhost:8088"
    echo "API文档: http://localhost:8088/docs"
else
    # 直接运行
    source venv/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8088 --reload
fi
```

---

## 2. 前端部署 (Flutter)

### 2.1 构建前准备

```bash
# 安装Flutter依赖
cd flutter_app
flutter pub get

# 检查环境
flutter doctor
```

### 2.2 Android 构建

```bash
# Debug APK
flutter build apk --debug

# Release APK
flutter build apk --release

# 输出: build/app/outputs/flutter-apk/app-release.apk
```

### 2.3 iOS 构建 (需macOS)

```bash
# Debug
flutter build ios --debug

# Release (需配置签名)
flutter build ios --release
```

### 2.4 Web 构建 (可选)

```bash
flutter build web
```

---

## 3. 快速启动

### 后端
```bash
cd backend
./start.sh
# 或
docker-compose up -d
```

### 前端
```bash
cd flutter_app
flutter build apk --release
```

---

## 4. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | 8088 | 服务端口 |
| `HOST` | 0.0.0.0 | 监听地址 |

---

## 5. 验证部署

```bash
# 后端健康检查
curl http://localhost:8088/health

# 响应: {"status":"ok","version":"1.1.0"}
```
