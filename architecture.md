# AI麻将助手 - 系统架构设计文档

## 1. 项目概述

### 1.1 项目目标

实现手机摄像头实时捕捉麻将画面，通过AI识别牌面，计算并推荐最优出牌策略。

### 1.2 技术选型

| 层级 | 技术栈 | 说明 |
|------|--------|------|
| 移动端 | Flutter | 跨平台(iOS/Android) |
| CV识别 | YOLOv8 + ONNX Runtime | 轻量化目标检测模型 |
| AI策略 | Mortal / RLCard / mahjong-helper | 牌效计算与决策 |
| 后端服务 | Python FastAPI | AI推理服务 |
| 部署 | Docker + K8s | 容器化部署 |

---

## 2. 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户层 (User Layer)                              │
│                                                                              │
│    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│    │  手机App    │     │  手机App    │     │  手机App    │                  │
│    │  (玩家A)    │     │  (玩家B)    │     │  (玩家C)    │                  │
│    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘                  │
└───────────┼───────────────────┼───────────────────┼─────────────────────────┘
            │                   │                   │
            │  HTTPS/WebSocket  │                   │
            ▼                   ▼                   ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           接入层 (Gateway Layer)                             │
│                                                                              │
│    ┌─────────────────────────────────────────────────────────────────┐        │
│    │                      API Gateway / Load Balancer               │        │
│    │                   (Nginx + Kong / AWS ALB)                     │        │
│    └─────────────────────────────────────────────────────────────────┘        │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          服务层 (Service Layer)                              │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │
│  │  图像识别服务     │  │  牌效计算服务     │  │  用户管理服务     │            │
│  │  (Image API)    │  │  (Strategy API)  │  │  (User API)     │            │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘            │
│           │                      │                      │                      │
│           ▼                      ▼                      ▼                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │
│  │  YOLOv8+ONNX    │  │  牌效算法引擎     │  │  MySQL/Redis    │            │
│  │  推理集群       │  │  (Mortal/RLCard) │  │  用户数据存储    │            │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘            │
│                                                                              │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 架构分层说明

| 层级 | 职责 | 关键技术 |
|------|------|----------|
| 用户层 | 移动端应用交互 | Flutter, Camera, WebSocket |
| 接入层 | 请求路由、负载均衡、限流 | Nginx, Kong, JWT认证 |
| 服务层 | 业务逻辑处理 | FastAPI, gRPC |
| 算法层 | 核心AI推理 | YOLOv8, ONNX Runtime, 牌效算法 |

---

## 3. 图像识别流程设计

### 3.1 识别流程图

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  摄像头采集  │───▶│  图像预处理  │───▶│  YOLOv8检测 │───▶│  牌面分类   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                    │
                                                                    ▼
                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                   │  结果校验    │◀───│  字符识别   │◀───│  图像校正   │
                   └─────────────┘    └─────────────┘    └─────────────┘
```

### 3.2 模块设计

#### 3.2.1 图像采集模块

```python
# 模块职责：摄像头控制、图像帧采集
class ImageCapture:
    def __init__(self):
        self.camera = CameraController()
        self.frame_buffer = RingBuffer(size=5)
    
    def capture_frame(self) -> np.ndarray:
        """获取当前帧"""
        frame = self.camera.capture()
        return self.frame_buffer.add(frame)
    
    def get_best_frame(self) -> np.ndarray:
        """从缓冲帧中选择最佳帧（防抖）"""
        frames = self.frame_buffer.get_all()
        return self.select_stable_frame(frames)
```

#### 3.2.2 图像预处理模块

```python
# 模块职责：图像增强、畸变校正、ROI提取
class ImagePreprocessor:
    def __init__(self):
        self.calibration = CameraCalibration()
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        # 畸变校正
        image = self.calibration.undistort(image)
        # 边缘增强
        image = self.enhance_edges(image)
        # 对比度调整
        image = self.adjust_contrast(image, clip_limit=2.0)
        # ROI提取（麻将牌区域）
        roi = self.extract_mahjong_region(image)
        return roi
```

#### 3.2.3 目标检测模块 (YOLOv8)

```python
# 模块职责：麻将牌定位与初步分类
class MahjongDetector:
    def __init__(self, model_path: str):
        self.model = ONNXModel(model_path)
        # 34种麻将牌 + 背景类
        self.num_classes = 35
    
    def detect(self, image: np.ndarray) -> List[Detection]:
        """
        Returns: List[Detection]
          - bbox: [x1, y1, x2, y2]
          - class_id: 0-33 (麻将牌类型)
          - confidence: float
        """
        outputs = self.model.predict(image)
        results = self.postprocess(outputs)
        return results
```

#### 3.2.4 牌面识别模块

```python
# 模块职责：识别每张牌的详细信息（万/筒/条/字牌）
class TileClassifier:
    def __init__(self):
        self.tile_types = {
            'wan': list(range(1, 10)),    # 万 1-9
            'tong': list(range(10, 19)), # 筒 1-9
            'tiao': list(range(19, 28)), # 条 1-9
            'zi': list(range(28, 34))    # 字牌(东南西北中发白)
        }
    
    def classify(self, tile_image: np.ndarray) -> TileInfo:
        """
        Returns: TileInfo
          - suit: 'wan'|'tong'|'tiao'|'zi'
          - number: 1-9 (字牌为特殊编码)
          - is_red: bool (用于识别中发白)
        """
        # 使用轻量级CNN或特征匹配
        suit, number = self.cnn_forward(tile_image)
        return TileInfo(suit=suit, number=number)
```

### 3.3 牌效计算模块设计

#### 3.3.1 模块架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      牌效计算引擎 (Strategy Engine)              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  手牌解析器   │  │  听牌分析器  │  │  弃牌推荐器  │          │
│  │ HandParser   │  │ TingAnalyzer │  │ DiscardAdvice│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                │                 │                    │
│         └────────────────┼─────────────────┘                    │
│                          ▼                                      │
│              ┌──────────────────────┐                           │
│              │    牌效算法核心        │                           │
│              │  (ShantenCalculator)  │                           │
│              └──────────────────────┘                           │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         ▼                ▼                ▼                      │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐              │
│  │ 进攻评估   │   │ 防守评估   │   │ 点数评估   │              │
│  │Aggression  │   │ Defense    │   │ Score      │              │
│  └────────────┘   └────────────┘   └────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 核心算法

```python
# 向听数计算 (Shanten Number)
class ShantenCalculator:
    """
    计算当前手牌距离听牌/和牌所需的最小打出牌数
    - 14张手牌：向听数0=听牌，向听数-1=和牌
    """
    
    def calculate(self, hand: List[Tile]) -> int:
        """
        向听数计算算法：
        1. 统计各牌数量
        2. 枚举所有可能的搭子/顺子/刻子组合
        3. 计算最小剩余单牌数
        """
        return self._compute_shanten(hand)
    
    def get_ukeire(self, hand: List[Tile]) -> List[Tile]:
        """
        摸进哪些牌可以降低向听数（进张牌）
        """
        all_tiles = self.get_all_tiles()
        ukeire = []
        for tile in all_tiles:
            if self.calculate(hand + [tile]) < self.calculate(hand):
                ukeire.append(tile)
        return ukeire
```

#### 3.3.3 出牌推荐算法

```python
class DiscardAdvisor:
    def __init__(self, game_context: GameContext):
        self.context = game_context
        self.shanten_calc = ShantenCalculator()
    
    def recommend(self, hand: List[Tile]) -> DiscardResult:
        """
        综合评估每张可打牌的打分，返回最优出牌
        
        评估因素：
        1. 向听数影响 (权重: 40%)
        2. 防守安全度 (权重: 30%)
        3. 食和期望值 (权重: 20%)
        4. 速度/点数平衡 (权重: 10%)
        """
        candidates = []
        for tile in hand:
            score = self._evaluate_discard(tile, hand)
            candidates.append((tile, score))
        
        # 返回最高分
        return max(candidates, key=lambda x: x[1])
    
    def _evaluate_discard(self, tile: Tile, hand: List[Tile]) -> float:
        shanten_impact = self._calc_shanten_impact(tile, hand)
        safety = self._calc_safety(tile, self.context)
        return (shanten_impact * 0.4 + 
                safety * 0.3 + 
                self._calc_expected_score(tile, hand) * 0.2 +
                self._calc_speed_score(tile, hand) * 0.1)
```

### 3.4 数据流设计

#### 3.4.1 实时识别数据流

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ 摄像头  │────▶│ Flutter │────▶│  云端   │────▶│ YOLOv8  │────▶│  牌效   │
│  帧流   │     │  App    │     │  API   │     │  推理   │     │ 计算    │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
    │                                                       │
    │         WebSocket 长连接                              │
    └───────────────────────────────────────────────────────┘
                        │
                        ▼
                 ┌─────────────┐
                 │  推荐结果    │
                 │  返回App    │
                 └─────────────┘
```

#### 3.4.2 数据协议设计

```json
// 请求：图像识别
{
  "request_id": "req_123456",
  "image_base64": "...",
  "game_state": {
    "round_wind": "east",
    "player_wind": "south",
    "dora_indicators": [5],
    "discards": {
      "opponent1": ["1m", "2p", "5s"],
      "opponent2": ["east", "south"],
      "opponent3": ["red", "white"]
    }
  },
  "timestamp": 1699999999999
}

// 响应：识别结果 + 策略推荐
{
  "request_id": "req_123456",
  "detected_tiles": [
    {"tile": "1m", "bbox": [100, 200, 150, 280], "confidence": 0.98},
    {"tile": "2p", "bbox": [160, 200, 210, 280], "confidence": 0.95}
  ],
  "hand_tiles": ["1m", "2p", "3p", "7m", "8m", "9m", "white", "white", "3s", "4s", "5s", "6s", "north", "north"],
  "strategy": {
    "recommended_discard": "2p",
    "shanten": 2,
    "ukeire": ["1p", "4p", "7p"],
    "alternatives": [
      {"tile": "3p", "score": 85},
      {"tile": "north", "score": 72}
    ],
    "reasoning": "打2p进张多，防守角度也相对安全"
  },
  "processing_time_ms": 156
}
```

#### 3.4.3 状态管理

```python
# 游戏状态管理
class GameState:
    def __init__(self):
        self.round_wind: Wind = Wind.EAST
        self.player_wind: Wind = Wind.SOUTH
        self.hand_tiles: List[Tile] = []      # 14张手牌
        self.drawn_tile: Optional[Tile] = None # 摸到的牌
        self.dora_indicators: List[Tile] = []  # 宝牌指示
        self.discards: Dict[int, List[Tile]] = {}  # 各家舍牌
        self.calls: Dict[int, List[Call]] = {}      # 鸣叫(吃碰杠)
```

---

## 4. 关键技术难点及解决方案

### 4.1 难点1：复杂光照下的识别准确率

| 问题 | 解决方案 |
|------|----------|
| 光照不均导致识别失败 | 1. 相机自动曝光/AEB<br>2. 图像预处理：自适应直方图均衡化(CLAHE)<br>3. 数据增强：模拟各种光照训练 |
| 反光/阴影干扰 | 1. 偏振镜消除反光<br>2. 阴影检测与修复<br>3. 多帧投票验证 |

### 4.2 难点2：实时性要求

| 问题 | 解决方案 |
|------|----------|
| 端侧推理延迟高 | 1. YOLOv8n(轻量)模型 + INT8量化<br>2. ONNX Runtime Mobile优化<br>3. Flutter平台通道调用native推理 |
| 网络传输延迟 | 1. WebSocket长连接<br>2. 关键帧+增量传输<br>3. 边缘节点部署 |

### 4.3 难点3：牌效计算精度

| 问题 | 解决方案 |
|------|----------|
| 局部最优而非全局最优 | 1. 引入Mortal的神经网络估值<br>2. Monte Carlo Tree Search扩展<br>3. 多维度评估(攻守平衡) |
| 防守判断困难 | 1. 防守代价函数：点和率+被吃率<br>2. 牌危险度预计算表<br>3. 考虑对手手牌猜测 |

### 4.4 难点4：用户体验

| 问题 | 解决方案 |
|------|----------|
| 识别结果反馈不及时 | 1. 本地轻量级模型即时反馈<br>2. 云端模型二次确认<br>3. 识别状态动画 |
| 误识别影响信任度 | 1. 显示识别置信度<br>2. 用户可手动修正<br>3. 识别历史可追溯 |

---

## 5. 部署架构

### 5.1 云端服务部署

```yaml
# docker-compose.yaml
version: '3.8'
services:
  api-gateway:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    
  image-api:
    image: ai-majiang/image-api:latest
    deploy:
      replicas: 3
    resources:
      limits:
        memory: 2G
    environment:
      - MODEL_PATH=/models/yolov8n.onnx
    
  strategy-api:
    image: ai-majiang/strategy-api:latest
    deploy:
      replicas: 5
    depends_on:
      - redis
    
  redis:
    image: redis:7-alpine
    
  mysql:
    image: mysql:8.0
```

### 5.2 移动端架构

```
lib/
├── main.dart
├── core/
│   ├── config/         # 配置管理
│   ├── constants/      # 常量定义
│   └── utils/          # 工具函数
├── data/
│   ├── models/         # 数据模型
│   ├── repositories/   # 数据仓库
│   └── services/       # API服务
├── domain/
│   ├── entities/       # 领域实体
│   └── usecases/       # 用例
├── presentation/
│   ├── pages/          # 页面
│   ├── widgets/        # 组件
│   └── providers/      # 状态管理
└── native/
    ├── onnx_inference/ # ONNX端侧推理
    └── camera/          # 相机控制
```

---

## 6. 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 端侧识别延迟 | < 200ms | 本地模型推理时间 |
| 云端识别延迟 | < 500ms | 含网络传输 |
| 牌效计算延迟 | < 100ms | 向听数+推荐 |
| 识别准确率 | > 95% | 标准光照下 |
| 端侧模型大小 | < 10MB | YOLOv8n INT8 |

---

## 7. 未来扩展

1. **多人联机观战** - WebSocket实时同步
2. **牌谱复盘** - 历史对局存储与分析
3. **AI对战模式** - 与AI对手练习
4. **段位赛匹配** - 天梯系统

---

*文档版本: v1.0*  
*创建时间: 2026-03-07*
