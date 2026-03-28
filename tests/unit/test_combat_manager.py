"""
Unit tests for CombatManager initialization.
Validates: Requirements 1.1, 1.2, 1.3
"""
from __future__ import annotations
import pytest


def make_registry():
    from sts2_simulator.data.registry import Registry
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


VALID_CONFIG = {
    "player": {"hp": 54, "max_hp": 80, "energy": 3},
    "deck": ["strike", "strike", "defend"],
    "relics": ["akabeko"],
    "potions": ["block_potion"],
    "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
}

states_received = []


def on_state_change(state: dict) -> None:
    states_received.append(state)


# ---------------------------------------------------------------------------
# 1. 合法配置初始化成功，State 字段完整
# ---------------------------------------------------------------------------

class TestCombatManagerInitSuccess:
    def setup_method(self):
        states_received.clear()

    def test_get_state_returns_state_type(self):
        """get_state() 返回 type='state' 的字典"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        state = cm.get_state()
        assert state["type"] == "state"

    def test_state_data_has_required_fields(self):
        """State.data 包含 player、enemies、turn、phase、legal_actions、result"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        data = cm.get_state()["data"]
        assert "player" in data
        assert "enemies" in data
        assert "turn" in data
        assert "phase" in data
        assert "legal_actions" in data
        assert "result" in data

    def test_initial_turn_is_1(self):
        """初始化后 turn=1"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        assert cm.get_state()["data"]["turn"] == 1

    def test_initial_result_is_null(self):
        """初始化后 result=null（None）"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        assert cm.get_state()["data"]["result"] is None

    def test_player_fields_complete(self):
        """player 字段包含 hp、max_hp、energy、max_energy、block、buffs、hand、draw_pile_count、discard_pile_count、potions"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        player = cm.get_state()["data"]["player"]
        for field in ("hp", "max_hp", "energy", "max_energy", "block", "buffs",
                      "hand", "draw_pile_count", "discard_pile_count", "potions"):
            assert field in player, f"player 缺少字段: {field}"

    def test_player_hp_matches_config(self):
        """player.hp 与配置一致"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        assert cm.get_state()["data"]["player"]["hp"] == 54

    def test_enemies_list_length(self):
        """enemies 列表长度与配置一致"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        enemies = cm.get_state()["data"]["enemies"]
        assert len(enemies) == 1

    def test_enemy_fields_complete(self):
        """每个 enemy 包含 index、id、hp、max_hp、block、buffs、is_dead、intents"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        enemy = cm.get_state()["data"]["enemies"][0]
        for field in ("index", "id", "hp", "max_hp", "block", "buffs", "is_dead", "intents"):
            assert field in enemy, f"enemy 缺少字段: {field}"

    def test_legal_actions_is_list(self):
        """legal_actions 是列表"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        assert isinstance(cm.get_state()["data"]["legal_actions"], list)

    def test_legal_actions_contains_end_turn(self):
        """legal_actions 包含 end_turn 动作"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        actions = cm.get_state()["data"]["legal_actions"]
        assert any(a["action"] == "end_turn" for a in actions)

    def test_phase_is_player_action(self):
        """初始化后 phase 为 player_action（等待玩家指令）"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        phase = cm.get_state()["data"]["phase"]
        assert phase == "player_action"

    def test_on_state_change_called_on_init(self):
        """初始化时应调用 on_state_change 回调"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        CombatManager(VALID_CONFIG, registry, on_state_change)
        assert len(states_received) >= 1

    def test_deck_distributed_to_piles(self):
        """牌组中的牌应分布在手牌或抓牌堆中"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        cm = CombatManager(VALID_CONFIG, registry, on_state_change)
        player = cm.get_state()["data"]["player"]
        total = len(player["hand"]) + player["draw_pile_count"] + player["discard_pile_count"]
        assert total == len(VALID_CONFIG["deck"])


# ---------------------------------------------------------------------------
# 2. 不存在的卡牌 ID 返回错误，拒绝创建 Battle
# ---------------------------------------------------------------------------

class TestCombatManagerInvalidCardId:
    def test_unknown_card_raises_value_error(self):
        """不存在的卡牌 ID 应抛出 ValueError"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 54, "max_hp": 80, "energy": 3},
            "deck": ["strike", "nonexistent_card_xyz"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        with pytest.raises(ValueError, match="unknown_card_id"):
            CombatManager(config, registry, lambda s: None)

    def test_unknown_card_error_contains_id(self):
        """ValueError 消息应包含不存在的卡牌 ID"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        bad_id = "totally_fake_card"
        config = {
            "player": {"hp": 54, "max_hp": 80, "energy": 3},
            "deck": [bad_id],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        with pytest.raises(ValueError, match=bad_id):
            CombatManager(config, registry, lambda s: None)


# ---------------------------------------------------------------------------
# 3. 不存在的遗物 ID 返回错误
# ---------------------------------------------------------------------------

class TestCombatManagerInvalidRelicId:
    def test_unknown_relic_raises_value_error(self):
        """不存在的遗物 ID 应抛出 ValueError"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 54, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": ["nonexistent_relic_xyz"],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        with pytest.raises(ValueError, match="unknown_relic_id"):
            CombatManager(config, registry, lambda s: None)

    def test_unknown_relic_error_contains_id(self):
        """ValueError 消息应包含不存在的遗物 ID"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        bad_id = "totally_fake_relic"
        config = {
            "player": {"hp": 54, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": [bad_id],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        with pytest.raises(ValueError, match=bad_id):
            CombatManager(config, registry, lambda s: None)


# ---------------------------------------------------------------------------
# 4. 不存在的敌人 ID 返回错误
# ---------------------------------------------------------------------------

class TestCombatManagerInvalidEnemyId:
    def test_unknown_enemy_raises_value_error(self):
        """不存在的敌人 ID 应抛出 ValueError"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 54, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "nonexistent_enemy_xyz", "hp": 40, "max_hp": 40}],
        }
        with pytest.raises(ValueError, match="unknown_enemy_id"):
            CombatManager(config, registry, lambda s: None)

    def test_unknown_enemy_error_contains_id(self):
        """ValueError 消息应包含不存在的敌人 ID"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        bad_id = "totally_fake_enemy"
        config = {
            "player": {"hp": 54, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": bad_id, "hp": 40, "max_hp": 40}],
        }
        with pytest.raises(ValueError, match=bad_id):
            CombatManager(config, registry, lambda s: None)


# ===========================================================================
# play_card 单元测试
# Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 7.8
# ===========================================================================

def make_cm_with_hand(deck=None, enemies=None, energy=3):
    """Helper: create a CombatManager and return (cm, registry)."""
    from sts2_simulator.combat.manager import CombatManager
    registry = make_registry()
    config = {
        "player": {"hp": 80, "max_hp": 80, "energy": energy},
        "deck": deck or ["strike"],
        "relics": [],
        "potions": [],
        "enemies": enemies or [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
    }
    cm = CombatManager(config, registry, lambda s: None)
    return cm, registry


class TestPlayCardSuccess:
    """打出合法卡牌后能量减少、卡牌进入弃牌堆 (Req 3.1, 3.2)"""

    def test_play_card_returns_ok(self):
        """打出合法卡牌返回 {"ok": True}"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        # Find a strike in hand
        hand = cm._ctx.player.hand
        assert len(hand) >= 1
        result = cm.play_card(0, 0)
        assert result == {"ok": True}

    def test_play_card_reduces_energy(self):
        """打出费用为 1 的卡牌后能量减少 1"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        initial_energy = cm._ctx.player.energy
        cm.play_card(0, 0)
        assert cm._ctx.player.energy == initial_energy - 1

    def test_play_card_moves_to_discard_pile(self):
        """打出普通卡牌后卡牌进入弃牌堆"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        hand_before = len(cm._ctx.player.hand)
        cm.play_card(0, 0)
        player = cm._ctx.player
        # Card should be in discard pile, not in hand
        assert len(player.discard_pile) >= 1
        assert len(player.hand) == hand_before - 1

    def test_play_card_not_in_exhaust_pile_for_normal_card(self):
        """普通卡牌打出后不进入 exhaust_pile"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        cm.play_card(0, 0)
        assert len(cm._ctx.player.exhaust_pile) == 0


class TestPlayCardExhaust:
    """exhaust=True 的卡牌进入 exhaust_pile 而非 discard_pile (Req 3.2)"""

    def _make_cm_with_exhaust_card(self):
        """Create a CombatManager with a custom exhaust card in hand."""
        from sts2_simulator.combat.manager import CombatManager
        from sts2_simulator.data.registry import CardDef
        registry = make_registry()
        # Register a custom exhaust card
        registry.register_card(CardDef(
            id="test_exhaust_card",
            name="Test Exhaust Card",
            cost=1,
            card_type="skill",
            target="none",
            exhaust=True,
            playable=True,
            effects=[],
        ))
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["test_exhaust_card"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        return cm

    def test_exhaust_card_goes_to_exhaust_pile(self):
        """exhaust=True 的卡牌打出后进入 exhaust_pile"""
        cm = self._make_cm_with_exhaust_card()
        cm.play_card(0, -1)
        assert len(cm._ctx.player.exhaust_pile) == 1

    def test_exhaust_card_not_in_discard_pile(self):
        """exhaust=True 的卡牌打出后不进入 discard_pile"""
        cm = self._make_cm_with_exhaust_card()
        cm.play_card(0, -1)
        assert len(cm._ctx.player.discard_pile) == 0


class TestPlayCardInsufficientEnergy:
    """能量不足返回 insufficient_energy 错误 (Req 3.3)"""

    def test_insufficient_energy_returns_error(self):
        """能量不足时返回 {"ok": False, "error": "insufficient_energy"}"""
        from sts2_simulator.combat.manager import CombatManager
        from sts2_simulator.data.registry import CardDef
        registry = make_registry()
        # Register a card that costs more energy than the player has
        registry.register_card(CardDef(
            id="expensive_card",
            name="Expensive Card",
            cost=3,
            card_type="attack",
            target="single",
            exhaust=False,
            playable=True,
            effects=[],
        ))
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 1},
            "deck": ["expensive_card"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        result = cm.play_card(0, 0)
        assert result == {"ok": False, "error": "insufficient_energy"}

    def test_insufficient_energy_does_not_modify_state(self):
        """能量不足时不修改任何状态"""
        from sts2_simulator.combat.manager import CombatManager
        from sts2_simulator.data.registry import CardDef
        registry = make_registry()
        registry.register_card(CardDef(
            id="expensive_card2",
            name="Expensive Card 2",
            cost=3,
            card_type="attack",
            target="single",
            exhaust=False,
            playable=True,
            effects=[],
        ))
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 1},
            "deck": ["expensive_card2"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        energy_before = cm._ctx.player.energy
        hand_size_before = len(cm._ctx.player.hand)
        cm.play_card(0, 0)
        assert cm._ctx.player.energy == energy_before
        assert len(cm._ctx.player.hand) == hand_size_before


class TestPlayCardInvalidHandIndex:
    """手牌索引越界返回 invalid_hand_index 错误 (Req 3.4)"""

    def test_negative_index_returns_error(self):
        """负数索引返回 invalid_hand_index 错误"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        result = cm.play_card(-1, 0)
        assert result["ok"] is False
        assert "invalid_hand_index" in result["error"]

    def test_out_of_bounds_index_returns_error(self):
        """超出手牌范围的索引返回 invalid_hand_index 错误"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        hand_size = len(cm._ctx.player.hand)
        result = cm.play_card(hand_size, 0)
        assert result["ok"] is False
        assert "invalid_hand_index" in result["error"]

    def test_error_contains_index(self):
        """错误信息包含越界的索引值"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        result = cm.play_card(99, 0)
        assert "99" in result["error"]


class TestPlayCardNotPlayable:
    """playable=False 的卡牌返回 card_not_playable 错误 (Req 3.5)"""

    def _make_cm_with_unplayable_card(self):
        from sts2_simulator.combat.manager import CombatManager
        from sts2_simulator.data.registry import CardDef
        registry = make_registry()
        registry.register_card(CardDef(
            id="curse_card",
            name="Curse Card",
            cost=0,
            card_type="skill",
            target="none",
            exhaust=False,
            playable=False,
            effects=[],
        ))
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["curse_card"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        return cm

    def test_unplayable_card_returns_error(self):
        """playable=False 的卡牌返回 {"ok": False, "error": "card_not_playable"}"""
        cm = self._make_cm_with_unplayable_card()
        result = cm.play_card(0, -1)
        assert result == {"ok": False, "error": "card_not_playable"}

    def test_unplayable_card_does_not_modify_state(self):
        """playable=False 时不修改任何状态"""
        cm = self._make_cm_with_unplayable_card()
        hand_size_before = len(cm._ctx.player.hand)
        energy_before = cm._ctx.player.energy
        cm.play_card(0, -1)
        assert len(cm._ctx.player.hand) == hand_size_before
        assert cm._ctx.player.energy == energy_before


class TestPlayCardDeadTarget:
    """目标已死亡返回 invalid_target 错误 (Req 3.5)"""

    def test_dead_enemy_target_returns_error(self):
        """目标敌人已死亡时返回 invalid_target: enemy_dead 错误"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        # Kill the enemy directly
        cm._ctx.enemies[0].is_dead = True
        result = cm.play_card(0, 0)
        assert result["ok"] is False
        assert "invalid_target" in result["error"]
        assert "enemy_dead" in result["error"]

    def test_dead_enemy_does_not_modify_state(self):
        """目标已死亡时不修改任何状态"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        cm._ctx.enemies[0].is_dead = True
        energy_before = cm._ctx.player.energy
        hand_size_before = len(cm._ctx.player.hand)
        cm.play_card(0, 0)
        assert cm._ctx.player.energy == energy_before
        assert len(cm._ctx.player.hand) == hand_size_before


class TestPlayCardBattleEnded:
    """战斗结束后打牌返回 battle_already_ended 错误 (Req 7.8)"""

    def test_battle_ended_returns_error(self):
        """战斗已结束时返回 {"ok": False, "error": "battle_already_ended"}"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        # Force battle to ended state
        cm._ctx.phase = "ended"
        result = cm.play_card(0, 0)
        assert result == {"ok": False, "error": "battle_already_ended"}

    def test_battle_ended_does_not_modify_state(self):
        """战斗已结束时不修改任何状态"""
        cm, _ = make_cm_with_hand(deck=["strike"])
        cm._ctx.phase = "ended"
        hand_size_before = len(cm._ctx.player.hand)
        energy_before = cm._ctx.player.energy
        cm.play_card(0, 0)
        assert cm._ctx.phase == "ended"
        assert len(cm._ctx.player.hand) == hand_size_before
        assert cm._ctx.player.energy == energy_before


# ===========================================================================
# 敌人行动阶段单元测试
# Validates: Requirements 5.2, 5.4, 5.5, 5.6
# NOTE: These tests will FAIL until task 9.6 implements _run_enemy_phase.
# ===========================================================================

def make_cm_enemy_phase(player_hp=80, deck=None, enemies=None):
    """Helper: create a CombatManager for enemy phase tests."""
    from sts2_simulator.combat.manager import CombatManager
    registry = make_registry()
    config = {
        "player": {"hp": player_hp, "max_hp": 80, "energy": 3},
        "deck": deck or ["defend"],
        "relics": [],
        "potions": [],
        "enemies": enemies or [{"id": "jaw_worm", "hp": 44, "max_hp": 44}],
    }
    cm = CombatManager(config, registry, lambda s: None)
    return cm


class TestEnemyPhase:
    """敌人行动阶段测试 (Req 5.2, 5.4, 5.5, 5.6)"""

    # -----------------------------------------------------------------------
    # 5.2 sequential_loop 按 move_order 顺序执行
    # -----------------------------------------------------------------------

    def test_first_end_turn_jaw_worm_executes_chomp(self):
        """end_turn() 后颚虫执行第一个 move (chomp)，对玩家造成 11 点伤害 (Req 5.2)"""
        cm = make_cm_enemy_phase(player_hp=80)
        initial_hp = cm._ctx.player.hp
        cm.end_turn()
        # chomp deals 11 damage, player has no block at start of enemy phase
        assert cm._ctx.player.hp == initial_hp - 11

    def test_sequential_loop_follows_move_order(self):
        """颚虫按 move_order 顺序执行：chomp→thrash→bellow→thrash→bellow (Req 5.2)"""
        cm = make_cm_enemy_phase(player_hp=80)
        # move_order: ["chomp", "thrash", "bellow", "thrash", "bellow"]
        # chomp: 11 dmg; thrash: 7 dmg + 5 block; bellow: 0 dmg + strength/block

        hp_after = []

        # Turn 1: chomp (11 dmg)
        cm.end_turn()
        hp_after.append(cm._ctx.player.hp)

        # Turn 2: thrash (7 dmg)
        cm.end_turn()
        hp_after.append(cm._ctx.player.hp)

        # Turn 3: bellow (0 dmg to player)
        cm.end_turn()
        hp_after.append(cm._ctx.player.hp)

        # Turn 4: thrash (7 dmg)
        cm.end_turn()
        hp_after.append(cm._ctx.player.hp)

        # Turn 5: bellow (0 dmg to player)
        cm.end_turn()
        hp_after.append(cm._ctx.player.hp)

        # Verify damage sequence matches move_order
        # After turn 1 (chomp): 80 - 11 = 69
        assert hp_after[0] == 80 - 11, f"Turn 1 (chomp): expected {80 - 11}, got {hp_after[0]}"
        # After turn 2 (thrash): 69 - 7 = 62
        assert hp_after[1] == hp_after[0] - 7, f"Turn 2 (thrash): expected {hp_after[0] - 7}, got {hp_after[1]}"
        # After turn 3 (bellow): no damage to player
        assert hp_after[2] == hp_after[1], f"Turn 3 (bellow): expected no damage, got {hp_after[1] - hp_after[2]}"
        # After turn 4 (thrash): jaw_worm has strength 3 from bellow, but
        # strength reduces by 1 at turn_end each round.
        # After bellow (turn 3), strength=3. After turn 3's turn_end tick, strength=2.
        # So turn 4 thrash deals 7+2=9 dmg.
        assert hp_after[3] == hp_after[2] - 9, f"Turn 4 (thrash+strength): expected {hp_after[2] - 9}, got {hp_after[3]}"
        # After turn 5 (bellow): no damage to player
        assert hp_after[4] == hp_after[3], f"Turn 5 (bellow): expected no damage, got {hp_after[3] - hp_after[4]}"

    # -----------------------------------------------------------------------
    # 5.4 死亡敌人跳过行动
    # -----------------------------------------------------------------------

    def test_dead_enemy_skips_action(self):
        """is_dead=True 的敌人在敌人行动阶段不执行任何行动 (Req 5.4)"""
        cm = make_cm_enemy_phase(player_hp=80)
        # Kill the jaw_worm before end_turn
        cm._ctx.enemies[0].is_dead = True
        initial_hp = cm._ctx.player.hp
        cm.end_turn()
        # Dead enemy should not deal any damage
        assert cm._ctx.player.hp == initial_hp

    def test_dead_enemy_in_multi_enemy_skips_action(self):
        """多敌人场景中死亡敌人跳过，存活敌人正常行动 (Req 5.4)"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["defend"],
            "relics": [],
            "potions": [],
            "enemies": [
                {"id": "jaw_worm", "hp": 44, "max_hp": 44},
                {"id": "jaw_worm", "hp": 44, "max_hp": 44},
            ],
        }
        cm = CombatManager(config, registry, lambda s: None)
        # Kill the first jaw_worm
        cm._ctx.enemies[0].is_dead = True
        initial_hp = cm._ctx.player.hp
        cm.end_turn()
        # Only the second jaw_worm (chomp: 11 dmg) should act
        assert cm._ctx.player.hp == initial_hp - 11

    # -----------------------------------------------------------------------
    # 5.5 Intent 在每回合结束后正确更新
    # -----------------------------------------------------------------------

    def test_intent_updated_after_enemy_phase(self):
        """敌人行动后 intent 更新为下一个 move 的 intents (Req 5.5)"""
        from sts2_simulator.combat.enemy import IntentType
        cm = make_cm_enemy_phase(player_hp=80)
        # Initial intent: chomp (ATTACK 11)
        initial_intents = cm._ctx.enemies[0].intents
        assert len(initial_intents) == 1
        assert initial_intents[0].type == IntentType.ATTACK
        assert initial_intents[0].value == 11

        # After end_turn (chomp executes), intent should update to thrash
        cm.end_turn()
        intents_after_turn1 = cm._ctx.enemies[0].intents
        # thrash: ATTACK 7 + DEFEND 5
        assert len(intents_after_turn1) == 2
        attack_intents = [i for i in intents_after_turn1 if i.type == IntentType.ATTACK]
        defend_intents = [i for i in intents_after_turn1 if i.type == IntentType.DEFEND]
        assert len(attack_intents) == 1
        assert attack_intents[0].value == 7
        assert len(defend_intents) == 1

    def test_intent_cycles_through_move_order(self):
        """Intent 随 move_order 循环更新 (Req 5.5)"""
        from sts2_simulator.combat.enemy import IntentType
        cm = make_cm_enemy_phase(player_hp=80)
        # move_order: chomp(0) → thrash(1) → bellow(2) → thrash(3) → bellow(4)

        # After turn 1 (chomp), intent = thrash
        cm.end_turn()
        intents = cm._ctx.enemies[0].intents
        attack_vals = [i.value for i in intents if i.type == IntentType.ATTACK]
        assert 7 in attack_vals  # thrash attack value

        # After turn 2 (thrash), intent = bellow
        cm.end_turn()
        intents = cm._ctx.enemies[0].intents
        types = {i.type for i in intents}
        assert IntentType.BUFF in types  # bellow has BUFF intent
        assert IntentType.ATTACK not in types  # bellow has no attack

    # -----------------------------------------------------------------------
    # 5.6 Player HP≤0 时触发战斗失败
    # -----------------------------------------------------------------------

    def test_player_death_triggers_defeat(self):
        """敌人造成足够伤害使 Player HP≤0 时，phase 变为 ended，result 为 defeat (Req 5.6)"""
        # jaw_worm chomp deals 11 damage; player with hp=10 will die
        cm = make_cm_enemy_phase(player_hp=10)
        cm.end_turn()
        state = cm.get_state()
        assert state["data"]["phase"] == "ended"
        assert state["data"]["result"] == "defeat"

    def test_player_death_battle_already_ended(self):
        """玩家死亡后，后续 end_turn 返回 battle_already_ended (Req 5.6)"""
        cm = make_cm_enemy_phase(player_hp=10)
        cm.end_turn()
        # Battle should be ended now
        result = cm.end_turn()
        assert result == {"ok": False, "error": "battle_already_ended"}

    def test_player_death_no_further_actions(self):
        """玩家死亡后，play_card 也返回 battle_already_ended (Req 5.6)"""
        cm = make_cm_enemy_phase(player_hp=10)
        cm.end_turn()
        # Try to play a card after defeat
        result = cm.play_card(0, 0)
        assert result == {"ok": False, "error": "battle_already_ended"}


# ===========================================================================
# 合法动作与 preview_damage 单元测试
# Validates: Requirements 8.1, 8.3, 8.4, 9.6
# ===========================================================================

class TestLegalActionsAndPreview:
    """测试合法动作列表与伤害预览的正确性"""

    # -----------------------------------------------------------------------
    # 8.1 / 8.3  能量为 0 时合法动作仅含 end_turn（和可用药水）
    # -----------------------------------------------------------------------

    def test_zero_energy_no_play_card_actions(self):
        """能量为 0 且手牌全为费用≥1 时，legal_actions 不含 play_card 动作 (Req 8.1, 8.3)"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        # strike costs 1 energy
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["strike", "strike", "strike", "strike", "strike"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        # Manually drain energy to 0
        cm._ctx.player.energy = 0
        actions = cm.get_legal_actions()
        play_card_actions = [a for a in actions if a["action"] == "play_card"]
        assert play_card_actions == [], (
            f"Expected no play_card actions when energy=0, got: {play_card_actions}"
        )

    def test_zero_energy_contains_end_turn(self):
        """能量为 0 时，legal_actions 仍包含 end_turn (Req 8.1)"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["strike", "strike", "strike", "strike", "strike"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        cm._ctx.player.energy = 0
        actions = cm.get_legal_actions()
        assert any(a["action"] == "end_turn" for a in actions), (
            "end_turn should always be in legal_actions"
        )

    def test_zero_energy_with_potion_shows_potion_action(self):
        """能量为 0 时，可用药水仍出现在 legal_actions 中 (Req 8.1, 9.6)"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": [],
            "potions": ["block_potion"],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        cm._ctx.player.energy = 0
        actions = cm.get_legal_actions()
        potion_actions = [a for a in actions if a["action"] == "use_potion"]
        assert len(potion_actions) >= 1, (
            "block_potion (target=self) should appear in legal_actions even when energy=0"
        )

    # -----------------------------------------------------------------------
    # 8.4 / 属性17  preview_damage 与实际伤害一致
    # -----------------------------------------------------------------------

    def test_preview_damage_matches_actual_damage_for_strike(self):
        """strike 的 preview_damage 应与实际打出后造成的伤害一致 (Req 8.4, 属性17)"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 44, "max_hp": 44}],
        }
        cm = CombatManager(config, registry, lambda s: None)

        # Find the strike card in hand
        hand = cm._ctx.player.hand
        assert len(hand) >= 1
        strike_idx = next(
            i for i, c in enumerate(hand) if c.defn.id == "strike"
        )
        strike_card = hand[strike_idx]

        # preview_damage should be computed for enemy index 0
        preview = strike_card.preview_damage
        assert preview is not None, "strike card should have preview_damage"
        assert 0 in preview, "preview_damage should contain entry for enemy index 0"
        predicted_hits = preview[0]
        assert len(predicted_hits) == 1, "strike deals 1 hit"
        predicted_damage = predicted_hits[0]

        # Record enemy HP before playing
        enemy_hp_before = cm._ctx.enemies[0].hp
        enemy_block_before = cm._ctx.enemies[0].block

        # Play the strike card
        result = cm.play_card(strike_idx, 0)
        assert result == {"ok": True}

        # Actual damage = HP reduction (accounting for block)
        enemy_hp_after = cm._ctx.enemies[0].hp
        actual_damage = (enemy_hp_before + enemy_block_before) - (
            cm._ctx.enemies[0].hp + cm._ctx.enemies[0].block
        )
        # Simpler: since jaw_worm starts with 0 block, damage = hp_before - hp_after
        assert enemy_hp_after == enemy_hp_before - predicted_damage, (
            f"preview_damage predicted {predicted_damage} but actual HP change was "
            f"{enemy_hp_before - enemy_hp_after}"
        )

    def test_preview_damage_strike_is_6(self):
        """strike 对无 buff 的颚虫 preview_damage 应为 [6] (Req 8.4)"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": [],
            "potions": [],
            "enemies": [{"id": "jaw_worm", "hp": 44, "max_hp": 44}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        hand = cm._ctx.player.hand
        strike_card = next(c for c in hand if c.defn.id == "strike")
        assert strike_card.preview_damage is not None
        assert strike_card.preview_damage[0] == [6]

    # -----------------------------------------------------------------------
    # 9.6  药水使用后槽位变为 None，不再出现在 legal_actions
    # -----------------------------------------------------------------------

    def test_potion_slot_is_none_after_use(self):
        """use_potion() 后对应槽位应变为 None (Req 9.6)"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": [],
            "potions": ["block_potion"],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        # Verify potion is present before use
        assert cm._ctx.player.potions[0] is not None
        # Use block_potion (target=self, so target_index=-1)
        result = cm.use_potion(0, -1)
        assert result == {"ok": True}
        assert cm._ctx.player.potions[0] is None, (
            "Potion slot should be None after use"
        )

    def test_potion_not_in_legal_actions_after_use(self):
        """use_potion() 后该槽位的药水不再出现在 legal_actions (Req 9.6)"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": [],
            "potions": ["block_potion"],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        # Use the potion
        cm.use_potion(0, -1)
        actions = cm.get_legal_actions()
        potion_actions = [a for a in actions if a["action"] == "use_potion" and a["slot_index"] == 0]
        assert potion_actions == [], (
            f"Slot 0 potion should not appear in legal_actions after use, got: {potion_actions}"
        )

    def test_potion_state_shows_null_after_use(self):
        """get_state() 中药水槽位在使用后显示为 null (Req 9.6)"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        config = {
            "player": {"hp": 80, "max_hp": 80, "energy": 3},
            "deck": ["strike"],
            "relics": [],
            "potions": ["block_potion"],
            "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        }
        cm = CombatManager(config, registry, lambda s: None)
        cm.use_potion(0, -1)
        state = cm.get_state()
        potions_state = state["data"]["player"]["potions"]
        assert potions_state[0] is None, (
            f"State should show null for used potion slot, got: {potions_state[0]}"
        )
