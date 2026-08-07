"""
api/setup.py — One-time Google Sheets tab initialization.
Access: GET https://your-vercel-url/api/setup
"""
import json
from http.server import BaseHTTPRequestHandler
from lib import sheets


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def _send(self, status: int, body: str):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        try:
            sheets.setup_sheets()
            self._send(200, json.dumps({
                "ok": True,
                "msg": "Sheets setup complete — all tabs created"
            }))
        except Exception as e:
            self._send(500, json.dumps({"ok": False, "error": str(e)}))
