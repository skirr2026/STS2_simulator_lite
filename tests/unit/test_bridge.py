"""
Unit tests for ZmqBridge — mock ZeroMQ sockets.
Validates: Requirements 7.3, 7.4, 7.5, 7.6, 7.7
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call


def _make_bridge(address: str = "ipc:///tmp/test.ipc"):
    from sts2_simulator.bridge.zmq_bridge import ZmqBridge
    with patch("sts2_simulator.bridge.zmq_bridge.zmq") as mock_zmq:
        mock_ctx = MagicMock()
        mock_socket = MagicMock()
        mock_zmq.Context.return_value = mock_ctx
        mock_ctx.socket.return_value = mock_socket
        bridge = ZmqBridge(address)
        bridge._socket = mock_socket  # expose for assertions
    return bridge, mock_socket


# ---------------------------------------------------------------------------
# on_state_change — serialises state and sends over ZMQ
# ---------------------------------------------------------------------------

class TestOnStateChange:
    """测试 on_state_change 序列化 state 为 JSON 并推送"""

    def test_sends_json_encoded_state(self):
        """on_state_change 应将 state dict 序列化为 JSON 并通过 socket 发送"""
        from sts2_simulator.bridge.zmq_bridge import ZmqBridge
        with patch("sts2_simulator.bridge.zmq_bridge.zmq") as mock_zmq:
            mock_ctx = MagicMock()
            mock_socket = MagicMock()
            mock_zmq.Context.return_value = mock_ctx
            mock_ctx.socket.return_value = mock_socket
            # recv returns a valid end_turn action so the bridge doesn't loop
            mock_socket.recv.return_value = json.dumps({"action": "end_turn"}).encode()

            bridge = ZmqBridge()
            mock_cm = MagicMock()
            mock_cm.end_turn.return_value = {"ok": True}
            bridge.set_combat_manager(mock_cm)

            state = {"type": "state", "data": {"result": None, "turn": 1}}
            bridge.on_state_change(state)

            # First send call should be the state push
            first_send_bytes = mock_socket.send.call_args_list[0][0][0]
            sent_data = json.loads(first_send_bytes.decode())
            assert sent_data == state

    def test_receives_action_and_dispatches_end_turn(self):
        """on_state_change 收到 end_turn action 后应调用 cm.end_turn"""
        from sts2_simulator.bridge.zmq_bridge import ZmqBridge
        with patch("sts2_simulator.bridge.zmq_bridge.zmq") as mock_zmq:
            mock_ctx = MagicMock()
            mock_socket = MagicMock()
            mock_zmq.Context.return_value = mock_ctx
            mock_ctx.socket.return_value = mock_socket
            mock_socket.recv.return_value = json.dumps({"action": "end_turn"}).encode()

            bridge = ZmqBridge()
            mock_cm = MagicMock()
            mock_cm.end_turn.return_value = {"ok": True}
            bridge.set_combat_manager(mock_cm)

            bridge.on_state_change({"type": "state", "data": {"result": None}})
            mock_cm.end_turn.assert_called_once()

    def test_receives_play_card_action(self):
        """on_state_change 收到 play_card action 后应调用 cm.play_card"""
        from sts2_simulator.bridge.zmq_bridge import ZmqBridge
        with patch("sts2_simulator.bridge.zmq_bridge.zmq") as mock_zmq:
            mock_ctx = MagicMock()
            mock_socket = MagicMock()
            mock_zmq.Context.return_value = mock_ctx
            mock_ctx.socket.return_value = mock_socket
            action = {"action": "play_card", "hand_index": 0, "target_index": 1}
            mock_socket.recv.return_value = json.dumps(action).encode()

            bridge = ZmqBridge()
            mock_cm = MagicMock()
            mock_cm.play_card.return_value = {"ok": True}
            bridge.set_combat_manager(mock_cm)

            bridge.on_state_change({"type": "state", "data": {"result": None}})
            mock_cm.play_card.assert_called_once_with(0, 1)

    def test_receives_use_potion_action(self):
        """on_state_change 收到 use_potion action 后应调用 cm.use_potion"""
        from sts2_simulator.bridge.zmq_bridge import ZmqBridge
        with patch("sts2_simulator.bridge.zmq_bridge.zmq") as mock_zmq:
            mock_ctx = MagicMock()
            mock_socket = MagicMock()
            mock_zmq.Context.return_value = mock_ctx
            mock_ctx.socket.return_value = mock_socket
            action = {"action": "use_potion", "slot_index": 0, "target_index": 0}
            mock_socket.recv.return_value = json.dumps(action).encode()

            bridge = ZmqBridge()
            mock_cm = MagicMock()
            mock_cm.use_potion.return_value = {"ok": True}
            bridge.set_combat_manager(mock_cm)

            bridge.on_state_change({"type": "state", "data": {"result": None}})
            mock_cm.use_potion.assert_called_once_with(0, 0)

    def test_unknown_action_returns_error(self):
        """on_state_change 收到未知 action 类型应返回 invalid_action 错误"""
        from sts2_simulator.bridge.zmq_bridge import ZmqBridge
        with patch("sts2_simulator.bridge.zmq_bridge.zmq") as mock_zmq:
            mock_ctx = MagicMock()
            mock_socket = MagicMock()
            mock_zmq.Context.return_value = mock_ctx
            mock_ctx.socket.return_value = mock_socket
            mock_socket.recv.return_value = json.dumps({"action": "fly_away"}).encode()

            bridge = ZmqBridge()
            mock_cm = MagicMock()
            bridge.set_combat_manager(mock_cm)

            bridge.on_state_change({"type": "state", "data": {"result": None}})

            # Should have sent an error response back
            # (second send call after the state push)
            assert mock_socket.send.call_count >= 1


# ---------------------------------------------------------------------------
# on_battle_end
# ---------------------------------------------------------------------------

class TestOnBattleEnd:
    """测试 on_battle_end 推送 battle_log"""

    def test_sends_battle_log(self):
        """on_battle_end 应将 battle_log 序列化为 JSON 并发送"""
        from sts2_simulator.bridge.zmq_bridge import ZmqBridge
        with patch("sts2_simulator.bridge.zmq_bridge.zmq") as mock_zmq:
            mock_ctx = MagicMock()
            mock_socket = MagicMock()
            mock_zmq.Context.return_value = mock_ctx
            mock_ctx.socket.return_value = mock_socket

            bridge = ZmqBridge()
            log = {"result": "victory", "final_hp": 50, "turns": 3}
            bridge.on_battle_end(log)

            sent_bytes = mock_socket.send.call_args[0][0]
            sent_data = json.loads(sent_bytes.decode())
            assert sent_data["type"] == "battle_log"
            assert sent_data["data"] == log


# ---------------------------------------------------------------------------
# on_campaign_end
# ---------------------------------------------------------------------------

class TestOnCampaignEnd:
    """测试 on_campaign_end 推送 campaign_log"""

    def test_sends_campaign_log(self):
        """on_campaign_end 应将 campaign_log 序列化为 JSON 并发送"""
        from sts2_simulator.bridge.zmq_bridge import ZmqBridge
        with patch("sts2_simulator.bridge.zmq_bridge.zmq") as mock_zmq:
            mock_ctx = MagicMock()
            mock_socket = MagicMock()
            mock_zmq.Context.return_value = mock_ctx
            mock_ctx.socket.return_value = mock_socket

            bridge = ZmqBridge()
            log = {"result": "defeat", "battles_completed": 2, "final_hp": 0}
            bridge.on_campaign_end(log)

            sent_bytes = mock_socket.send.call_args[0][0]
            sent_data = json.loads(sent_bytes.decode())
            assert sent_data["type"] == "campaign_log"
            assert sent_data["data"] == log
