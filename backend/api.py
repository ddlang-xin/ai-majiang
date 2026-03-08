"""
长沙麻将后端API服务
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn

from mahjong import (
    ChangshaMahjong, StrategyCalculator, Tile, HandTiles,
    HuResult, parse_hand_string
)

app = FastAPI(title="长沙麻将API", version="1.0.0")

# 全局游戏实例
game = ChangshaMahjong(bird_count=2)


# ==================== 请求模型 ====================

class TileInput(BaseModel):
    """牌输入"""
    tiles: List[int]  # 牌值列表
    
    class Config:
        json_schema_extra = {
            "example": {
                "tiles": [0, 0, 0, 0, 9, 9, 9, 18, 18, 18, 1, 3, 5]
            }
        }


class HandStringInput(BaseModel):
    """手牌字符串输入"""
    hand: str  # 格式: "1t 2t 3t" 或 "112233"
    
    class Config:
        json_schema_extra = {
            "example": {
                "hand": "1t 1t 1t 2t 2t 3t 1s 1s 1s 2s 3s 4s 5s"
            }
        }


class DiscardInput(BaseModel):
    """打牌推荐输入"""
    hand_tiles: List[int]
    pool_tiles: Optional[List[int]] = None
    is_zhuang: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "hand_tiles": [0, 0, 0, 1, 1, 2, 3, 9, 9, 10, 18, 18, 20, 22],
                "pool_tiles": [1, 2, 3, 9, 10, 11],
                "is_zhuang": False
            }
        }


class HuInput(BaseModel):
    """胡牌判定输入"""
    tiles: List[int]
    is_big_hu: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "tiles": [0, 0, 0, 1, 1, 2, 3, 9, 9, 10, 18, 18, 20, 22],
                "is_big_hu": False
            }
        }


class BirdInput(BaseModel):
    """扎鸟计算输入"""
    birds: List[int]  # 鸟牌
    hu_seat: int      # 胡牌玩家座位 0-3
    is_zimo: bool     # 是否自摸
    
    class Config:
        json_schema_extra = {
            "example": {
                "birds": [0, 8, 10, 17],
                "hu_seat": 0,
                "is_zimo": True
            }
        }


class SettleInput(BaseModel):
    """结算输入"""
    hu_seat: int           # 胡牌玩家
    fans: int              # 番数
    is_zimo: bool          # 是否自摸
    is_zhuang: bool        # 是否庄家
    base_score: int = 2    # 基础分
    
    class Config:
        json_schema_extra = {
            "example": {
                "hu_seat": 0,
                "fans": 6,
                "is_zimo": True,
                "is_zhuang": False,
                "base_score": 2
            }
        }


class NewGameInput(BaseModel):
    """新游戏输入"""
    bird_count: int = 2
    
    class Config:
        json_schema_extra = {
            "example": {
                "bird_count": 2
            }
        }


# ==================== API 路由 ====================

@app.get("/")
def root():
    """根路径"""
    return {
        "name": "长沙麻将API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/game/new")
def new_game(input_data: NewGameInput):
    """创建新游戏"""
    global game
    game = ChangshaMahjong(bird_count=input_data.bird_count)
    game.shuffle()
    
    return {
        "status": "ok",
        "message": "新游戏已创建",
        "bird_count": input_data.bird_count,
        "remaining_tiles": len(game.wall_tiles)
    }


@app.get("/game/status")
def game_status():
    """游戏状态"""
    return {
        "remaining_tiles": len(game.wall_tiles),
        "discarded_count": len(game.discarded_tiles),
        "bird_count": len(game.birds),
        "birds": game.birds
    }


@app.post("/game/draw")
def draw_tile():
    """摸牌"""
    tile = game.draw_tile()
    if tile is None:
        raise HTTPException(status_code=400, detail="牌已摸完")
    
    return {
        "tile": tile,
        "tile_display": Tile(tile).display,
        "remaining": len(game.wall_tiles)
    }


@app.post("/game/discard")
def discard_tile(tiles: TileInput):
    """打牌"""
    if not tiles.tiles:
        raise HTTPException(status_code=400, detail="牌不能为空")
    
    tile = tiles.tiles[0]
    game.discard(tile)
    
    return {
        "tile": tile,
        "tile_display": Tile(tile).display,
        "discarded": game.discarded_tiles
    }


@app.post("/game/draw_birds")
def draw_birds():
    """扎鸟"""
    birds = game.draw_birds()
    
    return {
        "birds": birds,
        "bird_display": [Tile(b).display for b in birds]
    }


@app.post("/hu/check")
def check_hu(input_data: HuInput):
    """胡牌判定"""
    result = game.can_hu(input_data.tiles, input_data.is_big_hu)
    
    return {
        "is_hu": result.is_hu,
        "is_big_hu": result.is_big_hu,
        "hu_type": result.hu_type,
        "fans": result.fans,
        "patterns": result.hu_patterns
    }


@app.post("/hu/patterns")
def analyze_patterns(input_data: HuInput):
    """分析牌型"""
    result = game.can_hu(input_data.tiles, is_big_hu=True)
    
    # 详细分析
    hand = HandTiles(input_data.tiles)
    counts = hand.tile_counts
    
    analysis = {
        "is_hu": result.is_hu,
        "patterns": result.hu_patterns,
        "fans": result.fans,
        "details": {
            "is_pengpeng_hu": "碰碰胡" in result.hu_patterns,
            "is_qingyise": "清一色" in result.hu_patterns,
            "is_jiangjiang_hu": "将将胡" in result.hu_patterns,
            "is_qixiaodui": "七小对" in result.hu_patterns,
        },
        "suit_counts": {
            "tong": sum(counts[:9]),
            "tiao": sum(counts[9:18]),
            "wan": sum(counts[18:])
        }
    }
    
    return analysis


@app.post("/birds/calculate")
def calculate_birds(input_data: BirdInput):
    """计算扎鸟"""
    total, details = game.calculate_birds(
        input_data.birds, 
        input_data.hu_seat, 
        input_data.is_zimo
    )
    
    return {
        "total_birds": total,
        "bird_details": details,
        "multiplier": 1 + total
    }


@app.post("/settle")
def settle(input_data: SettleInput):
    """结算"""
    hu_info = {
        "seat": input_data.hu_seat,
        "fans": input_data.fans,
        "patterns": [],
        "is_big_hu": input_data.fans > 1
    }
    
    result = game.settle(
        hu_info,
        input_data.is_zimo,
        input_data.is_zhuang,
        input_data.base_score
    )
    
    return result


@app.post("/strategy/recommend")
def recommend_discard(input_data: DiscardInput):
    """打牌推荐"""
    strategy = StrategyCalculator(game)
    
    best_tile, score, details = strategy.recommend_discard(
        input_data.hand_tiles,
        input_data.pool_tiles
    )
    
    return {
        "recommend_tile": best_tile,
        "recommend_display": Tile(best_tile).display,
        "score": round(score, 2),
        "details": {
            "speed_score": round(details["speed"], 2),
            "defense_score": round(details["defense"], 2),
            "pattern_score": round(details["pattern"], 2),
            "jiang_score": round(details["jiang"], 2)
        },
        "weights": {
            "speed": StrategyCalculator.ALPHA,
            "defense": StrategyCalculator.BETA,
            "pattern": StrategyCalculator.GAMMA,
            "jiang": StrategyCalculator.DELTA
        }
    }


@app.post("/strategy/analyze")
def analyze_hand(input_data: TileInput):
    """分析手牌"""
    hand = HandTiles(input_data.tiles)
    counts = hand.tile_counts
    
    # 基本信息
    info = {
        "tile_count": hand.length,
        "suit_counts": {
            "tong": sum(counts[:9]),
            "tiao": sum(counts[9:18]),
            "wan": sum(counts[18:])
        }
    }
    
    # 潜力分析
    potential = {}
    
    # 七小对潜力
    pairs = sum(c // 2 for c in counts)
    potential["qixiaodui_pairs"] = pairs
    if pairs >= 5:
        potential["qixiaodui_potential"] = "高"
    elif pairs >= 3:
        potential["qixiaodui_potential"] = "中"
    else:
        potential["qixiaodui_potential"] = "低"
    
    # 清一色潜力
    suit_counts = hand.get_suit_counts()
    max_suit = max(suit_counts.values())
    potential["max_suit_count"] = max_suit
    if max_suit >= 8:
        potential["qingyise_potential"] = "高"
    elif max_suit >= 5:
        potential["qingyise_potential"] = "中"
    else:
        potential["qingyise_potential"] = "低"
    
    # 碰碰胡潜力
    kezi = sum(1 for c in counts if c >= 3)
    potential["kezi_count"] = kezi
    if kezi >= 3:
        potential["pengpeng_potential"] = "高"
    elif kezi >= 1:
        potential["pengpeng_potential"] = "中"
    else:
        potential["pengpeng_potential"] = "低"
    
    # 将将胡潜力
    jiang_258 = sum(counts[i] for i in range(27) if Tile(i).is_258)
    potential["jiang_258_count"] = jiang_258
    if jiang_258 >= 6:
        potential["jiangjiang_potential"] = "高"
    elif jiang_258 >= 3:
        potential["jiangjiang_potential"] = "中"
    else:
        potential["jiangjiang_potential"] = "低"
    
    # 检查听牌
    can_ting = False
    ting_tiles = []
    for draw in range(27):
        if counts[draw] < 4:
            test_hand = input_data.tiles + [draw]
            result = game.can_hu(test_hand, is_big_hu=True)
            if result.is_hu:
                can_ting = True
                ting_tiles.append(draw)
    
    info["can_ting"] = can_ting
    info["ting_tiles"] = ting_tiles
    info["ting_display"] = [Tile(t).display for t in ting_tiles]
    
    return {
        "basic": info,
        "potential": potential
    }


@app.post("/utils/parse")
def parse_hand(input_data: HandStringInput):
    """解析手牌字符串"""
    tiles = parse_hand_string(input_data.hand)
    
    return {
        "original": input_data.hand,
        "tiles": tiles,
        "display": [Tile(t).display for t in tiles],
        "count": len(tiles)
    }


@app.get("/utils/tile/{tile_id}")
def get_tile_info(tile_id: int):
    """获取牌信息"""
    try:
        tile = Tile(tile_id)
        return {
            "id": tile_id,
            "display": tile.display,
            "suit": tile.suit.name,
            "number": tile.number,
            "is_258": tile.is_258
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 主程序 ====================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
