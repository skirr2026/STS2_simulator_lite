"""
Unit tests for built-in static resource data.
Tests: requirements 6.1, 6.2, 6.3, 4.1

These tests verify that the built-in data modules register the correct
number of resources and cover the required mechanisms/triggers.
Tests will fail until tasks 4.2–4.6 are implemented.
"""
import pytest
from sts2_simulator.data.registry import Registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_registry_with_all_builtins() -> Registry:
    """Create a Registry populated with all built-in resources."""
    from sts2_simulator.data.cards import register_builtin_cards
    from sts2_simulator.data.relics import register_builtin_relics
    from sts2_simulator.data.enemies import register_builtin_enemies
    from sts2_simulator.data.potions import register_builtin_potions
    from sts2_simulator.data.buffs import register_builtin_buffs

    registry = Registry()
    register_builtin_cards(registry)
    register_builtin_relics(registry)
    register_builtin_enemies(registry)
    register_builtin_potions(registry)
    register_builtin_buffs(registry)
    return registry


# ---------------------------------------------------------------------------
# Built-in Cards (requirement 6.1)
# ---------------------------------------------------------------------------

class TestBuiltinCards:
    """Tests for built-in card data — requirement 6.1."""

    @pytest.fixture
    def registry(self):
        from sts2_simulator.data.cards import register_builtin_cards
        r = Registry()
        register_builtin_cards(r)
        return r

    # --- count ---

    def test_builtin_card_count_at_least_15(self, registry):
        """There must be at least 15 built-in cards (requirement 6.1)."""
        expected_ids = [
            "strike", "heavy_blade", "twin_strike", "pommel_strike", "whirlwind",
            "cleave", "defend", "iron_wave", "shrug_it_off", "battle_trance",
            "flex", "inflame", "clothesline", "bash", "thunderclap", "anger",
        ]
        for card_id in expected_ids:
            registry.get_card(card_id)  # raises KeyError if missing
        assert len(expected_ids) >= 15

    # --- mechanism 1: single-target damage ---

    def test_mechanism_single_target_damage(self, registry):
        """strike uses deal_damage (single-target attack)."""
        card = registry.get_card("strike")
        assert card.card_type == "attack"
        assert card.target == "single"
        effect_types = [e["type"] for e in card.effects]
        assert "deal_damage" in effect_types

    # --- mechanism 2: gain block ---

    def test_mechanism_gain_block(self, registry):
        """defend uses gain_block."""
        card = registry.get_card("defend")
        assert card.card_type == "skill"
        effect_types = [e["type"] for e in card.effects]
        assert "gain_block" in effect_types

    # --- mechanism 3: draw cards ---

    def test_mechanism_draw_cards(self, registry):
        """battle_trance uses draw_cards."""
        card = registry.get_card("battle_trance")
        effect_types = [e["type"] for e in card.effects]
        assert "draw_cards" in effect_types

    # --- mechanism 4: apply buff/debuff ---

    def test_mechanism_apply_buff(self, registry):
        """inflame or flex uses apply_buff."""
        # inflame permanently applies strength
        card = registry.get_card("inflame")
        effect_types = [e["type"] for e in card.effects]
        assert "apply_buff" in effect_types

    # --- mechanism 5: AOE (deal_damage_all) ---

    def test_mechanism_aoe(self, registry):
        """cleave uses deal_damage_all."""
        card = registry.get_card("cleave")
        assert card.card_type == "attack"
        effect_types = [e["type"] for e in card.effects]
        assert "deal_damage_all" in effect_types

    # --- mechanism 6: multi-hit (deal_damage_multi) ---

    def test_mechanism_multi_hit(self, registry):
        """twin_strike uses deal_damage_multi."""
        card = registry.get_card("twin_strike")
        assert card.card_type == "attack"
        effect_types = [e["type"] for e in card.effects]
        assert "deal_damage_multi" in effect_types

    # --- mechanism 7: high-cost card (cost >= 2) ---

    def test_mechanism_high_cost(self, registry):
        """heavy_blade has cost >= 2."""
        card = registry.get_card("heavy_blade")
        assert card.cost >= 2

    def test_all_seven_mechanisms_covered(self, registry):
        """All 7 card mechanisms must be present across the built-in card set."""
        all_cards = [
            "strike", "heavy_blade", "twin_strike", "pommel_strike", "whirlwind",
            "cleave", "defend", "iron_wave", "shrug_it_off", "battle_trance",
            "flex", "inflame", "clothesline", "bash", "thunderclap", "anger",
        ]

        has_single_damage = False
        has_gain_block = False
        has_draw_cards = False
        has_apply_buff = False
        has_aoe = False
        has_multi_hit = False
        has_high_cost = False

        for card_id in all_cards:
            card = registry.get_card(card_id)
            effect_types = [e["type"] for e in card.effects]
            if "deal_damage" in effect_types and card.target == "single":
                has_single_damage = True
            if "gain_block" in effect_types:
                has_gain_block = True
            if "draw_cards" in effect_types:
                has_draw_cards = True
            if "apply_buff" in effect_types:
                has_apply_buff = True
            if "deal_damage_all" in effect_types:
                has_aoe = True
            if "deal_damage_multi" in effect_types:
                has_multi_hit = True
            if card.cost >= 2:
                has_high_cost = True

        assert has_single_damage, "No card with single-target deal_damage"
        assert has_gain_block, "No card with gain_block"
        assert has_draw_cards, "No card with draw_cards"
        assert has_apply_buff, "No card with apply_buff"
        assert has_aoe, "No card with deal_damage_all (AOE)"
        assert has_multi_hit, "No card with deal_damage_multi (multi-hit)"
        assert has_high_cost, "No card with cost >= 2 (high-cost)"

    # --- individual card spot-checks ---

    def test_strike_damage_value(self, registry):
        card = registry.get_card("strike")
        damage_effects = [e for e in card.effects if e["type"] == "deal_damage"]
        assert damage_effects[0]["value"] == 6

    def test_defend_block_value(self, registry):
        card = registry.get_card("defend")
        block_effects = [e for e in card.effects if e["type"] == "gain_block"]
        assert block_effects[0]["value"] == 5

    def test_twin_strike_hits_twice(self, registry):
        card = registry.get_card("twin_strike")
        multi_effects = [e for e in card.effects if e["type"] == "deal_damage_multi"]
        assert multi_effects[0].get("count", 1) == 2

    def test_bash_applies_vulnerable(self, registry):
        card = registry.get_card("bash")
        buff_effects = [e for e in card.effects if e["type"] == "apply_buff"]
        buff_ids = [e["buff_id"] for e in buff_effects]
        assert "vulnerable" in buff_ids

    def test_clothesline_applies_weak(self, registry):
        card = registry.get_card("clothesline")
        buff_effects = [e for e in card.effects if e["type"] == "apply_buff"]
        buff_ids = [e["buff_id"] for e in buff_effects]
        assert "weak" in buff_ids

    def test_battle_trance_draws_three(self, registry):
        card = registry.get_card("battle_trance")
        draw_effects = [e for e in card.effects if e["type"] == "draw_cards"]
        assert draw_effects[0]["value"] == 3

    def test_inflame_is_power(self, registry):
        card = registry.get_card("inflame")
        assert card.card_type == "power"

    def test_heavy_blade_cost_is_2(self, registry):
        card = registry.get_card("heavy_blade")
        assert card.cost == 2


# ---------------------------------------------------------------------------
# Built-in Relics (requirement 6.2)
# ---------------------------------------------------------------------------

class TestBuiltinRelics:
    """Tests for built-in relic data — requirement 6.2."""

    EXPECTED_RELIC_IDS = [
        "akabeko", "bag_of_preparation", "bronze_scales", "pen_nib", "odd_mushroom",
    ]

    @pytest.fixture
    def registry(self):
        from sts2_simulator.data.relics import register_builtin_relics
        r = Registry()
        register_builtin_relics(r)
        return r

    def test_builtin_relic_count_at_least_5(self, registry):
        """There must be at least 5 built-in relics (requirement 6.2)."""
        for relic_id in self.EXPECTED_RELIC_IDS:
            registry.get_relic(relic_id)  # raises KeyError if missing
        assert len(self.EXPECTED_RELIC_IDS) >= 5

    def test_relics_cover_multiple_trigger_timings(self, registry):
        """Built-in relics must cover multiple distinct trigger timings."""
        triggers = {registry.get_relic(rid).trigger for rid in self.EXPECTED_RELIC_IDS}
        assert len(triggers) >= 3, f"Expected ≥3 distinct triggers, got: {triggers}"

    def test_akabeko_trigger_turn_start(self, registry):
        relic = registry.get_relic("akabeko")
        assert relic.trigger == "turn_start"

    def test_bag_of_preparation_trigger_battle_start(self, registry):
        relic = registry.get_relic("bag_of_preparation")
        assert relic.trigger == "battle_start"

    def test_bronze_scales_trigger_on_damage_taken(self, registry):
        relic = registry.get_relic("bronze_scales")
        assert relic.trigger == "on_damage_taken"

    def test_pen_nib_trigger_on_card_played(self, registry):
        relic = registry.get_relic("pen_nib")
        assert relic.trigger == "on_card_played"

    def test_odd_mushroom_trigger_on_buff_applied(self, registry):
        relic = registry.get_relic("odd_mushroom")
        assert relic.trigger == "on_buff_applied"


# ---------------------------------------------------------------------------
# Built-in Enemies (requirement 6.3)
# ---------------------------------------------------------------------------

class TestBuiltinEnemies:
    """Tests for built-in enemy data — requirement 6.3."""

    EXPECTED_ENEMY_IDS = ["jaw_worm", "acid_slime_m", "sentinel"]

    @pytest.fixture
    def registry(self):
        from sts2_simulator.data.enemies import register_builtin_enemies
        r = Registry()
        register_builtin_enemies(r)
        return r

    def test_builtin_enemy_count_at_least_3(self, registry):
        """There must be at least 3 built-in enemies (requirement 6.3)."""
        for enemy_id in self.EXPECTED_ENEMY_IDS:
            registry.get_enemy(enemy_id)
        assert len(self.EXPECTED_ENEMY_IDS) >= 3

    def test_all_enemies_have_non_empty_move_order(self, registry):
        """Every built-in enemy must have a non-empty move_order."""
        for enemy_id in self.EXPECTED_ENEMY_IDS:
            enemy = registry.get_enemy(enemy_id)
            assert len(enemy.move_order) > 0, f"{enemy_id} has empty move_order"

    def test_all_enemies_move_order_references_valid_moves(self, registry):
        """Every move_order entry must reference a key in the moves dict."""
        for enemy_id in self.EXPECTED_ENEMY_IDS:
            enemy = registry.get_enemy(enemy_id)
            for move_name in enemy.move_order:
                assert move_name in enemy.moves, (
                    f"{enemy_id}: move_order entry '{move_name}' not in moves"
                )

    def test_all_enemies_use_sequential_loop(self, registry):
        """All built-in enemies use sequential_loop move pattern."""
        for enemy_id in self.EXPECTED_ENEMY_IDS:
            enemy = registry.get_enemy(enemy_id)
            assert enemy.move_pattern == "sequential_loop", (
                f"{enemy_id} has move_pattern={enemy.move_pattern!r}"
            )

    def test_all_enemies_moves_have_intents(self, registry):
        """Every move in every built-in enemy must have at least one intent."""
        for enemy_id in self.EXPECTED_ENEMY_IDS:
            enemy = registry.get_enemy(enemy_id)
            for move_name, move_def in enemy.moves.items():
                assert len(move_def.intents) > 0, (
                    f"{enemy_id}.{move_name} has no intents"
                )

    def test_jaw_worm_move_order(self, registry):
        enemy = registry.get_enemy("jaw_worm")
        assert "chomp" in enemy.move_order
        assert enemy.move_order[0] == "chomp"

    def test_acid_slime_m_has_debuff_move(self, registry):
        enemy = registry.get_enemy("acid_slime_m")
        # lick applies a debuff
        assert "lick" in enemy.moves

    def test_sentinel_has_three_moves(self, registry):
        enemy = registry.get_enemy("sentinel")
        assert len(enemy.moves) >= 3


# ---------------------------------------------------------------------------
# Built-in Potions (requirement 9.1 / task 4.1)
# ---------------------------------------------------------------------------

class TestBuiltinPotions:
    """Tests for built-in potion data."""

    EXPECTED_POTION_IDS = [
        "block_potion", "attack_potion", "card_draw_potion", "energy_potion",
    ]

    @pytest.fixture
    def registry(self):
        from sts2_simulator.data.potions import register_builtin_potions
        r = Registry()
        register_builtin_potions(r)
        return r

    def test_builtin_potion_count_equals_4(self, registry):
        """There must be exactly 4 built-in potions."""
        for potion_id in self.EXPECTED_POTION_IDS:
            registry.get_potion(potion_id)
        assert len(self.EXPECTED_POTION_IDS) == 4

    def test_block_potion_target_self(self, registry):
        potion = registry.get_potion("block_potion")
        assert potion.target == "self"

    def test_attack_potion_target_single(self, registry):
        potion = registry.get_potion("attack_potion")
        assert potion.target == "single"

    def test_card_draw_potion_target_none(self, registry):
        potion = registry.get_potion("card_draw_potion")
        assert potion.target == "none"

    def test_energy_potion_target_none(self, registry):
        potion = registry.get_potion("energy_potion")
        assert potion.target == "none"

    def test_block_potion_has_gain_block_effect(self, registry):
        potion = registry.get_potion("block_potion")
        effect_types = [e["type"] for e in potion.effects]
        assert "gain_block" in effect_types

    def test_attack_potion_has_deal_damage_effect(self, registry):
        potion = registry.get_potion("attack_potion")
        effect_types = [e["type"] for e in potion.effects]
        assert "deal_damage" in effect_types

    def test_card_draw_potion_has_draw_cards_effect(self, registry):
        potion = registry.get_potion("card_draw_potion")
        effect_types = [e["type"] for e in potion.effects]
        assert "draw_cards" in effect_types

    def test_energy_potion_has_gain_energy_effect(self, registry):
        potion = registry.get_potion("energy_potion")
        effect_types = [e["type"] for e in potion.effects]
        assert "gain_energy" in effect_types


# ---------------------------------------------------------------------------
# Built-in Buffs/Debuffs (requirement 4.1)
# ---------------------------------------------------------------------------

class TestBuiltinBuffs:
    """Tests for built-in Buff/Debuff data — requirement 4.1."""

    REQUIRED_BUFF_IDS = ["strength", "dexterity", "vulnerable", "weak", "ritual"]

    @pytest.fixture
    def registry(self):
        from sts2_simulator.data.buffs import register_builtin_buffs
        r = Registry()
        register_builtin_buffs(r)
        return r

    def test_all_required_buffs_present(self, registry):
        """strength, dexterity, vulnerable, weak, ritual must all be registered."""
        for buff_id in self.REQUIRED_BUFF_IDS:
            registry.get_buff(buff_id)  # raises KeyError if missing

    def test_strength_is_not_permanent(self, registry):
        buff = registry.get_buff("strength")
        assert buff.is_permanent is False

    def test_dexterity_is_not_permanent(self, registry):
        buff = registry.get_buff("dexterity")
        assert buff.is_permanent is False

    def test_vulnerable_reduces_on_turn_start(self, registry):
        """Vulnerable is a debuff that reduces at turn_start."""
        buff = registry.get_buff("vulnerable")
        assert buff.reduce_on == "turn_start"

    def test_weak_reduces_on_turn_start(self, registry):
        """Weak is a debuff that reduces at turn_start."""
        buff = registry.get_buff("weak")
        assert buff.reduce_on == "turn_start"

    def test_strength_reduces_on_turn_end(self, registry):
        buff = registry.get_buff("strength")
        assert buff.reduce_on == "turn_end"

    def test_dexterity_reduces_on_turn_end(self, registry):
        buff = registry.get_buff("dexterity")
        assert buff.reduce_on == "turn_end"

    def test_ritual_reduces_on_turn_end(self, registry):
        buff = registry.get_buff("ritual")
        assert buff.reduce_on == "turn_end"
