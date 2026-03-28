from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Player:
    hp: int
    max_hp: int
    energy: int
    max_energy: int
    block: int
    buffs: dict[str, int]
    hand: list  # list[CardInstance]
    draw_pile: list
    discard_pile: list
    exhaust_pile: list
    relics: list  # list[RelicInstance]
    potions: list  # list[PotionInstance | None]
