"""
牌效计算模块
计算打牌后的进张数、听牌效率等
优化版本 - 添加缓存和高效算法
"""

from typing import List, Dict, Tuple, Optional
from collections import Counter
from app.core.tiles import (
    Tile, TileType, TileNumber, HonorTile, 
    parse_tile, tile_to_string
)
from app.core.rules import MahjongRuleEngine


class TileEfficiency:
    """牌效计算器 - 优化版"""
    
    def __init__(self):
        self.rule_engine = MahjongRuleEngine()
        # 所有进张牌（可以摸到的牌）
        self._all_draws: List[Tile] = []
        self._init_draws()
        # 缓存已计算的结果
        self._cache: Dict[str, Dict] = {}
        # 简化版all_tiles用于快速检查
        self._simple_tiles: List[Tile] = []
        self._init_simple_tiles()
    
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
    
    def _init_simple_tiles(self):
        """初始化简化版牌列表（用于快速检查）"""
        # 只使用每个种类的一张代表牌，用于快速听牌检查
        for suit in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            for num in range(1, 10):
                self._simple_tiles.append(Tile(
                    tile_type=suit,
                    number=TileNumber(num)
                ))
        for honor in HonorTile:
            self._simple_tiles.append(Tile(
                tile_type=TileType.ZI,
                honor=honor
            ))
    
    def _get_cache_key(self, tiles: List[Tile]) -> str:
        """生成缓存键"""
        return "".join(sorted([tile_to_string(t) for t in tiles]))
    
    def calculate_efficiency(self, tiles: List[Tile], discarded: List[Tile] = None) -> Dict:
        """
        计算牌效
        返回：进张数、听牌效率、改进建议
        """
        if len(tiles) != 13:
            return {"error": "需要13张手牌"}
        
        # 检查缓存
        cache_key = self._get_cache_key(tiles)
        if cache_key in self._cache:
            result = self._cache[cache_key].copy()
            # 即使有缓存也要更新打牌建议（因为depends on discarded）
            if discarded:
                discarded_counter = Counter(discarded)
                remaining_tiles = self._get_remaining_tiles(discarded_counter)
                melds_analysis = self._analyze_melds(tiles)
                result["discard_advice"] = self._get_discard_advice(tiles, remaining_tiles, melds_analysis)
            return result
        
        discarded = discarded or []
        
        # 统计已经打过的牌
        discarded_counter = Counter(discarded)
        
        # 计算每种牌的剩余数量
        remaining_tiles = self._get_remaining_tiles(discarded_counter)
        
        # 计算各种指标 - 使用优化后的方法
        shanten = self._calc_shanten_fast(tiles)
        draw_count = self._count_draws_fast(tiles, remaining_tiles)
        tenpai_count = self._count_tenpai_draws_fast(tiles, remaining_tiles)
        
        # 分析搭子
        melds_analysis = self._analyze_melds(tiles)
        
        result = {
            "shanten": shanten,
            "draw_count": draw_count,
            "tenpai_count": tenpai_count,
            "tenpai_rate": round(tenpai_count / max(draw_count, 1), 2),
            "melds": melds_analysis,
            "discard_advice": self._get_discard_advice(tiles, remaining_tiles, melds_analysis)
        }
        
        # 缓存结果
        self._cache[cache_key] = result
        return result
    
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
    
    def _calc_shanten_fast(self, tiles: List[Tile]) -> int:
        """
        快速计算向听数
        使用简化的向听数算法，避免深度递归
        """
        # 统计每种牌的数量
        counter = Counter(tiles)
        
        # 统计面子数（刻子+顺子潜力）
        complete_melds = 0  # 完整面子
        pair_count = 0     # 对子数
        
        # 统计刻子
        for tile, count in counter.items():
            if count >= 3:
                complete_melds += count // 3
        
        # 统计对子
        for tile, count in counter.items():
            if count >= 2:
                pair_count += 1
        
        # 简化：假设数牌可以组成顺子
        # 统计顺子潜力
        for suit in [TileType.WAN, TileType.TONG, TileType.TIAO]:
            suit_tiles = [t for t in tiles if t.tile_type == suit]
            nums_counter = Counter([t.number.value for t in suit_tiles])
            
            # 计算顺子（相邻的3张牌）
            for num in range(1, 8):
                if nums_counter[num] > 0 and nums_counter[num+1] > 0 and nums_counter[num+2] > 0:
                    complete_melds += 1
        
        # 限制最大面子数
        complete_melds = min(complete_melds, 4)
        pair_count = min(pair_count, 1)
        
        # 向听数 = 6 - (完整面子 * 2 + 对子)
        # 最大向听数为6（13张牌需要6次进张才能听牌）
        shanten = 6 - (complete_melds * 2 + pair_count)
        
        # 如果已经有4组面子+1对子，听牌
        if complete_melds >= 4 and pair_count >= 1:
            return 0
        
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
    
    def _count_draws_fast(self, tiles: List[Tile], remaining: Counter) -> int:
        """
        快速计算进张数
        通过比较向听数改善来判断
        """
        shanten_before = self._calc_shanten_fast(tiles)
        
        # 如果已经听牌，返回剩余牌数
        if shanten_before == 0:
            return sum(remaining.values())
        
        # 限制检查范围：只检查与手牌相邻的牌
        total = 0
        counter = Counter(tiles)
        
        for tile in self._all_draws:
            # 跳过剩余数为0的牌
            if remaining.get(tile, 0) == 0:
                continue
            
            # 尝试加入这张牌
            test_tiles = tiles + [tile]
            shanten_after = self._calc_shanten_fast(test_tiles)
            
            # 如果向听数减少或不变，则是有效进张
            if shanten_after < shanten_before:
                total += remaining.get(tile, 0)
        
        return total
    
    def _count_tenpai_draws_fast(self, tiles: List[Tile], remaining: Counter) -> int:
        """
        快速计算听牌进张数
        通过检查向听数是否为0来判断
        """
        total = 0
        
        for tile in self._all_draws:
            if remaining.get(tile, 0) == 0:
                continue
            
            # 尝试加入这张牌，然后打出一张
            test_tiles = tiles + [tile]
            shanten_with_tile = self._calc_shanten_fast(test_tiles)
            
            # 如果加入这张牌后变成听牌（向听数0），则这张牌是听牌进张
            if shanten_with_tile == 0:
                total += remaining.get(tile, 0)
        
        return total
    
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
