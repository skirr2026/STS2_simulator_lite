from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class EnemyConfig:
    id: str
    hp: int
    max_hp: int


@dataclass
class SingleBattleConfig:
    player_hp: int
    player_max_hp: int
    player_energy: int = 3
    deck: list = field(default_factory=list)
    relics: list = field(default_factory=list)
    potions: list = field(default_factory=list)
    enemies: list = field(default_factory=list)  # list[EnemyConfig]


@dataclass
class CampaignConfig:
    initial_player_hp: int
    initial_player_max_hp: int
    initial_energy: int = 3
    initial_deck: list = field(default_factory=list)
    initial_relics: list = field(default_factory=list)
    initial_potions: list = field(default_factory=list)
    enemy_sequence: list = field(default_factory=list)  # list[list[EnemyConfig]]
    max_battles: int = 100
