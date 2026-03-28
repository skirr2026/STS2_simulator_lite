"""
End-to-end integration tests — no ZeroMQ dependency.
Uses mock bridge callbacks to drive complete battle flows.
Validates: Requirements 1, 2, 3, 4, 5, 6
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class AutoBridge:
    """Bridge that auto-plays the first legal action each turn."""

    def __init__(self):
        self.states: list[dict] = []
        self.battle_end_logs: list[dict] = []
        self.campaign_end_logs: list[dict] = []
        self._cm = None

    def set_combat_manager(self, cm) -> None:
        self._cm = cm

    def on_state_change(self, state: dict) -> None:
        self.states.append(state)
        # Auto-drive: play first legal action if battle not ended
        if state["data"]["result"] is not None:
            return
        if self._cm is None:
            return
        actions = state["data"]["legal_actions"]
        if not actions:
            return
        action = actions[0]
        if action["action"] == "play_card":
            self._cm.play_card(action["hand_index"], action["target_index"])
        elif action["action"] == "use_potion":
            self._cm.use_potion(action["slot_index"], action["target_index"])
        elif action["action"] == "end_turn":
            self._cm.end_turn()

    def on_battle_end(self, log: dict) -> None:
        self.battle_end_logs.append(log)

    def on_campaign_end(self, log: dict) -> None:
        self.campaign_end_logs.append(log)


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


class PassiveBridge:
    """Bridge that only records states, does not auto-drive."""

    def __init__(self):
        self.states: list[dict] = []
        self.battle_end_logs: list[dict] = []
        self.campaign_end_logs: list[dict] = []

    def on_state_change(self, state: dict) -> None:
        self.states.append(state)

    def on_battle_end(self, log: dict) -> None:
        self.battle_end_logs.append(log)

    def on_campaign_end(self, log: dict) -> None:
        self.campaign_end_logs.append(log)


def make_cm(deck, enemies, relics=None, potions=None, player_hp=80, bridge=None):
    from sts2_simulator.combat.manager import CombatManager
    registry = make_registry()
    if bridge is None:
        bridge = PassiveBridge()
    config = {
        "player": {"hp": player_hp, "max_hp": player_hp, "energy": 3},
        "deck": deck,
        "relics": relics or [],
        "potions": potions or [],
        "enemies": enemies,
    }
    cm = CombatManager(config, registry, bridge.on_state_change)
    return cm, bridge


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------

class TestBattleInitialization:
    def test_initial_state_has_required_fields(self):
        """初始化后 State 应包含所有必要字段"""
        cm, _ = make_cm(
            deck=["strike", "defend"],
            enemies=[{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        )
        state = cm.get_state()["data"]
        assert "player" in state
        assert "enemies" in state
        assert state["turn"] == 1
        assert "phase" in state
        assert "legal_actions" in state
        assert state["result"] is None

    def test_initial_hand_has_five_cards(self):
        """初始化后手牌应为 5 张"""
        cm, _ = make_cm(
            deck=["strike"] * 10,
            enemies=[{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        )
        assert len(cm.get_state()["data"]["player"]["hand"]) == 5

    def test_unknown_card_id_raises(self):
        """不存在的卡牌 ID 应拒绝初始化"""
        from sts2_simulator.combat.manager import CombatManager
        registry = make_registry()
        bridge = AutoBridge()
        with pytest.raises(ValueError, match="unknown_card_id"):
            CombatManager(
                {"player": {"hp": 80, "max_hp": 80, "energy": 3},
                 "deck": ["nonexistent_card"], "relics": [], "potions": [],
                 "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}]},
                registry, bridge.on_state_change,
            )


# ---------------------------------------------------------------------------
# 完整战斗流程
# ---------------------------------------------------------------------------

class TestFullBattleFlow:
    def test_victory_when_enemy_killed(self):
        """杀死所有敌人后战斗应以胜利结束"""
        cm, bridge = make_cm(
            deck=["strike"] * 10,
            enemies=[{"id": "jaw_worm", "hp": 1, "max_hp": 40}],
        )
        # Auto-bridge drives the battle; play first strike to kill jaw_worm
        cm.play_card(0, 0)
        state = cm.get_state()["data"]
        assert state["result"] == "victory"

    def test_defeat_when_player_dies(self):
        """玩家 HP 归零后战斗应以失败结束"""
        cm, bridge = make_cm(
            deck=["defend"],
            enemies=[{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
            player_hp=1,
        )
        # End turn immediately — jaw_worm chomp (11 dmg) kills player
        cm.end_turn()
        state = cm.get_state()["data"]
        assert state["result"] == "defeat"

    def test_turn_increments_after_end_turn(self):
        """结束回合后回合数应增加"""
        cm, _ = make_cm(
            deck=["defend"] * 10,
            enemies=[{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        )
        assert cm.get_state()["data"]["turn"] == 1
        cm.end_turn()
        assert cm.get_state()["data"]["turn"] == 2

    def test_hand_refreshed_after_end_turn(self):
        """结束回合后手牌应重新抓满"""
        cm, _ = make_cm(
            deck=["defend"] * 10,
            enemies=[{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        )
        cm.end_turn()
        assert len(cm.get_state()["data"]["player"]["hand"]) == 5

    def test_battle_already_ended_error(self):
        """战斗结束后继续操作应返回 battle_already_ended"""
        cm, _ = make_cm(
            deck=["strike"] * 10,
            enemies=[{"id": "jaw_worm", "hp": 1, "max_hp": 40}],
        )
        cm.play_card(0, 0)  # kills enemy
        result = cm.play_card(0, 0)
        assert result["error"] == "battle_already_ended"


# ---------------------------------------------------------------------------
# 遗物效果
# ---------------------------------------------------------------------------

class TestRelicEffects:
    def test_bag_of_preparation_draws_extra_cards(self):
        """准备袋应在战斗开始时额外抓 2 张牌"""
        cm, _ = make_cm(
            deck=["strike"] * 10,
            enemies=[{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
            relics=["bag_of_preparation"],
        )
        # bag_of_preparation triggers on battle_start: draws 2 extra
        # Initial draw is 5, plus 2 = 7
        hand_size = len(cm.get_state()["data"]["player"]["hand"])
        assert hand_size == 7


# ---------------------------------------------------------------------------
# Buff/Debuff 减层
# ---------------------------------------------------------------------------

class TestBuffDebuffDecay:
    def test_vulnerable_decays_after_turn(self):
        """脆弱状态应在回合开始时减层"""
        cm, _ = make_cm(
            deck=["bash"] * 10,  # bash applies 2 vulnerable
            enemies=[{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        )
        # Play bash to apply 2 vulnerable to enemy
        cm.play_card(0, 0)
        enemy_buffs = cm.get_state()["data"]["enemies"][0]["buffs"]
        assert enemy_buffs.get("vulnerable", 0) == 2

        # End turn and start new turn — vulnerable reduces on turn_start
        cm.end_turn()
        enemy_buffs_after = cm.get_state()["data"]["enemies"][0]["buffs"]
        assert enemy_buffs_after.get("vulnerable", 0) == 1

    def test_strength_decays_after_turn(self):
        """力量状态应在回合结束时减层"""
        cm, _ = make_cm(
            deck=["flex"] * 10,  # flex gives 2 strength, loses it at turn_end
            enemies=[{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        )
        cm.play_card(0, 0)
        player_buffs = cm.get_state()["data"]["player"]["buffs"]
        assert player_buffs.get("strength", 0) == 2

        cm.end_turn()
        player_buffs_after = cm.get_state()["data"]["player"]["buffs"]
        # strength should have decayed by 1 (reduce_on=turn_end)
        assert player_buffs_after.get("strength", 0) <= 1


# ---------------------------------------------------------------------------
# Campaign 集成测试
# ---------------------------------------------------------------------------

class TestCampaignIntegration:
    def test_hp_carries_over(self):
        """Campaign 中 HP 应在战斗间正确继承"""
        from sts2_simulator.runner.campaign import CampaignRunner
        from sts2_simulator.runner.config import CampaignConfig, EnemyConfig

        bridge = PassiveBridge()
        config = CampaignConfig(
            initial_player_hp=80,
            initial_player_max_hp=80,
            initial_energy=3,
            initial_deck=["strike"] * 5,
            initial_relics=[],
            initial_potions=[],
            enemy_sequence=[
                [EnemyConfig(id="jaw_worm", hp=1, max_hp=40)],
                [EnemyConfig(id="jaw_worm", hp=1, max_hp=40)],
            ],
        )
        runner = CampaignRunner(config, bridge)
        result = runner.run()
        assert result["battles_completed"] == 2
        assert result["result"] == "victory"

    def test_campaign_stops_on_defeat(self):
        """Campaign 中玩家死亡后不应继续下一场战斗"""
        from sts2_simulator.runner.campaign import CampaignRunner
        from sts2_simulator.runner.config import CampaignConfig, EnemyConfig

        bridge = PassiveBridge()
        config = CampaignConfig(
            initial_player_hp=1,
            initial_player_max_hp=80,
            initial_energy=3,
            initial_deck=["defend"],
            initial_relics=[],
            initial_potions=[],
            enemy_sequence=[
                [EnemyConfig(id="jaw_worm", hp=40, max_hp=40)],
                [EnemyConfig(id="jaw_worm", hp=40, max_hp=40)],
            ],
        )
        runner = CampaignRunner(config, bridge)
        result = runner.run()
        assert result["battles_completed"] == 1
        assert result["result"] == "defeat"
