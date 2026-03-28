"""SingleBattleRunner — runs one battle, wiring CombatManager to Bridge."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sts2_simulator.combat.manager import CombatManager
from sts2_simulator.data.buffs import register_builtin_buffs
from sts2_simulator.data.cards import register_builtin_cards
from sts2_simulator.data.enemies import register_builtin_enemies
from sts2_simulator.data.potions import register_builtin_potions
from sts2_simulator.data.relics import register_builtin_relics
from sts2_simulator.data.registry import Registry
from sts2_simulator.runner.config import EnemyConfig, SingleBattleConfig


def _make_registry() -> Registry:
    registry = Registry()
    register_builtin_cards(registry)
    register_builtin_relics(registry)
    register_builtin_enemies(registry)
    register_builtin_potions(registry)
    register_builtin_buffs(registry)
    return registry


class SingleBattleRunner:
    def __init__(self, config: SingleBattleConfig, bridge) -> None:
        self.config = config
        self.bridge = bridge

    def run(self, registry: Registry | None = None) -> dict:
        """Run a single battle and return the battle log.

        The bridge's on_state_change callback drives the battle loop:
        each time CombatManager pushes a state, the bridge receives it,
        sends back an action (play_card / end_turn / use_potion), and
        calls the corresponding CombatManager method.

        For the ZmqBridge this happens over the network; for tests a
        mock bridge can drive the loop directly.

        Returns a log dict with keys: result, final_hp, turns.
        """
        if registry is None:
            registry = _make_registry()

        cm_config = {
            "player": {
                "hp": self.config.player_hp,
                "max_hp": self.config.player_max_hp,
                "energy": self.config.player_energy,
            },
            "deck": self.config.deck,
            "relics": self.config.relics,
            "potions": self.config.potions,
            "enemies": [
                {"id": e.id, "hp": e.hp, "max_hp": e.max_hp}
                for e in self.config.enemies
            ],
        }

        # Wire bridge: on_state_change drives the battle loop.
        # The bridge must call cm.play_card / cm.end_turn / cm.use_potion
        # until the battle ends (state["data"]["result"] is not None).
        cm = CombatManager(cm_config, registry, self.bridge.on_state_change)

        # Expose cm to bridge so it can call back into it
        if hasattr(self.bridge, "set_combat_manager"):
            self.bridge.set_combat_manager(cm)
            # Bridge drives the loop — wait for it to finish
        else:
            # No bridge-driven loop: run a greedy auto-pilot until battle ends.
            # This is used by CampaignRunner and simple test mocks.
            self._run_autopilot(cm)

        final_state = cm.get_state()
        result = final_state["data"]["result"]
        final_hp = final_state["data"]["player"]["hp"]
        turns = final_state["data"]["turn"]

        log = {
            "result": result,
            "final_hp": final_hp,
            "turns": turns,
        }

        self.bridge.on_battle_end(log)
        return log

    @staticmethod
    def _run_autopilot(cm: CombatManager) -> None:
        """Greedy auto-pilot: always play the first legal action until battle ends."""
        max_iterations = 10_000  # safety guard against infinite loops
        for _ in range(max_iterations):
            state = cm.get_state()
            if state["data"]["result"] is not None:
                break
            actions = state["data"]["legal_actions"]
            if not actions:
                break
            action = actions[0]
            if action["action"] == "play_card":
                cm.play_card(action["hand_index"], action["target_index"])
            elif action["action"] == "use_potion":
                cm.use_potion(action["slot_index"], action["target_index"])
            elif action["action"] == "end_turn":
                cm.end_turn()
            else:
                break

    @classmethod
    def from_json(cls, path: str, bridge) -> "SingleBattleRunner":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        enemies = [
            EnemyConfig(id=e["id"], hp=e["hp"], max_hp=e["max_hp"])
            for e in data.get("enemies", [])
        ]

        config = SingleBattleConfig(
            player_hp=data["player_hp"],
            player_max_hp=data["player_max_hp"],
            player_energy=data.get("player_energy", 3),
            deck=data.get("deck", []),
            relics=data.get("relics", []),
            potions=data.get("potions", []),
            enemies=enemies,
        )

        return cls(config, bridge)
