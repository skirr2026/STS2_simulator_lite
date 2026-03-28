from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from sts2_simulator.combat.player import Player
from sts2_simulator.combat.enemy import Enemy


@dataclass
class BattleContext:
    player: Player
    enemies: list  # list[Enemy]
    turn: int
    phase: str  # "init" | "player_turn" | "player_action" | "enemy_turn" | "ended"
    event_bus: Any  # EventBus (placeholder)
    registry: Any  # Registry (placeholder)
    log: list[dict]
    on_state_change: Any  # Callable[[dict], None]
