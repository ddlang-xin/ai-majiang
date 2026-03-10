"""
WebSocket和图像识别API路由
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.core.websocket import (
    manager, game_manager,
    create_message, create_error_message,
    create_game_state_message, create_analysis_message,
    MessageType, GamePhase, GameState
)
from app.core.image_recognition import (
    RecognitionRequest, RecognitionResponse,
    ImageFormat, DetectionModel,
    recognize_tiles_async
)
from app.core.tiles import parse_tile, tile_to_string
from app.core.rules import MahjongRuleEngine
from app.core.efficiency import TileEfficiency

router = APIRouter()

# 全局实例
rule_engine = MahjongRuleEngine(game_type="changsha")
efficiency_calc = TileEfficiency()


# ============== WebSocket 路由 ==============

@router.websocket("/ws/game/{game_id}/{seat}")
async def websocket_game(websocket: WebSocket, game_id: str, seat: int):
    """
    WebSocket游戏连接
    :param game_id: 游戏ID
    :param seat: 玩家座位 (0-3)
    """
    await websocket.accept()
    
    # 注册连接
    await manager.connect(game_id, seat, websocket)
    
    # 获取或创建游戏
    game = game_manager.get_game(game_id)
    if not game:
        # 创建默认游戏
        game = game_manager.create_game(
            game_id, 
            [f"玩家{i+1}" for i in range(4)]
        )
    
    # 发送初始游戏状态
    await websocket.send_json(create_game_state_message(game))
    
    # 发送欢迎消息
    await websocket.send_json(create_message(
        MessageType.PLAYER_ACTION,
        {"action": "connected", "seat": seat, "message": f"已加入游戏 {game_id}"}
    ))
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            await handle_websocket_message(game_id, seat, message)
            
    except WebSocketDisconnect:
        manager.disconnect(game_id, seat)
        await manager.broadcast(
            game_id,
            create_message(
                MessageType.PLAYER_ACTION,
                {"action": "disconnected", "seat": seat}
            )
        )
    except Exception as e:
        await websocket.send_json(create_error_message(str(e)))


async def handle_websocket_message(game_id: str, seat: int, message: dict):
    """处理WebSocket消息"""
    msg_type = message.get("type")
    data = message.get("data", {})
    
    game = game_manager.get_game(game_id)
    if not game:
        return
    
    if msg_type == "create_game":
        # 创建新游戏
        player_names = data.get("player_names", [f"玩家{i+1}" for i in range(4)])
        game = game_manager.create_game(game_id, player_names)
        await manager.broadcast_all(game_id, create_game_state_message(game))
    
    elif msg_type == "start_game":
        # 开始游戏（发牌）
        game.phase = GamePhase.PLAYING
        # TODO: 实现发牌逻辑
        await manager.broadcast_all(game_id, create_game_state_message(game))
    
    elif msg_type == "discard":
        # 打牌
        tile = data.get("tile")
        if tile:
            game_manager.update_player_discarded(game_id, seat, tile)
            game.last_action = {"type": "discard", "player": seat, "tile": tile}
            await manager.broadcast_all(
                game_id, 
                create_message(MessageType.TILE_DISCARDED, {
                    "player": seat,
                    "tile": tile
                })
            )
    
    elif msg_type == "draw":
        # 摸牌
        # TODO: 实现摸牌逻辑
        await manager.broadcast_all(
            game_id,
            create_message(MessageType.TILE_DRAWN, {"player": seat})
        )
    
    elif msg_type == "hu":
        # 胡牌
        game_manager.set_player_hu(game_id, seat, True)
        await manager.broadcast_all(
            game_id,
            create_message(MessageType.TILE_HU, {"player": seat})
        )
    
    elif msg_type == "analyze":
        # 分析手牌
        tiles = data.get("tiles", [])
        try:
            parsed_tiles = [parse_tile(t) for t in tiles]
            efficiency = efficiency_calc.calculate_efficiency(parsed_tiles)
            ting_info = rule_engine.get_ting_info(parsed_tiles)
            
            await manager.send_to_player(
                game_id, seat,
                create_analysis_message({
                    "efficiency": efficiency,
                    "ting_info": ting_info
                })
            )
        except Exception as e:
            await manager.send_to_player(
                game_id, seat,
                create_error_message(str(e))
            )
    
    elif msg_type == "get_state":
        # 获取游戏状态
        await manager.send_to_player(
            game_id, seat,
            create_game_state_message(game)
        )
    
    elif msg_type == "heartbeat":
        # 心跳
        await manager.send_to_player(
            game_id, seat,
            create_message(MessageType.HEARTBEAT, {"time": datetime.now().isoformat()})
        )
    
    else:
        await manager.send_to_player(
            game_id, seat,
            create_error_message(f"未知消息类型: {msg_type}")
        )


# ============== 图像识别API ==============

@router.post("/recognize", response_model=RecognitionResponse)
async def recognize_image(request: RecognitionRequest):
    """
    识别图像中的麻将牌
    
    - **image**: 图像数据（base64/URL/文件路径）
    - **format**: 图像格式
    - **model**: 使用的模型
    - **confidence**: 置信度阈值
    - **detect_hand**: 是否识别手牌
    - **detect_discarded**: 是否识别打出的牌
    - **detect_drawn**: 是否识别摸到的牌
    """
    try:
        result = await recognize_tiles_async(
            image_data=request.image,
            format=request.format,
            model=request.model
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")


@router.post("/recognize-base64")
async def recognize_from_base64(image_base64: str, detect_hand: bool = True):
    """
    从Base64识别麻将牌（简化接口）
    """
    try:
        result = await recognize_tiles_async(
            image_data=image_base64,
            format=ImageFormat.BASE64
        )
        
        # 提取手牌
        hand_tiles = [t.tile for t in result.hand_tiles] if detect_hand else []
        
        return {
            "success": result.success,
            "hand_tiles": hand_tiles,
            "all_tiles": [t.tile for t in result.all_tiles],
            "processing_time": result.processing_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")


@router.post("/recognize-url")
async def recognize_from_url(image_url: str):
    """
    从URL识别麻将牌
    """
    try:
        result = await recognize_tiles_async(
            image_data=image_url,
            format=ImageFormat.URL
        )
        
        return {
            "success": result.success,
            "hand_tiles": [t.tile for t in result.hand_tiles],
            "discarded_tiles": [t.tile for t in result.discarded_tiles],
            "all_tiles": [t.tile for t in result.all_tiles],
            "processing_time": result.processing_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")


# ============== 实时分析API ==============

@router.post("/realtime/analyze")
async def realtime_analyze(tiles: List[str], discarded: List[str] = None):
    """
    实时分析（用于WebSocket推送）
    """
    try:
        if len(tiles) != 13:
            raise HTTPException(status_code=400, detail="需要13张手牌")
        
        parsed_tiles = [parse_tile(t) for t in tiles]
        parsed_discarded = [parse_tile(t) for t in discarded] if discarded else []
        
        # 牌效分析
        efficiency = efficiency_calc.calculate_efficiency(parsed_tiles, parsed_discarded)
        
        # 听牌信息
        ting_info = rule_engine.get_ting_info(parsed_tiles)
        
        return {
            "success": True,
            "efficiency": efficiency,
            "ting_info": ting_info
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"牌解析错误: {str(e)}")


@router.post("/realtime/ting-info")
async def realtime_ting_info(tiles: List[str]):
    """
    实时听牌信息（用于WebSocket推送）
    """
    try:
        parsed_tiles = [parse_tile(t) for t in tiles]
        ting_info = rule_engine.get_ting_info(parsed_tiles)
        
        return {
            "success": True,
            **ting_info
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"牌解析错误: {str(e)}")


# ============== 游戏状态API ==============

@router.get("/game/{game_id}/state")
async def get_game_state(game_id: str):
    """获取游戏状态"""
    game = game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    return game.to_dict()


@router.post("/game/{game_id}/action")
async def game_action(game_id: str, action: str, seat: int, data: dict = None):
    """执行游戏动作"""
    game = game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    
    data = data or {}
    
    if action == "discard":
        tile = data.get("tile")
        if tile:
            game_manager.update_player_discarded(game_id, seat, tile)
            game.last_action = {"type": "discard", "player": seat, "tile": tile}
            
            # 广播给所有玩家
            await manager.broadcast_all(
                game_id,
                create_message(MessageType.TILE_DISCARDED, {
                    "player": seat,
                    "tile": tile
                })
            )
    
    elif action == "hu":
        game_manager.set_player_hu(game_id, seat, True)
        game.phase = GamePhase.SETTLE
        await manager.broadcast_all(
            game_id,
            create_message(MessageType.TILE_HU, {"player": seat})
        )
    
    return {"success": True, "game_state": game.to_dict()}
