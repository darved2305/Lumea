"""
ConnectionManager tests (backend/src/routes/websocket.py).
"""

import pytest


class _WS:
    def __init__(self, fail_send=False):
        self.accepted = False
        self.sent = []
        self.fail_send = fail_send

    async def accept(self):
        self.accepted = True

    async def send_json(self, msg):
        if self.fail_send:
            raise RuntimeError("dead")
        self.sent.append(msg)


@pytest.mark.anyio
async def test_connection_manager_tracks_connections_and_cleans_dead():
    from src.routes.websocket import ConnectionManager

    mgr = ConnectionManager()
    ws1 = _WS()
    ws2 = _WS(fail_send=True)

    await mgr.connect(ws1, "u")
    await mgr.connect(ws2, "u")

    assert ws1.accepted and ws2.accepted
    assert "u" in mgr.active_connections
    assert len(mgr.active_connections["u"]) == 2

    await mgr.send_to_user("u", {"type": "x"})
    # Dead connection removed
    assert len(mgr.active_connections["u"]) == 1

