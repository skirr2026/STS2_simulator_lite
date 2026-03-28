from __future__ import annotations
from typing import Callable, Any

STOP_PROPAGATION = object()


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable]]] = {}

    def on(self, event: str, handler: Callable, priority: int = 0) -> None:
        """Register event handler, sorted by priority descending."""
        self._handlers.setdefault(event, []).append((priority, handler))
        self._handlers[event].sort(key=lambda x: -x[0])

    def emit(self, event: str, ctx: Any, **kwargs) -> bool:
        """Trigger event. Returns False if propagation was stopped."""
        for _, handler in self._handlers.get(event, []):
            result = handler(ctx, **kwargs)
            if result is STOP_PROPAGATION:
                return False
        return True
