"""
长沙麻将算法模块

牌定义：108张（筒0-8,条9-17,万18-26）
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import random


class Suit(Enum):
    """花色枚举"""
    TONG = 0  # 筒
    TIAO = 1  # 条
    WAN = 2   # 万


class Tile:
    """牌定义"""
    
    def __init__(self, value: int):
        """
        初始化牌
        value: 0-8 筒, 9-17 条, 18-26 万
        """
        if not 0 <= value <= 26:
            raise ValueError(f"牌值必须在0-26之间，当前值: {value}")
        self.value = value
    
    @property
    def suit(self) -> Suit:
        """花色"""
        if self.value <= 8:
            return Suit.TONG
        elif self.value <= 17:
            return Suit.TIAO
        else:
            return Suit.WAN
    
    @property
    def number(self) -> int:
        """点数(1-9)"""
        return self.value % 9 + 1
    
    @property
    def is_258(self) -> bool:
        """是否是258将牌"""
        return self.number in (2, 5, 8)
    
    @property
    def display(self) -> str:
        """显示名称"""
        suit_names = {Suit.TONG: "筒", Suit.TIAO: "条", Suit.WAN: "万"}
        return f"{suit_names[self.suit]}{self.number}"
    
    def __eq__(self, other):
        if not isinstance(other, Tile):
            return False
        return self.value == other.value
    
    def __hash__(self):
        return hash(self.value)
    
    def __repr__(self):
        return self.display


class HandTiles:
    """手牌管理"""
    
    def __init__(self, tiles: List[int] = None):
        """
        初始化手牌
        tiles: 牌值列表，如 [0,0,0,0, 9,9,9, 18,18,18, 1,3,5]
        """
        if tiles is None:
            tiles = []
        # 排序并统计
        self._counts = [0] * 27
        for t in tiles:
            self._counts[t] += 1
        
        # 转换为列表（用于计算）
        self._tiles = sorted(tiles)
    
    @property
    def tiles(self) -> List[int]:
        """获取所有牌值"""
        result = []
        for i, count in enumerate(self._counts):
            result.extend([i] * count)
        return result
    
    @property
    def tile_counts(self) -> List[int]:
        """获取27种牌的计数"""
        return self._counts.copy()
    
    @property
    def length(self) -> int:
        """牌数量"""
        return sum(self._counts)
    
    def add(self, tile: int) -> 'HandTiles':
        """添加一张牌"""
        new_tiles = self.tiles + [tile]
        return HandTiles(new_tiles)
    
    def remove(self, tile: int) -> 'HandTiles':
        """移除一张牌"""
        if self._counts[tile] <= 0:
            raise ValueError(f"牌 {tile} 不足")
        new_tiles = self.tiles.copy()
        new_tiles.remove(tile)
        return HandTiles(new_tiles)
    
    def get_suit_counts(self) -> Dict[Suit, int]:
        """获取各花色牌数"""
        result = {Suit.TONG: 0, Suit.TIAO: 0, Suit.WAN: 0}
        for i, count in enumerate(self._counts):
            if i <= 8:
                result[Suit.TONG] += count
            elif i <= 17:
                result[Suit.TIAO] += count
            else:
                result[Suit.WAN] += count
        return result
    
    def get_suit_list(self) -> List[int]:
        """获取各花色牌列表"""
        tong = [i for i in range(9) if self._counts[i] > 0]
        tiao = [i for i in range(9, 18) if self._counts[i] > 0]
        wan = [i for i in range(18, 27) if self._counts[i] > 0]
        return tong, tiao, wan


class MeldType(Enum):
    """面子类型"""
    PENG = "碰"       # 刻子
    GANG = "杠"       # 杠子
    CHI_LEFT = "吃左"   # 顺子左
    CHI_MID = "吃中"   # 顺子中
    CHI_RIGHT = "吃右"  # 顺子右


@dataclass
class Meld:
    """面子数据"""
    type: MeldType
    tiles: List[int]  # 牌值列表
    from_player: int = -1  # 来源玩家(-1: 摸牌)


class HuResult:
    """胡牌结果"""
    
    def __init__(self, is_hu: bool, is_big_hu: bool = False, 
                 hu_type: str = "", fans: int = 0):
        self.is_hu = is_hu
        self.is_big_hu = is_big_hu
        self.hu_type = hu_type
        self.fans = fans
        
        # 番型详情
        self.hu_patterns: List[str] = []
        
        # 牌型详情
        self.melds: List[Meld] = []  # 副露
        self.eyes: List[int] = []    # 将牌
        
        # 特殊胡牌标记
        self.is_zimo: bool = False          # 自摸
        self.is_haidilaoyue: bool = False   # 海底捞月
        self.is_gangshanghua: bool = False # 杠上开花
        self.is_quanqiuren: bool = False    # 全求人
        self.is_diangelog: bool = False     # 抢杠胡
        self.is_gangkai: bool = False       # 杠开
        
    def __bool__(self):
        return self.is_hu


# ==================== 核心算法 ====================

class ChangshaMahjong:
    """长沙麻将算法核心类"""
    
    # 基础配置
    TOTAL_TILES = 108
    TILES_PER_SUIT = 9
    MAX_FAN = 14  # 封顶番数
    
    def __init__(self, bird_count: int = 2):
        """
        初始化
        bird_count: 扎鸟数量
        """
        self.bird_count = bird_count
        self.wall_tiles = list(range(27)) * 4  # 牌墙
        self.discarded_tiles: List[int] = []   # 打出的牌
        self.birds: List[int] = []             # 鸟牌
        
    def shuffle(self):
        """洗牌"""
        random.shuffle(self.wall_tiles)
        self.discarded_tiles.clear()
        self.birds.clear()
    
    def draw_tile(self) -> Optional[int]:
        """摸牌"""
        if not self.wall_tiles:
            return None
        return self.wall_tiles.pop()
    
    def draw_birds(self) -> List[int]:
        """扎鸟"""
        birds = []
        for _ in range(self.bird_count):
            if self.wall_tiles:
                birds.append(self.wall_tiles.pop())
        self.birds = birds
        return birds
    
    def discard(self, tile: int):
        """打牌"""
        self.discarded_tiles.append(tile)
    
    # ==================== 胡牌判定 ====================
    
    def can_hu(self, tiles: List[int], is_big_hu: bool = False,
               is_zimo: bool = False, has_gang: bool = False,
               is_last_tile: bool = False, gang_tile: int = None) -> HuResult:
        """
        判断是否胡牌
        tiles: 牌值列表（手牌+副露）
        is_big_hu: 是否大胡模式
        is_zimo: 是否自摸（用于海底捞月判定）
        has_gang: 是否有杠（用于杠上开花判定）
        is_last_tile: 是否最后一张牌（海底捞月判定）
        gang_tile: 杠后摸到的牌（杠上开花判定）
        """
        hand = HandTiles(tiles)
        
        # 必须是14张（或13张+1张）
        if hand.length % 3 != 2:
            return HuResult(False)
        
        # 检查胡牌
        result = self._check_hu(hand, is_big_hu)
        
        # 判定番型
        if result.is_hu:
            result.is_zimo = is_zimo
            result = self._analyze_hu_patterns(hand, result, is_big_hu, 
                                               has_gang, is_last_tile, gang_tile)
        
        return result
    
    def _check_hu(self, hand: HandTiles, is_big_hu: bool) -> HuResult:
        """检查胡牌结构"""
        counts = hand.tile_counts
        
        # 尝试每个可能的将牌
        for jiang in range(27):
            if counts[jiang] < 2:
                continue
            
            # 移除将牌
            temp_counts = counts.copy()
            temp_counts[jiang] -= 2
            
            # 检查剩余牌是否全是面子
            if self._check_all_melds(temp_counts):
                # 小胡需要258将
                if not is_big_hu:
                    tile = Tile(jiang)
                    if not tile.is_258:
                        continue
                
                result = HuResult(True, is_big_hu=is_big_hu, 
                               hu_type="大胡" if is_big_hu else "小胡",
                               fans=1)
                result.eyes = [jiang]
                return result
        
        return HuResult(False)
    
    def _check_all_melds(self, counts: List[int]) -> bool:
        """检查是否全是面子（递归）"""
        # 找到第一张有牌的牌
        first_tile = -1
        for i in range(27):
            if counts[i] > 0:
                first_tile = i
                break
        
        if first_tile == -1:
            return True  # 全部面子完成
        
        count = counts[first_tile]
        
        # 尝试刻子
        if count >= 3:
            counts[first_tile] -= 3
            if self._check_all_melds(counts):
                counts[first_tile] += 3
                return True
            counts[first_tile] += 3
        
        # 尝试顺子 (只能同花色)
        # 0-8 筒, 9-17 条, 18-26 万
        suit_start = (first_tile // 9) * 9
        idx_in_suit = first_tile - suit_start
        
        if idx_in_suit <= 6 and counts[first_tile + 1] > 0 and counts[first_tile + 2] > 0:
            counts[first_tile] -= 1
            counts[first_tile + 1] -= 1
            counts[first_tile + 2] -= 1
            if self._check_all_melds(counts):
                counts[first_tile] += 1
                counts[first_tile + 1] += 1
                counts[first_tile + 2] += 1
                return True
            counts[first_tile] += 1
            counts[first_tile + 1] += 1
            counts[first_tile + 2] += 1
        
        return False
    
    def _analyze_hu_patterns(self, hand: HandTiles, result: HuResult, 
                             is_big_hu: bool, has_gang: bool = False,
                             is_last_tile: bool = False, gang_tile: int = None) -> HuResult:
        """
        分析番型
        hand: 手牌
        result: 胡牌结果
        is_big_hu: 是否大胡模式
        has_gang: 是否有杠
        is_last_tile: 是否最后一张牌
        gang_tile: 杠后摸到的牌
        """
        counts = hand.tile_counts
        tong, tiao, wan = hand.get_suit_list()
        
        # 检查大胡番型
        big_patterns = []
        
        # 1. 碰碰胡: 只有刻子
        if self._is_pengpeng_hu(counts):
            big_patterns.append("碰碰胡")
        
        # 2. 清一色: 同花色
        suit_counts = hand.get_suit_counts()
        if suit_counts[Suit.TONG] == hand.length or suit_counts[Suit.TIAO] == hand.length or suit_counts[Suit.WAN] == hand.length:
            big_patterns.append("清一色")
        
        # 3. 将将胡: 所有牌都是258
        if self._is_jiangjiang_hu(counts):
            big_patterns.append("将将胡")
        
        # 4. 七小对
        if self._is_qixiaodui(counts):
            big_patterns.append("七小对")
        
        result.hu_patterns = big_patterns
        result.is_big_hu = len(big_patterns) > 0
        
        # 计算番数
        if result.is_big_hu:
            result.fans = self._calculate_big_fan(len(big_patterns))
            result.hu_type = "+".join(big_patterns)
        else:
            result.fans = 1
        
        return result
    
    def _is_pengpeng_hu(self, counts: List[int]) -> bool:
        """是否碰碰胡"""
        remainder = sum(c % 3 for c in counts)
        return remainder == 2  # 剩一对将
    
    def _is_jiangjiang_hu(self, counts: List[int]) -> bool:
        """是否将将胡"""
        for i in range(27):
            if counts[i] > 0:
                if Tile(i).number not in (2, 5, 8):
                    return False
        return True
    
    def _is_qixiaodui(self, counts: List[int]) -> bool:
        """是否七小对"""
        # 必须有7对
        pairs = sum(c // 2 for c in counts)
        if pairs < 7:
            return False
        
        # 检查是否只能组成7对（不能有刻子）
        for c in counts:
            if c == 3:  # 有刻子不能是七小对
                return False
        
        return True
    
    def _calculate_big_fan(self, n: int) -> int:
        """计算大胡番数（倍数法）"""
        # 大胡1个=6番, 大胡2个=12番, 大胡3个=24番...
        return 6 * (2 ** (n - 1))
    
    # ==================== 番型计算 ====================
    
    def calculate_fan(self, tiles: List[int], patterns: List[str], is_zhuang: bool = False) -> int:
        """
        计算番数
        tiles: 牌值列表
        patterns: 番型列表
        is_zhuang: 是否庄家
        """
        if not patterns:
            return 1 if is_zhuang else 1
        
        # 小胡
        if "平胡" in patterns:
            return 2 if is_zhuang else 1
        
        # 大胡 - 使用倍数法
        big_count = len(patterns)
        base_fan = 6 * (2 ** (big_count - 1))
        
        # 庄家加1番
        if is_zhuang:
            base_fan += 1
        
        return min(base_fan, self.MAX_FAN)
    
    # ==================== 扎鸟算法 ====================
    
    def calculate_birds(self, birds: List[int], hu_seat: int, is_zimo: bool) -> Tuple[int, Dict[int, int]]:
        """
        计算扎鸟结果
        birds: 鸟牌列表
        hu_seat: 胡牌玩家座位(0-3)
        is_zimo: 是否自摸
        
        返回: (中鸟总数, {座位: 中鸟数})
        """
        bird_count = {0: 0, 1: 0, 2: 0, 3: 0}
        
        for bird in birds:
            tile = Tile(bird)
            bird_point = tile.number
            
            # 鸟牌方位映射
            if bird_point in (1, 5, 9):
                target_seat = 0  # 庄家
            elif bird_point in (2, 6):
                target_seat = 1  # 下家
            elif bird_point in (3, 7):
                target_seat = 2  # 对家
            else:  # 4, 8
                target_seat = 3  # 上家
            
            # 计算倍数
            # 自摸时：中鸟的玩家都算
            # 点炮时：胡牌方中鸟或非胡牌方中鸟都算
            if is_zimo:
                bird_count[target_seat] += 1
            else:
                # 点炮方中鸟
                if target_seat == hu_seat:
                    bird_count[hu_seat] += 1
                # 非胡牌方中鸟
                else:
                    bird_count[target_seat] += 1
        
        total_birds = sum(bird_count.values())
        return total_birds, bird_count
    
    def calculate_score(self, base_score: int, fans: int, bird_multiplier: int) -> int:
        """
        计算得分
        base_score: 基础分
        fans: 番数
        bird_multiplier: 鸟倍数(1 + 中鸟数)
        """
        return base_score * fans * bird_multiplier
    
    # ==================== 结算算法 ====================
    
    def settle(self, hu_info: Dict, is_zimo: bool, is_zhuang: bool, 
               base_score: int = 2) -> Dict:
        """
        结算
        hu_info: 胡牌信息 {seat, fans, patterns, is_big_hu}
        is_zimo: 是否自摸
        is_zhuang: 是否庄家胡牌
        base_score: 基础分
        """
        hu_seat = hu_info["seat"]
        fans = hu_info.get("fans", 1)
        
        # 扎鸟
        total_birds, bird_count = self.calculate_birds(
            self.birds, hu_seat, is_zimo
        )
        
        # 计算各玩家应付金额
        payments = {}
        
        if is_zimo:
            # 自摸：三家付款
            for seat in range(4):
                if seat != hu_seat:
                    multiplier = 1 + bird_count[seat]
                    payments[seat] = base_score * fans * multiplier
        else:
            # 点炮：点炮方付款
            # 实际实现需要知道点炮方，这里简化为其他三家
            for seat in range(4):
                if seat != hu_seat:
                    # 简化：自摸才算鸟
                    multiplier = 1 + bird_count[hu_seat] if is_zimo else 1
                    payments[seat] = base_score * fans * multiplier
        
        return {
            "hu_seat": hu_seat,
            "is_zimo": is_zimo,
            "fans": fans,
            "base_score": base_score,
            "bird_count": total_birds,
            "bird_details": bird_count,
            "payments": payments,
            "total": sum(payments.values())
        }


# ==================== 打牌推荐算法 ====================

class StrategyCalculator:
    """打牌策略计算器"""
    
    # 权重配置
    ALPHA = 0.35  # 速度权重
    BETA = 0.30   # 防守权重
    GAMMA = 0.25  # 番型潜力权重
    DELTA = 0.10  # 将牌权重
    
    # 番型分配置
    PATTERN_EXISTING_SCORES = {
        "碰碰胡": 70,
        "清一色": 65,
        "七小对": 60,
        "将将胡": 55,
        "平胡": 30
    }
    
    # 潜力番型分
    PATTERN_POTENTIAL_SCORES = {
        "七小对≥5对": 50,
        "清一色≥8张": 45,
        "碰碰胡≥3刻": 40,
        "将将胡258≥6": 35
    }
    
    def __init__(self, game: ChangshaMahjong):
        self.game = game
    
    def recommend_discard(self, hand_tiles: List[int], 
                          pool_tiles: List[int] = None) -> Tuple[int, float, Dict]:
        """
        推荐打牌
        hand_tiles: 手牌
        pool_tiles: 牌池（已打出的牌）
        
        返回: (推荐打出的牌, 评分, 详情)
        """
        if pool_tiles is None:
            pool_tiles = []
        
        hand = HandTiles(hand_tiles)
        pool_counts = [0] * 27
        for t in pool_tiles:
            pool_counts[t] += 1
        
        best_tile = None
        best_score = float('-inf')
        best_details = {}
        
        # 遍历每张可打的牌
        for tile_val in set(hand_tiles):
            # 尝试打出这张牌
            new_hand = HandTiles([t for t in hand_tiles if t != tile_val])
            
            # 计算各项分数
            speed_score = self._calc_speed_score(hand_tiles, tile_val, pool_counts)
            defense_score = self._calc_defense_score(tile_val, pool_counts)
            pattern_score = self._calc_pattern_score(new_hand)
            jiang_score = self._calc_jiang_score(new_hand)
            
            # 综合评分
            total_score = (
                self.ALPHA * speed_score +
                self.BETA * defense_score +
                self.GAMMA * pattern_score +
                self.DELTA * jiang_score
            )
            
            if total_score > best_score:
                best_score = total_score
                best_tile = tile_val
                best_details = {
                    "speed": speed_score,
                    "defense": defense_score,
                    "pattern": pattern_score,
                    "jiang": jiang_score
                }
        
        return best_tile, best_score, best_details
    
    def _calc_speed_score(self, original_tiles: List[int], discard_tile: int, 
                          pool_counts: List[int]) -> float:
        """计算速度分"""
        # 简化：计算向听数变化
        hand = HandTiles([t for t in original_tiles if t != discard_tile])
        
        # 理论最大进张数
        max_ting_count = 0
        for draw in range(27):
            if pool_counts[draw] < 4:  # 牌池未满
                test_tiles = hand.tiles + [draw]
                result = self.game.can_hu(test_tiles)
                if result.is_hu:
                    # 统计听牌数
                    for ting in range(27):
                        if pool_counts[ting] < 4:
                            test_ting = hand.tiles + [draw, ting]
                            if self.game.can_hu(test_ting).is_hu:
                                max_ting_count += 1
        
        # 归一化分数
        return min(max_ting_count / 10.0, 100)
    
    def _calc_defense_score(self, tile: int, pool_counts: List[int]) -> float:
        """计算防守分"""
        # 已打出数量越多越安全
        played_count = sum(pool_counts)
        safety = played_count / 108.0 * 100
        
        # 危险牌检测（牌池未打）
        tile_safety = pool_counts[tile] / 4.0 * 50
        
        return safety + tile_safety
    
    def _calc_pattern_score(self, hand: HandTiles) -> float:
        """计算番型潜力分"""
        counts = hand.tile_counts
        
        score = 0
        
        # 已有番型
        # 碰碰胡检测
        kezi_count = sum(1 for c in counts if c >= 3)
        if kezi_count >= 3:
            score += self.PATTERN_EXISTING_SCORES["碰碰胡"]
        
        # 清一色检测
        suit_counts = hand.get_suit_counts()
        max_suit = max(suit_counts.values())
        if max_suit >= 8:
            score += self.PATTERN_EXISTING_SCORES["清一色"]
        
        # 七小对检测
        pairs = sum(c // 2 for c in counts)
        if pairs >= 5:
            score += self.PATTERN_POTENTIAL_SCORES["七小对≥5对"]
        
        # 将将胡潜力
        jiang_258_count = sum(counts[i] for i in range(27) if Tile(i).is_258)
        if jiang_258_count >= 6:
            score += self.PATTERN_POTENTIAL_SCORES["将将胡258≥6"]
        
        return score
    
    def _calc_jiang_score(self, hand: HandTiles) -> float:
        """计算将牌分"""
        counts = hand.tile_counts
        
        # 已有将牌
        jiang_count = sum(1 for i in range(27) if counts[i] >= 2 and Tile(i).is_258)
        
        # 潜力将牌
        potential_jiang = 0
        for i in range(27):
            if counts[i] == 1 and Tile(i).is_258:
                potential_jiang += 0.5
        
        return jiang_count * 10 + potential_jiang * 5


# ==================== 工具函数 ====================

def create_tiles_from_numbers(numbers: List[int], suit: Suit) -> List[int]:
    """
    从数字创建牌值列表
    numbers: 点数列表 [1,2,3]
    suit: 花色
    """
    base = suit.value * 9
    return [base + n - 1 for n in numbers]


def parse_hand_string(s: str) -> List[int]:
    """
    解析手牌字符串
    格式: "1t 2t 3t 1w 5w" 或 "1122334455667"
    """
    tiles = []
    s = s.strip().replace(" ", "")
    
    # 简单解析：数字+字母
    import re
    pattern = r'(\d+)([tTwW])'
    matches = re.findall(pattern, s)
    
    for num, suit_char in matches:
        num = int(num)
        if suit_char.lower() == 't':
            tiles.append(num - 1)  # 筒 0-8
        elif suit_char.lower() == 's':
            tiles.append(9 + num - 1)  # 条 9-17
        elif suit_char.lower() == 'w':
            tiles.append(18 + num - 1)  # 万 18-26
    
    return tiles


# ==================== 测试 ====================

if __name__ == "__main__":
    # 测试牌定义
    print("=== 牌定义测试 ===")
    t1 = Tile(0)  # 1筒
    t2 = Tile(9)  # 1条
    t3 = Tile(18) # 1万
    print(f"Tile(0): {t1}, suit={t1.suit}, number={t1.number}, is_258={t1.is_258}")
    print(f"Tile(9): {t2}, suit={t2.suit}, number={t2.number}, is_258={t2.is_258}")
    print(f"Tile(18): {t3}, suit={t3.suit}, number={t3.number}, is_258={t3.is_258}")
    
    # 测试手牌
    print("\n=== 手牌测试 ===")
    hand = HandTiles([0, 0, 0, 0, 9, 9, 9, 18, 18, 18, 1, 3, 5])
    print(f"手牌: {[Tile(t).display for t in hand.tiles]}")
    print(f"牌数: {hand.length}")
    print(f"花色统计: {hand.get_suit_counts()}")
    
    # 测试胡牌判定
    print("\n=== 胡牌判定测试 ===")
    game = ChangshaMahjong()
    
    # 平胡测试 (4面子+258将)
    ping_hu_tiles = [0, 0, 0, 9, 9, 9, 18, 18, 18, 19, 20, 21, 22, 22]
    result = game.can_hu(ping_hu_tiles, is_big_hu=False)
    print(f"平胡测试: is_hu={result.is_hu}, type={result.hu_type}, fans={result.fans}")
    
    # 大胡测试 - 碰碰胡
    pengpeng_tiles = [0, 0, 0, 9, 9, 9, 18, 18, 18, 1, 1, 5, 5, 5]  # 碰碰胡
    result = game.can_hu(pengpeng_tiles, is_big_hu=True)
    print(f"碰碰胡测试: is_hu={result.is_hu}, type={result.hu_type}, fans={result.fans}")
    
    # 清一色测试
    qingyise_tiles = [0, 0, 0, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 8]  # 筒一色
    result = game.can_hu(qingyise_tiles, is_big_hu=True)
    print(f"清一色测试: is_hu={result.is_hu}, type={result.hu_type}, fans={result.fans}")
    
    # 将将胡测试 - 222 555 888 222 555 88
    jiangjiang_tiles = [1, 1, 1, 4, 4, 4, 7, 7, 7, 10, 10, 10, 13, 13]
    result = game.can_hu(jiangjiang_tiles, is_big_hu=True)
    print(f"将将胡测试: is_hu={result.is_hu}, type={result.hu_type}, fans={result.fans}")
    
    # 七小对测试 - 正确的7对
    qixiaodui_tiles = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]
    result = game.can_hu(qixiaodui_tiles, is_big_hu=True)
    print(f"七小对测试: is_hu={result.is_hu}, type={result.hu_type}, fans={result.fans}")
    
    # 测试扎鸟
    print("\n=== 扎鸟算法测试 ===")
    game.birds = [0, 8, 10, 17]  # 1筒,9筒,2条,9条
    total, details = game.calculate_birds(game.birds, hu_seat=0, is_zimo=True)
    print(f"中鸟总数: {total}, 详情: {details}")
    
    # 测试结算
    print("\n=== 结算测试 ===")
    hu_info = {"seat": 0, "fans": 6, "patterns": ["碰碰胡"], "is_big_hu": True}
    result = game.settle(hu_info, is_zimo=True, is_zhuang=False, base_score=2)
    print(f"结算结果: {result}")
    
    # 测试打牌推荐
    print("\n=== 打牌推荐测试 ===")
    strategy = StrategyCalculator(game)
    hand_tiles = [0, 0, 0, 1, 1, 2, 3, 9, 9, 10, 18, 18, 20, 22]
    best, score, details = strategy.recommend_discard(hand_tiles)
    print(f"推荐打牌: {Tile(best).display}, 评分: {score:.2f}")
    print(f"详情: {details}")
