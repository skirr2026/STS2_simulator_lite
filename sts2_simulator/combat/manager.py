from __future__ import annotations

import random
from typing import Callable

from sts2_simulator.combat.card_pile import draw_cards, discard_hand
from sts2_simulator.combat.context import BattleContext
from sts2_simulator.combat.enemy import Enemy
from sts2_simulator.combat.player import Player
from sts2_simulator.data.registry import (
    CardInstance,
    PotionInstance,
    RelicInstance,
    Registry,
)
from sts2_simulator.engine.effect_resolver import EffectResolver
from sts2_simulator.engine.event_bus import EventBus


class CombatManager:
    def __init__(
        self,
        config: dict,
        registry: Registry,
        on_state_change: Callable[[dict], None],
    ) -> None:
        # --- 1. Validate IDs ---
        for card_id in config.get("deck", []):
            try:
                registry.get_card(card_id)
            except KeyError:
                raise ValueError(f"unknown_card_id: {card_id}")

        for relic_id in config.get("relics", []):
            try:
                registry.get_relic(relic_id)
            except KeyError:
                raise ValueError(f"unknown_relic_id: {relic_id}")

        for enemy_cfg in config.get("enemies", []):
            try:
                registry.get_enemy(enemy_cfg["id"])
            except KeyError:
                raise ValueError(f"unknown_enemy_id: {enemy_cfg['id']}")

        # --- 2. Build instances ---
        player_cfg = config.get("player", {})

        draw_pile = [
            CardInstance(defn=registry.get_card(cid))
            for cid in config.get("deck", [])
        ]
        random.shuffle(draw_pile)

        relics = [
            RelicInstance(defn=registry.get_relic(rid))
            for rid in config.get("relics", [])
        ]

        potions: list = [
            PotionInstance(defn=registry.get_potion(pid))
            for pid in config.get("potions", [])
        ]

        player = Player(
            hp=player_cfg.get("hp", 80),
            max_hp=player_cfg.get("max_hp", 80),
            energy=player_cfg.get("energy", 3),
            max_energy=player_cfg.get("energy", 3),
            block=0,
            buffs={},
            hand=[],
            draw_pile=draw_pile,
            discard_pile=[],
            exhaust_pile=[],
            relics=relics,
            potions=potions,
        )

        enemies = [
            Enemy(
                id=ecfg["id"],
                hp=ecfg["hp"],
                max_hp=ecfg["max_hp"],
                block=0,
                buffs={},
                is_dead=False,
                move_index=0,
                intents=[],
            )
            for ecfg in config.get("enemies", [])
        ]

        # --- 3. Create EventBus and BattleContext ---
        event_bus = EventBus()

        self._ctx = BattleContext(
            player=player,
            enemies=enemies,
            turn=1,
            phase="player_action",
            event_bus=event_bus,
            registry=registry,
            log=[],
            on_state_change=on_state_change,
        )

        self._resolver = EffectResolver()

        # --- 4. Register relic event handlers (priority=10) ---
        for relic_inst in relics:
            relic_def = relic_inst.defn
            handler = self._make_relic_handler(relic_def)
            if handler is not None:
                event_bus.on(relic_def.trigger, handler, priority=10)

        # --- 5. Emit battle_start ---
        event_bus.emit("battle_start", self._ctx)

        # --- 6. Set initial intents for each enemy ---
        for i, enemy in enumerate(enemies):
            enemy_def = registry.get_enemy(enemy.id)
            if enemy_def.move_order:
                first_move_name = enemy_def.move_order[0]
                first_move = enemy_def.moves[first_move_name]
                enemy.intents = list(first_move.intents)

        # --- 7. Draw 5 cards ---
        draw_cards(self._ctx, 5)

        # --- 8. Compute initial preview_damage ---
        self._update_preview_damage()

        # --- 9. Notify state ---
        on_state_change(self.get_state())

    # ------------------------------------------------------------------
    # Relic handler factory
    # ------------------------------------------------------------------

    def _make_relic_handler(self, relic_def):
        """Return an EventBus handler for the given relic, or None."""
        if relic_def.id == "bag_of_preparation":
            def handler(ctx, **kwargs):
                draw_cards(ctx, 2)
            return handler

        # Other relics: placeholder (no-op for now)
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        ctx = self._ctx
        player = ctx.player

        hand_data = []
        for idx, card_inst in enumerate(player.hand):
            defn = card_inst.defn
            preview = card_inst.preview_damage
            # Serialize preview_damage: convert int keys to str for JSON compat
            if preview is not None:
                preview = {str(k): v for k, v in preview.items()}
            hand_data.append({
                "index": idx,
                "card_id": defn.id,
                "cost": defn.cost,
                "playable": defn.playable,
                "exhaust": defn.exhaust,
                "preview_damage": preview,
            })

        potions_data = []
        for slot, pot in enumerate(player.potions):
            if pot is None:
                potions_data.append(None)
            else:
                potions_data.append({"slot": slot, "id": pot.defn.id})

        enemies_data = []
        for idx, enemy in enumerate(ctx.enemies):
            intents_data = [
                {"type": intent.type.value, "value": intent.value}
                for intent in enemy.intents
            ]
            enemies_data.append({
                "index": idx,
                "id": enemy.id,
                "hp": enemy.hp,
                "max_hp": enemy.max_hp,
                "block": enemy.block,
                "buffs": dict(enemy.buffs),
                "is_dead": enemy.is_dead,
                "intents": intents_data,
            })

        result = None
        if ctx.phase == "ended":
            # Determine victory or defeat from log
            for entry in reversed(ctx.log):
                if entry.get("event") in ("victory", "defeat"):
                    result = entry["event"]
                    break

        return {
            "type": "state",
            "data": {
                "turn": ctx.turn,
                "phase": ctx.phase,
                "player": {
                    "hp": player.hp,
                    "max_hp": player.max_hp,
                    "energy": player.energy,
                    "max_energy": player.max_energy,
                    "block": player.block,
                    "buffs": dict(player.buffs),
                    "hand": hand_data,
                    "draw_pile_count": len(player.draw_pile),
                    "discard_pile_count": len(player.discard_pile),
                    "potions": potions_data,
                },
                "enemies": enemies_data,
                "legal_actions": self.get_legal_actions(),
                "result": result,
            },
        }

    def get_legal_actions(self) -> list[dict]:
        ctx = self._ctx
        actions: list[dict] = []

        if ctx.phase == "ended":
            return actions

        player = ctx.player
        living_enemies = [i for i, e in enumerate(ctx.enemies) if not e.is_dead]

        for hand_idx, card_inst in enumerate(player.hand):
            defn = card_inst.defn
            if not defn.playable:
                continue
            if player.energy < defn.cost:
                continue
            # Determine targeting
            if defn.target == "single":
                for enemy_idx in living_enemies:
                    actions.append({
                        "action": "play_card",
                        "hand_index": hand_idx,
                        "target_index": enemy_idx,
                    })
            else:
                # "self", "all", "none" — no specific enemy target
                actions.append({
                    "action": "play_card",
                    "hand_index": hand_idx,
                    "target_index": -1,
                })

        # Potions
        for slot, pot in enumerate(player.potions):
            if pot is None:
                continue
            pot_def = pot.defn
            if pot_def.target == "single":
                for enemy_idx in living_enemies:
                    actions.append({
                        "action": "use_potion",
                        "slot_index": slot,
                        "target_index": enemy_idx,
                    })
            else:
                actions.append({
                    "action": "use_potion",
                    "slot_index": slot,
                    "target_index": -1,
                })

        actions.append({"action": "end_turn"})
        return actions

    # ------------------------------------------------------------------
    # play_card
    # ------------------------------------------------------------------

    def play_card(self, hand_index: int, target_index: int) -> dict:
        ctx = self._ctx
        player = ctx.player

        # 1. Battle ended?
        if ctx.phase == "ended":
            return {"ok": False, "error": "battle_already_ended"}

        # 2. Valid hand index?
        if hand_index < 0 or hand_index >= len(player.hand):
            return {"ok": False, "error": f"invalid_hand_index: {hand_index}"}

        card = player.hand[hand_index]

        # 3. Playable?
        if not card.defn.playable:
            return {"ok": False, "error": "card_not_playable"}

        # 4. Enough energy?
        if player.energy < card.defn.cost:
            return {"ok": False, "error": "insufficient_energy"}

        # 5. Valid target?
        if card.defn.target == "single":
            if (
                target_index < 0
                or target_index >= len(ctx.enemies)
                or ctx.enemies[target_index].is_dead
            ):
                return {"ok": False, "error": "invalid_target: enemy_dead"}

        # --- Execute ---
        ctx.event_bus.emit("pre_action", ctx)

        player.energy -= card.defn.cost

        # Determine target
        if card.defn.target == "single":
            target = ctx.enemies[target_index]
        else:
            target = player

        # Execute effects
        if card.defn.effect_fn is not None:
            card.defn.effect_fn(card, ctx, player, target)
        else:
            for effect in card.defn.effects:
                self._resolver.resolve(effect, ctx, player, target)

        # Move card
        player.hand.remove(card)
        if card.defn.exhaust:
            player.exhaust_pile.append(card)
        else:
            player.discard_pile.append(card)

        ctx.event_bus.emit("post_action", ctx)
        ctx.event_bus.emit("on_card_played", ctx, card=card)

        # Update preview damage for remaining hand cards
        self._update_preview_damage()

        ctx.on_state_change(self.get_state())
        return {"ok": True}

    # ------------------------------------------------------------------
    # use_potion
    # ------------------------------------------------------------------

    def use_potion(self, slot_index: int, target_index: int) -> dict:
        ctx = self._ctx
        player = ctx.player
        enemies = ctx.enemies

        # 1. Battle ended?
        if ctx.phase == "ended":
            return {"ok": False, "error": "battle_already_ended"}

        # 2. Valid slot?
        if (
            slot_index < 0
            or slot_index >= len(player.potions)
            or player.potions[slot_index] is None
        ):
            return {"ok": False, "error": f"invalid_potion_slot: {slot_index}"}

        potion = player.potions[slot_index]

        # 3. Valid target?
        if potion.defn.target == "single":
            if (
                target_index < 0
                or target_index >= len(enemies)
                or enemies[target_index].is_dead
            ):
                return {"ok": False, "error": "invalid_target: enemy_dead"}

        # Determine target
        if potion.defn.target == "single":
            target = enemies[target_index]
        else:
            target = player

        # Execute effects
        if potion.defn.effect_fn is not None:
            potion.defn.effect_fn(potion, ctx, player, target)
        else:
            for effect in potion.defn.effects:
                self._resolver.resolve(effect, ctx, player, target)

        player.potions[slot_index] = None

        ctx.on_state_change(self.get_state())
        return {"ok": True}

    # ------------------------------------------------------------------
    # end_turn
    # ------------------------------------------------------------------

    def end_turn(self) -> dict:
        ctx = self._ctx

        if ctx.phase == "ended":
            return {"ok": False, "error": "battle_already_ended"}

        ctx.event_bus.emit("turn_end", ctx)
        self._resolver._buff_manager.tick_all(ctx, when="turn_end")
        discard_hand(ctx)

        # Enemy phase (stub — will be implemented in task 9.6)
        self._run_enemy_phase(ctx)

        # Start new player turn if battle not ended
        if ctx.phase != "ended":
            ctx.turn += 1
            ctx.player.block = 0
            ctx.player.energy = ctx.player.max_energy
            ctx.event_bus.emit("turn_start", ctx)
            self._resolver._buff_manager.tick_all(ctx, when="turn_start")
            draw_cards(ctx, 5)
            self._update_preview_damage()
            ctx.on_state_change(self.get_state())

        return {"ok": True}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _run_enemy_phase(self, ctx: BattleContext) -> None:
        """Execute the enemy action phase."""
        ctx.event_bus.emit("enemy_phase_start", ctx)

        for enemy in ctx.enemies:
            if enemy.is_dead:
                continue

            enemy_def = ctx.registry.get_enemy(enemy.id)

            # Determine current move name
            if enemy_def.move_pattern == "sequential_loop":
                move_name = enemy_def.move_order[enemy.move_index % len(enemy_def.move_order)]
            else:  # "fn"
                move_name = enemy_def.move_fn(enemy, ctx, ctx.turn)

            move = enemy_def.moves[move_name]

            # Execute move effects
            for effect in move.effects:
                target_str = effect.get("target", "player")
                target = ctx.player if target_str == "player" else enemy
                self._resolver.resolve(effect, ctx, enemy, target)

            # Death check: if player died (handled by EffectResolver), stop
            if ctx.phase == "ended":
                return

            # Update move_index
            enemy.move_index += 1

            # Calculate next intent
            next_move_name = enemy_def.move_order[enemy.move_index % len(enemy_def.move_order)]
            enemy.intents = list(enemy_def.moves[next_move_name].intents)

        ctx.event_bus.emit("enemy_phase_end", ctx)

    def _update_preview_damage(self) -> None:
        """Recompute preview_damage for all cards in hand."""
        ctx = self._ctx
        for card_inst in ctx.player.hand:
            card_inst.preview_damage = self._resolver.compute_preview(
                card_inst.defn, ctx
            )
