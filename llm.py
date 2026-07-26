"""OpenAI-compatible LLM integration for LiveTalking.

The browser never receives provider credentials.  Conversation history,
cancellation and request serialization are isolated by LiveTalking session ID.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from utils.logger import logger

if TYPE_CHECKING:
    from avatars.base_avatar import BaseAvatar


DEFAULT_SYSTEM_PROMPT = "你是一名简洁、自然、友好的AI数字人助手。"
_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```")
_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARKDOWN_RE = re.compile(r"(?m)^\s{0,3}(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+)|[*_~>`]+")
_WHITESPACE_RE = re.compile(r"\s+")
_SPEECH_BOUNDARY_RE = re.compile(r"(?<=[。！？!?；;])")


class LLMError(RuntimeError):
    def __init__(self, message: str, code: str = "llm_error"):
        super().__init__(message)
        self.code = code


class LLMCancelled(LLMError):
    def __init__(self):
        super().__init__("回答已停止", "cancelled")


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float
    max_retries: int
    temperature: float
    max_history_turns: int
    stream: bool
    system_prompt: str

    @classmethod
    def from_opt(cls, opt) -> "LLMSettings":
        def value(name, default=""):
            return getattr(opt, name, None) or os.getenv(name, default)

        stream_value = value("LLM_STREAM", "true")
        stream = (
            stream_value
            if isinstance(stream_value, bool)
            else str(stream_value).strip().lower() in {"1", "true", "yes", "on"}
        )
        settings = cls(
            provider=str(value("LLM_PROVIDER", "openai_compatible")),
            base_url=str(value("LLM_BASE_URL", "")).strip().rstrip("/"),
            api_key=str(value("LLM_API_KEY", "")).strip(),
            model=str(value("LLM_MODEL", "")).strip(),
            timeout_seconds=float(value("LLM_TIMEOUT_SECONDS", 60)),
            max_retries=int(value("LLM_MAX_RETRIES", 2)),
            temperature=float(value("LLM_TEMPERATURE", 0.7)),
            max_history_turns=int(value("LLM_MAX_HISTORY_TURNS", 10)),
            stream=stream,
            system_prompt=str(value("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)).strip(),
        )
        settings.validate()
        return settings

    def validate(self):
        if self.provider != "openai_compatible":
            raise LLMError("当前仅支持 OpenAI 兼容的大模型服务", "provider_invalid")
        if not self.base_url:
            raise LLMError("未配置大模型服务地址 LLM_BASE_URL", "base_url_missing")
        if not self.api_key:
            raise LLMError("未配置大模型 API Key", "api_key_missing")
        if not self.model:
            raise LLMError("未配置大模型名称 LLM_MODEL", "model_missing")
        if not 1 <= self.timeout_seconds <= 300:
            raise LLMError("大模型超时时间必须在 1 到 300 秒之间", "timeout_invalid")
        if not 0 <= self.max_retries <= 5:
            raise LLMError("大模型重试次数必须在 0 到 5 之间", "retries_invalid")
        if not 0 <= self.temperature <= 2:
            raise LLMError("大模型温度必须在 0 到 2 之间", "temperature_invalid")
        if not 1 <= self.max_history_turns <= 50:
            raise LLMError("最大历史轮数必须在 1 到 50 之间", "history_invalid")


def clean_text_for_speech(text: str) -> str:
    """Convert model output into safe, natural text for TTS."""
    value = str(text or "")
    value = _CODE_BLOCK_RE.sub(" ", value)
    value = _MARKDOWN_LINK_RE.sub(r"\1", value)
    value = _URL_RE.sub(" ", value)
    value = _MARKDOWN_RE.sub("", value)
    value = value.replace("&nbsp;", " ").replace("&amp;", "和")
    value = _WHITESPACE_RE.sub(" ", value).strip()
    return value


def split_text_for_speech(text: str, max_chars: int = 180) -> list[str]:
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        return []
    output: list[str] = []
    current = ""
    for sentence in _SPEECH_BOUNDARY_RE.split(cleaned):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) <= max_chars:
            current += sentence
            continue
        if current:
            output.append(current)
        while len(sentence) > max_chars:
            output.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        current = sentence
    if current:
        output.append(current)
    return output


def _emit(avatar_session, status: str, **payload):
    event = {"type": "llm", "status": status, **payload}
    try:
        avatar_session.send_msg(json.dumps(event, ensure_ascii=False))
    except Exception:
        logger.debug("LLM status event could not be delivered")


class OpenAICompatibleLLM:
    def __init__(self, settings: LLMSettings, client=None):
        self.settings = settings
        self._injected_client = client is not None
        self._client_lock = threading.Lock()
        self.client = client or self._new_client()
        self._history: dict[str, list[dict[str, str]]] = {}
        self._history_lock = threading.RLock()
        self._session_locks: dict[str, threading.Lock] = {}
        self._cancel_events: dict[str, threading.Event] = {}

    def _new_client(self):
        return OpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url,
            timeout=self.settings.timeout_seconds,
            max_retries=self.settings.max_retries,
        )

    def _reset_client(self):
        if self._injected_client:
            return
        with self._client_lock:
            old_client = self.client
            self.client = self._new_client()
            try:
                old_client.close()
            except Exception:
                pass

    def _session_lock(self, sessionid: str) -> threading.Lock:
        with self._history_lock:
            return self._session_locks.setdefault(sessionid, threading.Lock())

    def _cancel_event(self, sessionid: str) -> threading.Event:
        with self._history_lock:
            return self._cancel_events.setdefault(sessionid, threading.Event())

    def get_history(self, sessionid: str) -> list[dict[str, str]]:
        with self._history_lock:
            return [dict(item) for item in self._history.get(sessionid, [])]

    def clear_session(self, sessionid: str):
        self.cancel_session(sessionid)
        with self._history_lock:
            self._history.pop(sessionid, None)

    def remove_session(self, sessionid: str):
        self.clear_session(sessionid)
        with self._history_lock:
            self._session_locks.pop(sessionid, None)
            self._cancel_events.pop(sessionid, None)

    def cancel_session(self, sessionid: str):
        self._cancel_event(sessionid).set()

    def _messages(self, sessionid: str, user_message: str) -> list[dict[str, str]]:
        with self._history_lock:
            history = list(self._history.get(sessionid, []))
        return [
            {"role": "system", "content": self.settings.system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ]

    def _save_turn(self, sessionid: str, user_message: str, assistant_message: str):
        with self._history_lock:
            history = self._history.setdefault(sessionid, [])
            history.extend(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message},
                ]
            )
            max_messages = self.settings.max_history_turns * 2
            if len(history) > max_messages:
                del history[:-max_messages]

    def _map_error(self, exc: Exception) -> LLMError:
        if isinstance(exc, AuthenticationError):
            return LLMError("大模型认证失败，请检查 API Key", "authentication_failed")
        if isinstance(exc, RateLimitError):
            return LLMError("大模型请求过多，请稍后重试", "rate_limited")
        if isinstance(exc, APITimeoutError):
            return LLMError("大模型请求超时，请稍后重试", "timeout")
        if isinstance(exc, APIConnectionError):
            return LLMError("无法连接大模型服务，请检查服务地址和网络", "unavailable")
        if isinstance(exc, APIStatusError):
            if exc.status_code == 404:
                return LLMError("大模型服务或模型名称不存在", "model_not_found")
            if exc.status_code >= 500:
                return LLMError("大模型服务暂时不可用", "unavailable")
            return LLMError("大模型请求参数不被服务接受", "request_rejected")
        return LLMError("大模型返回异常，请稍后重试", "invalid_response")

    def generate(self, sessionid: str, user_message: str) -> tuple[str, dict]:
        message = str(user_message or "").strip()
        if not message:
            raise LLMError("问题不能为空", "empty_message")
        lock = self._session_lock(sessionid)
        if not lock.acquire(blocking=False):
            raise LLMError("当前会话正在生成回答，请稍候或先停止", "session_busy")
        cancel_event = self._cancel_event(sessionid)
        cancel_event.clear()
        started = time.perf_counter()
        first_token_seconds = None
        raw_answer = ""
        try:
            request = {
                "model": self.settings.model,
                "messages": self._messages(sessionid, message),
                "temperature": self.settings.temperature,
                "stream": self.settings.stream,
            }
            if self.settings.stream:
                stream_finished = False
                response = self.client.chat.completions.create(**request)
                for chunk in response:
                    if cancel_event.is_set():
                        raise LLMCancelled()
                    choices = getattr(chunk, "choices", None) or []
                    if not choices:
                        continue
                    if getattr(choices[0], "finish_reason", None) is not None:
                        stream_finished = True
                    content = getattr(choices[0].delta, "content", None)
                    if content:
                        if first_token_seconds is None:
                            first_token_seconds = time.perf_counter() - started
                        raw_answer += content
                if not stream_finished:
                    raise LLMError("大模型流式连接中断，请重试", "stream_interrupted")
            else:
                response = self.client.chat.completions.create(**request)
                if cancel_event.is_set():
                    raise LLMCancelled()
                choices = getattr(response, "choices", None) or []
                if choices:
                    raw_answer = getattr(choices[0].message, "content", None) or ""
                    first_token_seconds = time.perf_counter() - started
        except LLMError:
            raise
        except Exception as exc:
            if self.settings.stream and raw_answer:
                raise LLMError(
                    "大模型流式连接中断，请重试", "stream_interrupted"
                ) from None
            if isinstance(exc, (APIConnectionError, APITimeoutError)):
                self._reset_client()
            raise self._map_error(exc) from None
        else:
            spoken_answer = clean_text_for_speech(raw_answer)
            if not spoken_answer:
                raise LLMError("大模型返回内容为空", "empty_response")
            if cancel_event.is_set():
                raise LLMCancelled()
            self._save_turn(sessionid, message, raw_answer)
            metrics = {
                "first_token_seconds": round(first_token_seconds or 0.0, 4),
                "total_seconds": round(time.perf_counter() - started, 4),
            }
            return spoken_answer, metrics
        finally:
            lock.release()


_service: OpenAICompatibleLLM | None = None
_service_signature: tuple | None = None
_service_lock = threading.Lock()


def get_llm_service(opt) -> OpenAICompatibleLLM:
    global _service, _service_signature
    settings = LLMSettings.from_opt(opt)
    signature = tuple(settings.__dict__.values())
    with _service_lock:
        if _service is None or signature != _service_signature:
            _service = OpenAICompatibleLLM(settings)
            _service_signature = signature
        return _service


def clear_llm_session(sessionid: str):
    if _service is not None:
        _service.clear_session(sessionid)


def cancel_llm_session(sessionid: str):
    if _service is not None:
        _service.cancel_session(sessionid)


def remove_llm_session(sessionid: str):
    if _service is not None:
        _service.remove_session(sessionid)


def get_llm_history(sessionid: str) -> list[dict[str, str]]:
    if _service is None:
        return []
    return _service.get_history(sessionid)


def llm_response(message, avatar_session: "BaseAvatar", datainfo: dict | None = None):
    """Backward-compatible entry point used by the existing `/human` route."""
    datainfo = datainfo or {}
    sessionid = str(getattr(avatar_session, "sessionid", "") or avatar_session.opt.sessionid)
    _emit(avatar_session, "generating")
    try:
        service = get_llm_service(avatar_session.opt)
        answer, metrics = service.generate(sessionid, message)
        if hasattr(avatar_session, "runtime_metrics"):
            avatar_session.runtime_metrics["llm_first_token_seconds"] = metrics[
                "first_token_seconds"
            ]
            avatar_session.runtime_metrics["llm_total_seconds"] = metrics[
                "total_seconds"
            ]
        _emit(avatar_session, "answer", text=answer, metrics=metrics)
        # EdgeTTS performs its own safe network segmentation while preserving
        # one start/end lifecycle for the whole answer.
        avatar_session.put_msg_txt(answer, datainfo)
        _emit(avatar_session, "synthesizing", text=answer, metrics=metrics)
        logger.info(
            "LLM completed session=%s first_token=%.4fs total=%.4fs",
            sessionid,
            metrics["first_token_seconds"],
            metrics["total_seconds"],
        )
        return {"ok": True, "answer": answer, "metrics": metrics}
    except LLMCancelled as exc:
        if hasattr(avatar_session, "runtime_metrics"):
            avatar_session.runtime_metrics["request_active"] = False
        _emit(avatar_session, "interrupted", message=str(exc), code=exc.code)
        return {"ok": False, "message": str(exc), "code": exc.code}
    except LLMError as exc:
        if hasattr(avatar_session, "runtime_metrics"):
            avatar_session.runtime_metrics["request_active"] = False
        _emit(avatar_session, "error", message=str(exc), code=exc.code)
        logger.warning("LLM request failed session=%s code=%s", sessionid, exc.code)
        return {"ok": False, "message": str(exc), "code": exc.code}
    except Exception:
        if hasattr(avatar_session, "runtime_metrics"):
            avatar_session.runtime_metrics["request_active"] = False
        _emit(
            avatar_session,
            "error",
            message="大模型处理失败，请稍后重试",
            code="internal_error",
        )
        logger.error("Unexpected LLM failure session=%s", sessionid)
        return {
            "ok": False,
            "message": "大模型处理失败，请稍后重试",
            "code": "internal_error",
        }
