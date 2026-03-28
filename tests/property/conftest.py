"""
Hypothesis strategies for property-based tests.
"""
from __future__ import annotations

from hypothesis import strategies as st
from sts2_simulator.combat.context import BattleContext
from sts2_simulator.combat.enemy import Enemy, Intent, IntentType
from sts2_simulator.combat.player import Player
from sts2_simulator.data.registry import (
    CardDef, CardInstance, Registry,
    EnemyDef, MoveDef, BuffDef,
)
from sts2_simulator.engine.event_bus import EventBus


def make_test_registry() -> Registry:
    from sts2_simulator.data.cards import register_builtin_cards
    from sts2_simulator.data.relics import register_builtin_relics
    from sts2_simulator.data.enemies import register_builtin_enemies
    from sts2_simulator.data.potions import register_builtin_potions
    from sts2_simulator.data.buffs import register_builtin_buffs
    r = Registry()
    register_builtin_cards(r)
    register_builtin_relics(r)
    register_builtin_enemies(r)
    register_builtin_potions(r)
    register_builtin_buffs(r)
    return r


def make_test_context(
    player_hp: int = 50,
    player_block: int = 0,
    player_buffs: dict | None = None,
    enemy_hp: int = 40,
    enemy_block: int = 0,
    enemy_buffs: dict | None = None,
    draw_pile: list | None = None,
    hand: list | None = None,
) -> BattleContext:
    registry = make_test_registry()
    player = Player(
        hp=player_hp, max_hp=100,
        energy=3, max_energy=3,
        block=player_block,
        buffs=player_buffs or {},
        hand=hand or [],
        draw_pile=draw_pile or [],
        discard_pile=[], exhaust_pile=[],
        relics=[], potions=[],
    )
    enemy = Enemy(
        id="jaw_worm", hp=enemy_hp, max_hp=enemy_hp,
        block=enemy_block,
        buffs=enemy_buffs or {},
        is_dead=False, move_index=0,
        intents=[Intent(type=IntentType.ATTACK, value=11, target="player")],
    )
    return BattleContext(
        player=player,
        enemies=[enemy],
        turn=1,
        phase="player_action",
        event_bus=EventBus(),
        registry=registry,
        log=[],
        on_state_change=lambda s: None,
    )


def make_enemy(hp: int = 40, block: int = 0, buffs: dict | None = None) -> Enemy:
    return Enemy(
        id="jaw_worm", hp=hp, max_hp=hp,
        block=block, buffs=buffs or {},
        is_dead=False, move_index=0,
        intents=[],
    )


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

st_hp = st.integers(min_value=1, max_value=100)
st_block = st.integers(min_value=0, max_value=50)
st_damage = st.integers(min_value=1, max_value=80)
st_stacks = st.integers(min_value=1, max_value=10)
st_card_ids = st.sampled_from(["strike", "defend", "bash", "cleave", "twin_strike"])
st_enemy_ids = st.sampled_from(["jaw_worm", "acid_slime_m", "sentinel"])
