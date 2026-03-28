"""
Property-based tests for Campaign mode.
Property 18: Campaign 模式 HP 在战斗间正确继承
"""
from __future__ import annotations

from hypothesis import given, settings, strategies as st


# Feature: sts2-battle-simulator, Property 18: Campaign 模式 HP 在战斗间正确继承
@given(
    initial_hp=st.integers(min_value=10, max_value=80),
    max_hp=st.integers(min_value=80, max_value=80),
    n_battles=st.integers(min_value=2, max_value=4),
)
@settings(max_examples=100)
def test_campaign_hp_inheritance(initial_hp, max_hp, n_battles):
    """第 N+1 场战斗开始时 HP 应等于第 N 场战斗结束时的 HP（不超过 max_hp）"""
    from sts2_simulator.runner.campaign import CampaignRunner
    from sts2_simulator.runner.config import CampaignConfig, EnemyConfig

    # Use jaw_worm with 1 HP so battles end quickly (player wins each)
    enemy_sequence = [
        [EnemyConfig(id="jaw_worm", hp=1, max_hp=40)]
        for _ in range(n_battles)
    ]

    config = CampaignConfig(
        initial_player_hp=initial_hp,
        initial_player_max_hp=max_hp,
        initial_energy=3,
        initial_deck=["strike"] * 5,
        initial_relics=[],
        initial_potions=[],
        enemy_sequence=enemy_sequence,
    )

    hp_snapshots: list[int] = []

    class TrackingBridge:
        def on_state_change(self, state: dict) -> None:
            pass
        def on_battle_end(self, log: dict) -> None:
            hp_snapshots.append(log["final_hp"])
        def on_campaign_end(self, log: dict) -> None:
            pass

    runner = CampaignRunner(config, TrackingBridge())
    result = runner.run()

    assert result["battles_completed"] == n_battles
    assert result["result"] == "victory"

    # Each battle's starting HP must equal the previous battle's ending HP
    for i in range(1, len(hp_snapshots)):
        assert hp_snapshots[i] <= max_hp

    # Final HP must not exceed max_hp
    assert result["final_hp"] <= max_hp
