# 长沙麻将后端

## 项目结构

```
backend/
├── mahjong.py      # 核心算法模块
├── api.py          # FastAPI 服务
├── requirements.txt
└── README.md
```

## 核心功能

### 1. 牌定义 (mahjong.py)
- 108张牌：筒0-8, 条9-17, 万18-26
- `Tile` 类：花色、点数、258判断
- `HandTiles` 类：手牌管理

### 2. 胡牌判定
- 小胡：4面子 + 258将
- 大胡：无258限制
- 支持番型检测：碰碰胡、清一色、将将胡、七小对

### 3. 番型计算
- 倍数法：`大胡N个 = 6 × 2^(N-1)`
- 封顶：14番

### 4. 扎鸟算法
- 鸟牌点数对应方位：1/5/9→庄家, 2/6→下家, 3/7→对家, 4/8→上家
- 金额 = 基础分 × 番数 × (1 + 中鸟数)

### 5. 打牌推荐
- 综合评分 = α×速度分 + β×防守分 + γ×番型分 + δ×将牌分
- α=0.35, β=0.30, γ=0.25, δ=0.10

### 6. 结算
- 自摸：三家付款
- 点炮：点炮方付款

## 启动服务

```bash
pip install -r requirements.txt
python api.py
```

API文档：http://localhost:8000/docs

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/game/new` | POST | 创建新游戏 |
| `/game/status` | GET | 游戏状态 |
| `/game/draw` | POST | 摸牌 |
| `/game/discard` | POST | 打牌 |
| `/game/draw_birds` | POST | 扎鸟 |
| `/hu/check` | POST | 胡牌判定 |
| `/hu/patterns` | POST | 牌型分析 |
| `/birds/calculate` | POST | 扎鸟计算 |
| `/settle` | POST | 结算 |
| `/strategy/recommend` | POST | 打牌推荐 |
| `/strategy/analyze` | POST | 手牌分析 |
| `/utils/parse` | POST | 解析手牌字符串 |

## 测试

```bash
python mahjong.py
```

## 牌值映射

| 牌 | 值 | 牌 | 值 | 牌 | 值 |
|----|----|----|----|----|----|
| 筒1 | 0 | 条1 | 9 | 万1 | 18 |
| 筒2 | 1 | 条2 | 10 | 万2 | 19 |
| ... | ... | ... | ... | ... | ... |
| 筒9 | 8 | 条9 | 17 | 万9 | 26 |
