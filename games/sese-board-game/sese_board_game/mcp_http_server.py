from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .engine import run_command
from .mcp_server import handle_request
from .tool_adapter import default_save_path


HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "10000"))
SAVE_PATH = Path(os.environ.get("SESE_SAVE_PATH", "/tmp/sese-board-game.json"))


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class MCPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_json(self, payload: Any, status: int = 200) -> None:
        raw = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept, MCP-Protocol-Version, MCP-Session-Id")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True})

    def do_GET(self) -> None:
        if self.path.rstrip("/") in {"", "/health", "/healthz"}:
            self._send_json(
                {
                    "ok": True,
                    "service": "sese-board-game-mcp",
                    "transport": "streamable-http-compatible",
                }
            )
            return
        self._send_json({"ok": False, "error": "not found"}, status=404)

    def do_DELETE(self) -> None:
        if self.path.rstrip("/") != "/mcp":
            self._send_json({"ok": False, "error": "not found"}, status=404)
            return
        self._send_json({"ok": True})

    def do_POST(self) -> None:
        path = self.path.rstrip("/")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                self._send_json({"ok": False, "error": "empty request body"}, status=400)
                return
            body = json.loads(self.rfile.read(length).decode("utf-8"))

            # Simple JSON command endpoint used by the standalone web preview.
            # The MCP client continues to use /mcp below.
            if path == "/command":
                if not isinstance(body, dict):
                    self._send_json({"ok": False, "error": "request body must be an object"}, status=400)
                    return
                command = str(body.get("command") or "status").strip()
                save_path = body.get("save_path") or default_save_path()
                payload = run_command(command, save_path=save_path)
                self._send_json(payload, status=200 if payload.get("ok", True) else 400)
                return

            if path != "/mcp":
                self._send_json({"ok": False, "error": "not found"}, status=404)
                return

            response = handle_request(body)
            if response is None:
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self._send_json(response)
        except json.JSONDecodeError as exc:
            self._send_json(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error", "data": {"detail": str(exc)}}},
                status=400,
            )
        except Exception as exc:
            print(f"MCP HTTP error: {exc}")
            self._send_json({"ok": False, "error": "internal server error"}, status=500)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[mcp-http] {self.address_string()} - {fmt % args}")


def main() -> None:
    SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), MCPHandler)
    print(f"Sese Board Game MCP HTTP server listening on http://{HOST}:{PORT}")
    print(f"MCP endpoint: http://{HOST}:{PORT}/mcp")
    print(f"Command endpoint: http://{HOST}:{PORT}/command")
    print(f"Save path: {SAVE_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
