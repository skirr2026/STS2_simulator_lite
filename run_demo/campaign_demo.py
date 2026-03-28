# campaign_demo.py — 连续多场战斗演示
from sts2_simulator.runner.campaign import CampaignRunner
from sts2_simulator.runner.config import CampaignConfig, EnemyConfig


class PrintBridge:
    def on_state_change(self, state):
        d = state["data"]
        if d["phase"] == "player_action" and not d["player"]["hand"]:
            return  # 跳过空手牌状态
        enemy_hp = d["enemies"][0]["hp"] if d["enemies"] else "?"
        print(f"  Turn {d['turn']} | Player HP: {d['player']['hp']:3d} "
              f"| Enemy HP: {enemy_hp:3d} "
              f"| Energy: {d['player']['energy']}")

    def on_battle_end(self, log):
        result = "🏆 Victory" if log["result"] == "victory" else "💀 Defeat"
        print(f"  → {result} | Final HP: {log['final_hp']} | Turns: {log['turns']}\n")

    def on_campaign_end(self, log):
        print("=" * 50)
        result = "🏆 Campaign Victory!" if log["result"] == "victory" else "💀 Campaign Defeat"
        print(f"{result}")
        print(f"Battles completed : {log['battles_completed']}")
        print(f"Final HP          : {log['final_hp']}")
        print(f"Total turns       : {log['total_turns']}")
        print("=" * 50)


config = CampaignConfig(
    initial_player_hp=80,
    initial_player_max_hp=80,
    initial_energy=3,
    initial_deck=["strike", "strike", "strike", "defend", "defend"],
    initial_relics=[],
    initial_potions=[],
    enemy_sequence=[
        [EnemyConfig(id="jaw_worm",    hp=44, max_hp=44)],
        [EnemyConfig(id="acid_slime_m", hp=28, max_hp=28)],
        [EnemyConfig(id="sentinel",    hp=54, max_hp=54)],
    ],
)

print("=" * 50)
print("STS2 Campaign Demo — 3 battles")
print("=" * 50)

for i, enemies in enumerate(config.enemy_sequence, 1):
    print(f"\nBattle {i}: {enemies[0].id} (HP {enemies[0].hp})")

print()

runner = CampaignRunner(config, PrintBridge())
runner.run()
