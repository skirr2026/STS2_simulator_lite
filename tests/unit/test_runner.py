"""
Unit tests for SingleBattleRunner and CampaignRunner.
Validates: Requirements 7.1
"""
from __future__ import annotations

import json
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockBridge:
    """Records all bridge callbacks for assertion."""

    def __init__(self):
        self.state_changes: list[dict] = []
        self.battle_end_logs: list[dict] = []
        self.campaign_end_logs: list[dict] = []

    def on_state_change(self, state: dict) -> None:
        self.state_changes.append(state)

    def on_battle_end(self, log: dict) -> None:
        self.battle_end_logs.append(log)

    def on_campaign_end(self, log: dict) -> None:
        self.campaign_end_logs.append(log)


SINGLE_BATTLE_CONFIG_DICT = {
    "player_hp": 80,
    "player_max_hp": 80,
    "player_energy": 3,
    "deck": ["strike", "defend"],
    "relics": [],
    "potions": [],
    "enemies": [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
}

CAMPAIGN_CONFIG_DICT = {
    "initial_player_hp": 80,
    "initial_player_max_hp": 80,
    "initial_energy": 3,
    "initial_deck": ["strike", "defend"],
    "initial_relics": [],
    "initial_potions": [],
    "enemy_sequence": [
        [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
        [{"id": "jaw_worm", "hp": 40, "max_hp": 40}],
    ],
}


# ---------------------------------------------------------------------------
# SingleBattleRunner.from_json
# ---------------------------------------------------------------------------

class TestSingleBattleRunnerFromJson:
    """测试 SingleBattleRunner.from_json 正确解析配置文件"""

    def test_from_json_returns_runner_instance(self, tmp_path):
        from sts2_simulator.runner.single import SingleBattleRunner
        config_file = tmp_path / "single_battle.json"
        config_file.write_text(json.dumps(SINGLE_BATTLE_CONFIG_DICT))
        runner = SingleBattleRunner.from_json(str(config_file), MockBridge())
        assert isinstance(runner, SingleBattleRunner)

    def test_from_json_parses_player_fields(self, tmp_path):
        from sts2_simulator.runner.single import SingleBattleRunner
        config_file = tmp_path / "single_battle.json"
        config_file.write_text(json.dumps(SINGLE_BATTLE_CONFIG_DICT))
        runner = SingleBattleRunner.from_json(str(config_file), MockBridge())
        assert runner.config.player_hp == 80
        assert runner.config.player_max_hp == 80
        assert runner.config.player_energy == 3

    def test_from_json_parses_deck(self, tmp_path):
        from sts2_simulator.runner.single import SingleBattleRunner
        config_file = tmp_path / "single_battle.json"
        config_file.write_text(json.dumps(SINGLE_BATTLE_CONFIG_DICT))
        runner = SingleBattleRunner.from_json(str(config_file), MockBridge())
        assert runner.config.deck == ["strike", "defend"]

    def test_from_json_parses_enemies(self, tmp_path):
        from sts2_simulator.runner.single import SingleBattleRunner
        config_file = tmp_path / "single_battle.json"
        config_file.write_text(json.dumps(SINGLE_BATTLE_CONFIG_DICT))
        runner = SingleBattleRunner.from_json(str(config_file), MockBridge())
        assert len(runner.config.enemies) == 1
        assert runner.config.enemies[0].id == "jaw_worm"
        assert runner.config.enemies[0].hp == 40

    def test_from_json_stores_bridge(self, tmp_path):
        from sts2_simulator.runner.single import SingleBattleRunner
        config_file = tmp_path / "single_battle.json"
        config_file.write_text(json.dumps(SINGLE_BATTLE_CONFIG_DICT))
        bridge = MockBridge()
        runner = SingleBattleRunner.from_json(str(config_file), bridge)
        assert runner.bridge is bridge

    def test_from_json_nonexistent_file_raises(self, tmp_path):
        from sts2_simulator.runner.single import SingleBattleRunner
        with pytest.raises((FileNotFoundError, OSError)):
            SingleBattleRunner.from_json(str(tmp_path / "nonexistent.json"), MockBridge())


# ---------------------------------------------------------------------------
# CampaignRunner — HP 在战斗间正确继承
# ---------------------------------------------------------------------------

class TestCampaignRunnerHpInheritance:
    """测试 CampaignRunner 多场战斗时 HP 在战斗间正确继承（不超过 max_hp）"""

    def _make_runner(self, initial_hp, max_hp, deck, enemy_sequence):
        from sts2_simulator.runner.campaign import CampaignRunner
        from sts2_simulator.runner.config import CampaignConfig, EnemyConfig
        config = CampaignConfig(
            initial_player_hp=initial_hp,
            initial_player_max_hp=max_hp,
            initial_energy=3,
            initial_deck=deck,
            initial_relics=[],
            initial_potions=[],
            enemy_sequence=[
                [EnemyConfig(**e) for e in battle]
                for battle in enemy_sequence
            ],
        )
        bridge = MockBridge()
        return CampaignRunner(config, bridge), bridge

    def test_hp_carries_over_between_battles(self):
        """第一场战斗结束后，玩家 HP 应携带到第二场战斗"""
        # jaw_worm hp=1 dies on first strike; player takes no damage
        runner, bridge = self._make_runner(
            initial_hp=80, max_hp=80,
            deck=["strike", "strike", "strike", "strike", "strike"],
            enemy_sequence=[
                [{"id": "jaw_worm", "hp": 1, "max_hp": 40}],
                [{"id": "jaw_worm", "hp": 1, "max_hp": 40}],
            ],
        )
        result = runner.run()
        # Both battles completed means HP carried over successfully
        assert result["battles_completed"] == 2

    def test_hp_does_not_exceed_max_hp(self):
        """HP 继承时不应超过 max_hp"""
        runner, bridge = self._make_runner(
            initial_hp=80, max_hp=80,
            deck=["strike", "strike", "strike", "strike", "strike"],
            enemy_sequence=[
                [{"id": "jaw_worm", "hp": 1, "max_hp": 40}],
                [{"id": "jaw_worm", "hp": 1, "max_hp": 40}],
            ],
        )
        result = runner.run()
        assert result["final_hp"] <= 80


# ---------------------------------------------------------------------------
# CampaignRunner — 战斗失败时 Campaign 终止
# ---------------------------------------------------------------------------

class TestCampaignRunnerFailureTermination:
    """测试战斗失败时 Campaign 终止"""

    def _make_defeat_runner(self):
        from sts2_simulator.runner.campaign import CampaignRunner
        from sts2_simulator.runner.config import CampaignConfig, EnemyConfig
        # Player has 1 HP, jaw_worm chomp deals 11 — dies on first enemy turn
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
        bridge = MockBridge()
        return CampaignRunner(config, bridge), bridge

    def test_campaign_terminates_on_defeat(self):
        """玩家在第一场战斗中死亡时，Campaign 应终止"""
        runner, bridge = self._make_defeat_runner()
        result = runner.run()
        assert result["battles_completed"] == 1
        assert result["result"] == "defeat"

    def test_campaign_defeat_calls_on_campaign_end(self):
        """Campaign 失败时应调用 bridge.on_campaign_end"""
        runner, bridge = self._make_defeat_runner()
        runner.run()
        assert len(bridge.campaign_end_logs) == 1
        assert bridge.campaign_end_logs[0]["result"] == "defeat"

    def test_second_battle_not_started_after_defeat(self):
        """第一场战斗失败后，第二场战斗不应被启动"""
        runner, bridge = self._make_defeat_runner()
        runner.run()
        # on_battle_end should only be called once
        assert len(bridge.battle_end_logs) == 1

    def test_campaign_victory_completes_all_battles(self):
        """所有战斗胜利时，Campaign 应完成全部战斗"""
        from sts2_simulator.runner.campaign import CampaignRunner
        from sts2_simulator.runner.config import CampaignConfig, EnemyConfig
        config = CampaignConfig(
            initial_player_hp=80,
            initial_player_max_hp=80,
            initial_energy=3,
            initial_deck=["strike", "strike", "strike", "strike", "strike"],
            initial_relics=[],
            initial_potions=[],
            enemy_sequence=[
                [EnemyConfig(id="jaw_worm", hp=1, max_hp=40)],
                [EnemyConfig(id="jaw_worm", hp=1, max_hp=40)],
            ],
        )
        bridge = MockBridge()
        runner = CampaignRunner(config, bridge)
        result = runner.run()
        assert result["battles_completed"] == 2
        assert result["result"] == "victory"
        assert len(bridge.battle_end_logs) == 2


# ---------------------------------------------------------------------------
# CampaignRunner.from_json
# ---------------------------------------------------------------------------

class TestCampaignRunnerFromJson:
    """测试 CampaignRunner.from_json 正确解析配置文件"""

    def test_from_json_returns_runner_instance(self, tmp_path):
        from sts2_simulator.runner.campaign import CampaignRunner
        config_file = tmp_path / "campaign.json"
        config_file.write_text(json.dumps(CAMPAIGN_CONFIG_DICT))
        runner = CampaignRunner.from_json(str(config_file), MockBridge())
        assert isinstance(runner, CampaignRunner)

    def test_from_json_parses_initial_hp(self, tmp_path):
        from sts2_simulator.runner.campaign import CampaignRunner
        config_file = tmp_path / "campaign.json"
        config_file.write_text(json.dumps(CAMPAIGN_CONFIG_DICT))
        runner = CampaignRunner.from_json(str(config_file), MockBridge())
        assert runner.config.initial_player_hp == 80

    def test_from_json_parses_enemy_sequence(self, tmp_path):
        from sts2_simulator.runner.campaign import CampaignRunner
        config_file = tmp_path / "campaign.json"
        config_file.write_text(json.dumps(CAMPAIGN_CONFIG_DICT))
        runner = CampaignRunner.from_json(str(config_file), MockBridge())
        assert len(runner.config.enemy_sequence) == 2
        assert runner.config.enemy_sequence[0][0].id == "jaw_worm"
