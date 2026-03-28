from __future__ import annotations
from sts2_simulator.data.registry import PotionDef, Registry


def register_builtin_potions(registry: Registry) -> None:
    registry.register_potion(PotionDef(
        id="block_potion",
        name="护甲药水",
        target="self",
        effects=[{"type": "gain_block", "value": 12}],
    ))
    registry.register_potion(PotionDef(
        id="attack_potion",
        name="攻击药水",
        target="single",
        effects=[{"type": "deal_damage", "value": 10}],
    ))
    registry.register_potion(PotionDef(
        id="card_draw_potion",
        name="抓牌药水",
        target="none",
        effects=[{"type": "draw_cards", "value": 3}],
    ))
    registry.register_potion(PotionDef(
        id="energy_potion",
        name="能量药水",
        target="none",
        effects=[{"type": "gain_energy", "value": 2}],
    ))
