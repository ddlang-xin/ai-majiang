"""
API请求/响应模型
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """分析请求"""
    tiles: List[str] = Field(..., description="手牌列表，如['1W','2W','3W']")
    discarded: Optional[List[str]] = Field(default=None, description="打过的牌")
    field_wind: Optional[str] = Field(default="E", description="场风")
    seat_wind: Optional[str] = Field(default="E", description="自风")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tiles": ["1W", "2W", "3W", "4T", "5T", "6T", "7S", "8S", "9S", "1W", "1W", "2W", "3W"],
                "discarded": ["1T", "2T", "3S"],
                "field_wind": "E",
                "seat_wind": "E"
            }
        }


class DiscardAdvice(BaseModel):
    """打牌建议"""
    tile: str
    value: float


class MeldInfo(BaseModel):
    """搭子信息"""
    type: str
    tile: str
    count: Optional[int] = None
    remaining: Optional[int] = None
    priority: str


class AnalyzeResponse(BaseModel):
    """分析响应"""
    success: bool
    shanten: int = Field(..., description="向听数")
    draw_count: int = Field(..., description="进张数")
    tenpai_count: int = Field(..., description="听牌进张数")
    tenpai_rate: float = Field(..., description="听牌率")
    is_ting: bool = Field(..., description="是否听牌")
    melds: List[MeldInfo] = Field(default_factory=list, description="搭子分析")
    discard_advice: List[DiscardAdvice] = Field(default_factory=list, description="打牌建议")
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "shanten": 1,
                "draw_count": 12,
                "tenpai_count": 4,
                "tenpai_rate": 0.33,
                "is_ting": False,
                "melds": [
                    {"type": "pair", "tile": "1W", "count": 2, "priority": "high"},
                    {"type": "run_wait", "tile": "4-5", "priority": "low"}
                ],
                "discard_advice": [
                    {"tile": "7S", "value": 15.0},
                    {"tile": "8S", "value": 20.0}
                ]
            }
        }


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
