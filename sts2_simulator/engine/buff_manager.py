from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sts2_simulator.combat.context import BattleContext

from sts2_simulator.combat.enemy import Enemy
from sts2_simulator.combat.player import Player


class BuffManager:
    def apply(self, target, buff_id: str, stacks: int, ctx: "BattleContext") -> None:
        """Accumulate buff stacks on target and emit on_buff_applied event."""
        target.buffs[buff_id] = target.buffs.get(buff_id, 0) + stacks
        ctx.event_bus.emit("on_buff_applied", ctx, buff_id=buff_id, stacks=stacks)

    def tick(self, target, ctx: "BattleContext", when: str | None = None) -> None:
        """Apply effect_fn (if any), reduce non-permanent buff stacks, then death-check if HP changed.
        
        If `when` is specified, only reduce buffs where reduce_on == when.
        If `when` is None, reduce all non-permanent buffs (backward compatible).
        """
        hp_before = target.hp
        # Iterate over a snapshot of buff keys to allow mutation during iteration
        for buff_id in list(target.buffs.keys()):
            stacks = target.buffs.get(buff_id)
            if stacks is None:
                continue
            buff_def = ctx.registry.get_buff(buff_id)
            # Apply effect if defined
            if getattr(buff_def, "effect_fn", None) is not None:
                buff_def.effect_fn(target, stacks, ctx)
            # Reduce stacks unless permanent, and only if when matches (or when is None)
            if not buff_def.is_permanent:
                if when is None or buff_def.reduce_on == when:
                    new_stacks = stacks - 1
                    if new_stacks <= 0:
                        del target.buffs[buff_id]
                    else:
                        target.buffs[buff_id] = new_stacks

        # Death check if HP changed
        if target.hp != hp_before:
            self._death_check(target, ctx)

    def tick_all(self, ctx: "BattleContext", when: str | None = None) -> None:
        """Tick buffs for player and all living enemies.
        
        If `when` is specified, only reduce buffs where reduce_on == when.
        If `when` is None, reduce all non-permanent buffs (backward compatible).
        """
        self.tick(ctx.player, ctx, when=when)
        for enemy in ctx.enemies:
            if not enemy.is_dead:
                self.tick(enemy, ctx, when=when)

    def _death_check(self, target, ctx: "BattleContext") -> None:
        if isinstance(target, Enemy):
            if target.hp <= 0:
                target.is_dead = True
                if all(e.is_dead for e in ctx.enemies):
                    ctx.phase = "ended"
        elif isinstance(target, Player):
            if target.hp <= 0:
                ctx.phase = "ended"
