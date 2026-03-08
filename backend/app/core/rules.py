"""
麻将规则引擎
实现牌型判断、和牌判定、胡牌检测
"""

from typing import List, Optional, Tuple
from collections import Counter
from app.core.tiles import (
    Tile, TileType, TileNumber, HonorTile, 
    Meld, MeldType, Hand, parse_tile, tile_to_string
)


class MahjongRuleEngine:
    """麻将规则引擎"""
    
    def __init__(self):
        # 所有牌型
        self.all_tiles: List[Tile] = []
        self._init_tiles()
    
    def _init_tiles(self):
        """初始化所有牌（每种4张）"""
        # 数牌 1-9，每个花色36张（9*4）
        for suit in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            for num in range(1, 10):
                for _ in range(4):
                    self.all_tiles.append(Tile(
                        tile_type=suit,
                        number=TileNumber(num)
                    ))
        
        # 字牌 7种，每种4张
        for honor in HonorTile:
            for _ in range(4):
                self.all_tiles.append(Tile(
                    tile_type=TileType.ZI,
                    honor=honor
                ))
    
    def can_hu(self, tiles: List[Tile]) -> bool:
        """判断是否能胡牌"""
        if len(tiles) != 14:
            return False
        
        # 去掉一张牌看是否能凑成4面子+1雀头
        for i in range(len(tiles)):
            remaining = tiles[:i] + tiles[i+1:]
            if self._is_complete_hand(remaining):
                return True
        return False
    
    def _is_complete_hand(self, tiles: List[Tile]) -> bool:
        """判断是否组成4面子+1雀头"""
        if len(tiles) != 13:
            return False
        
        # 统计每种牌的数量
        counter = Counter(tiles)
        tile_list = list(counter.elements())
        
        # 尝试找到雀头
        for tile, count in counter.items():
            if count >= 2:
                # 把这2张作为雀头
                remaining = []
                for t, c in counter.items():
                    if t == tile:
                        remaining.extend([t] * (c - 2))
                    else:
                        remaining.extend([t] * c)
                
                # 检查剩余牌能否组成3面子
                if self._can_form_melds(remaining):
                    return True
        return False
    
    def _can_form_melds(self, tiles: List[Tile]) -> bool:
        """检查牌能否组成3面子（刻子或顺子）"""
        if not tiles:
            return True
        if len(tiles) % 3 != 0:
            return False
        
        counter = Counter(tiles)
        
        # 优先处理字牌（只有刻子）
        for tile, count in list(counter.items()):
            if tile.is_honor:
                if count >= 3:
                    # 组成刻子
                    counter[tile] -= 3
                    if self._can_form_melds(list(counter.elements())):
                        return True
                    counter[tile] += 3
                return False
        
        # 处理数牌
        # 按花色分组
        suits = {}
        for tile in tiles:
            key = (tile.tile_type,)
            if key not in suits:
                suits[key] = []
            suits[key].append(tile.number.value)
        
        for suit_tiles in suits.values():
            suit_counter = Counter(suit_tiles)
            if self._can_form_num_melds(suit_counter):
                return True
        
        return False
    
    def _can_form_num_melds(self, counter: Counter) -> bool:
        """检查数牌能否组成顺子"""
        if not counter:
            return True
        
        # 取最小的牌
        num = min(counter.keys())
        count = counter[num]
        
        if count == 0:
            return self._can_form_num_melds(Counter({k: v for k, v in counter.items() if k > num}))
        
        # 尝试组成顺子
        new_counter = Counter(counter)
        new_counter[num] -= count
        
        # 检查num, num+1, num+2是否能组成顺子
        for offset in range(count):
            for i in range(3):
                if num + i not in counter or counter[num + i] < count:
                    return False
                new_counter[num + i] -= count
        
        # 递归检查剩余牌
        remaining = []
        for k, v in new_counter.items():
            remaining.extend([k] * v)
        
        return self._can_form_num_melds(Counter(remaining))
    
    def get_ting_cards(self, tiles: List[Tile]) -> List[Tile]:
        """获取听牌后能胡的牌"""
        if len(tiles) != 13:
            return []
        
        ting_cards = []
        for i in range(len(tiles)):
            # 尝试加入每种牌
            for tile in self.all_tiles:
                test_tiles = tiles[:i] + [tile] + tiles[i+1:]
                # 去掉一张看是否能胡
                for j in range(len(test_tiles)):
                    remaining = test_tiles[:j] + test_tiles[j+1:]
                    if self._is_complete_hand(remaining):
                        if tile not in ting_cards:
                            ting_cards.append(tile)
                        break
        return ting_cards
    
    def is_ting(self, tiles: List[Tile]) -> bool:
        """判断是否听牌"""
        return len(self.get_ting_cards(tiles)) > 0
    
    def get_ting_info(self, tiles: List[Tile]) -> dict:
        """获取听牌信息"""
        if len(tiles) != 13:
            return {"is_ting": False, "ting_cards": [], "han": 0}
        
        ting_cards = self.get_ting_cards(tiles)
        return {
            "is_ting": len(ting_cards) > 0,
            "ting_cards": [tile_to_string(t) for t in ting_cards],
            "ting_count": len(ting_cards),
            "han": self._estimate_han(tiles)
        }
    
    def _estimate_han(self, tiles: List[Tile]) -> int:
        """估算番数（简化版）"""
        # 简单估算：幺九牌和字牌多则番数高
        terminal_honor_count = sum(1 for t in tiles if t.is_terminal)
        return min(6, terminal_honor_count // 2)


# 测试
if __name__ == "__main__":
    engine = MahjongRuleEngine()
    
    # 测试和牌判定
    # 123 456 789 111 22 (国士无双十三面)
    test_tiles = [
        parse_tile("1W"), parse_tile("2W"), parse_tile("3W"),
        parse_tile("4T"), parse_tile("5T"), parse_tile("6T"),
        parse_tile("7S"), parse_tile("8S"), parse_tile("9S"),
        parse_tile("1W"), parse_tile("1W"), parse_tile("1W"),
        parse_tile("2W"), parse_tile("2W")
    ]
    
    print(f"和牌判定: {engine.can_hu(test_tiles)}")
    
    # 测试听牌
    # 123 456 789 111 2 (听2万)
    ting_tiles = [
        parse_tile("1W"), parse_tile("2W"), parse_tile("3W"),
        parse_tile("4T"), parse_tile("5T"), parse_tile("6T"),
        parse_tile("7S"), parse_tile("8S"), parse_tile("9S"),
        parse_tile("1W"), parse_tile("1W"), parse_tile("1W"),
        parse_tile("2W")
    ]
    
    print(f"听牌判定: {engine.is_ting(ting_tiles)}")
    print(f"听牌信息: {engine.get_ting_info(ting_tiles)}")
