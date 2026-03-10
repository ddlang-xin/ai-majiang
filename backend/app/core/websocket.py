"""
WebSocket实时通信模块
支持麻将游戏实时状态推送
"""

import json
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
from fastapi import WebSocket


class MessageType(str, Enum):
    """消息类型"""
    # 游戏状态
    GAME_STATE = "game_state"
    PLAYER_ACTION = "player_action"
    TILE_DRAWN = "tile_drawn"
    TILE_DISCARDED = "tile_discarded"
    TILE_CHOW = "tile_chow"
    TILE_PUNG = "tile_pung"
    TILE_KONG = "tile_kong"
    TILE_HU = "tile_hu"
    
    # 分析结果
    ANALYSIS_RESULT = "analysis_result"
    EFFICIENCY_UPDATE = "efficiency_update"
    TING_INFO = "ting_info"
    
    # 系统
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class GamePhase(str, Enum):
    """游戏阶段"""
    WAITING = "waiting"      # 等待开始
    DICE = "dice"            # 掷骰子
    DEAL = "deal"            # 发牌
    PLAYING = "playing"      # 进行中
    DRAW = "draw"            # 摸牌
    DISCARD = "discard"      # 打牌
    CHOW = "chow"            # 吃
    PUNG = "pung"            # 碰
    KONG = "kong"            # 杠
    HU = "hu"                # 胡
    SETTLE = "settle"        # 结算
    END = "end"              # 结束


@dataclass
class Player:
    """玩家"""
    seat: int                # 座位 (0-3)
    name: str                # 名称
    tiles: List[str] = field(default_factory=list)  # 手牌
    melds: List[dict] = field(default_factory=list)  # 副露
    discarded: List[str] = field(default_factory=list)  # 打过的牌
    is_ting: bool = False    # 是否听牌
    is_hu: bool = False      # 是否胡牌
    score: int = 0           # 分数
    
    def to_dict(self) -> dict:
        return {
            "seat": self.seat,
            "name": self.name,
            "tiles": self.tiles,
            "melds": self.melds,
            "discarded": self.discarded,
            "is_ting": self.is_ting,
            "is_hu": self.is_hu,
            "score": self.score
        }


@dataclass
class GameState:
    """游戏状态"""
    game_id: str
    phase: GamePhase = GamePhase.WAITING
    dice: List[int] = field(default_factory=list)  # 骰子点数
    dealer: int = 0              # 庄家座位
    current_player: int = 0     # 当前玩家座位
    current_tile: Optional[str] = None  # 当前摸到的牌
    remaining_tiles: int = 136   # 剩余牌数
    last_action: Optional[dict] = None  # 最后动作
    players: List[Player] = field(default_factory=list)
    bird_tile: Optional[str] = None  # 鸟牌
    
    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "phase": self.phase.value,
            "dice": self.dice,
            "dealer": self.dealer,
            "current_player": self.current_player,
            "current_tile": self.current_tile,
            "remaining_tiles": self.remaining_tiles,
            "last_action": self.last_action,
            "players": [p.to_dict() for p in self.players],
            "bird_tile": self.bird_tile,
            "timestamp": datetime.now().isoformat()
        }


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # game_id -> {seat -> websocket}
        self.active_connections: Dict[str, Dict[int, asyncio.WebSocketServerProtocol]] = {}
        # websocket -> game_id
        self.ws_to_game: Dict[asyncio.WebSocketServerProtocol, str] = {}
    
    async def connect(self, game_id: str, seat: int, websocket: WebSocket):
        """玩家连接"""
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
        
        self.active_connections[game_id][seat] = websocket
        self.ws_to_game[websocket] = game_id
    
    def disconnect(self, game_id: str, seat: int):
        """玩家断开"""
        if game_id in self.active_connections:
            ws = self.active_connections[game_id].pop(seat, None)
            if ws:
                self.ws_to_game.pop(ws, None)
    
    async def send_to_player(self, game_id: str, seat: int, message: dict):
        """发送给指定玩家"""
        if game_id in self.active_connections:
            ws = self.active_connections[game_id].get(seat)
            if ws:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass  # 连接已关闭
    
    async def broadcast(self, game_id: str, message: dict, exclude_seat: int = None):
        """广播给所有玩家"""
        if game_id in self.active_connections:
            for seat, ws in self.active_connections[game_id].items():
                if seat != exclude_seat:
                    try:
                        await ws.send_json(message)
                    except Exception:
                        pass
    
    async def broadcast_all(self, game_id: str, message: dict):
        """广播给所有玩家（包括发送者）"""
        await self.broadcast(game_id, message, exclude_seat=None)


# 全局连接管理器
manager = ConnectionManager()


def create_message(msg_type: MessageType, data: dict = None) -> dict:
    """创建WebSocket消息"""
    return {
        "type": msg_type.value,
        "data": data or {},
        "timestamp": datetime.now().isoformat()
    }


def create_error_message(error: str, code: int = 400) -> dict:
    """创建错误消息"""
    return create_message(MessageType.ERROR, {
        "error": error,
        "code": code
    })


def create_game_state_message(state: GameState) -> dict:
    """创建游戏状态消息"""
    return create_message(MessageType.GAME_STATE, state.to_dict())


def create_analysis_message(result: dict) -> dict:
    """创建分析结果消息"""
    return create_message(MessageType.ANALYSIS_RESULT, result)


def create_ting_message(ting_info: dict) -> dict:
    """创建听牌信息消息"""
    return create_message(MessageType.TING_INFO, ting_info)


def create_efficiency_message(efficiency: dict) -> dict:
    """创建牌效消息"""
    return create_message(MessageType.EFFICIENCY_UPDATE, efficiency)


# 异步任务管理
class GameManager:
    """游戏管理器"""
    
    def __init__(self):
        self.games: Dict[str, GameState] = {}
        self.analysis_cache: Dict[str, dict] = {}  # game_id -> analysis
    
    def create_game(self, game_id: str, player_names: List[str]) -> GameState:
        """创建游戏"""
        state = GameState(
            game_id=game_id,
            phase=GamePhase.WAITING,
            players=[
                Player(seat=i, name=player_names[i] if i < len(player_names) else f"玩家{i+1}")
                for i in range(4)
            ]
        )
        self.games[game_id] = state
        return state
    
    def get_game(self, game_id: str) -> Optional[GameState]:
        """获取游戏"""
        return self.games.get(game_id)
    
    def update_player_tiles(self, game_id: str, seat: int, tiles: List[str]):
        """更新玩家手牌"""
        game = self.games.get(game_id)
        if game and seat < len(game.players):
            game.players[seat].tiles = tiles
    
    def update_player_discarded(self, game_id: str, seat: int, tile: str):
        """更新玩家打牌"""
        game = self.games.get(game_id)
        if game and seat < len(game.players):
            game.players[seat].discarded.append(tile)
    
    def add_meld(self, game_id: str, seat: int, meld: dict):
        """添加副露"""
        game = self.games.get(game_id)
        if game and seat < len(game.players):
            game.players[seat].melds.append(meld)
    
    def set_player_ting(self, game_id: str, seat: int, is_ting: bool):
        """设置玩家听牌状态"""
        game = self.games.get(game_id)
        if game and seat < len(game.players):
            game.players[seat].is_ting = is_ting
    
    def set_player_hu(self, game_id: str, seat: int, is_hu: bool):
        """设置玩家胡牌状态"""
        game = self.games.get(game_id)
        if game and seat < len(game.players):
            game.players[seat].is_hu = is_hu


# 全局游戏管理器
game_manager = GameManager()
