"""
Unit tests for CardPile (card_pile.py).
Tests will fail until CardPile is implemented in task 8.2.

Validates: Requirements 2 (抓牌流程子流程)
"""
from __future__ import annotations

import pytest

from sts2_simulator.combat.player import Player
from sts2_simulator.combat.enemy import Enemy
from sts2_simulator.combat.context import BattleContext
from sts2_simulator.engine.event_bus import EventBus
from sts2_simulator.data.registry import Registry
from sts2_simulator.combat.card_pile import draw_cards, discard_hand, shuffle_discard_to_draw


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cards(n: int) -> list:
    """Return n distinct card placeholder objects."""
    return [object() for _ in range(n)]


def make_player(hand=None, draw_pile=None, discard_pile=None, **kwargs) -> Player:
    defaults = dict(
        hp=80, max_hp=80, energy=3, max_energy=3, block=0,
        buffs={}, exhaust_pile=[], relics=[], potions=[],
    )
    defaults.update(kwargs)
    return Player(
        hand=hand if hand is not None else [],
        draw_pile=draw_pile if draw_pile is not None else [],
        discard_pile=discard_pile if discard_pile is not None else [],
        **defaults,
    )


def make_ctx(player=None) -> BattleContext:
    return BattleContext(
        player=player or make_player(),
        enemies=[],
        turn=1,
        phase="player_turn",
        event_bus=EventBus(),
        registry=Registry(),
        log=[],
        on_state_change=lambda s: None,
    )


# ---------------------------------------------------------------------------
# draw_cards: normal draw from non-empty draw pile
# ---------------------------------------------------------------------------

class TestDrawCardsNormal:
    def test_draw_moves_cards_from_draw_pile_to_hand(self):
        """draw_cards should move n cards from draw_pile into hand."""
        cards = make_cards(5)
        player = make_player(draw_pile=list(cards))
        ctx = make_ctx(player)

        draw_cards(ctx, 3)

        assert len(ctx.player.hand) == 3
        assert len(ctx.player.draw_pile) == 2

    def test_drawn_cards_are_from_draw_pile(self):
        """Cards drawn should be the ones that were in draw_pile."""
        cards = make_cards(5)
        player = make_player(draw_pile=list(cards))
        ctx = make_ctx(player)

        draw_cards(ctx, 3)

        # All cards in hand must have come from the original draw_pile
        for card in ctx.player.hand:
            assert card in cards

    def test_draw_all_cards_empties_draw_pile(self):
        """Drawing exactly as many cards as in draw_pile should empty it."""
        cards = make_cards(4)
        player = make_player(draw_pile=list(cards))
        ctx = make_ctx(player)

        draw_cards(ctx, 4)

        assert len(ctx.player.hand) == 4
        assert len(ctx.player.draw_pile) == 0

    def test_draw_single_card(self):
        """draw_cards(ctx, 1) should draw exactly one card."""
        cards = make_cards(3)
        player = make_player(draw_pile=list(cards))
        ctx = make_ctx(player)

        draw_cards(ctx, 1)

        assert len(ctx.player.hand) == 1
        assert len(ctx.player.draw_pile) == 2


# ---------------------------------------------------------------------------
# draw_cards: empty draw pile → shuffle discard into draw, then continue
# ---------------------------------------------------------------------------

class TestDrawCardsShuffleOnEmpty:
    def test_draw_shuffles_discard_into_draw_when_draw_pile_empty(self):
        """When draw_pile is empty, discard_pile should be shuffled into draw_pile."""
        discard = make_cards(5)
        player = make_player(draw_pile=[], discard_pile=list(discard))
        ctx = make_ctx(player)

        draw_cards(ctx, 3)

        assert len(ctx.player.hand) == 3
        # discard_pile should have been consumed (minus what was drawn)
        assert len(ctx.player.draw_pile) + len(ctx.player.hand) == 5
        assert len(ctx.player.discard_pile) == 0

    def test_drawn_cards_come_from_discard_after_shuffle(self):
        """Cards drawn after shuffle should originate from the discard pile."""
        discard = make_cards(4)
        player = make_player(draw_pile=[], discard_pile=list(discard))
        ctx = make_ctx(player)

        draw_cards(ctx, 2)

        for card in ctx.player.hand:
            assert card in discard

    def test_draw_spans_draw_pile_and_shuffled_discard(self):
        """Drawing more cards than in draw_pile should use discard after exhausting draw_pile."""
        draw = make_cards(2)
        discard = make_cards(4)
        player = make_player(draw_pile=list(draw), discard_pile=list(discard))
        ctx = make_ctx(player)

        draw_cards(ctx, 5)

        assert len(ctx.player.hand) == 5
        # All drawn cards must come from the original draw or discard piles
        all_original = set(draw) | set(discard)
        for card in ctx.player.hand:
            assert card in all_original

    def test_discard_pile_is_empty_after_shuffle_and_draw(self):
        """After shuffling discard into draw and drawing all, discard_pile should be empty."""
        discard = make_cards(3)
        player = make_player(draw_pile=[], discard_pile=list(discard))
        ctx = make_ctx(player)

        draw_cards(ctx, 3)

        assert len(ctx.player.discard_pile) == 0
        assert len(ctx.player.hand) == 3


# ---------------------------------------------------------------------------
# draw_cards: both piles empty → stop drawing
# ---------------------------------------------------------------------------

class TestDrawCardsBothEmpty:
    def test_draw_stops_when_both_piles_empty(self):
        """draw_cards should stop without error when both draw_pile and discard_pile are empty."""
        player = make_player(draw_pile=[], discard_pile=[])
        ctx = make_ctx(player)

        draw_cards(ctx, 5)

        assert len(ctx.player.hand) == 0

    def test_draw_partial_when_not_enough_cards(self):
        """draw_cards should draw as many as available when fewer cards exist than requested."""
        cards = make_cards(2)
        player = make_player(draw_pile=list(cards), discard_pile=[])
        ctx = make_ctx(player)

        draw_cards(ctx, 5)

        assert len(ctx.player.hand) == 2
        assert len(ctx.player.draw_pile) == 0

    def test_draw_zero_cards_is_noop(self):
        """draw_cards(ctx, 0) should not change any pile."""
        cards = make_cards(3)
        player = make_player(draw_pile=list(cards))
        ctx = make_ctx(player)

        draw_cards(ctx, 0)

        assert len(ctx.player.hand) == 0
        assert len(ctx.player.draw_pile) == 3


# ---------------------------------------------------------------------------
# draw_cards: hand full (10 cards) → overflow to discard_pile
# ---------------------------------------------------------------------------

class TestDrawCardsHandFull:
    def test_card_goes_to_discard_when_hand_is_full(self):
        """When hand already has 10 cards, newly drawn cards go to discard_pile."""
        hand = make_cards(10)
        draw = make_cards(3)
        player = make_player(hand=list(hand), draw_pile=list(draw))
        ctx = make_ctx(player)

        draw_cards(ctx, 3)

        assert len(ctx.player.hand) == 10
        assert len(ctx.player.discard_pile) == 3

    def test_overflow_cards_are_from_draw_pile(self):
        """Cards that overflow to discard should be the ones drawn from draw_pile."""
        hand = make_cards(10)
        draw = make_cards(2)
        player = make_player(hand=list(hand), draw_pile=list(draw))
        ctx = make_ctx(player)

        draw_cards(ctx, 2)

        for card in ctx.player.discard_pile:
            assert card in draw

    def test_partial_fill_then_overflow(self):
        """When hand has 9 cards, drawing 3 should add 1 to hand and 2 to discard."""
        hand = make_cards(9)
        draw = make_cards(3)
        player = make_player(hand=list(hand), draw_pile=list(draw))
        ctx = make_ctx(player)

        draw_cards(ctx, 3)

        assert len(ctx.player.hand) == 10
        assert len(ctx.player.discard_pile) == 2

    def test_hand_limit_is_exactly_ten(self):
        """Hand should never exceed 10 cards regardless of how many are drawn."""
        hand = make_cards(8)
        draw = make_cards(10)
        player = make_player(hand=list(hand), draw_pile=list(draw))
        ctx = make_ctx(player)

        draw_cards(ctx, 10)

        assert len(ctx.player.hand) == 10
        assert len(ctx.player.hand) + len(ctx.player.discard_pile) + len(ctx.player.draw_pile) == 18


# ---------------------------------------------------------------------------
# discard_hand: move all hand cards to discard_pile
# ---------------------------------------------------------------------------

class TestDiscardHand:
    def test_discard_hand_moves_all_cards_to_discard(self):
        """discard_hand should move every card from hand to discard_pile."""
        hand = make_cards(5)
        player = make_player(hand=list(hand))
        ctx = make_ctx(player)

        discard_hand(ctx)

        assert len(ctx.player.hand) == 0
        assert len(ctx.player.discard_pile) == 5

    def test_discarded_cards_are_the_hand_cards(self):
        """Cards in discard_pile after discard_hand should be the original hand cards."""
        hand = make_cards(4)
        player = make_player(hand=list(hand))
        ctx = make_ctx(player)

        discard_hand(ctx)

        for card in hand:
            assert card in ctx.player.discard_pile

    def test_discard_hand_appends_to_existing_discard(self):
        """discard_hand should append to existing discard_pile, not replace it."""
        hand = make_cards(3)
        existing_discard = make_cards(2)
        player = make_player(hand=list(hand), discard_pile=list(existing_discard))
        ctx = make_ctx(player)

        discard_hand(ctx)

        assert len(ctx.player.discard_pile) == 5
        for card in existing_discard:
            assert card in ctx.player.discard_pile
        for card in hand:
            assert card in ctx.player.discard_pile

    def test_discard_hand_with_empty_hand_is_noop(self):
        """discard_hand on an empty hand should not raise and leave discard unchanged."""
        player = make_player(hand=[], discard_pile=[])
        ctx = make_ctx(player)

        discard_hand(ctx)

        assert len(ctx.player.hand) == 0
        assert len(ctx.player.discard_pile) == 0

    def test_discard_hand_clears_hand(self):
        """After discard_hand, hand should be empty."""
        hand = make_cards(7)
        player = make_player(hand=list(hand))
        ctx = make_ctx(player)

        discard_hand(ctx)

        assert ctx.player.hand == []


# ---------------------------------------------------------------------------
# shuffle_discard_to_draw: move discard into draw pile
# ---------------------------------------------------------------------------

class TestShuffleDiscardToDraw:
    def test_shuffle_moves_all_discard_to_draw(self):
        """shuffle_discard_to_draw should move all discard cards into draw_pile."""
        discard = make_cards(5)
        player = make_player(draw_pile=[], discard_pile=list(discard))
        ctx = make_ctx(player)

        shuffle_discard_to_draw(ctx)

        assert len(ctx.player.draw_pile) == 5
        assert len(ctx.player.discard_pile) == 0

    def test_shuffle_all_cards_preserved(self):
        """All cards from discard_pile should appear in draw_pile after shuffle."""
        discard = make_cards(4)
        player = make_player(draw_pile=[], discard_pile=list(discard))
        ctx = make_ctx(player)

        shuffle_discard_to_draw(ctx)

        for card in discard:
            assert card in ctx.player.draw_pile

    def test_shuffle_empty_discard_is_noop(self):
        """shuffle_discard_to_draw with empty discard should not raise."""
        player = make_player(draw_pile=[], discard_pile=[])
        ctx = make_ctx(player)

        shuffle_discard_to_draw(ctx)

        assert len(ctx.player.draw_pile) == 0
        assert len(ctx.player.discard_pile) == 0
