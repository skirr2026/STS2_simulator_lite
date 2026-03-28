from __future__ import annotations
from sts2_simulator.data.registry import CardDef, Registry


def register_builtin_cards(registry: Registry) -> None:
    cards = [
        CardDef(
            id="strike",
            name="打击",
            cost=1,
            card_type="attack",
            target="single",
            effects=[{"type": "deal_damage", "value": 6, "target": "single"}],
        ),
        CardDef(
            id="heavy_blade",
            name="重刃",
            cost=2,
            card_type="attack",
            target="single",
            effects=[{"type": "deal_damage", "value": 14, "target": "single"}],
        ),
        CardDef(
            id="twin_strike",
            name="双重打击",
            cost=1,
            card_type="attack",
            target="single",
            effects=[{"type": "deal_damage_multi", "value": 5, "count": 2, "target": "single"}],
        ),
        CardDef(
            id="pommel_strike",
            name="剑柄打击",
            cost=1,
            card_type="attack",
            target="single",
            effects=[
                {"type": "deal_damage", "value": 9, "target": "single"},
                {"type": "draw_cards", "value": 1},
            ],
        ),
        CardDef(
            id="whirlwind",
            name="旋风斩",
            cost=0,
            card_type="attack",
            target="all",
            effects=[{"type": "deal_damage_all", "value": 5}],
        ),
        CardDef(
            id="cleave",
            name="横扫",
            cost=1,
            card_type="attack",
            target="all",
            effects=[{"type": "deal_damage_all", "value": 8}],
        ),
        CardDef(
            id="defend",
            name="防御",
            cost=1,
            card_type="skill",
            target="self",
            effects=[{"type": "gain_block", "value": 5}],
        ),
        CardDef(
            id="iron_wave",
            name="铁波",
            cost=1,
            card_type="skill",
            target="single",
            effects=[
                {"type": "gain_block", "value": 5},
                {"type": "deal_damage", "value": 5, "target": "single"},
            ],
        ),
        CardDef(
            id="shrug_it_off",
            name="一笑置之",
            cost=1,
            card_type="skill",
            target="self",
            effects=[
                {"type": "gain_block", "value": 8},
                {"type": "draw_cards", "value": 1},
            ],
        ),
        CardDef(
            id="battle_trance",
            name="战斗恍惚",
            cost=0,
            card_type="skill",
            target="self",
            effects=[{"type": "draw_cards", "value": 3}],
        ),
        CardDef(
            id="flex",
            name="弯曲",
            cost=0,
            card_type="skill",
            target="self",
            effects=[{"type": "apply_buff", "buff_id": "strength", "value": 2, "target": "self"}],
        ),
        CardDef(
            id="inflame",
            name="燃烧",
            cost=1,
            card_type="power",
            target="self",
            effects=[{"type": "apply_buff", "buff_id": "strength", "value": 2, "target": "self"}],
        ),
        CardDef(
            id="clothesline",
            name="晾衣绳",
            cost=2,
            card_type="attack",
            target="single",
            effects=[
                {"type": "deal_damage", "value": 12, "target": "single"},
                {"type": "apply_buff", "buff_id": "weak", "value": 2, "target": "target"},
            ],
        ),
        CardDef(
            id="bash",
            name="猛击",
            cost=2,
            card_type="attack",
            target="single",
            effects=[
                {"type": "deal_damage", "value": 8, "target": "single"},
                {"type": "apply_buff", "buff_id": "vulnerable", "value": 2, "target": "target"},
            ],
        ),
        CardDef(
            id="thunderclap",
            name="雷击",
            cost=1,
            card_type="attack",
            target="all",
            effects=[
                {"type": "deal_damage_all", "value": 4},
                {"type": "apply_buff", "buff_id": "vulnerable", "value": 1, "target": "target"},
            ],
        ),
        CardDef(
            id="anger",
            name="愤怒",
            cost=0,
            card_type="attack",
            target="single",
            effects=[{"type": "deal_damage", "value": 6, "target": "single"}],
        ),
    ]

    for card in cards:
        registry.register_card(card)
