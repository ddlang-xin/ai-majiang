"""
长沙麻将后端 - 单元测试

运行方式: python3 backend/tests/test_mahjong.py
"""

import sys
sys.path.insert(0, 'backend')

from mahjong import Tile, HandTiles, Suit


class TestTile:
    """测试牌定义"""
    
    def test_tile_value_range(self):
        """测试牌值范围"""
        # 有效牌值
        for i in range(27):
            tile = Tile(i)
            assert tile.value == i
        
        # 无效牌值
        try:
            Tile(-1)
            assert False, "应该抛出异常"
        except ValueError:
            pass
        
        try:
            Tile(27)
            assert False, "应该抛出异常"
        except ValueError:
            pass
        print("✓ 牌值范围测试通过")
    
    def test_tile_suit(self):
        """测试花色判断"""
        # 筒 0-8
        for i in range(9):
            assert Tile(i).suit == Suit.TONG
        
        # 条 9-17
        for i in range(9, 18):
            assert Tile(i).suit == Suit.TIAO
        
        # 万 18-26
        for i in range(18, 27):
            assert Tile(i).suit == Suit.WAN
        print("✓ 花色判断测试通过")
    
    def test_tile_number(self):
        """测试点数计算"""
        for suit_idx, suit in enumerate([Suit.TONG, Suit.TIAO, Suit.WAN]):
            for num in range(1, 10):
                value = suit_idx * 9 + (num - 1)
                tile = Tile(value)
                assert tile.number == num
        print("✓ 点数计算测试通过")
    
    def test_is_258(self):
        """测试258将牌判断"""
        # 2,5,8 是258将牌
        assert Tile(1).is_258 is True   # 筒2
        assert Tile(4).is_258 is True   # 筒5
        assert Tile(7).is_258 is True   # 筒8
        assert Tile(10).is_258 is True  # 条2
        
        # 其他点数不是258
        assert Tile(0).is_258 is False  # 筒1
        assert Tile(2).is_258 is False  # 筒3
        print("✓ 258将牌判断测试通过")
    
    def test_tile_display(self):
        """测试显示名称"""
        assert Tile(0).display == "筒1"
        assert Tile(8).display == "筒9"
        assert Tile(9).display == "条1"
        assert Tile(17).display == "条9"
        assert Tile(18).display == "万1"
        assert Tile(26).display == "万9"
        print("✓ 显示名称测试通过")


class TestHandTiles:
    """测试手牌管理"""
    
    def test_hand_tiles_init(self):
        """测试手牌初始化"""
        hand = HandTiles([0, 0, 0, 1, 1, 2])
        assert len(hand.tiles) == 6
        assert hand.tile_counts[0] == 3
        assert hand.tile_counts[1] == 2
        assert hand.tile_counts[2] == 1
        print("✓ 手牌初始化测试通过")
    
    def test_hand_tiles_empty(self):
        """测试空手牌"""
        hand = HandTiles()
        assert len(hand.tiles) == 0
        print("✓ 空手牌测试通过")
    
    def test_hand_tiles_sorted(self):
        """测试手牌排序"""
        hand = HandTiles([5, 1, 3, 2, 4])
        assert hand.tiles == [1, 2, 3, 4, 5]
        print("✓ 手牌排序测试通过")
    
    def test_hand_tiles_tile_counts(self):
        """测试牌计数"""
        hand = HandTiles([0, 0, 0, 0])  # 4张筒1
        counts = hand.tile_counts
        assert counts[0] == 4
        assert sum(counts) == 4
        print("✓ 牌计数测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("开始运行长沙麻将后端单元测试")
    print("=" * 50)
    
    # 牌定义测试
    print("\n[测试类: TestTile]")
    test_tile = TestTile()
    test_tile.test_tile_value_range()
    test_tile.test_tile_suit()
    test_tile.test_tile_number()
    test_tile.test_is_258()
    test_tile.test_tile_display()
    
    # 手牌管理测试
    print("\n[测试类: TestHandTiles]")
    test_hand = TestHandTiles()
    test_hand.test_hand_tiles_init()
    test_hand.test_hand_tiles_empty()
    test_hand.test_hand_tiles_sorted()
    test_hand.test_hand_tiles_tile_counts()
    
    print("\n" + "=" * 50)
    print("所有测试通过! ✓")
    print("=" * 50)


if __name__ == '__main__':
    run_all_tests()
