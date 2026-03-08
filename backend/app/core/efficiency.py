"""
牌效计算模块
计算打牌后的进张数、听牌效率等
"""

from typing import List, Dict, Tuple, Optional
from collections import Counter
from app.core.tiles import (
    Tile, TileType, TileNumber, HonorTile, 
    parse_tile, tile_to_string
)
from app.core.rules import MahjongRuleEngine


class TileEfficiency:
    """牌效计算器"""
    
    def __init__(self):
        self.rule_engine = MahjongRuleEngine()
        # 所有进张牌（可以摸到的牌）
        self._all_draws: List[Tile] = []
        self._init_draws()
    
    def _init_draws(self):
        """初始化所有可能的进张牌"""
        for suit in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            for num in range(1, 10):
                self._all_draws.append(Tile(
                    tile_type=suit,
                    number=TileNumber(num)
                ))
        for honor in HonorTile:
            self._all_draws.append(Tile(
                tile_type=TileType.ZI,
                honor=honor
            ))
    
    def calculate_efficiency(self, tiles: List[Tile], discarded: List[Tile] = None) -> Dict:
        """
        计算牌效
        返回：进张数、听牌效率、改进建议
        """
        if len(tiles) != 13:
            return {"error": "需要13张手牌"}
        
        discarded = discarded or []
        
        # 统计已经打过的牌
        discarded_counter = Counter(discarded)
        
        # 计算每张牌的剩余数量
        remaining_tiles = self._get_remaining_tiles(discarded_counter)
        
        # 计算各种指标
        shanten = self._calc_shanten(tiles)
        draw_count = self._count_draws(tiles, remaining_tiles)
        tenpai_count = self._count_tenpai_draws(tiles, remaining_tiles)
        
        # 分析搭子
        melds_analysis = self._analyze_melds(tiles)
        
        return {
            "shanten": shanten,              # 向听数
            "draw_count": draw_count,        # 进张数
            "tenpai_count": tenpai_count,    # 听牌进张数
            "tenpai_rate": round(tenpai_count / max(draw_count, 1), 2),  # 听牌率
            "melds": melds_analysis,         # 搭子分析
            "discard_advice": self._get_discard_advice(tiles, remaining_tiles, melds_analysis)
        }
    
    def _get_remaining_tiles(self, discarded: Counter) -> Counter:
        """计算剩余牌数（每种4张减去已打出的）"""
        remaining = Counter()
        
        for suit in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            for num in range(1, 10):
                tile = Tile(tile_type=suit, number=TileNumber(num))
                remaining[tile] = 4 - discarded.get(tile, 0)
        
        for honor in HonorTile:
            tile = Tile(tile_type=TileType.ZI, honor=honor)
            remaining[tile] = 4 - discarded.get(tile, 0)
        
        return remaining
    
    def _calc_shanten(self, tiles: List[Tile]) -> int:
        """计算向听数（距离听牌还差几张）"""
        # 简单实现：尝试每种牌打出，计算最小向听数
        best_shanten = 8  # 最大向听数
        
        for i, tile in enumerate(tiles):
            remaining = tiles[:i] + tiles[i+1:]
            # 简化：直接检查是否听牌
            if self.rule_engine.is_ting(remaining):
                return 0
        
        # 如果不打牌能听牌，向听数为0
        if self.rule_engine.is_ting(tiles):
            return 0
        
        # 否则计算大概的向听数
        # 统计面子数
        melds = self._count_melds(tiles)
        complete_melds = melds["complete"]  # 完整面子
        pair_count = melds["pair"]           # 对子
        
        # 向听数 = 8 - (完整面子 * 2 + 对子) 
        shanten = 8 - (complete_melds * 2 + min(pair_count, 1))
        return max(0, shanten)
    
    def _count_melds(self, tiles: List[Tile]) -> Dict:
        """统计面子数"""
        counter = Counter(tiles)
        
        complete = 0  # 完整面子（刻子+顺子）
        pair = 0     # 对子
        
        # 统计刻子
        for tile, count in counter.items():
            if count >= 3:
                complete += count // 3
        
        # 统计对子
        for tile, count in counter.items():
            if count >= 2:
                pair += 1
        
        # 简化：假设数牌可以组成顺子
        # 统计顺子潜力
        for suit in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            suit_nums = [t.number.value for t in tiles if t.tile_type == suit]
            nums_counter = Counter(suit_nums)
            
            # 计算顺子
            for num in range(1, 8):
                if nums_counter[num] > 0 and nums_counter[num+1] > 0 and nums_counter[num+2] > 0:
                    complete += 1
        
        return {"complete": min(complete, 4), "pair": min(pair, 1)}
    
    def _count_draws(self, tiles: List[Tile], remaining: Counter) -> int:
        """计算进张数（能摸到的有效牌数量）"""
        total = 0
        
        for tile in self._all_draws:
            test_tiles = tiles + [tile]
            # 检查是否有效（进张后向听数不增加）
            if len(test_tiles) == 14:
                test_tiles = test_tiles[:-1]  # 去掉一张测试
                shanten_before = self._calc_shanten(tiles)
                shanten_after = self._calc_shantes(test_tiles)
                if shanten_after <= shanten_before:
                    total += remaining.get(tile, 0)
        
        return total
    
    def _count_tenpai_draws(self, tiles: List[Tile], remaining: Counter) -> int:
        """计算听牌进张数"""
        total = 0
        
        # 尝试每种牌作为进张
        for tile in self._all_draws:
            test_tiles = tiles + [tile]
            if len(test_tiles) == 14:
                # 去掉一张，看是否听牌
                for i in range(13):
                    remaining_tiles = test_tiles[:i] + test_tiles[i+1:]
                    if self.rule_engine.is_ting(remaining_tiles):
                        total += remaining.get(tile, 0)
                        break
        
        return total
    
    def _calc_shantes(self, tiles: List[Tile]) -> int:
        """计算向听数（内部方法）"""
        return self._calc_shanten(tiles)
    
    def _analyze_melds(self, tiles: List[Tile]) -> List[Dict]:
        """分析搭子"""
        analysis = []
        counter = Counter(tiles)
        
        # 分析对子
        pairs = [(t, c) for t, c in counter.items() if c >= 2]
        for tile, count in pairs:
            analysis.append({
                "type": "pair",
                "tile": tile_to_string(tile),
                "count": count,
                "priority": "high" if tile.is_terminal else "medium"
            })
        
        # 分析刻子潜力
        for tile, count in counter.items():
            if count == 2:
                analysis.append({
                    "type": "pung_wait",
                    "tile": tile_to_string(tile),
                    "remaining": 4 - count,
                    "priority": "high" if tile.is_terminal else "medium"
                })
        
        # 分析顺子潜力（数牌）
        for suit in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            suit_tiles = [t for t in tiles if t.tile_type == suit]
            nums = sorted([t.number.value for t in suit_tiles])
            
            for num in nums:
                if num <= 7:
                    # 两面搭子
                    if num in nums and num + 1 in nums:
                        analysis.append({
                            "type": "run_wait",
                            "tile": f"{num}-{num+1}",
                            "priority": "low"
                        })
                    # 嵌张搭子
                    if num + 2 in nums:
                        analysis.append({
                            "type": "嵌张",
                            "tile": f"{num}-{num+2}",
                            "priority": "medium"
                        })
        
        return analysis
    
    def _get_discard_advice(self, tiles: List[Tile], remaining: Counter, melds: List[Dict]) -> List[Dict]:
        """获取打牌建议"""
        advices = []
        
        # 统计手牌
        counter = Counter(tiles)
        
        # 评估每张牌的价值
        tile_values = []
        for tile in tiles:
            value = self._evaluate_tile(tile, counter, remaining, melds)
            tile_values.append({
                "tile": tile_to_string(tile),
                "value": value
            })
        
        # 按价值排序
        tile_values.sort(key=lambda x: x["value"])
        
        # 返回建议打出的牌（价值最低的）
        for tv in tile_values[:3]:
            advices.append(tv)
        
        return advices
    
    def _evaluate_tile(self, tile: Tile, counter: Counter, remaining: Counter, melds: List[Dict]) -> float:
        """评估单张牌的价值"""
        # 基础分数
        score = 0
        
        # 1. 幺九牌价值高
        if tile.is_terminal:
            score += 30
        
        # 2. 字牌价值（场风、门风、自风）
        if tile.is_honor:
            score += 25
        
        # 3. 剩余数量多（易进张）
        score += remaining.get(tile, 0) * 5
        
        # 4. 有对子或搭子
        for meld in melds:
            if tile_to_string(tile) == meld.get("tile"):
                score += 20
                break
        
        # 5. 孤张（无靠牌）减分
        if self._is_lonely(tile, counter):
            score -= 20
        
        # 6. 中张牌（有靠牌潜力）加分
        if not tile.is_terminal:
            score += 10
        
        return score
    
    def _is_lonely(self, tile: Tile, counter: Counter) -> bool:
        """判断是否是孤张"""
        if tile.is_honor:
            return counter.get(tile, 0) < 2
        
        # 数牌检查上下家
        suit = tile.tile_type
        num = tile.number.value
        
        has_adjacent = False
        for offset in [-2, -1, 1, 2]:
            check_num = num + offset
            if 1 <= check_num <= 9:
                check_tile = Tile(tile_type=suit, number=TileNumber(check_num))
                if counter.get(check_tile, 0) > 0:
                    has_adjacent = True
                    break
        
        return not has_adjacent


# 测试
if __name__ == "__main__":
    calc = TileEfficiency()
    
    # 测试牌效
    test_tiles = [
        parse_tile("1W"), parse_tile("2W"), parse_tile("3W"),
        parse_tile("4T"), parse_tile("5T"), parse_tile("6T"),
        parse_tile("7S"), parse_tile("8S"), parse_tile("9S"),
        parse_tile("1W"), parse_tile("1W"), parse_tile("2W"), parse_tile("3W")
    ]
    
    result = calc.calculate_efficiency(test_tiles)
    print(f"牌效分析: {result}")
