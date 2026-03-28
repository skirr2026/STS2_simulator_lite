from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    ATTACK = "attack"
    DEFEND = "defend"
    BUFF = "buff"
    DEBUFF = "debuff"
    SUMMON = "summon"
    SUICIDE = "suicide"


@dataclass
class Intent:
    type: IntentType
    value: int | None
    target: str | None


@dataclass
class Enemy:
    id: str
    hp: int
    max_hp: int
    block: int
    buffs: dict[str, int]
    is_dead: bool
    move_index: int  # sequential_loop current position
    intents: list  # list[IntentType]
