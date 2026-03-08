"""
长沙麻将算法模块
实现胡牌判定、番型计算、扎鸟算法、结算
"""

from typing import List, Tuple, Optional, Dict
from collections import Counter
from enum import IntEnum


# ============== 牌定义 ==============
# 筒: 0-8, 条: 9-17, 万: 18-26 (共108张)
class ChangshaTile:
    """长沙麻将牌（整数表示）"""
    
    # 牌值范围
    TONG_MIN, TONG_MAX = 0, 8      # 筒子
    TIAO_MIN, TIAO_MAX = 9, 17     # 条子
    WAN_MIN, WAN_MAX = 18, 26       # 万子
    
    @staticmethod
    def get_suit(tile: int) -> int:
        """获取花色: 0=筒, 1=条, 2=万"""
        if tile <= 8:
            return 0
        elif tile <= 17:
            return 1
        else:
            return 2
    
    @staticmethod
    def get_number(tile: int) -> int:
        """获取点数 (1-9)"""
        return tile % 9 + 1
    
    @staticmethod
    def is_258(tile: int) -> bool:
        """是否是258将牌（2、5、8）"""
        num = tile % 9 + 1
        return num in (2, 5, 8)
    
    @staticmethod
    def is_terminal(tile: int) -> bool:
        """是否幺九牌（1、9）"""
        num = tile % 9 + 1
        return num in (1, 9)
    
    @staticmethod
    def to_string(tile: int) -> str:
        """牌转字符串"""
        suit = ChangshaTile.get_suit(tile)
        num = ChangshaTile.get_number(tile)
        suit_chars = ['筒', '条', '万']
        return f"{num}{suit_chars[suit]}"
    
    @staticmethod
    def parse_tile(tile_str: str) -> int:
        """解析牌字符串，如 "1万" -> 18"""
        num = int(tile_str[0])
        suit_char = tile_str[1]
        suit_map = {'筒': 0, '条': 1, '万': 2}
        suit = suit_map.get(suit_char, 0)
        return suit * 9 + num - 1


# ============== 番型定义 ==============
class FanType(IntEnum):
    """番型枚举"""
    # 小胡
    PING_HU = 1          # 平胡
    QI_SHOU_SI_XI = 2   # 起手四喜
    BAN_BAN_HU = 3      # 板板胡
    QUE_YI_SE = 4       # 缺一色
    LIU_LIU_SHUN = 5    # 六六顺
    
    # 大胡
    PENG_PENG_HU = 10   # 碰碰胡
    QING_YI_SE = 11     # 清一色
    JIANG_JIANG_HU = 12 # 将将胡
    QI_XIAO_DUI = 13    # 七小对
    GANG_SHANG_HUA = 14 # 杠上花
    HAI_DI_LAO_YUE = 15 # 海底捞月


# 番型定义（番数，名称，是否大胡）
FAN_DEFINITIONS = {
    FanType.PING_HU: (1, "平胡", False),
    FanType.QI_SHOU_SI_XI: (1, "起手四喜", False),
    FanType.BAN_BAN_HU: (1, "板板胡", False),
    FanType.QUE_YI_SE: (1, "缺一色", False),
    FanType.LIU_LIU_SHUN: (1, "六六顺", False),
    FanType.PENG_PENG_HU: (6, "碰碰胡", True),
    FanType.QING_YI_SE: (6, "清一色", True),
    FanType.JIANG_JIANG_HU: (6, "将将胡", True),
    FanType.QI_XIAO_DUI: (6, "七小对", True),
    FanType.GANG_SHANG_HUA: (6, "杠上花", True),
    FanType.HAI_DI_LAO_YUE: (6, "海底捞月", True),
}


# ============== 座位定义 ==============
class Seat(IntEnum):
    """座位方位"""
    ZHUANG = 0    # 庄家
    XIA_JIA = 1   # 下家
    DUI_JIA = 2   # 对家
    SHANG_JIA = 3 # 上家


# ============== 胡牌结果 ==============
class HuResult:
    """胡牌结果"""
    def __init__(
        self,
        is_hu: bool,
        is_big_hu: bool = False,        # 是否大胡
        fan_types: List[FanType] = None, # 番型列表
        base_fan: int = 1,              # 基础番数
        is_zhuang: bool = False,         # 庄家
        is_zimo: bool = False,           # 自摸
        bird_tile: int = None,           # 鸟牌
        bird_player: int = None,         # 中鸟玩家
        bird_multiple: int = 1,           # 鸟倍数
        total_fan: int = 0,              # 总番数
        score: int = 0                   # 得分
    ):
        self.is_hu = is_hu
        self.is_big_hu = is_big_hu
        self.fan_types = fan_types or []
        self.base_fan = base_fan
        self.is_zhuang = is_zhuang
        self.is_zimo = is_zimo
        self.bird_tile = bird_tile
        self.bird_player = bird_player
        self.bird_multiple = bird_multiple
        self.total_fan = total_fan
        self.score = score
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "is_hu": self.is_hu,
            "is_big_hu": self.is_big_hu,
            "fan_types": [FAN_DEFINITIONS.get(f, ("未知", 0, False))[1] for f in self.fan_types],
            "base_fan": self.base_fan,
            "is_zhuang": self.is_zhuang,
            "is_zimo": self.is_zimo,
            "bird_tile": ChangshaTile.to_string(self.bird_tile) if self.bird_tile is not None else None,
            "bird_player": self.bird_player,
            "bird_multiple": self.bird_multiple,
            "total_fan": self.total_fan,
            "score": self.score
        }


# ============== 核心算法 ==============
class ChangshaMahjong:
    """长沙麻将算法引擎"""
    
    def __init__(self, base_score: int = 1):
        """
        初始化
        :param base_score: 基础分，默认为1
        """
        self.base_score = base_score
    
    def can_hu(self, tiles: List[int], require_258: bool = True) -> bool:
        """
        判断是否能胡牌
        :param tiles: 牌列表（手牌+副露）
        :param require_258: 是否需要258将（小胡需要，大胡不需要）
        :return: 是否能胡
        """
        if len(tiles) != 14:
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
                    # 如果需要258将，检查雀头是否是258
                    if require_258 and not ChangshaTile.is_258(tile):
                        continue
                    return True
        return False
    
    def _can_form_melds(self, tiles: List[int]) -> bool:
        """检查牌能否组成3面子（刻子或顺子）"""
        if not tiles:
            return True
        if len(tiles) % 3 != 0:
            return False
        
        counter = Counter(tiles)
        tile_list = list(counter.keys())
        
        # 取最小的牌
        tile = min(tile_list)
        count = counter[tile]
        
        # 尝试组成刻子
        if count >= 3:
            new_counter = Counter(counter)
            new_counter[tile] -= 3
            remaining = [t for t in tiles if new_counter[t] > 0]
            if self._can_form_melds(remaining):
                return True
        
        # 尝试组成顺子（仅限数牌）
        suit = ChangshaTile.get_suit(tile)
        num = ChangshaTile.get_number(tile)
        
        # 检查是否能组成顺子 (num, num+1, num+2)
        if num <= 7:
            next1 = tile + 1  # 同一花色的下一张
            next2 = tile + 2
            if counter.get(next1, 0) >= count and counter.get(next2, 0) >= count:
                new_counter = Counter(counter)
                new_counter[tile] -= count
                new_counter[next1] -= count
                new_counter[next2] -= count
                remaining = [t for t in tiles if new_counter[t] > 0]
                if self._can_form_melds(remaining):
                    return True
        
        return False
    
    def check_hu(
        self,
        hand_tiles: List[int],           # 手牌（13张）
        melds: List[Tuple[int, ...]] = None,  # 副露（碰/杠）
        winning_tile: int = None,         # 胡的那张牌
        is_zhuang: bool = False,          # 是否庄家
        is_zimo: bool = False,            # 是否自摸
        is_gang_shang: bool = False,      # 是否杠上花
        is_hai_di: bool = False,         # 是否海底捞月
        last_tile: int = None             # 海底牌
    ) -> HuResult:
        """
        完整胡牌检测
        :param hand_tiles: 手牌（13张）
        :param melds: 副露列表 [(牌值, ...), ...]
        :param winning_tile: 胡的那张牌
        :param is_zhuang: 是否庄家
        :param is_zimo: 是否自摸
        :param is_gang_shang: 是否杠上花
        :param is_hai_di: 是否海底捞月
        :param last_tile: 海底捞月的最后一张牌
        :return: HuResult
        """
        melds = melds or []
        
        # 合成完整手牌（14张）
        all_tiles = hand_tiles[:]
        if winning_tile is not None:
            all_tiles.append(winning_tile)
        
        # 加上副露
        for meld in melds:
            all_tiles.extend(list(meld))
        
        # 先检查起手胡（四喜、六六顺等起手牌型）
        qishou_result = self._check_qishou(hand_tiles, melds)
        if qishou_result:
            return qishou_result
        
        # 尝试大胡（无258限制）
        big_hu_result = self._check_big_hu(
            all_tiles, hand_tiles, melds, 
            is_zimo, is_gang_shang, is_hai_di
        )
        if big_hu_result:
            big_hu_result.is_zhuang = is_zhuang
            big_hu_result.is_zimo = is_zimo
            return big_hu_result
        
        # 尝试小胡（需要258将）
        if self.can_hu(all_tiles, require_258=True):
            # 检查小胡番型
            fan_types = self._check_xiaohu_fan(hand_tiles, melds, is_zimo)
            base_fan = 1  # 小胡基础番
            
            result = HuResult(
                is_hu=True,
                is_big_hu=False,
                fan_types=fan_types,
                base_fan=base_fan,
                is_zhuang=is_zhuang,
                is_zimo=is_zimo
            )
            return result
        
        return HuResult(is_hu=False)
    
    def _check_qishou(
        self, 
        hand_tiles: List[int], 
        melds: List[Tuple[int, ...]]
    ) -> Optional[HuResult]:
        """检查起手胡牌型（四喜、六六顺等）"""
        counter = Counter(hand_tiles)
        
        # 检查起手四喜：起手4个一样
        if any(count >= 4 for count in counter.values()):
            return HuResult(
                is_hu=True,
                is_big_hu=False,
                fan_types=[FanType.QI_SHOU_SI_XI],
                base_fan=1
            )
        
        # 检查六六顺：起手3个一样x2
        three_of_kind = sum(1 for count in counter.values() if count >= 3)
        if three_of_kind >= 2:
            return HuResult(
                is_hu=True,
                is_big_hu=False,
                fan_types=[FanType.LIU_LIU_SHUN],
                base_fan=1
            )
        
        # 检查板板胡：起手所有牌都是258
        if all(ChangshaTile.is_258(t) for t in hand_tiles):
            return HuResult(
                is_hu=True,
                is_big_hu=False,
                fan_types=[FanType.BAN_BAN_HU],
                base_fan=1
            )
        
        # 检查缺一色：起手缺少一种花色
        suits = set(ChangshaTile.get_suit(t) for t in hand_tiles)
        if len(suits) == 2:
            return HuResult(
                is_hu=True,
                is_big_hu=False,
                fan_types=[FanType.QUE_YI_SE],
                base_fan=1
            )
        
        return None
    
    def _check_big_hu(
        self,
        all_tiles: List[int],
        hand_tiles: List[int],
        melds: List[Tuple[int, ...]],
        is_zimo: bool,
        is_gang_shang: bool,
        is_hai_di: bool
    ) -> Optional[HuResult]:
        """检查大胡牌型"""
        fan_types = []
        
        counter = Counter(all_tiles)
        
        # 碰碰胡：全是刻子
        if self._is_pengpeng(hand_tiles, melds):
            fan_types.append(FanType.PENG_PENG_HU)
        
        # 清一色：全是同一花色
        if self._is_qingyise(all_tiles):
            fan_types.append(FanType.QING_YI_SE)
        
        # 将将胡：全是258
        if all(ChangshaTile.is_258(t) for t in all_tiles):
            fan_types.append(FanType.JIANG_JIANG_HU)
        
        # 七小对：4个对子+1个刻子
        if self._is_qixiaodui(counter):
            fan_types.append(FanType.QI_XIAO_DUI)
        
        # 杠上花
        if is_gang_shang:
            fan_types.append(FanType.GANG_SHANG_HUA)
        
        # 海底捞月
        if is_hai_di:
            fan_types.append(FanType.HAI_DI_LAO_YUE)
        
        if fan_types:
            return HuResult(
                is_hu=True,
                is_big_hu=True,
                fan_types=fan_types,
                base_fan=6,  # 大胡基础番
                is_zimo=is_zimo
            )
        
        return None
    
    def _is_pengpeng(
        self, 
        hand_tiles: List[int], 
        melds: List[Tuple[int, ...]]
    ) -> bool:
        """判断碰碰胡"""
        # 检查手牌能否组成全刻子
        if len(hand_tiles) != 13:
            return False
        
        counter = Counter(hand_tiles)
        
        # 尝试找到雀头
        for tile, count in counter.items():
            if count >= 2:
                remaining = []
                for t, c in counter.items():
                    if t == tile:
                        remaining.extend([t] * (c - 2))
                    else:
                        remaining.extend([t] * c)
                
                # 剩余牌必须全是刻子
                if all(c == 3 for c in Counter(remaining).values()):
                    return True
        
        return False
    
    def _is_qingyise(self, tiles: List[int]) -> bool:
        """判断清一色"""
        if len(tiles) != 14:
            return False
        suits = set(ChangshaTile.get_suit(t) for t in tiles)
        return len(suits) == 1
    
    def _is_qixiaodui(self, counter: Counter) -> bool:
        """判断七小对"""
        # 需要4对 + 1个刻子（刻子算作一对）
        pair_count = 0
        remaining = []
        
        for tile, count in counter.items():
            if count >= 2:
                pair_count += count // 2
                remaining.extend([tile] * (count % 2))
            else:
                remaining.append(tile)
        
        # 如果有单张，检查是否能组成刻子
        # 七小对 = 4对子 + 1个刻子（算作一对）
        # 所以需要至少4对，或者3对+1刻子
        three_count = sum(1 for c in counter.values() if c >= 3)
        
        return pair_count + three_count >= 4
    
    def _check_xiaohu_fan(
        self,
        hand_tiles: List[int],
        melds: List[Tuple[int, ...]],
        is_zimo: bool
    ) -> List[FanType]:
        """检查小胡番型"""
        fan_types = [FanType.PING_HU]  # 默认平胡
        
        counter = Counter(hand_tiles)
        
        # 板板胡：所有牌都是258
        if all(ChangshaTile.is_258(t) for t in hand_tiles):
            # 避免重复
            if FanType.PING_HU in fan_types:
                fan_types.remove(FanType.PING_HU)
            fan_types.append(FanType.BAN_BAN_HU)
        
        # 缺一色：缺少一种花色
        suits = set(ChangshaTile.get_suit(t) for t in hand_tiles)
        if len(suits) == 2:
            if FanType.PING_HU in fan_types:
                fan_types.remove(FanType.PING_HU)
            fan_types.append(FanType.QUE_YI_SE)
        
        return fan_types
    
    # ============== 扎鸟算法 ==============
    def calc_bird(
        self,
        bird_tile: int,       # 鸟牌
        zhuang_seat: int,     # 庄家座位
        hu_player: int,       # 胡牌玩家座位
        is_zimo: bool         # 是否自摸
    ) -> Tuple[int, int]:
        """
        计算扎鸟
        :param bird_tile: 鸟牌（翻开的牌）
        :param zhuang_seat: 庄家座位 (0-3)
        :param hu_player: 胡牌玩家座位 (0-3)
        :param is_zimo: 是否自摸
        :return: (中鸟玩家, 鸟倍数)
        """
        # 计算鸟牌对应的方位
        num = bird_tile % 9 + 1  # 1-9
        
        # 方位偏移：1/5/9->0(庄), 2/6->1(下), 3/7->2(对), 4/8->3(上)
        offset_map = {1: 0, 5: 0, 2: 1, 6: 1, 3: 2, 7: 2, 4: 3, 8: 3, 9: 0}
        offset = offset_map.get(num, 0)
        
        # 中鸟玩家
        bird_player = (zhuang_seat + offset) % 4
        
        # 计算倍数
        # 自摸：无论中不中都2倍
        # 点胡：中鸟玩家是胡牌方则2倍，否则1倍
        if is_zimo:
            bird_multiple = 2
        else:
            bird_multiple = 2 if bird_player == hu_player else 1
        
        return bird_player, bird_multiple
    
    # ============== 结算算法 ==============
    def calculate_score(
        self,
        hu_result: HuResult,
        zhuang_seat: int,
        hu_player: int,
        bird_tile: int = None,
        is_zimo: bool = False
    ) -> int:
        """
        计算得分
        :param hu_result: 胡牌结果
        :param zhuang_seat: 庄家座位
        :param hu_player: 胡牌玩家座位
        :param bird_tile: 鸟牌（可选）
        :param is_zimo: 是否自摸
        :return: 得分
        """
        if not hu_result.is_hu:
            return 0
        
        # 计算基础番数
        base_fan = hu_result.base_fan
        
        # 庄家加成
        zhuang_bonus = 1 if hu_result.is_zhuang else 0
        
        # 番上番累加（大胡可叠加）
        extra_fan = 0
        for fan_type in hu_result.fan_types:
            if fan_type in FAN_DEFINITIONS:
                is_big = FAN_DEFINITIONS[fan_type][2]
                if is_big:
                    extra_fan += FAN_DEFINITIONS[fan_type][0]
        
        # 总番数
        total_fan = base_fan + zhuang_bonus + extra_fan
        total_fan = min(total_fan, 14)  # 封顶14番
        
        # 扎鸟倍数
        bird_multiple = 1
        if bird_tile is not None:
            _, bird_multiple = self.calc_bird(
                bird_tile, zhuang_seat, hu_player, is_zimo
            )
        
        # 计算得分
        score = self.base_score * total_fan * bird_multiple
        
        # 更新结果
        hu_result.total_fan = total_fan
        hu_result.bird_tile = bird_tile
        hu_result.bird_multiple = bird_multiple
        hu_result.score = score
        
        return score
    
    def settle(
        self,
        hu_results: Dict[int, HuResult],  # {玩家座位: 胡牌结果}
        zhuang_seat: int,                    # 庄家座位
        bird_tile: int = None,               # 鸟牌
        base_score: int = None                # 基础分
    ) -> Dict[int, int]:
        """
        结算所有玩家
        :param hu_results: 胡牌结果字典
        :param zhuang_seat: 庄家座位
        :param bird_tile: 鸟牌
        :param base_score: 基础分（可选）
        :return: {玩家座位: 得分}
        """
        if base_score is not None:
            self.base_score = base_score
        
        scores = {}
        
        for player, result in hu_results.items():
            if result.is_hu:
                is_zimo = result.is_zimo
                score = self.calculate_score(
                    result, zhuang_seat, player, bird_tile, is_zimo
                )
                scores[player] = score
            else:
                scores[player] = 0
        
        return scores


# ============== 工具函数 ==============
def create_tiles_from_list(tile_values: List[int]) -> List[int]:
    """从牌值列表创建牌组"""
    return tile_values[:]


def parse_tiles(tile_strs: List[str]) -> List[int]:
    """解析牌字符串列表"""
    return [ChangshaTile.parse_tile(s) for s in tile_strs]


# ============== 测试 ==============
if __name__ == "__main__":
    engine = ChangshaMahjong(base_score=1)
    
    # 测试1: 小胡-平胡
    print("=== 测试1: 小胡-平胡 ===")
    # 123 456 789 111 22 (111是刻子，22是258将)
    hand = [0, 1, 2, 9, 10, 11, 18, 19, 20, 0, 0, 0, 1, 1]  # 12345678911122
    result = engine.check_hu(hand[:13], [], winning_tile=hand[13], is_zhuang=False, is_zimo=True)
    print(f"胡牌: {result.is_hu}")
    print(f"番型: {[FAN_DEFINITIONS.get(f, ('未知', 0, False))[1] for f in result.fan_types]}")
    
    # 测试2: 大胡-清一色
    print("\n=== 测试2: 大胡-清一色 ===")
    # 111 222 333 444 55 (清一色)
    hand2 = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4]
    result2 = engine.check_hu(hand2[:13], [], winning_tile=hand2[13], is_zhuang=False, is_zimo=True)
    print(f"胡牌: {result2.is_hu}")
    print(f"番型: {[FAN_DEFINITIONS.get(f, ('未知', 0, False))[1] for f in result2.fan_types]}")
    
    # 测试3: 扎鸟计算
    print("\n=== 测试3: 扎鸟计算 ===")
    # 鸟牌5筒 -> 庄家中鸟, 自摸2倍
    player, multiple = engine.calc_bird(4, 0, 0, True)
    print(f"鸟牌5筒 -> 中鸟玩家: {player}, 倍数: {multiple}")
    
    # 鸟牌2万 -> 下家中鸟
    player, multiple = engine.calc_bird(19, 0, 0, False)
    print(f"鸟牌2万 -> 中鸟玩家: {player}, 倍数: {multiple}")
    
    # 测试4: 结算
    print("\n=== 测试4: 结算 ===")
    result.total_fan = result.base_fan
    result.bird_multiple = 2
    score = engine.calculate_score(result, 0, 0, 4, True)
    print(f"得分: {score}")
    
    # 测试5: 起手四喜
    print("\n=== 测试5: 起手四喜 ===")
    # 起手4个一样
    hand3 = [0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    result3 = engine.check_hu(hand3, [], is_zhuang=False, is_zimo=True)
    print(f"胡牌: {result3.is_hu}")
    print(f"番型: {[FAN_DEFINITIONS.get(f, ('未知', 0, False))[1] for f in result3.fan_types]}")
