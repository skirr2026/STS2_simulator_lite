"""Unit tests for EventBus.

Tests will fail until EventBus is implemented in task 5.2.
"""
from unittest.mock import MagicMock

import pytest

from sts2_simulator.engine.event_bus import STOP_PROPAGATION, EventBus


def make_ctx():
    """Return a minimal mock BattleContext."""
    return MagicMock()


# ---------------------------------------------------------------------------
# 1. 注册处理器后 emit 可触发
# ---------------------------------------------------------------------------

def test_emit_triggers_registered_handler():
    bus = EventBus()
    ctx = make_ctx()
    called_with = []

    def handler(c, **kwargs):
        called_with.append((c, kwargs))

    bus.on("test_event", handler)
    result = bus.emit("test_event", ctx, value=42)

    assert len(called_with) == 1
    assert called_with[0][0] is ctx
    assert called_with[0][1] == {"value": 42}
    assert result is True


def test_emit_triggers_multiple_handlers():
    bus = EventBus()
    ctx = make_ctx()
    order = []

    bus.on("ev", lambda c, **kw: order.append("a"))
    bus.on("ev", lambda c, **kw: order.append("b"))
    bus.emit("ev", ctx)

    assert len(order) == 2


# ---------------------------------------------------------------------------
# 2. 优先级排序（高优先级先执行）
# ---------------------------------------------------------------------------

def test_priority_high_before_low():
    bus = EventBus()
    ctx = make_ctx()
    order = []

    bus.on("ev", lambda c, **kw: order.append("low"), priority=0)
    bus.on("ev", lambda c, **kw: order.append("high"), priority=10)
    bus.on("ev", lambda c, **kw: order.append("mid"), priority=5)

    bus.emit("ev", ctx)

    assert order == ["high", "mid", "low"]


def test_priority_relic_before_buff_before_card():
    """遗物=10，Buff/Debuff=5，卡牌效果=0 的优先级约定。"""
    bus = EventBus()
    ctx = make_ctx()
    order = []

    bus.on("ev", lambda c, **kw: order.append("card"), priority=0)
    bus.on("ev", lambda c, **kw: order.append("buff"), priority=5)
    bus.on("ev", lambda c, **kw: order.append("relic"), priority=10)

    bus.emit("ev", ctx)

    assert order == ["relic", "buff", "card"]


# ---------------------------------------------------------------------------
# 3. 返回 STOP_PROPAGATION 时中断传播，emit 返回 False
# ---------------------------------------------------------------------------

def test_stop_propagation_halts_chain():
    bus = EventBus()
    ctx = make_ctx()
    order = []

    def stopper(c, **kw):
        order.append("stopper")
        return STOP_PROPAGATION

    bus.on("ev", lambda c, **kw: order.append("first"), priority=10)
    bus.on("ev", stopper, priority=5)
    bus.on("ev", lambda c, **kw: order.append("never"), priority=0)

    result = bus.emit("ev", ctx)

    assert result is False
    assert order == ["first", "stopper"]
    assert "never" not in order


def test_stop_propagation_returns_false():
    bus = EventBus()
    ctx = make_ctx()

    bus.on("ev", lambda c, **kw: STOP_PROPAGATION)
    result = bus.emit("ev", ctx)

    assert result is False


def test_no_stop_propagation_returns_true():
    bus = EventBus()
    ctx = make_ctx()

    bus.on("ev", lambda c, **kw: None)
    result = bus.emit("ev", ctx)

    assert result is True


# ---------------------------------------------------------------------------
# 4. 未注册事件 emit 不报错，返回 True
# ---------------------------------------------------------------------------

def test_emit_unregistered_event_returns_true():
    bus = EventBus()
    ctx = make_ctx()

    result = bus.emit("nonexistent_event", ctx)

    assert result is True


def test_emit_unregistered_event_no_exception():
    bus = EventBus()
    ctx = make_ctx()

    # Should not raise any exception
    try:
        bus.emit("totally_unknown", ctx, foo="bar")
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"emit raised an unexpected exception: {exc}")
