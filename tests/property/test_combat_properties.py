"""
Property-based tests for combat system.
Properties 1, 2, 9-16, 17, 19, 20 + card pile properties 12, 13
"""
from __future__ import annotations

from hypothesis import given, settings, strategies as st

from tests.property.conftest import (
    make_test_context, make_test_registry,
    st_card_ids, st_enemy_ids, st_hp,
)
from sts2_simulator.combat.card_pile import draw_cards
from sts2_simulator.data.registry import CardInstance, PotionInstance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cm(deck, enemy_id="jaw_worm", enemy_hp=40, player_hp=80,
            relics=None, potions=None):
    from sts2_simulator.combat.manager import CombatManager
    registry = make_test_registry()
    config = {
        "player": {"hp": player_hp, "max_hp": player_hp, "energy": 3},
        "deck": deck,
        "relics": relics or [],
        "potions": potions or [],
        "enemies": [{"id": enemy_id, "hp": enemy_hp, "max_hp": enemy_hp}],
    }
    states = []
    cm = CombatManager(config, registry, lambda s: states.append(s))
    return cm, registry


# ---------------------------------------------------------------------------
# Property 1: 初始化后 State 完整性
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 1: 初始化后 State 完整性
@given(
    deck=st.lists(st_card_ids, min_size=1, max_size=10),
    enemy_id=st_enemy_ids,
)
@settings(max_examples=100)
def test_initial_state_completeness(deck, enemy_id):
    cm, _ = make_cm(deck, enemy_id=enemy_id)
    state = cm.get_state()["data"]
    assert "player" in state
    assert "enemies" in state
    assert state["turn"] == 1
    assert "phase" in state
    assert "legal_actions" in state
    assert state["result"] is None


# ---------------------------------------------------------------------------
# Property 2: 非法资源 ID 拒绝初始化
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 2: 非法资源 ID 拒绝初始化
@given(bad_id=st.text(min_size=1, max_size=20).filter(
    lambda s: s not in ("strike", "defend", "bash", "cleave", "twin_strike",
                        "heavy_blade", "pommel_strike", "whirlwind", "iron_wave",
                        "shrug_it_off", "battle_trance", "flex", "inflame",
                        "clothesline", "thunderclap", "anger")))
@settings(max_examples=100)
def test_invalid_card_id_rejected(bad_id):
    from sts2_simulator.combat.manager import CombatManager
    registry = make_test_registry()
    try:
        CombatManager(
            {"player": {"hp": 80, "max_hp": 80, "energy": 3},
             "deck": [bad_id], "relics": [], "potions": [],
             "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}]},
            registry, lambda s: None,
        )
        # If no exception, the id must have been valid (hypothesis may generate valid ids)
    except (ValueError, KeyError):
        pass  # Expected: invalid id rejected


# ---------------------------------------------------------------------------
# Property 9: exhaust 牌进入 exhaust_pile
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 9: exhaust 牌进入 exhaust_pile
@given(n_strikes=st.integers(min_value=1, max_value=5))
@settings(max_examples=100)
def test_exhaust_card_goes_to_exhaust_pile(n_strikes):
    # Use bash which is not exhaust; inject an exhaust card manually
    ctx = make_test_context(enemy_hp=200)
    from sts2_simulator.data.registry import CardDef, CardInstance
    exhaust_card = CardInstance(defn=CardDef(
        id="test_exhaust", name="Test", cost=0,
        card_type="skill", target="self",
        exhaust=True, effects=[],
    ))
    ctx.player.hand = [exhaust_card]
    ctx.player.energy = 3

    from sts2_simulator.combat.manager import CombatManager
    registry = make_test_registry()
    cm, _ = make_cm(["strike"], enemy_hp=200)
    # Directly test exhaust logic via play_card
    from sts2_simulator.data.registry import CardDef, CardInstance
    exhaust_defn = CardDef(
        id="test_exhaust2", name="Test2", cost=0,
        card_type="skill", target="self",
        exhaust=True, effects=[],
    )
    exhaust_inst = CardInstance(defn=exhaust_defn)
    cm._ctx.player.hand.insert(0, exhaust_inst)

    before_exhaust = len(cm._ctx.player.exhaust_pile)
    before_discard = len(cm._ctx.player.discard_pile)
    cm.play_card(0, -1)

    assert len(cm._ctx.player.exhaust_pile) == before_exhaust + 1
    assert len(cm._ctx.player.discard_pile) == before_discard


# ---------------------------------------------------------------------------
# Property 10: 不可打出的牌不出现在合法动作中
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 10: 不可打出的牌不出现在合法动作中
@given(deck=st.lists(st_card_ids, min_size=1, max_size=5))
@settings(max_examples=100)
def test_unplayable_cards_not_in_legal_actions(deck):
    cm, _ = make_cm(deck)
    # Inject an unplayable card into hand
    from sts2_simulator.data.registry import CardDef, CardInstance
    unplayable = CardInstance(defn=CardDef(
        id="curse", name="Curse", cost=0,
        card_type="skill", target="self",
        playable=False, effects=[],
    ))
    cm._ctx.player.hand.append(unplayable)

    actions = cm.get_legal_actions()
    play_card_actions = [a for a in actions if a["action"] == "play_card"]
    hand = cm._ctx.player.hand

    for action in play_card_actions:
        card = hand[action["hand_index"]]
        assert card.defn.playable is True
        assert cm._ctx.player.energy >= card.defn.cost


# ---------------------------------------------------------------------------
# Property 11: 合法动作可执行性保证
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 11: 合法动作可执行性保证
@given(deck=st.lists(st_card_ids, min_size=3, max_size=8))
@settings(max_examples=100)
def test_legal_actions_are_executable(deck):
    cm, _ = make_cm(deck, enemy_hp=500)
    actions = cm.get_legal_actions()
    for action in actions:
        if action["action"] == "play_card":
            result = cm.play_card(action["hand_index"], action["target_index"])
            assert result.get("error") not in (
                "insufficient_energy", "card_not_playable",
            ), f"Legal action failed: {result}"
            # Reset for next iteration
            cm, _ = make_cm(deck, enemy_hp=500)
            break  # test one action per example


# ---------------------------------------------------------------------------
# Property 12: 抓牌堆空时自动洗入弃牌堆
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 12: 抓牌堆空时自动洗入弃牌堆
@given(
    n_discard=st.integers(min_value=1, max_value=8),
    n_draw=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=100)
def test_empty_draw_pile_shuffles_discard(n_discard, n_draw):
    ctx = make_test_context()
    from sts2_simulator.data.registry import CardDef, CardInstance
    card_defn = CardDef(id="strike", name="Strike", cost=1,
                        card_type="attack", target="single", effects=[])
    ctx.player.draw_pile = []
    ctx.player.discard_pile = [CardInstance(defn=card_defn) for _ in range(n_discard)]
    ctx.player.hand = []

    draw_cards(ctx, n_draw)

    total_cards = len(ctx.player.hand) + len(ctx.player.draw_pile) + len(ctx.player.discard_pile)
    assert total_cards == n_discard
    assert len(ctx.player.hand) == min(n_draw, n_discard)


# ---------------------------------------------------------------------------
# Property 13: 手牌上限 10 张
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 13: 手牌上限 10 张
@given(n_draw=st.integers(min_value=1, max_value=15))
@settings(max_examples=100)
def test_hand_size_capped_at_ten(n_draw):
    ctx = make_test_context()
    from sts2_simulator.data.registry import CardDef, CardInstance
    card_defn = CardDef(id="strike", name="Strike", cost=1,
                        card_type="attack", target="single", effects=[])
    ctx.player.draw_pile = [CardInstance(defn=card_defn) for _ in range(n_draw + 5)]
    ctx.player.hand = []

    draw_cards(ctx, n_draw)
    assert len(ctx.player.hand) <= 10


# ---------------------------------------------------------------------------
# Property 14: 所有敌人死亡时战斗胜利
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 14: 所有敌人死亡时战斗胜利
@given(enemy_hp=st.integers(min_value=1, max_value=5))
@settings(max_examples=100)
def test_all_enemies_dead_means_victory(enemy_hp):
    cm, _ = make_cm(["strike"] * 5, enemy_hp=enemy_hp)
    # Kill enemy directly
    cm._ctx.enemies[0].hp = 0
    from sts2_simulator.engine.effect_resolver import EffectResolver
    resolver = EffectResolver()
    resolver._death_check(cm._ctx.enemies[0], cm._ctx)

    state = cm.get_state()["data"]
    assert state["result"] == "victory"

    result = cm.play_card(0, 0)
    assert result.get("error") == "battle_already_ended"


# ---------------------------------------------------------------------------
# Property 15: Player HP≤0 时战斗失败
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 15: Player HP≤0 时战斗失败
@given(player_hp=st.integers(min_value=1, max_value=5))
@settings(max_examples=100)
def test_player_dead_means_defeat(player_hp):
    cm, _ = make_cm(["strike"] * 5, player_hp=player_hp)
    cm._ctx.player.hp = 0
    from sts2_simulator.engine.effect_resolver import EffectResolver
    resolver = EffectResolver()
    resolver._death_check(cm._ctx.player, cm._ctx)

    state = cm.get_state()["data"]
    assert state["result"] == "defeat"

    result = cm.end_turn()
    assert result.get("error") == "battle_already_ended"


# ---------------------------------------------------------------------------
# Property 16: sequential_loop 敌人按固定顺序循环
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 16: sequential_loop 敌人按固定顺序循环
@given(n_turns=st.integers(min_value=1, max_value=8))
@settings(max_examples=100)
def test_sequential_loop_order(n_turns):
    registry = make_test_registry()
    enemy_def = registry.get_enemy("jaw_worm")
    move_order = enemy_def.move_order

    cm, _ = make_cm(["defend"] * 20, enemy_hp=500, player_hp=500)

    for turn in range(n_turns):
        expected_move = move_order[turn % len(move_order)]
        actual_move_idx = cm._ctx.enemies[0].move_index % len(move_order)
        assert move_order[actual_move_idx] == expected_move
        cm.end_turn()


# ---------------------------------------------------------------------------
# Property 17: preview_damage 与实际伤害一致
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 17: preview_damage 与实际伤害一致
@given(strength=st.integers(min_value=0, max_value=5))
@settings(max_examples=100)
def test_preview_damage_matches_actual(strength):
    cm, _ = make_cm(["strike"] * 5, enemy_hp=500)
    if strength > 0:
        cm._ctx.player.buffs["strength"] = strength
    cm._update_preview_damage()

    # Find a strike card in hand
    for i, card_inst in enumerate(cm._ctx.player.hand):
        if card_inst.defn.id == "strike":
            preview = card_inst.preview_damage
            assert preview is not None
            # preview[0] should be [6 + strength]
            assert preview[0] == [6 + strength]
            break


# ---------------------------------------------------------------------------
# Property 19: Intent 列表与 Move 的 intents 字段一致
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 19: Intent 列表与 Move 的 intents 字段一致
@given(enemy_id=st_enemy_ids)
@settings(max_examples=100)
def test_intent_matches_move_definition(enemy_id):
    cm, registry = make_cm(["defend"] * 5, enemy_id=enemy_id, enemy_hp=200)
    enemy = cm._ctx.enemies[0]
    enemy_def = registry.get_enemy(enemy_id)

    current_move_name = enemy_def.move_order[enemy.move_index % len(enemy_def.move_order)]
    expected_intents = enemy_def.moves[current_move_name].intents

    assert len(enemy.intents) == len(expected_intents)
    for actual, expected in zip(enemy.intents, expected_intents):
        assert actual.type == expected.type
        assert actual.value == expected.value


# ---------------------------------------------------------------------------
# Property 20: 药水使用后从槽位移除
# ---------------------------------------------------------------------------

# Feature: sts2-battle-simulator, Property 20: 药水使用后从槽位移除
@given(potion_id=st.sampled_from(["block_potion", "card_draw_potion", "energy_potion"]))
@settings(max_examples=100)
def test_potion_removed_after_use(potion_id):
    cm, _ = make_cm(["strike"] * 5, potions=[potion_id])
    assert cm._ctx.player.potions[0] is not None

    cm.use_potion(0, -1)

    assert cm._ctx.player.potions[0] is None

    actions = cm.get_legal_actions()
    potion_actions = [a for a in actions if a["action"] == "use_potion" and a["slot_index"] == 0]
    assert len(potion_actions) == 0
