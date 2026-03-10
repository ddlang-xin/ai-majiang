"""
麻将规则引擎
实现牌型判断、和牌判定、胡牌检测
集成长沙麻将规则
"""

from typing import List, Optional, Tuple, Dict
from collections import Counter
from app.core.tiles import (
    Tile, TileType, TileNumber, HonorTile, 
    Meld, MeldType, Hand, parse_tile, tile_to_string
)
from app.core.changsha_rules import (
    ChangshaMahjong, ChangshaTile, FanType, HuResult,
    FAN_DEFINITIONS, Seat
)


class MahjongRuleEngine:
    """麻将规则引擎（集成标准麻将 + 长沙麻将）"""
    
    def __init__(self, game_type: str = "changsha"):
        """
        初始化规则引擎
        :param game_type: 游戏类型 ("standard" 或 "changsha")
        """
        self.game_type = game_type
        self.all_tiles: List[Tile] = []
        self._init_tiles()
        
        # 长沙麻将引擎
        if game_type == "changsha":
            self.changsha_engine = ChangshaMahjong(base_score=1)
        else:
            self.changsha_engine = None
    
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
    
    def can_hu(self, tiles: List[Tile], require_258: bool = True) -> bool:
        """
        判断是否能胡牌
        :param tiles: 手牌列表
        :param require_258: 是否需要258将（长沙麻将小胡需要）
        """
        if len(tiles) != 14:
            return False
        
        if self.game_type == "changsha" and self.changsha_engine:
            # 使用长沙麻将引擎
            tile_values = [self._tile_to_value(t) for t in tiles]
            return self.changsha_engine.can_hu(tile_values, require_258=require_258)
        
        # 标准麻将胡牌判定
        return self._can_hu_standard(tiles)
    
    def _can_hu_standard(self, tiles: List[Tile]) -> bool:
        """标准麻将胡牌判定"""
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
                    counter[tile] -= 3
                    if self._can_form_melds(list(counter.elements())):
                        return True
                    counter[tile] += 3
                return False
        
        # 处理数牌 - 按花色分组
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
        
        num = min(counter.keys())
        count = counter[num]
        
        if count == 0:
            return self._can_form_num_melds(Counter({k: v for k, v in counter.items() if k > num}))
        
        # 尝试组成顺子
        new_counter = Counter(counter)
        new_counter[num] -= count
        
        for offset in range(count):
            for i in range(3):
                if num + i not in counter or counter[num + i] < count:
                    return False
                new_counter[num + i] -= count
        
        remaining = []
        for k, v in new_counter.items():
            remaining.extend([k] * v)
        
        return self._can_form_num_melds(Counter(remaining))
    
    def _tile_to_value(self, tile: Tile) -> int:
        """将Tile对象转换为牌值（长沙麻将用）"""
        if tile.is_honor:
            # 字牌: 东(27) 南(28) 西(29) 北(30) 中(31) 发(32) 白(33)
            honor_map = {
                HonorTile.DONG: 27,
                HonorTile.NAN: 28,
                HonorTile.XI: 29,
                HonorTile.BEI: 30,
                HonorTile.ZHONG: 31,
                HonorTile.FA: 32,
                HonorTile.BAI: 33,
            }
            return honor_map.get(tile.honor, 27)
        else:
            # 数牌: 筒0-8, 条9-17, 万18-26
            suit_offset = {TileType.TONG: 0, TileType.TIAO: 9, TileType.WAN: 18}
            return suit_offset.get(tile.tile_type, 0) + tile.number.value - 1
    
    def get_ting_cards(self, tiles: List[Tile]) -> List[Tile]:
        """获取听牌后能胡的牌"""
        if len(tiles) != 13:
            return []
        
        if self.game_type == "changsha" and self.changsha_engine:
            # 长沙麻将：尝试加入每张牌，看是否能胡
            # 使用can_hu方法（已集成长沙麻将引擎）
            ting_cards = []
            for tile in self.all_tiles:
                test_tiles = tiles + [tile]
                if len(test_tiles) == 14:
                    if self.can_hu(test_tiles):  # 修复：使用can_hu而不是_can_hu_standard
                        if tile not in ting_cards:
                            ting_cards.append(tile)
            return ting_cards
        
        # 标准麻将
        ting_cards = []
        for i in range(len(tiles)):
            for tile in self.all_tiles:
                test_tiles = tiles[:i] + [tile] + tiles[i+1:]
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
    
    def get_ting_info(self, tiles: List[Tile]) -> Dict:
        """获取听牌信息"""
        if len(tiles) != 13:
            return {"is_ting": False, "ting_cards": [], "han": 0}
        
        ting_cards = self.get_ting_cards(tiles)
        
        # 长沙麻将使用更准确的番数估算
        if self.game_type == "changsha" and self.changsha_engine:
            tile_values = [self._tile_to_value(t) for t in tiles]
            hu_result = self.changsha_engine.check_hu(
                tile_values[:13], 
                winning_tile=tile_values[0] if tile_values else None,
                is_zimo=False
            )
            han = hu_result.total_fan if hu_result.is_hu else 0
        else:
            han = self._estimate_han(tiles)
        
        return {
            "is_ting": len(ting_cards) > 0,
            "ting_cards": [tile_to_string(t) for t in ting_cards],
            "ting_count": len(ting_cards),
            "han": han
        }
    
    def _estimate_han(self, tiles: List[Tile]) -> int:
        """估算番数（简化版）"""
        terminal_honor_count = sum(1 for t in tiles if t.is_terminal)
        return min(6, terminal_honor_count // 2)
    
    # ========== 长沙麻将专用方法 ==========
    
    def check_hu_changsha(
        self,
        hand_tiles: List[Tile],
        winning_tile: Tile = None,
        is_zhuang: bool = False,
        is_zimo: bool = False,
        is_gang_shang: bool = False,
        is_hai_di: bool = False
    ) -> Dict:
        """
        长沙麻将胡牌检测（完整版）
        :param hand_tiles: 手牌（13张）
        :param winning_tile: 胡的那张牌
        :param is_zhuang: 是否庄家
        :param is_zimo: 是否自摸
        :param is_gang_shang: 是否杠上花
        :param is_hai_di: 是否海底捞月
        :return: 胡牌结果字典
        """
        if self.game_type != "changsha" or not self.changsha_engine:
            return {"error": "请使用长沙麻将模式"}
        
        hand_values = [self._tile_to_value(t) for t in hand_tiles]
        winning_value = self._tile_to_value(winning_tile) if winning_tile else None
        
        hu_result = self.changsha_engine.check_hu(
            hand_tiles=hand_values[:13],
            winning_tile=winning_value,
            is_zhuang=is_zhuang,
            is_zimo=is_zimo,
            is_gang_shang=is_gang_shang,
            is_hai_di=is_hai_di
        )
        
        return hu_result.to_dict()
    
    def calculate_bird(
        self,
        bird_tile: Tile,
        zhuang_seat: int = 0,
        hu_player: int = 0,
        is_zimo: bool = False
    ) -> Dict:
        """
        计算扎鸟
        :param bird_tile: 鸟牌
        :param zhuang_seat: 庄家座位 (0-3)
        :param hu_player: 胡牌玩家座位 (0-3)
        :param is_zimo: 是否自摸
        :return: 中鸟玩家和倍数
        """
        if not self.changsha_engine:
            return {"error": "请使用长沙麻将模式"}
        
        bird_value = self._tile_to_value(bird_tile)
        player, multiple = self.changsha_engine.calc_bird(
            bird_value, zhuang_seat, hu_player, is_zimo
        )
        
        return {
            "bird_tile": tile_to_string(bird_tile),
            "bird_player": player,
            "bird_multiple": multiple
        }
    
    def settle_changsha(
        self,
        hu_results: Dict[int, Dict],
        zhuang_seat: int = 0,
        bird_tile: Tile = None,
        base_score: int = 1
    ) -> Dict[int, int]:
        """
        长沙麻将结算
        :param hu_results: {玩家座位: 胡牌结果}
        :param zhuang_seat: 庄家座位
        :param bird_tile: 鸟牌
        :param base_score: 基础分
        :return: {玩家座位: 得分}
        """
        if not self.changsha_engine:
            return {"error": "请使用长沙麻将模式"}
        
        # 转换胡牌结果
        results = {}
        for seat, result_dict in hu_results.items():
            result = HuResult(
                is_hu=result_dict.get("is_hu", False),
                is_big_hu=result_dict.get("is_big_hu", False),
                is_zhuang=result_dict.get("is_zhuang", False),
                is_zimo=result_dict.get("is_zimo", False)
            )
            results[seat] = result
        
        bird_value = self._tile_to_value(bird_tile) if bird_tile else None
        
        return self.changsha_engine.settle(
            results, zhuang_seat, bird_value, base_score
        )


# 测试
if __name__ == "__main__":
    engine = MahjongRuleEngine(game_type="changsha")
    
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
    ting_tiles = [
        parse_tile("1W"), parse_tile("2W"), parse_tile("3W"),
        parse_tile("4T"), parse_tile("5T"), parse_tile("6T"),
        parse_tile("7S"), parse_tile("8S"), parse_tile("9S"),
        parse_tile("1W"), parse_tile("1W"), parse_tile("1W"),
        parse_tile("2W")
    ]
    
    print(f"听牌判定: {engine.is_ting(ting_tiles)}")
    print(f"听牌信息: {engine.get_ting_info(ting_tiles)}")
    
    # 测试长沙麻将胡牌
    print("\n=== 长沙麻将测试 ===")
    result = engine.check_hu_changsha(
        hand_tiles=ting_tiles[:13],
        winning_tile=ting_tiles[13],
        is_zimo=True
    )
    print(f"胡牌结果: {result}")
