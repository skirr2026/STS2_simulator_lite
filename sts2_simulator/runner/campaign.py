"""CampaignRunner — runs a sequence of battles, carrying HP between them."""
from __future__ import annotations

import json

from sts2_simulator.runner.config import CampaignConfig, EnemyConfig, SingleBattleConfig
from sts2_simulator.runner.single import SingleBattleRunner, _make_registry


class CampaignRunner:
    def __init__(self, config: CampaignConfig, bridge) -> None:
        self.config = config
        self.bridge = bridge

    def run(self) -> dict:
        """Run all battles in sequence, carrying HP between them.

        Returns a campaign log dict with keys:
            result          - "victory" | "defeat"
            battles_completed - number of battles finished
            final_hp        - player HP at end of campaign
            total_turns     - sum of turns across all battles
        """
        cfg = self.config
        registry = _make_registry()

        current_hp = cfg.initial_player_hp
        max_hp = cfg.initial_player_max_hp
        battles_completed = 0
        total_turns = 0
        campaign_result = "victory"

        for battle_enemies in cfg.enemy_sequence:
            battle_config = SingleBattleConfig(
                player_hp=current_hp,
                player_max_hp=max_hp,
                player_energy=cfg.initial_energy,
                deck=list(cfg.initial_deck),
                relics=list(cfg.initial_relics),
                potions=list(cfg.initial_potions),
                enemies=list(battle_enemies),
            )

            runner = SingleBattleRunner(battle_config, self.bridge)
            log = runner.run(registry=registry)

            battles_completed += 1
            total_turns += log.get("turns", 0)
            current_hp = min(log["final_hp"], max_hp)

            if log["result"] == "defeat":
                campaign_result = "defeat"
                break

        campaign_log = {
            "result": campaign_result,
            "battles_completed": battles_completed,
            "final_hp": current_hp,
            "total_turns": total_turns,
        }

        self.bridge.on_campaign_end(campaign_log)
        return campaign_log

    @classmethod
    def from_json(cls, path: str, bridge) -> "CampaignRunner":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        enemy_sequence = [
            [EnemyConfig(id=e["id"], hp=e["hp"], max_hp=e["max_hp"]) for e in battle]
            for battle in data.get("enemy_sequence", [])
        ]

        config = CampaignConfig(
            initial_player_hp=data["initial_player_hp"],
            initial_player_max_hp=data["initial_player_max_hp"],
            initial_energy=data.get("initial_energy", 3),
            initial_deck=data.get("initial_deck", []),
            initial_relics=data.get("initial_relics", []),
            initial_potions=data.get("initial_potions", []),
            enemy_sequence=enemy_sequence,
        )

        return cls(config, bridge)
