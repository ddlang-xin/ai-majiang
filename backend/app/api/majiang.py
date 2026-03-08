"""
麻将分析API
"""

from typing import List
from fastapi import APIRouter, HTTPException
from app.schemas.request import (
    AnalyzeRequest, AnalyzeResponse, 
    HealthResponse, ErrorResponse,
    DiscardAdvice, MeldInfo
)
from app.core.tiles import parse_tile, tile_to_string
from app.core.rules import MahjongRuleEngine
from app.core.efficiency import TileEfficiency

router = APIRouter()

# 全局实例
rule_engine = MahjongRuleEngine()
efficiency_calc = TileEfficiency()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(status="ok", version="1.0.0")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_hand(request: AnalyzeRequest):
    """
    分析手牌
    
    - **tiles**: 手牌列表（13张）
    - **discarded**: 打过的牌（可选）
    - **field_wind**: 场风（可选）
    - **seat_wind**: 自风（可选）
    """
    try:
        # 验证手牌数量
        if len(request.tiles) != 13:
            raise HTTPException(
                status_code=400,
                detail=f"手牌数量错误: 需要13张，当前{len(request.tiles)}张"
            )
        
        # 解析手牌
        tiles = []
        for tile_str in request.tiles:
            tiles.append(parse_tile(tile_str))
        
        # 解析打过的牌
        discarded = []
        if request.discarded:
            for tile_str in request.discarded:
                discarded.append(parse_tile(tile_str))
        
        # 计算牌效
        efficiency = efficiency_calc.calculate_efficiency(tiles, discarded)
        
        if "error" in efficiency:
            raise HTTPException(status_code=400, detail=efficiency["error"])
        
        # 检查是否听牌
        is_ting = rule_engine.is_ting(tiles)
        
        # 转换搭子信息
        melds = []
        for meld in efficiency.get("melds", []):
            melds.append(MeldInfo(**meld))
        
        # 转换打牌建议
        discard_advice = []
        for advice in efficiency.get("discard_advice", []):
            discard_advice.append(DiscardAdvice(**advice))
        
        return AnalyzeResponse(
            success=True,
            shanten=efficiency["shanten"],
            draw_count=efficiency["draw_count"],
            tenpai_count=efficiency["tenpai_count"],
            tenpai_rate=efficiency["tenpai_rate"],
            is_ting=is_ting,
            melds=melds,
            discard_advice=discard_advice
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"牌解析错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.post("/can-hu", response_model=dict)
async def check_hu(tiles: List[str]):
    """
    检查是否能胡牌
    
    - **tiles**: 手牌列表（14张）
    """
    try:
        if len(tiles) != 14:
            raise HTTPException(
                status_code=400,
                detail=f"手牌数量错误: 需要14张，当前{len(tiles)}张"
            )
        
        parsed_tiles = [parse_tile(t) for t in tiles]
        can_hu = rule_engine.can_hu(parsed_tiles)
        
        return {
            "can_hu": can_hu,
            "tiles": tiles
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"牌解析错误: {str(e)}")


@router.post("/ting-info", response_model=dict)
async def get_ting_info(tiles: List[str]):
    """
    获取听牌信息
    
    - **tiles**: 手牌列表（13张）
    """
    try:
        if len(tiles) != 13:
            raise HTTPException(
                status_code=400,
                detail=f"手牌数量错误: 需要13张，当前{len(tiles)}张"
            )
        
        parsed_tiles = [parse_tile(t) for t in tiles]
        ting_info = rule_engine.get_ting_info(parsed_tiles)
        
        return ting_info
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"牌解析错误: {str(e)}")


@router.post("/best-discard")
async def get_best_discard(request: AnalyzeRequest):
    """
    获取最佳打牌建议
    
    - **tiles**: 手牌列表（13张）
    - **discarded**: 打过的牌（可选）
    """
    try:
        # 解析手牌
        tiles = [parse_tile(t) for t in request.tiles]
        discarded = [parse_tile(t) for t in request.discarded] if request.discarded else []
        
        # 计算牌效
        efficiency = efficiency_calc.calculate_efficiency(tiles, discarded)
        
        if efficiency.get("discard_advice"):
            best = efficiency["discard_advice"][0]
            return {
                "best_discard": best["tile"],
                "value": best["value"],
                "all_advices": efficiency["discard_advice"]
            }
        
        return {"error": "无法给出建议"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"牌解析错误: {str(e)}")
