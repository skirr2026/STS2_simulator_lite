# simple_demo.py
from pprint import pprint

from sts2_simulator.runner.single import SingleBattleRunner
from sts2_simulator.runner.config import SingleBattleConfig, EnemyConfig

class PrintBridge:
    def on_state_change(self, state):
        d = state["data"]
        pprint(d)
        print(f"Turn {d['turn']} | Player HP: {d['player']['hp']} | "
              f"Enemy HP: {d['enemies'][0]['hp']}")
    def on_battle_end(self, log):
        print(f"\nBattle ended: {log}")
    def on_campaign_end(self, log): pass

config = SingleBattleConfig(
    player_hp=80, player_max_hp=80, player_energy=3,
    deck=["strike", "strike", "strike", "defend", "defend"],
    relics=[], potions=[],
    enemies=[EnemyConfig(id="jaw_worm", hp=44, max_hp=44)],
)

runner = SingleBattleRunner(config, PrintBridge())
runner.run()
