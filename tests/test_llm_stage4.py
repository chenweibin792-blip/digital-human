import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock

from llm import (
    LLMError,
    LLMSettings,
    OpenAICompatibleLLM,
    clean_text_for_speech,
)


class MockOpenAIHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    requests = []

    def log_message(self, *_args):
        return

    def _write_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._write_json(404, {"error": {"message": "not found"}})
            return
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length).decode("utf-8"))
        self.__class__.requests.append(
            {
                "authorization": self.headers.get("Authorization"),
                "request": request,
            }
        )
        if self.headers.get("Authorization") != "Bearer mock-key":
            self._write_json(
                401,
                {"error": {"message": "invalid key", "type": "authentication_error"}},
            )
            return

        model = request.get("model")
        if model == "missing-model":
            self._write_json(404, {"error": {"message": "model not found"}})
            return
        if model == "rate-model":
            self._write_json(429, {"error": {"message": "too many requests"}})
            return
        if model == "non-json":
            body = b"upstream proxy returned html"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if model == "timeout-model":
            time.sleep(1.2)

        content = (
            ""
            if model == "empty-model"
            else "**你好** [文档](https://example.test) https://secret.test "
                 "```python\nprint('not spoken')\n``` 回答完成。"
        )
        if request.get("stream"):
            self.close_connection = True
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            parts = [content[: len(content) // 2], content[len(content) // 2 :]]
            for part in parts:
                event = {
                    "id": "chatcmpl-mock",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": model,
                    "choices": [
                        {"index": 0, "delta": {"content": part}, "finish_reason": None}
                    ],
                }
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
                self.wfile.flush()
            if model == "interrupted-model":
                return
            final = {
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            self.wfile.write(f"data: {json.dumps(final)}\n\ndata: [DONE]\n\n".encode("utf-8"))
            self.wfile.flush()
            return

        self._write_json(
            200,
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": 1,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
            },
        )


class LLMStage4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        MockOpenAIHandler.requests = []
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockOpenAIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def settings(self, **overrides):
        values = {
            "provider": "openai_compatible",
            "base_url": self.base_url,
            "api_key": "mock-key",
            "model": "mock-model",
            "timeout_seconds": 3,
            "max_retries": 0,
            "temperature": 0.7,
            "max_history_turns": 2,
            "stream": True,
            "system_prompt": "测试系统提示",
        }
        values.update(overrides)
        return LLMSettings(**values)

    def assert_error_code(self, service, expected):
        with self.assertRaises(LLMError) as caught:
            service.generate("session-error", "测试")
        self.assertEqual(caught.exception.code, expected)
        self.assertNotIn("mock-key", str(caught.exception))

    def test_streaming_multiturn_history_isolated_and_limited(self):
        def stream_response(**_kwargs):
            return iter(
                [
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(
                                    content="**你好** [文档](https://example.test) "
                                ),
                                finish_reason=None,
                            )
                        ]
                    ),
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(content="https://secret.test 回答完成。"),
                                finish_reason=None,
                            )
                        ]
                    ),
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(content=None),
                                finish_reason="stop",
                            )
                        ]
                    ),
                ]
            )

        create = Mock(side_effect=stream_response)
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create)
            )
        )
        service = OpenAICompatibleLLM(self.settings(), client=client)
        for number in range(3):
            answer, metrics = service.generate("session-a", f"问题{number}")
            self.assertEqual(answer, "你好 文档 回答完成。")
            self.assertGreaterEqual(metrics["first_token_seconds"], 0)
        history = service.get_history("session-a")
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]["content"], "问题1")
        self.assertEqual(service.get_history("session-b"), [])
        last_request = create.call_args_list[-1].kwargs
        self.assertEqual(last_request["messages"][0]["role"], "system")

    def test_non_streaming_response(self):
        service = OpenAICompatibleLLM(self.settings(stream=False))
        answer, _ = service.generate("non-stream", "你好")
        self.assertEqual(answer, "你好 文档 回答完成。")
        self.assertEqual(
            MockOpenAIHandler.requests[-1]["authorization"], "Bearer mock-key"
        )

    def test_markdown_code_and_url_are_not_spoken(self):
        cleaned = clean_text_for_speech(
            "# 标题\n**说明** https://example.test\n```js\nalert(1)\n```"
        )
        self.assertEqual(cleaned, "标题 说明")

    def test_missing_api_key(self):
        with self.assertRaises(LLMError) as caught:
            self.settings(api_key="").validate()
        self.assertEqual(caught.exception.code, "api_key_missing")

    def test_authentication_failure(self):
        self.assert_error_code(
            OpenAICompatibleLLM(self.settings(api_key="wrong-key")),
            "authentication_failed",
        )

    def test_model_not_found(self):
        self.assert_error_code(
            OpenAICompatibleLLM(self.settings(model="missing-model")),
            "model_not_found",
        )

    def test_rate_limit(self):
        self.assert_error_code(
            OpenAICompatibleLLM(self.settings(model="rate-model")),
            "rate_limited",
        )

    def test_timeout(self):
        self.assert_error_code(
            OpenAICompatibleLLM(
                self.settings(model="timeout-model", timeout_seconds=0.1)
            ),
            "timeout",
        )

    def test_service_unavailable(self):
        self.assert_error_code(
            OpenAICompatibleLLM(
                self.settings(base_url="http://127.0.0.1:1/v1")
            ),
            "unavailable",
        )

    def test_non_json_response(self):
        service = OpenAICompatibleLLM(
            self.settings(model="non-json", stream=False)
        )
        with self.assertRaises(LLMError) as caught:
            service.generate("session-error", "测试")
        self.assertIn(caught.exception.code, {"invalid_response", "empty_response"})
        self.assertNotIn("mock-key", str(caught.exception))

    def test_empty_response(self):
        chunk = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=None),
                    finish_reason="stop",
                )
            ]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=Mock(return_value=iter([chunk]))
                )
            )
        )
        self.assert_error_code(
            OpenAICompatibleLLM(self.settings(), client=client),
            "empty_response",
        )

    def test_stream_interruption(self):
        chunk = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="已经开始"),
                    finish_reason=None,
                )
            ]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=iter([chunk])))
            )
        )
        self.assert_error_code(
            OpenAICompatibleLLM(self.settings(), client=client),
            "stream_interrupted",
        )

    def test_clear_single_session(self):
        service = OpenAICompatibleLLM(self.settings(stream=False))
        service.generate("one", "问题")
        service.generate("two", "问题")
        service.clear_session("one")
        self.assertEqual(service.get_history("one"), [])
        self.assertEqual(len(service.get_history("two")), 2)


if __name__ == "__main__":
    unittest.main()
