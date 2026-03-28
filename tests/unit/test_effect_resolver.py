"""
Unit tests for EffectResolver.
Tests will fail until EffectResolver is implemented in task 7.2.

Validates: Requirements 3.6, 3.7, 3.11, 3.12, 4.4, 4.5, 4.6, 4.7, 6.7
"""
from __future__ import annotations

import pytest
from math import floor

from sts2_simulator.combat.player import Player
from sts2_simulator.combat.enemy import Enemy
from sts2_simulator.combat.context import BattleContext
from sts2_simulator.engine.event_bus import EventBus
from sts2_simulator.data.registry import Registry, BuffDef
from sts2_simulator.engine.effect_resolver import EffectResolver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_player(**kwargs) -> Player:
    defaults = dict(
        hp=80, max_hp=80, energy=3, max_energy=3, block=0,
        buffs={}, hand=[], draw_pile=[], discard_pile=[],
        exhaust_pile=[], relics=[], potions=[],
    )
    defaults.update(kwargs)
    return Player(**defaults)


def make_enemy(**kwargs) -> Enemy:
    defaults = dict(
        id="test", hp=40, max_hp=40, block=0, buffs={},
        is_dead=False, move_index=0, intents=[],
    )
    defaults.update(kwargs)
    return Enemy(**defaults)


def make_registry() -> Registry:
    registry = Registry()
    registry.register_buff(BuffDef(id="strength", name="力量", is_permanent=False, reduce_on="turn_end"))
    registry.register_buff(BuffDef(id="weak", name="虚弱", is_permanent=False, reduce_on="turn_start"))
    registry.register_buff(BuffDef(id="vulnerable", name="脆弱", is_permanent=False, reduce_on="turn_start"))
    return registry


def make_ctx(player=None, enemies=None) -> BattleContext:
    return BattleContext(
        player=player or make_player(),
        enemies=enemies or [make_enemy()],
        turn=1,
        phase="player_action",
        event_bus=EventBus(),
        registry=make_registry(),
        log=[],
        on_state_change=lambda s: None,
    )


# ---------------------------------------------------------------------------
# deal_damage tests
# ---------------------------------------------------------------------------

class TestDealDamage:
    def test_damage_less_than_block_hp_unchanged(self):
        """伤害 < Block 时 HP 不变，Block 减少。Validates: Requirement 3.6"""
        enemy = make_enemy(hp=40, block=10)
        ctx = make_ctx(enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 6, "target": "single"}
        er.resolve(effect, ctx, ctx.player, enemy)
        assert enemy.hp == 40
        assert enemy.block == 4

    def test_damage_equal_to_block_hp_unchanged_block_zero(self):
        """伤害 = Block 时 HP 不变，Block 归零。Validates: Requirement 3.6"""
        enemy = make_enemy(hp=40, block=6)
        ctx = make_ctx(enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 6, "target": "single"}
        er.resolve(effect, ctx, ctx.player, enemy)
        assert enemy.hp == 40
        assert enemy.block == 0

    def test_damage_greater_than_block_hp_decreases_block_zero(self):
        """伤害 > Block 时 HP 减少，Block 归零。Validates: Requirement 3.6"""
        enemy = make_enemy(hp=40, block=4)
        ctx = make_ctx(enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 10, "target": "single"}
        er.resolve(effect, ctx, ctx.player, enemy)
        assert enemy.hp == 34  # 40 - (10 - 4)
        assert enemy.block == 0

    def test_damage_no_block_full_hp_reduction(self):
        """无 Block 时伤害直接扣 HP。Validates: Requirement 3.6"""
        enemy = make_enemy(hp=40, block=0)
        ctx = make_ctx(enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 8, "target": "single"}
        er.resolve(effect, ctx, ctx.player, enemy)
        assert enemy.hp == 32
        assert enemy.block == 0

    def test_damage_with_strength_buff(self):
        """力量加成正确增加伤害。Validates: Requirement 4.4"""
        player = make_player(buffs={"strength": 3})
        enemy = make_enemy(hp=40, block=0)
        ctx = make_ctx(player=player, enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 6, "target": "single"}
        er.resolve(effect, ctx, player, enemy)
        assert enemy.hp == 40 - (6 + 3)  # base + strength

    def test_damage_with_weak_buff(self):
        """虚弱减少攻击方伤害（×0.75 向下取整）。Validates: Requirement 4.7"""
        player = make_player(buffs={"weak": 2})
        enemy = make_enemy(hp=40, block=0)
        ctx = make_ctx(player=player, enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 8, "target": "single"}
        er.resolve(effect, ctx, player, enemy)
        expected = floor(8 * 0.75)  # 6
        assert enemy.hp == 40 - expected

    def test_damage_with_vulnerable_buff(self):
        """脆弱增加受到的伤害（×1.5 向下取整）。Validates: Requirement 4.6"""
        enemy = make_enemy(hp=40, block=0, buffs={"vulnerable": 2})
        ctx = make_ctx(enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 8, "target": "single"}
        er.resolve(effect, ctx, ctx.player, enemy)
        expected = floor(8 * 1.5)  # 12
        assert enemy.hp == 40 - expected

    def test_damage_weak_and_vulnerable_combined(self):
        """脆弱 + 虚弱同时存在时的组合计算。Validates: Requirements 4.6, 4.7"""
        player = make_player(buffs={"weak": 1})
        enemy = make_enemy(hp=40, block=0, buffs={"vulnerable": 1})
        ctx = make_ctx(player=player, enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 10, "target": "single"}
        er.resolve(effect, ctx, player, enemy)
        # weak first: floor(10 * 0.75) = 7, then vulnerable: floor(7 * 1.5) = 10
        after_weak = floor(10 * 0.75)
        after_vulnerable = floor(after_weak * 1.5)
        assert enemy.hp == 40 - after_vulnerable


# ---------------------------------------------------------------------------
# deal_damage_all tests
# ---------------------------------------------------------------------------

class TestDealDamageAll:
    def test_deal_damage_all_hits_all_living_enemies(self):
        """deal_damage_all 对所有存活敌人生效。Validates: Requirement 3.7"""
        enemies = [
            make_enemy(id="e1", hp=30, block=0),
            make_enemy(id="e2", hp=20, block=0),
        ]
        ctx = make_ctx(enemies=enemies)
        er = EffectResolver()
        effect = {"type": "deal_damage_all", "value": 8}
        er.resolve(effect, ctx, ctx.player, None)
        assert enemies[0].hp == 22
        assert enemies[1].hp == 12

    def test_deal_damage_all_skips_dead_enemies(self):
        """deal_damage_all 跳过已死亡敌人。Validates: Requirement 3.7"""
        dead_enemy = make_enemy(id="dead", hp=0, block=0, is_dead=True)
        live_enemy = make_enemy(id="live", hp=30, block=0)
        ctx = make_ctx(enemies=[dead_enemy, live_enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage_all", "value": 5}
        er.resolve(effect, ctx, ctx.player, None)
        assert dead_enemy.hp == 0  # unchanged
        assert live_enemy.hp == 25

    def test_deal_damage_all_with_block(self):
        """deal_damage_all 对有 Block 的敌人正确抵消。Validates: Requirement 3.7"""
        enemies = [
            make_enemy(id="e1", hp=30, block=3),
            make_enemy(id="e2", hp=20, block=10),
        ]
        ctx = make_ctx(enemies=enemies)
        er = EffectResolver()
        effect = {"type": "deal_damage_all", "value": 8}
        er.resolve(effect, ctx, ctx.player, None)
        assert enemies[0].hp == 25  # 30 - (8-3)
        assert enemies[0].block == 0
        assert enemies[1].hp == 20  # block absorbs all
        assert enemies[1].block == 2  # 10 - 8


# ---------------------------------------------------------------------------
# deal_damage_multi tests
# ---------------------------------------------------------------------------

class TestDealDamageMulti:
    def test_multi_hit_each_hit_independent_block(self):
        """每次 hit 独立触发 Block 抵消。Validates: Requirement 3.11"""
        # Block=5, 2 hits of 4 each
        # hit1: block absorbs 4, block=1, hp unchanged
        # hit2: block absorbs 1, hp -= 3
        enemy = make_enemy(hp=40, block=5)
        ctx = make_ctx(enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage_multi", "value": 4, "count": 2, "target": "single"}
        er.resolve(effect, ctx, ctx.player, enemy)
        assert enemy.block == 0
        assert enemy.hp == 37  # 40 - 3

    def test_multi_hit_no_block(self):
        """连击无 Block 时每次 hit 直接扣 HP。Validates: Requirement 3.11"""
        enemy = make_enemy(hp=40, block=0)
        ctx = make_ctx(enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage_multi", "value": 5, "count": 3, "target": "single"}
        er.resolve(effect, ctx, ctx.player, enemy)
        assert enemy.hp == 25  # 40 - 15

    def test_multi_hit_single_count(self):
        """count=1 的连击等同于单体伤害。Validates: Requirement 3.11"""
        enemy = make_enemy(hp=40, block=0)
        ctx = make_ctx(enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage_multi", "value": 6, "count": 1, "target": "single"}
        er.resolve(effect, ctx, ctx.player, enemy)
        assert enemy.hp == 34


# ---------------------------------------------------------------------------
# gain_block tests
# ---------------------------------------------------------------------------

class TestGainBlock:
    def test_gain_block_increases_block(self):
        """gain_block 正确增加 Block 值。Validates: Requirement 4.5"""
        player = make_player(block=0)
        ctx = make_ctx(player=player)
        er = EffectResolver()
        effect = {"type": "gain_block", "value": 5}
        er.resolve(effect, ctx, player, player)
        assert player.block == 5

    def test_gain_block_stacks_on_existing(self):
        """gain_block 叠加到已有 Block 上。Validates: Requirement 4.5"""
        player = make_player(block=8)
        ctx = make_ctx(player=player)
        er = EffectResolver()
        effect = {"type": "gain_block", "value": 5}
        er.resolve(effect, ctx, player, player)
        assert player.block == 13

    def test_gain_block_on_enemy(self):
        """gain_block 对敌人也生效。Validates: Requirement 4.5"""
        enemy = make_enemy(block=0)
        ctx = make_ctx(enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "gain_block", "value": 6}
        er.resolve(effect, ctx, enemy, enemy)
        assert enemy.block == 6


# ---------------------------------------------------------------------------
# draw_cards tests
# ---------------------------------------------------------------------------

class TestDrawCards:
    def test_draw_cards_moves_from_draw_pile_to_hand(self):
        """draw_cards 从牌堆抽牌到手牌。Validates: Requirement 3.12"""
        card_a = object()
        card_b = object()
        card_c = object()
        player = make_player(hand=[], draw_pile=[card_a, card_b, card_c])
        ctx = make_ctx(player=player)
        er = EffectResolver()
        effect = {"type": "draw_cards", "value": 2}
        er.resolve(effect, ctx, player, player)
        assert len(player.hand) == 2
        assert len(player.draw_pile) == 1

    def test_draw_cards_draws_correct_count(self):
        """draw_cards 抽取正确数量的牌。Validates: Requirement 3.12"""
        cards = [object() for _ in range(5)]
        player = make_player(hand=[], draw_pile=list(cards))
        ctx = make_ctx(player=player)
        er = EffectResolver()
        effect = {"type": "draw_cards", "value": 3}
        er.resolve(effect, ctx, player, player)
        assert len(player.hand) == 3
        assert len(player.draw_pile) == 2

    def test_draw_cards_empty_draw_pile(self):
        """draw_cards 牌堆为空时不抛出异常。Validates: Requirement 3.12"""
        player = make_player(hand=[], draw_pile=[])
        ctx = make_ctx(player=player)
        er = EffectResolver()
        effect = {"type": "draw_cards", "value": 2}
        er.resolve(effect, ctx, player, player)  # should not raise
        assert len(player.hand) == 0


# ---------------------------------------------------------------------------
# apply_buff tests
# ---------------------------------------------------------------------------

class TestApplyBuff:
    def test_apply_buff_to_self(self):
        """apply_buff target=self 调用 BuffManager.apply 施加 Buff。Validates: Requirement 6.7"""
        player = make_player()
        ctx = make_ctx(player=player)
        er = EffectResolver()
        effect = {"type": "apply_buff", "buff_id": "strength", "value": 2, "target": "self"}
        er.resolve(effect, ctx, player, make_enemy())
        assert player.buffs.get("strength") == 2

    def test_apply_buff_to_target(self):
        """apply_buff target=target 施加 Buff 到目标。Validates: Requirement 6.7"""
        player = make_player()
        enemy = make_enemy()
        ctx = make_ctx(player=player, enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "apply_buff", "buff_id": "vulnerable", "value": 2, "target": "target"}
        er.resolve(effect, ctx, player, enemy)
        assert enemy.buffs.get("vulnerable") == 2

    def test_apply_buff_stacks_accumulate(self):
        """apply_buff 多次施加同一 Buff 时层数叠加。Validates: Requirement 6.7"""
        player = make_player()
        enemy = make_enemy()
        ctx = make_ctx(player=player, enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "apply_buff", "buff_id": "vulnerable", "value": 2, "target": "target"}
        er.resolve(effect, ctx, player, enemy)
        er.resolve(effect, ctx, player, enemy)
        assert enemy.buffs.get("vulnerable") == 4


# ---------------------------------------------------------------------------
# gain_energy tests
# ---------------------------------------------------------------------------

class TestGainEnergy:
    def test_gain_energy_increases_player_energy(self):
        """gain_energy 增加玩家能量。Validates: Requirement 3.12"""
        player = make_player(energy=1, max_energy=3)
        ctx = make_ctx(player=player)
        er = EffectResolver()
        effect = {"type": "gain_energy", "value": 2}
        er.resolve(effect, ctx, player, player)
        assert player.energy == 3

    def test_gain_energy_from_zero(self):
        """gain_energy 从 0 能量增加。Validates: Requirement 3.12"""
        player = make_player(energy=0, max_energy=3)
        ctx = make_ctx(player=player)
        er = EffectResolver()
        effect = {"type": "gain_energy", "value": 1}
        er.resolve(effect, ctx, player, player)
        assert player.energy == 1


# ---------------------------------------------------------------------------
# Combined buff interaction tests
# ---------------------------------------------------------------------------

class TestCombinedBuffs:
    def test_weak_and_vulnerable_combined_calculation(self):
        """脆弱 + 虚弱同时存在时的组合计算（含 Block）。Validates: Requirements 4.6, 4.7"""
        player = make_player(buffs={"weak": 2})
        enemy = make_enemy(hp=50, block=5, buffs={"vulnerable": 2})
        ctx = make_ctx(player=player, enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 12, "target": "single"}
        er.resolve(effect, ctx, player, enemy)
        # weak: floor(12 * 0.75) = 9
        # vulnerable: floor(9 * 1.5) = 13
        # block absorbs 5, hp -= 8
        after_weak = floor(12 * 0.75)
        after_vulnerable = floor(after_weak * 1.5)
        absorbed = min(5, after_vulnerable)
        expected_hp = 50 - (after_vulnerable - absorbed)
        assert enemy.hp == expected_hp
        assert enemy.block == 0

    def test_strength_weak_vulnerable_combined(self):
        """力量 + 虚弱 + 脆弱三者组合计算。Validates: Requirements 4.4, 4.6, 4.7"""
        player = make_player(buffs={"strength": 3, "weak": 1})
        enemy = make_enemy(hp=50, block=0, buffs={"vulnerable": 1})
        ctx = make_ctx(player=player, enemies=[enemy])
        er = EffectResolver()
        effect = {"type": "deal_damage", "value": 6, "target": "single"}
        er.resolve(effect, ctx, player, enemy)
        # strength: 6 + 3 = 9
        # weak: floor(9 * 0.75) = 6
        # vulnerable: floor(6 * 1.5) = 9
        after_strength = 6 + 3
        after_weak = floor(after_strength * 0.75)
        after_vulnerable = floor(after_weak * 1.5)
        assert enemy.hp == 50 - after_vulnerable
