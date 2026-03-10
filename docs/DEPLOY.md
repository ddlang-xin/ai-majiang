# AI麻将助手 - 部署文档

## 项目信息

| 项目 | AI麻将助手后端 |
|------|----------------|
| 版本 | 1.1.0 |
| 框架 | FastAPI + Uvicorn |
| 端口 | 8088 |
| 项目路径 | ~/ai-projects/ai-majiang/backend |

## 当前状态

### ⚠️ 端口占用情况
- **端口8088已被占用**
- 当前占用进程: `uvicorn` (PID: 582611)
- 运行命令: `/root/ai-projects/ai-majiang/backend/venv/bin/python3 ... uvicorn main:app --host 0.0.0.0 --port 8088`

### 解决方案
如需重新部署，请先停止现有进程:
```bash
# 方案1: 使用PM2管理
pm2 stop ai-majiang-backend
pm2 delete ai-majiang-backend

# 方案2: 直接杀死进程
kill 582611
```

## 部署步骤

### 1. 安装依赖
```bash
cd ~/ai-projects/ai-majiang/backend
pip install -r requirements.txt
# 或使用虚拟环境
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 使用PM2启动
```bash
cd ~/ai-projects/ai-majiang/backend
pm2 start ecosystem.config.js
```

### 3. 查看状态
```bash
pm2 status
pm2 logs ai-majiang-backend
```

### 4. 常用命令
```bash
# 重启
pm2 restart ai-majiang-backend

# 停止
pm2 stop ai-majiang-backend

# 查看日志
pm2 logs ai-majiang-backend --lines 100

# 开机自启
pm2 save
pm2 startup
```

## API文档

部署完成后访问:
- Swagger UI: http://your-server:8088/docs
- ReDoc: http://your-server:8088/redoc
- 健康检查: http://your-server:8088/health

## PM2配置文件

配置文件位置: `backend/ecosystem.config.js`

```javascript
module.exports = {
  apps: [{
    name: 'ai-majiang-backend',
    script: 'main.py',
    interpreter: 'python3',
    cwd: '/root/ai-projects/ai-majiang/backend',
    env: { PORT: 8088 }
  }]
};
```

---
创建时间: 2026-03-08
