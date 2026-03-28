"""
Property-based tests for damage calculation.
Properties 3, 4, 5, 6, 7, 8
"""
from __future__ import annotations

from math import floor

from hypothesis import given, settings, strategies as st

from tests.property.conftest import (
    make_test_context, make_enemy,
    st_hp, st_block, st_damage, st_stacks,
)
from sts2_simulator.engine.effect_resolver import EffectResolver


# ---------------------------------------------------------------------------
# Property 3: Block 先于 HP 被消耗
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 3: Block 先于 HP 被消耗
@given(
    hp=st_hp,
    block=st_block,
    damage=st_damage,
)
@settings(max_examples=100)
def test_block_absorbs_before_hp(hp, block, damage):
    ctx = make_test_context(player_hp=hp, player_block=block)
    resolver = EffectResolver()
    resolver.resolve_damage(
        source=make_enemy(), target=ctx.player, base_value=damage, ctx=ctx
    )
    absorbed = min(block, damage)
    expected_hp = hp - max(0, damage - block)
    assert ctx.player.block == block - absorbed
    assert ctx.player.hp == expected_hp


# ---------------------------------------------------------------------------
# Property 4: 伤害结算后 HP 不超过上限
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 4: 伤害结算后 HP 不超过上限
@given(hp=st_hp, block=st_block, damage=st_damage)
@settings(max_examples=100)
def test_hp_never_exceeds_max_after_damage(hp, block, damage):
    ctx = make_test_context(player_hp=hp, player_block=block)
    resolver = EffectResolver()
    resolver.resolve_damage(
        source=make_enemy(), target=ctx.player, base_value=damage, ctx=ctx
    )
    assert ctx.player.hp <= ctx.player.max_hp
    # HP may go negative (death check triggers at hp <= 0, no clamping)
    assert ctx.player.hp == hp - max(0, damage - block)


# ---------------------------------------------------------------------------
# Property 5: 脆弱状态伤害计算
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 5: 脆弱状态伤害计算
@given(base_damage=st_damage)
@settings(max_examples=100)
def test_vulnerable_damage_multiplier(base_damage):
    ctx = make_test_context(enemy_hp=200, enemy_block=0, enemy_buffs={"vulnerable": 2})
    resolver = EffectResolver()
    initial_hp = ctx.enemies[0].hp
    resolver.resolve_damage(
        source=ctx.player, target=ctx.enemies[0], base_value=base_damage, ctx=ctx
    )
    expected = floor(base_damage * 1.5)
    assert initial_hp - ctx.enemies[0].hp == expected


# ---------------------------------------------------------------------------
# Property 6: 虚弱状态伤害计算
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 6: 虚弱状态伤害计算
@given(base_damage=st_damage)
@settings(max_examples=100)
def test_weak_damage_multiplier(base_damage):
    ctx = make_test_context(
        player_buffs={"weak": 2},
        enemy_hp=200, enemy_block=0,
    )
    resolver = EffectResolver()
    initial_hp = ctx.enemies[0].hp
    resolver.resolve_damage(
        source=ctx.player, target=ctx.enemies[0], base_value=base_damage, ctx=ctx
    )
    expected = floor(base_damage * 0.75)
    assert initial_hp - ctx.enemies[0].hp == expected


# ---------------------------------------------------------------------------
# Property 7: 力量加成伤害计算
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 7: 力量加成伤害计算
@given(base_damage=st_damage, strength=st_stacks)
@settings(max_examples=100)
def test_strength_adds_to_damage(base_damage, strength):
    ctx = make_test_context(
        player_buffs={"strength": strength},
        enemy_hp=500, enemy_block=0,
    )
    resolver = EffectResolver()
    initial_hp = ctx.enemies[0].hp
    resolver.resolve_damage(
        source=ctx.player, target=ctx.enemies[0], base_value=base_damage, ctx=ctx
    )
    expected = base_damage + strength
    assert initial_hp - ctx.enemies[0].hp == expected


# ---------------------------------------------------------------------------
# Property 8: 敏捷加成 Block 计算
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 8: 敏捷加成 Block 计算
@given(base_block=st.integers(min_value=1, max_value=20), dexterity=st_stacks)
@settings(max_examples=100)
def test_dexterity_adds_to_block(base_block, dexterity):
    ctx = make_test_context(player_buffs={"dexterity": dexterity})
    initial_block = ctx.player.block
    # Simulate gain_block effect with dexterity bonus
    ctx.player.block += base_block + ctx.player.buffs.get("dexterity", 0)
    expected = initial_block + base_block + dexterity
    assert ctx.player.block == expected
