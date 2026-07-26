"""Local OpenAI-compatible mock used when no real API key is available.

This is a test-only server. It never accepts or prints a real credential.
"""

from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


MOCK_KEY = "mock-test-key"
MOCK_MODEL = "mock-digital-human"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("[mock-llm]", fmt % args)

    def json_response(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.json_response(200, {"status": "ok", "model": MOCK_MODEL})
        else:
            self.json_response(404, {"error": {"message": "not found"}})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.json_response(404, {"error": {"message": "not found"}})
            return
        if self.headers.get("Authorization") != f"Bearer {MOCK_KEY}":
            self.json_response(401, {"error": {"message": "invalid mock key"}})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.json_response(400, {"error": {"message": "invalid json"}})
            return
        if payload.get("model") != MOCK_MODEL:
            self.json_response(404, {"error": {"message": "mock model not found"}})
            return

        messages = payload.get("messages") or []
        user_messages = [item for item in messages if item.get("role") == "user"]
        latest = str(user_messages[-1].get("content", "")) if user_messages else ""
        answer = f"这是第{len(user_messages)}轮回答：我收到了“{latest}”。"
        if payload.get("stream"):
            self.close_connection = True
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            midpoint = max(1, len(answer) // 2)
            for part in (answer[:midpoint], answer[midpoint:]):
                time.sleep(0.15)
                event = {
                    "id": "chatcmpl-local-mock",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": MOCK_MODEL,
                    "choices": [
                        {"index": 0, "delta": {"content": part}, "finish_reason": None}
                    ],
                }
                self.wfile.write(
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
                )
                self.wfile.flush()
            final = {
                "id": "chatcmpl-local-mock",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": MOCK_MODEL,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            self.wfile.write(
                f"data: {json.dumps(final)}\n\ndata: [DONE]\n\n".encode("utf-8")
            )
            self.wfile.flush()
            return

        self.json_response(
            200,
            {
                "id": "chatcmpl-local-mock",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": MOCK_MODEL,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": answer},
                        "finish_reason": "stop",
                    }
                ],
            },
        )


def main():
    parser = argparse.ArgumentParser(description="Local OpenAI-compatible mock")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Mock OpenAI API: http://{args.host}:{args.port}/v1")
    print(f"Model: {MOCK_MODEL}; test key is fixed and non-secret.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
