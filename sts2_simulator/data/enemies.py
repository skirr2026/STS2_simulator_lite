from sts2_simulator.combat.enemy import Intent, IntentType
from sts2_simulator.data.registry import EnemyDef, MoveDef, Registry


def register_builtin_enemies(registry: Registry) -> None:
    # --- Jaw Worm ---
    registry.register_enemy(EnemyDef(
        id="jaw_worm",
        name="颚虫",
        hp=44,
        max_hp=44,
        moves={
            "chomp": MoveDef(
                name="chomp",
                intents=[Intent(type=IntentType.ATTACK, value=11, target="player")],
                effects=[{"type": "deal_damage", "value": 11, "target": "player"}],
            ),
            "thrash": MoveDef(
                name="thrash",
                intents=[
                    Intent(type=IntentType.ATTACK, value=7, target="player"),
                    Intent(type=IntentType.DEFEND, value=5, target="self"),
                ],
                effects=[
                    {"type": "deal_damage", "value": 7, "target": "player"},
                    {"type": "gain_block", "value": 5, "target": "self"},
                ],
            ),
            "bellow": MoveDef(
                name="bellow",
                intents=[
                    Intent(type=IntentType.BUFF, value=3, target="self"),
                    Intent(type=IntentType.DEFEND, value=6, target="self"),
                ],
                effects=[
                    {"type": "apply_buff", "buff_id": "strength", "value": 3, "target": "self"},
                    {"type": "gain_block", "value": 6, "target": "self"},
                ],
            ),
        },
        move_pattern="sequential_loop",
        move_order=["chomp", "thrash", "bellow", "thrash", "bellow"],
    ))

    # --- Acid Slime M ---
    registry.register_enemy(EnemyDef(
        id="acid_slime_m",
        name="酸性史莱姆",
        hp=28,
        max_hp=28,
        moves={
            "corrosive_spit": MoveDef(
                name="corrosive_spit",
                intents=[
                    Intent(type=IntentType.ATTACK, value=7, target="player"),
                    Intent(type=IntentType.DEBUFF, value=2, target="player"),
                ],
                effects=[
                    {"type": "deal_damage", "value": 7, "target": "player"},
                    {"type": "apply_buff", "buff_id": "vulnerable", "value": 2, "target": "player"},
                ],
            ),
            "tackle": MoveDef(
                name="tackle",
                intents=[Intent(type=IntentType.ATTACK, value=10, target="player")],
                effects=[{"type": "deal_damage", "value": 10, "target": "player"}],
            ),
            "lick": MoveDef(
                name="lick",
                intents=[Intent(type=IntentType.DEBUFF, value=1, target="player")],
                effects=[{"type": "apply_buff", "buff_id": "weak", "value": 1, "target": "player"}],
            ),
        },
        move_pattern="sequential_loop",
        move_order=["corrosive_spit", "tackle", "lick", "corrosive_spit"],
    ))

    # --- Sentinel ---
    registry.register_enemy(EnemyDef(
        id="sentinel",
        name="哨兵",
        hp=54,
        max_hp=54,
        moves={
            "strike": MoveDef(
                name="strike",
                intents=[Intent(type=IntentType.ATTACK, value=9, target="player")],
                effects=[{"type": "deal_damage", "value": 9, "target": "player"}],
            ),
            "tackle": MoveDef(
                name="tackle",
                intents=[Intent(type=IntentType.ATTACK, value=15, target="player")],
                effects=[{"type": "deal_damage", "value": 15, "target": "player"}],
            ),
            "escape": MoveDef(
                name="escape",
                intents=[Intent(type=IntentType.BUFF, value=5, target="self")],
                effects=[{"type": "apply_buff", "buff_id": "strength", "value": 5, "target": "self"}],
            ),
        },
        move_pattern="sequential_loop",
        move_order=["strike", "tackle", "escape", "strike"],
    ))
