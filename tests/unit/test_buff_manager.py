"""
Unit tests for BuffManager.
Tests will fail until BuffManager is implemented in task 6.2.

Validates: Requirements 4.2, 4.3
"""
from __future__ import annotations

import pytest

from sts2_simulator.combat.player import Player
from sts2_simulator.combat.enemy import Enemy
from sts2_simulator.combat.context import BattleContext
from sts2_simulator.engine.event_bus import EventBus
from sts2_simulator.data.registry import Registry, BuffDef
from sts2_simulator.engine.buff_manager import BuffManager


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


def make_ctx(player=None, enemies=None) -> BattleContext:
    registry = Registry()
    registry.register_buff(BuffDef(id="strength", name="力量", is_permanent=False, reduce_on="turn_end"))
    registry.register_buff(BuffDef(id="vulnerable", name="脆弱", is_permanent=False, reduce_on="turn_start"))
    registry.register_buff(BuffDef(id="permanent_buff", name="永久", is_permanent=True, reduce_on="turn_end"))
    return BattleContext(
        player=player or make_player(),
        enemies=enemies or [make_enemy()],
        turn=1,
        phase="player_action",
        event_bus=EventBus(),
        registry=registry,
        log=[],
        on_state_change=lambda s: None,
    )


# ---------------------------------------------------------------------------
# apply() tests
# ---------------------------------------------------------------------------

class TestApply:
    def test_apply_adds_stacks_to_empty_buffs(self):
        """apply() should add buff with given stacks when target has no existing buff."""
        ctx = make_ctx()
        bm = BuffManager()
        bm.apply(ctx.player, "strength", 3, ctx)
        assert ctx.player.buffs["strength"] == 3

    def test_apply_stacks_on_top_of_existing(self):
        """apply() should accumulate stacks on top of existing ones."""
        ctx = make_ctx(player=make_player(buffs={"strength": 2}))
        bm = BuffManager()
        bm.apply(ctx.player, "strength", 3, ctx)
        assert ctx.player.buffs["strength"] == 5

    def test_apply_to_enemy(self):
        """apply() should work on Enemy targets as well."""
        ctx = make_ctx()
        bm = BuffManager()
        bm.apply(ctx.enemies[0], "vulnerable", 2, ctx)
        assert ctx.enemies[0].buffs["vulnerable"] == 2

    def test_apply_triggers_on_buff_applied_event(self):
        """apply() should emit the on_buff_applied event."""
        ctx = make_ctx()
        events = []
        ctx.event_bus.on("on_buff_applied", lambda c, **kw: events.append(kw))
        bm = BuffManager()
        bm.apply(ctx.player, "strength", 1, ctx)
        assert len(events) == 1
        assert events[0]["buff_id"] == "strength"
        assert events[0]["stacks"] == 1

    def test_apply_multiple_different_buffs(self):
        """apply() should handle multiple distinct buffs independently."""
        ctx = make_ctx()
        bm = BuffManager()
        bm.apply(ctx.player, "strength", 2, ctx)
        bm.apply(ctx.player, "vulnerable", 1, ctx)
        assert ctx.player.buffs["strength"] == 2
        assert ctx.player.buffs["vulnerable"] == 1


# ---------------------------------------------------------------------------
# tick() tests
# ---------------------------------------------------------------------------

class TestTick:
    def test_tick_reduces_stacks_by_one(self):
        """tick() should reduce each non-permanent buff's stacks by 1."""
        ctx = make_ctx(player=make_player(buffs={"strength": 3}))
        bm = BuffManager()
        bm.tick(ctx.player, ctx)
        assert ctx.player.buffs["strength"] == 2

    def test_tick_removes_buff_when_stacks_reach_zero(self):
        """tick() should remove a buff entirely when its stacks drop to 0."""
        ctx = make_ctx(player=make_player(buffs={"strength": 1}))
        bm = BuffManager()
        bm.tick(ctx.player, ctx)
        assert "strength" not in ctx.player.buffs

    def test_tick_does_not_reduce_permanent_buff(self):
        """tick() should NOT reduce stacks of a buff with is_permanent=True."""
        ctx = make_ctx(player=make_player(buffs={"permanent_buff": 5}))
        bm = BuffManager()
        bm.tick(ctx.player, ctx)
        assert ctx.player.buffs["permanent_buff"] == 5

    def test_tick_reduces_only_non_permanent_buffs(self):
        """tick() should reduce non-permanent buffs but leave permanent ones intact."""
        ctx = make_ctx(player=make_player(buffs={"strength": 2, "permanent_buff": 3}))
        bm = BuffManager()
        bm.tick(ctx.player, ctx)
        assert ctx.player.buffs["strength"] == 1
        assert ctx.player.buffs["permanent_buff"] == 3

    def test_tick_on_enemy(self):
        """tick() should work on Enemy targets."""
        ctx = make_ctx(enemies=[make_enemy(buffs={"vulnerable": 2})])
        bm = BuffManager()
        bm.tick(ctx.enemies[0], ctx)
        assert ctx.enemies[0].buffs["vulnerable"] == 1

    def test_tick_removes_enemy_buff_at_zero(self):
        """tick() should remove enemy buff when stacks reach 0."""
        ctx = make_ctx(enemies=[make_enemy(buffs={"vulnerable": 1})])
        bm = BuffManager()
        bm.tick(ctx.enemies[0], ctx)
        assert "vulnerable" not in ctx.enemies[0].buffs

    def test_tick_no_buffs_is_noop(self):
        """tick() on a unit with no buffs should not raise and leave state unchanged."""
        ctx = make_ctx()
        bm = BuffManager()
        bm.tick(ctx.player, ctx)  # should not raise
        assert ctx.player.buffs == {}


# ---------------------------------------------------------------------------
# tick() with HP-change effect (death check)
# ---------------------------------------------------------------------------

class TestTickDeathCheck:
    def test_tick_with_hp_effect_triggers_death_check_on_lethal(self):
        """
        When a buff's on_tick effect reduces HP to 0, the unit should be
        marked dead (Enemy) or phase set to 'ended' (Player).
        This test uses a buff registered with an effect_fn that deals damage.
        """
        # Register a "poison" buff whose effect_fn reduces HP by stacks each tick
        ctx = make_ctx(enemies=[make_enemy(hp=3, buffs={"poison": 3})])
        poison_def = BuffDef(id="poison", name="中毒", is_permanent=False, reduce_on="turn_end")

        def poison_effect_fn(target, stacks, ctx):
            target.hp -= stacks

        poison_def_with_fn = BuffDef(id="poison", name="中毒", is_permanent=False, reduce_on="turn_end")
        # Attach effect_fn via attribute (design allows effect_fn on BuffDef)
        poison_def_with_fn.effect_fn = poison_effect_fn
        ctx.registry.register_buff(poison_def_with_fn)

        bm = BuffManager()
        bm.tick(ctx.enemies[0], ctx)

        # HP should have been reduced by 3 (the stacks value before reduction)
        # and enemy should be marked dead
        assert ctx.enemies[0].is_dead is True

    def test_tick_with_hp_effect_does_not_kill_if_hp_remains(self):
        """
        When a buff's on_tick effect reduces HP but target survives, is_dead stays False.
        """
        ctx = make_ctx(enemies=[make_enemy(hp=10, buffs={"poison": 3})])
        poison_def = BuffDef(id="poison", name="中毒", is_permanent=False, reduce_on="turn_end")

        def poison_effect_fn(target, stacks, ctx):
            target.hp -= stacks

        poison_def.effect_fn = poison_effect_fn
        ctx.registry.register_buff(poison_def)

        bm = BuffManager()
        bm.tick(ctx.enemies[0], ctx)

        assert ctx.enemies[0].is_dead is False
        assert ctx.enemies[0].hp == 7  # 10 - 3


# ---------------------------------------------------------------------------
# tick_all() tests
# ---------------------------------------------------------------------------

class TestTickAll:
    def test_tick_all_processes_player(self):
        """tick_all() should tick the player's buffs."""
        ctx = make_ctx(player=make_player(buffs={"strength": 2}))
        bm = BuffManager()
        bm.tick_all(ctx)
        assert ctx.player.buffs["strength"] == 1

    def test_tick_all_processes_all_enemies(self):
        """tick_all() should tick buffs on every enemy."""
        enemies = [
            make_enemy(id="e1", buffs={"vulnerable": 2}),
            make_enemy(id="e2", buffs={"vulnerable": 1}),
        ]
        ctx = make_ctx(enemies=enemies)
        bm = BuffManager()
        bm.tick_all(ctx)
        assert ctx.enemies[0].buffs["vulnerable"] == 1
        assert "vulnerable" not in ctx.enemies[1].buffs

    def test_tick_all_skips_dead_enemies(self):
        """tick_all() should not process buffs on dead enemies."""
        dead_enemy = make_enemy(id="dead", buffs={"vulnerable": 2}, is_dead=True)
        ctx = make_ctx(enemies=[dead_enemy])
        bm = BuffManager()
        bm.tick_all(ctx)
        # Dead enemy's buffs should remain untouched
        assert ctx.enemies[0].buffs["vulnerable"] == 2

    def test_tick_all_processes_player_and_enemies_together(self):
        """tick_all() should process both player and all living enemies in one call."""
        player = make_player(buffs={"strength": 3})
        enemies = [make_enemy(buffs={"vulnerable": 2})]
        ctx = make_ctx(player=player, enemies=enemies)
        bm = BuffManager()
        bm.tick_all(ctx)
        assert ctx.player.buffs["strength"] == 2
        assert ctx.enemies[0].buffs["vulnerable"] == 1
