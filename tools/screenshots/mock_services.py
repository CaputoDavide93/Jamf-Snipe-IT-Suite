"""Tiny stand-ins for the parts of Jamf Pro and Snipe-IT that model-sync talks to.

Demo data only: made-up serials and Mac models. The mocks answer the same paths the
clients call, with the response shapes of the Jamf Pro Classic API, the Jamf Pro token
endpoint and the Snipe-IT v1 API. They are a screenshot and docs fixture, not emulators.

Snipe-IT starts with two of the four models, one of them under a different case than
Jamf reports, and no manufacturers, so the dry run has something to show.
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Jamf computers: id -> (serial, hardware model, model identifier)
COMPUTERS = {
    101: ("DEMO0000101", "MacBook Pro (16-inch, 2023)", "Mac15,7"),
    102: ("DEMO0000102", "MacBook Pro (16-inch, 2023)", "Mac15,7"),
    103: ("DEMO0000103", "MacBook Air (13-inch, M2, 2022)", "Mac14,2"),
    104: ("DEMO0000104", "Mac mini (2023)", "Mac14,3"),
    105: ("DEMO0000105", "Mac Studio (2022)", "Mac13,1"),
}

# Snipe-IT models: id -> name
SNIPE_MODELS = {
    11: "MacBook Pro (16-inch, 2023)",
    12: "MacBook Air (13-inch, M2, 2022)",
}

# Snipe-IT assets: id -> (serial, model id or None)
SNIPE_ASSETS = {
    201: ("DEMO0000101", 11),
    202: ("DEMO0000102", None),  # registered without a model
    203: ("DEMO0000103", 11),  # wrong model
    204: ("DEMO0000104", None),
    205: ("DEMO0000105", None),
}
TOKEN = "demo-token"


class _Base(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep the terminal quiet
        pass

    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class JamfHandler(_Base):
    def do_POST(self):
        if self.path == "/api/v1/auth/token":
            return self._send(200, {"token": TOKEN, "expires_in": 1800})
        self._send(404, {})

    def do_GET(self):
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self._send(401, {"error": "unauthorized"})
        if self.path == "/JSSResource/computers/subset/basic":
            rows = [{"id": cid, "serial_number": c[0]} for cid, c in COMPUTERS.items()]
            return self._send(200, {"computers": rows})
        m = re.fullmatch(r"/JSSResource/computers/id/(\d+)/subset/Hardware", self.path)
        if m and int(m.group(1)) in COMPUTERS:
            _, model, ident = COMPUTERS[int(m.group(1))]
            return self._send(200, {"computer": {"hardware": {"model": model, "model_identifier": ident}}})
        self._send(404, {})


class SnipeHandler(_Base):
    def _page(self, rows: list[dict]) -> dict:
        return {"total": len(rows), "rows": rows}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/v1/models":
            return self._send(200, self._page([{"id": i, "name": n} for i, n in SNIPE_MODELS.items()]))
        if path == "/api/v1/manufacturers":
            return self._send(200, self._page([]))
        if path == "/api/v1/hardware":
            rows = [
                {"id": aid, "serial": s,
                 "model": {"id": mid, "name": SNIPE_MODELS[mid]} if mid else None}
                for aid, (s, mid) in SNIPE_ASSETS.items()
            ]
            return self._send(200, self._page(rows))
        self._send(404, {})


def serve(handler, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), handler)
