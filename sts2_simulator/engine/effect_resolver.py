from __future__ import annotations

from math import floor
from typing import TYPE_CHECKING

from sts2_simulator.combat.enemy import Enemy
from sts2_simulator.combat.player import Player
from sts2_simulator.engine.buff_manager import BuffManager

if TYPE_CHECKING:
    from sts2_simulator.combat.context import BattleContext


class EffectResolver:
    def __init__(self):
        self._buff_manager = BuffManager()

    def resolve(self, effect: dict, ctx: "BattleContext", source, target) -> None:
        match effect["type"]:
            case "deal_damage":
                self.resolve_damage(source, target, effect["value"], ctx)
            case "deal_damage_all":
                for enemy in ctx.enemies:
                    if not enemy.is_dead:
                        self.resolve_damage(source, enemy, effect["value"], ctx)
            case "deal_damage_multi":
                count = effect.get("count", 1)
                for _ in range(count):
                    if isinstance(target, Enemy) and target.is_dead:
                        break
                    self.resolve_damage(source, target, effect["value"], ctx)
            case "gain_block":
                target.block += effect["value"]
            case "draw_cards":
                n = effect["value"]
                for _ in range(n):
                    if ctx.player.draw_pile:
                        ctx.player.hand.append(ctx.player.draw_pile.pop(0))
            case "apply_buff":
                buff_target = source if effect.get("target") == "self" else target
                self._buff_manager.apply(buff_target, effect["buff_id"], effect["value"], ctx)
            case "gain_energy":
                ctx.player.energy += effect["value"]

    def resolve_damage(self, source, target, base_value: int, ctx: "BattleContext") -> bool:
        """Apply damage from source to target. Returns True if battle ended."""
        ctx.event_bus.emit("pre_damage", ctx, source=source, target=target, value=base_value)

        value = base_value + source.buffs.get("strength", 0)
        if source.buffs.get("weak", 0) > 0:
            value = floor(value * 0.75)
        if target.buffs.get("vulnerable", 0) > 0:
            value = floor(value * 1.5)

        absorbed = min(target.block, value)
        target.block -= absorbed
        target.hp -= (value - absorbed)

        ctx.event_bus.emit("post_damage", ctx, source=source, target=target, actual=value - absorbed)
        return self._death_check(target, ctx)

    def _death_check(self, target, ctx: "BattleContext") -> bool:
        """Returns True if battle ended."""
        if isinstance(target, Enemy) and target.hp <= 0:
            target.is_dead = True
            if all(e.is_dead for e in ctx.enemies):
                ctx.phase = "ended"
                ctx.log.append({"event": "victory"})
                ctx.event_bus.emit("battle_end", ctx, result="victory")
                return True
        elif isinstance(target, Player) and target.hp <= 0:
            ctx.phase = "ended"
            ctx.log.append({"event": "defeat"})
            ctx.event_bus.emit("battle_end", ctx, result="defeat")
            return True
        return False

    def compute_preview(self, card, ctx: "BattleContext") -> dict | None:
        """Compute preview damage for a card against all living enemies.

        Returns a dict mapping enemy index to list of per-hit damage values,
        or None if the card is not an attack.
        """
        if card.card_type != "attack":
            return None
        result = {}
        for i, enemy in enumerate(ctx.enemies):
            if enemy.is_dead:
                continue
            hits = []
            for effect in card.effects:
                if effect["type"] in ("deal_damage", "deal_damage_multi"):
                    count = effect.get("count", 1)
                    base = effect["value"] + ctx.player.buffs.get("strength", 0)
                    if ctx.player.buffs.get("weak", 0) > 0:
                        base = floor(base * 0.75)
                    if enemy.buffs.get("vulnerable", 0) > 0:
                        base = floor(base * 1.5)
                    hits.extend([base] * count)
            result[i] = hits
        return result
