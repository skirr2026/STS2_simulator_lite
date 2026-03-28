"""
Built-in relic static data — requirement 6.2.
"""
from sts2_simulator.data.registry import Registry, RelicDef


def register_builtin_relics(registry: Registry) -> None:
    relics = [
        RelicDef(
            id="akabeko",
            name="赤牛",
            trigger="turn_start",
            effects=[{"type": "first_attack_bonus", "value": 8}],
        ),
        RelicDef(
            id="bag_of_preparation",
            name="准备袋",
            trigger="battle_start",
            effects=[{"type": "draw_cards", "value": 2}],
        ),
        RelicDef(
            id="bronze_scales",
            name="铜鳞",
            trigger="on_damage_taken",
            effects=[{"type": "thorns", "value": 3}],
        ),
        RelicDef(
            id="pen_nib",
            name="笔尖",
            trigger="on_card_played",
            effects=[{"type": "every_nth_attack_double", "n": 10}],
        ),
        RelicDef(
            id="odd_mushroom",
            name="奇异蘑菇",
            trigger="on_buff_applied",
            effects=[{"type": "halve_weak_stacks"}],
        ),
    ]
    for relic in relics:
        registry.register_relic(relic)
