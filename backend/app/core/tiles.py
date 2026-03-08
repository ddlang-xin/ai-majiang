"""
麻将牌定义模块
支持标准麻将牌型：万、筒、索、字牌
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class TileType(str, Enum):
    """牌类型"""
    WAN = "wan"      # 万子
    TONG = "tong"    # 筒子
    TIAO = "tiao"    # 索子
    ZI = "zi"        # 字牌


class TileNumber(int, Enum):
    """牌数字 1-9"""
    NUM_1 = 1
    NUM_2 = 2
    NUM_3 = 3
    NUM_4 = 4
    NUM_5 = 5
    NUM_6 = 6
    NUM_7 = 7
    NUM_8 = 8
    NUM_9 = 9


class HonorTile(str, Enum):
    """字牌"""
    DONG = "dong"    # 东
    NAN = "nan"      # 南
    XI = "xi"        # 西
    BEI = "bei"      # 北
    ZHONG = "zhong"  # 中
    FA = "fa"        # 发
    BAI = "bai"      # 白


class Tile(BaseModel):
    """麻将牌"""
    tile_type: TileType
    number: Optional[TileNumber] = None
    honor: Optional[HonorTile] = None
    
    def __str__(self):
        if self.tile_type == TileType.ZI:
            return f"{self.honor.value}"
        return f"{self.number.value}{self.tile_type.value}"
    
    def __hash__(self):
        return hash((self.tile_type, self.number, self.honor))
    
    def __eq__(self, other):
        if not isinstance(other, Tile):
            return False
        return (self.tile_type == other.tile_type and 
                self.number == other.number and 
                self.honor == other.honor)
    
    @property
    def is_honor(self) -> bool:
        return self.tile_type == TileType.ZI
    
    @property
    def is_terminal(self) -> bool:
        """是否幺九牌（1、9或字牌）"""
        if self.is_honor:
            return True
        return self.number in (TileNumber.NUM_1, TileNumber.NUM_9)


class MeldType(str, Enum):
    """面子类型"""
    PUNG = "pung"      # 刻子
    CHOW = "chow"      # 顺子
    KONG = "kong"      # 杠子
    PAIR = "pair"      # 雀头


class Meld(BaseModel):
    """面子（吃/碰/杠/听牌型）"""
    meld_type: MeldType
    tiles: List[Tile]
    
    def __str__(self):
        return "".join(str(t) for t in self.tiles)


class Hand(BaseModel):
    """手牌"""
    tiles: List[Tile]
    melds: List[Meld] = []  # 已吃的面子
    discarded: List[Tile] = []  # 打过的牌
    
    def add_tile(self, tile: Tile):
        self.tiles.append(tile)
    
    def remove_tile(self, tile: Tile):
        self.tiles.remove(tile)
    
    @property
    def tile_count(self) -> int:
        return len(self.tiles)
    
    @property
    def is_complete(self) -> bool:
        """是否凑齐14张牌"""
        return self.tile_count == 14


# 牌型解析辅助函数
def parse_tile(tile_str: str) -> Tile:
    """解析牌字符串，如 "1W" -> 万子1"""
    if not tile_str:
        raise ValueError("Empty tile string")
    
    # 字牌
    honors = {
        "D": "dong", "N": "nan", "X": "xi", "B": "bei",
        "Z": "zhong", "F": "fa", "Bai": "bai"
    }
    
    if tile_str[0].upper() in honors:
        return Tile(
            tile_type=TileType.ZI,
            honor=HonorTile(honors[tile_str[0].upper()])
        )
    
    # 数牌
    num = int(tile_str[0])
    suit = tile_str[1].upper()
    
    if suit == 'W':
        return Tile(tile_type=TileType.WAN, number=TileNumber(num))
    elif suit == 'T' or suit == 'B':
        return Tile(tile_type=TileType.TONG, number=TileNumber(num))
    elif suit == 'S':
        return Tile(tile_type=TileType.TIAO, number=TileNumber(num))
    
    raise ValueError(f"Invalid tile: {tile_str}")


def tile_to_string(tile: Tile) -> str:
    """牌转字符串"""
    if tile.is_honor:
        honor_map = {
            HonorTile.DONG: "D",
            HonorTile.NAN: "N", 
            HonorTile.XI: "X",
            HonorTile.BEI: "B",
            HonorTile.ZHONG: "Z",
            HonorTile.FA: "F",
            HonorTile.BAI: "Bai"
        }
        return honor_map[tile.honor]
    
    suit_map = {
        TileType.WAN: "W",
        TileType.TONG: "T",
        TileType.TIAO: "S"
    }
    return f"{tile.number.value}{suit_map[tile.tile_type]}"


# 测试
if __name__ == "__main__":
    t1 = parse_tile("1W")
    print(t1)
    t2 = parse_tile("9T")
    print(t2)
    t3 = parse_tile("D")
    print(t3)
