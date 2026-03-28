import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sts2_simulator.combat.context import BattleContext

MAX_HAND_SIZE = 10


def draw_cards(ctx: "BattleContext", n: int) -> None:
    """Draw n cards from draw_pile to hand.
    If draw_pile empty, shuffle discard into draw first.
    If hand full (10), overflow to discard_pile.
    """
    for _ in range(n):
        if not ctx.player.draw_pile:
            if not ctx.player.discard_pile:
                break  # both empty, stop
            shuffle_discard_to_draw(ctx)

        card = ctx.player.draw_pile.pop(0)
        if len(ctx.player.hand) >= MAX_HAND_SIZE:
            ctx.player.discard_pile.append(card)
        else:
            ctx.player.hand.append(card)


def discard_hand(ctx: "BattleContext") -> None:
    """Move all hand cards to discard_pile."""
    ctx.player.discard_pile.extend(ctx.player.hand)
    ctx.player.hand.clear()


def shuffle_discard_to_draw(ctx: "BattleContext") -> None:
    """Shuffle discard_pile into draw_pile."""
    ctx.player.draw_pile.extend(ctx.player.discard_pile)
    ctx.player.discard_pile.clear()
    random.shuffle(ctx.player.draw_pile)
