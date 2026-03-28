"""
Unit tests for the Registry class.
Tests: requirements 6.5, 6.8, 6.9, 6.10
"""
import pytest
from sts2_simulator.data.registry import (
    Registry,
    CardDef,
    RelicDef,
    EnemyDef,
    PotionDef,
    BuffDef,
    MoveDef,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry():
    return Registry()


@pytest.fixture
def sample_card():
    return CardDef(id="strike", name="打击", cost=1, card_type="attack", target="single",
                   effects=[{"type": "deal_damage", "value": 6}])


@pytest.fixture
def sample_relic():
    return RelicDef(id="akabeko", name="赤牛", trigger="turn_start")


@pytest.fixture
def sample_enemy():
    move = MoveDef(name="chomp", intents=[], effects=[{"type": "deal_damage", "value": 11}])
    return EnemyDef(
        id="jaw_worm", name="颚虫", hp=44, max_hp=44,
        moves={"chomp": move},
        move_pattern="sequential_loop",
        move_order=["chomp"],
    )


@pytest.fixture
def sample_potion():
    return PotionDef(id="block_potion", name="护甲药水", target="self",
                     effects=[{"type": "gain_block", "value": 12}])


@pytest.fixture
def sample_buff():
    return BuffDef(id="strength", name="力量")


# ---------------------------------------------------------------------------
# Card registration and retrieval (requirement 6.5, 6.8)
# ---------------------------------------------------------------------------

class TestCardRegistration:
    def test_register_and_get_card(self, registry, sample_card):
        registry.register_card(sample_card)
        result = registry.get_card("strike")
        assert result is sample_card

    def test_get_card_not_found_raises_key_error(self, registry):
        with pytest.raises(KeyError):
            registry.get_card("nonexistent_card")

    def test_register_multiple_cards(self, registry):
        card1 = CardDef(id="strike", name="打击", cost=1, card_type="attack", target="single")
        card2 = CardDef(id="defend", name="防御", cost=1, card_type="skill", target="self")
        registry.register_card(card1)
        registry.register_card(card2)
        assert registry.get_card("strike") is card1
        assert registry.get_card("defend") is card2

    def test_register_card_overwrites_existing(self, registry):
        card_v1 = CardDef(id="strike", name="打击v1", cost=1, card_type="attack", target="single")
        card_v2 = CardDef(id="strike", name="打击v2", cost=2, card_type="attack", target="single")
        registry.register_card(card_v1)
        registry.register_card(card_v2)
        assert registry.get_card("strike") is card_v2


# ---------------------------------------------------------------------------
# Relic registration and retrieval (requirement 6.8)
# ---------------------------------------------------------------------------

class TestRelicRegistration:
    def test_register_and_get_relic(self, registry, sample_relic):
        registry.register_relic(sample_relic)
        assert registry.get_relic("akabeko") is sample_relic

    def test_get_relic_not_found_raises_key_error(self, registry):
        with pytest.raises(KeyError):
            registry.get_relic("nonexistent_relic")


# ---------------------------------------------------------------------------
# Enemy registration and retrieval (requirement 6.8)
# ---------------------------------------------------------------------------

class TestEnemyRegistration:
    def test_register_and_get_enemy(self, registry, sample_enemy):
        registry.register_enemy(sample_enemy)
        assert registry.get_enemy("jaw_worm") is sample_enemy

    def test_get_enemy_not_found_raises_key_error(self, registry):
        with pytest.raises(KeyError):
            registry.get_enemy("nonexistent_enemy")


# ---------------------------------------------------------------------------
# Potion registration and retrieval (requirement 6.8)
# ---------------------------------------------------------------------------

class TestPotionRegistration:
    def test_register_and_get_potion(self, registry, sample_potion):
        registry.register_potion(sample_potion)
        assert registry.get_potion("block_potion") is sample_potion

    def test_get_potion_not_found_raises_key_error(self, registry):
        with pytest.raises(KeyError):
            registry.get_potion("nonexistent_potion")


# ---------------------------------------------------------------------------
# Buff registration and retrieval (requirement 6.8)
# ---------------------------------------------------------------------------

class TestBuffRegistration:
    def test_register_and_get_buff(self, registry, sample_buff):
        registry.register_buff(sample_buff)
        assert registry.get_buff("strength") is sample_buff

    def test_get_buff_not_found_raises_key_error(self, registry):
        with pytest.raises(KeyError):
            registry.get_buff("nonexistent_buff")


# ---------------------------------------------------------------------------
# load_from_dict batch loading (requirement 6.9, 6.10)
# ---------------------------------------------------------------------------

class TestLoadFromDict:
    def test_load_cards_from_dict(self, registry):
        data = {
            "cards": [
                {"id": "strike", "name": "打击", "cost": 1, "card_type": "attack",
                 "target": "single", "effects": [{"type": "deal_damage", "value": 6}]},
                {"id": "defend", "name": "防御", "cost": 1, "card_type": "skill",
                 "target": "self", "effects": [{"type": "gain_block", "value": 5}]},
            ]
        }
        registry.load_from_dict(data)
        assert registry.get_card("strike").name == "打击"
        assert registry.get_card("defend").name == "防御"

    def test_load_relics_from_dict(self, registry):
        data = {
            "relics": [
                {"id": "akabeko", "name": "赤牛", "trigger": "turn_start", "effects": []},
            ]
        }
        registry.load_from_dict(data)
        assert registry.get_relic("akabeko").name == "赤牛"

    def test_load_enemies_from_dict(self, registry):
        data = {
            "enemies": [
                {
                    "id": "jaw_worm",
                    "name": "颚虫",
                    "hp": 44,
                    "max_hp": 44,
                    "moves": {
                        "chomp": {
                            "name": "chomp",
                            "intents": [],
                            "effects": [{"type": "deal_damage", "value": 11}],
                        }
                    },
                    "move_pattern": "sequential_loop",
                    "move_order": ["chomp"],
                }
            ]
        }
        registry.load_from_dict(data)
        enemy = registry.get_enemy("jaw_worm")
        assert enemy.name == "颚虫"
        assert enemy.hp == 44

    def test_load_potions_from_dict(self, registry):
        data = {
            "potions": [
                {"id": "block_potion", "name": "护甲药水", "target": "self",
                 "effects": [{"type": "gain_block", "value": 12}]},
            ]
        }
        registry.load_from_dict(data)
        assert registry.get_potion("block_potion").name == "护甲药水"

    def test_load_buffs_from_dict(self, registry):
        data = {
            "buffs": [
                {"id": "strength", "name": "力量", "is_permanent": False, "reduce_on": "turn_end"},
                {"id": "vulnerable", "name": "脆弱", "is_permanent": False, "reduce_on": "turn_start"},
            ]
        }
        registry.load_from_dict(data)
        assert registry.get_buff("strength").name == "力量"
        assert registry.get_buff("vulnerable").reduce_on == "turn_start"

    def test_load_from_dict_empty_sections(self, registry):
        """load_from_dict with missing sections should not raise errors."""
        registry.load_from_dict({})  # no sections at all
        registry.load_from_dict({"cards": []})  # empty list

    def test_load_from_dict_multiple_sections(self, registry):
        """load_from_dict loads all resource types in one call."""
        data = {
            "cards": [
                {"id": "strike", "name": "打击", "cost": 1, "card_type": "attack",
                 "target": "single", "effects": []},
            ],
            "buffs": [
                {"id": "weak", "name": "虚弱", "is_permanent": False, "reduce_on": "turn_start"},
            ],
        }
        registry.load_from_dict(data)
        assert registry.get_card("strike").id == "strike"
        assert registry.get_buff("weak").id == "weak"

    def test_load_from_dict_card_default_fields(self, registry):
        """Cards loaded from dict should have correct default values for exhaust and playable."""
        data = {
            "cards": [
                {"id": "strike", "name": "打击", "cost": 1, "card_type": "attack",
                 "target": "single"},
            ]
        }
        registry.load_from_dict(data)
        card = registry.get_card("strike")
        assert card.exhaust is False
        assert card.playable is True
