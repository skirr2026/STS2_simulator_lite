"""ZmqBridge — REP socket bridge between CombatManager and external consumers."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import zmq

if TYPE_CHECKING:
    from sts2_simulator.combat.manager import CombatManager

DEFAULT_ADDRESS = "ipc:///tmp/sts2_sim.ipc"


class ZmqBridge:
    def __init__(self, address: str = DEFAULT_ADDRESS) -> None:
        self._address = address
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REP)
        self._socket.bind(address)
        self._cm: CombatManager | None = None

    def set_combat_manager(self, cm: "CombatManager") -> None:
        """Wire the bridge to a CombatManager instance."""
        self._cm = cm

    # ------------------------------------------------------------------
    # Callbacks called by CombatManager / Runner
    # ------------------------------------------------------------------

    def on_state_change(self, state: dict) -> None:
        """Push state to external consumer and dispatch the returned action."""
        self._send(state)
        raw = self._socket.recv()
        action = json.loads(raw.decode())
        self._dispatch(action)

    def on_battle_end(self, log: dict) -> None:
        """Push battle log to external consumer."""
        self._send({"type": "battle_log", "data": log})

    def on_campaign_end(self, log: dict) -> None:
        """Push campaign log to external consumer."""
        self._send({"type": "campaign_log", "data": log})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send(self, data: dict) -> None:
        self._socket.send(json.dumps(data).encode())

    def _dispatch(self, action: dict) -> None:
        """Parse action and call the corresponding CombatManager method."""
        if self._cm is None:
            self._send({"ok": False, "error": "no_combat_manager"})
            return

        action_type = action.get("action")

        if action_type == "play_card":
            result = self._cm.play_card(
                action.get("hand_index", 0),
                action.get("target_index", -1),
            )
            self._send(result)
        elif action_type == "use_potion":
            result = self._cm.use_potion(
                action.get("slot_index", 0),
                action.get("target_index", -1),
            )
            self._send(result)
        elif action_type == "end_turn":
            result = self._cm.end_turn()
            self._send(result)
        else:
            self._send({"ok": False, "error": f"invalid_action: {action_type}"})

    def close(self) -> None:
        """Release ZMQ resources."""
        self._socket.close()
        self._context.term()
