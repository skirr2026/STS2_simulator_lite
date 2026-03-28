from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CardDef:
    id: str
    name: str
    cost: int
    card_type: str  # "attack" | "skill" | "power"
    target: str  # "single" | "all" | "self" | "none"
    exhaust: bool = False
    playable: bool = True
    effects: list = field(default_factory=list)
    effect_fn: Any = None


@dataclass
class CardInstance:
    defn: CardDef
    preview_damage: Any = None  # dict[int, list[int]] | None


@dataclass
class BuffDef:
    id: str
    name: str
    is_permanent: bool = False
    reduce_on: str = "turn_end"  # "turn_start" | "turn_end"


@dataclass
class RelicDef:
    id: str
    name: str
    trigger: str
    effects: list = field(default_factory=list)
    effect_fn: Any = None


@dataclass
class RelicInstance:
    defn: RelicDef


@dataclass
class PotionDef:
    id: str
    name: str
    target: str  # "single" | "self" | "none"
    effects: list = field(default_factory=list)
    effect_fn: Any = None


@dataclass
class PotionInstance:
    defn: PotionDef


@dataclass
class MoveDef:
    name: str
    intents: list  # list[Intent]
    effects: list = field(default_factory=list)
    effect_fn: Any = None


@dataclass
class EnemyDef:
    id: str
    name: str
    hp: int
    max_hp: int
    moves: dict  # dict[str, MoveDef]
    move_pattern: str  # "sequential_loop" | "fn"
    move_fn: Any = None  # Callable | None
    move_order: list = field(default_factory=list)


class Registry:
    def __init__(self):
        self._cards: dict[str, CardDef] = {}
        self._relics: dict[str, RelicDef] = {}
        self._enemies: dict[str, EnemyDef] = {}
        self._potions: dict[str, PotionDef] = {}
        self._buffs: dict[str, BuffDef] = {}

    # --- register ---

    def register_card(self, defn: CardDef) -> None:
        self._cards[defn.id] = defn

    def register_relic(self, defn: RelicDef) -> None:
        self._relics[defn.id] = defn

    def register_enemy(self, defn: EnemyDef) -> None:
        self._enemies[defn.id] = defn

    def register_potion(self, defn: PotionDef) -> None:
        self._potions[defn.id] = defn

    def register_buff(self, defn: BuffDef) -> None:
        self._buffs[defn.id] = defn

    # --- get ---

    def get_card(self, id: str) -> CardDef:
        if id not in self._cards:
            raise KeyError(id)
        return self._cards[id]

    def get_relic(self, id: str) -> RelicDef:
        if id not in self._relics:
            raise KeyError(id)
        return self._relics[id]

    def get_enemy(self, id: str) -> EnemyDef:
        if id not in self._enemies:
            raise KeyError(id)
        return self._enemies[id]

    def get_potion(self, id: str) -> PotionDef:
        if id not in self._potions:
            raise KeyError(id)
        return self._potions[id]

    def get_buff(self, id: str) -> BuffDef:
        if id not in self._buffs:
            raise KeyError(id)
        return self._buffs[id]

    # --- bulk loading ---

    def load_from_dict(self, data: dict) -> None:
        for card_data in data.get("cards", []):
            self.register_card(CardDef(
                id=card_data["id"],
                name=card_data["name"],
                cost=card_data["cost"],
                card_type=card_data["card_type"],
                target=card_data["target"],
                exhaust=card_data.get("exhaust", False),
                playable=card_data.get("playable", True),
                effects=card_data.get("effects", []),
            ))

        for relic_data in data.get("relics", []):
            self.register_relic(RelicDef(
                id=relic_data["id"],
                name=relic_data["name"],
                trigger=relic_data["trigger"],
                effects=relic_data.get("effects", []),
            ))

        for enemy_data in data.get("enemies", []):
            moves = {
                move_name: MoveDef(
                    name=move_dict["name"],
                    intents=move_dict.get("intents", []),
                    effects=move_dict.get("effects", []),
                )
                for move_name, move_dict in enemy_data.get("moves", {}).items()
            }
            self.register_enemy(EnemyDef(
                id=enemy_data["id"],
                name=enemy_data["name"],
                hp=enemy_data["hp"],
                max_hp=enemy_data["max_hp"],
                moves=moves,
                move_pattern=enemy_data.get("move_pattern", "sequential_loop"),
                move_order=enemy_data.get("move_order", []),
            ))

        for potion_data in data.get("potions", []):
            self.register_potion(PotionDef(
                id=potion_data["id"],
                name=potion_data["name"],
                target=potion_data["target"],
                effects=potion_data.get("effects", []),
            ))

        for buff_data in data.get("buffs", []):
            self.register_buff(BuffDef(
                id=buff_data["id"],
                name=buff_data["name"],
                is_permanent=buff_data.get("is_permanent", False),
                reduce_on=buff_data.get("reduce_on", "turn_end"),
            ))

    def load_from_json(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.load_from_dict(data)
