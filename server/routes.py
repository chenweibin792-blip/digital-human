###############################################################################
#  服务器路由 — 统一异常处理的 API 路由
###############################################################################

import json
import asyncio
import time
from aiohttp import web

from utils.logger import logger
from llm import (
    cancel_llm_session,
    clear_llm_session,
    get_llm_history,
)
from tts.edge import (
    DEFAULT_PITCH,
    DEFAULT_RATE,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_VOICE,
    DEFAULT_VOLUME,
    EdgeTTSError,
    list_edge_voices,
    pcm_to_wav_bytes,
    speed_to_rate,
    synthesize_edge_pcm,
    validate_edge_settings,
)


# ─── 路由工具函数 ──────────────────────────────────────────────────────────

def json_ok(data=None):
    """返回成功 JSON 响应"""
    body = {"code": 0, "msg": "ok"}
    if data is not None:
        body["data"] = data
    return web.Response(
        content_type="application/json",
        text=json.dumps(body),
    )


def json_error(msg: str, code: int = -1):
    """返回错误 JSON 响应"""
    return web.Response(
        content_type="application/json",
        text=json.dumps({"code": code, "msg": str(msg)}),
    )


from server.session_manager import session_manager
from server.avatar_routes import setup_avatar_routes

def get_session(request, sessionid: str):
    """从 app 中获取 session 实例"""
    return session_manager.get_session(sessionid)


# ─── 路由处理函数 ──────────────────────────────────────────────────────────

async def human(request):
    """文本输入（echo/chat 模式），支持 voice/emotion 参数"""
    try:
        params: dict = await request.json()

        sessionid: str = params.get('sessionid', '')
        avatar_session = get_session(request, sessionid)
        if avatar_session is None:
            return json_error("session not found")

        if params.get('interrupt'):
            avatar_session.flush_talk()

        datainfo = {}
        if hasattr(avatar_session, "runtime_metrics"):
            avatar_session.runtime_metrics["request_started_at"] = time.perf_counter()
            avatar_session.runtime_metrics["last_request_mode"] = params.get("type", "")
            avatar_session.runtime_metrics["request_active"] = True
        if params.get('tts'):  # tts 参数透传（voice, emotion 等）
            datainfo['tts'] = params.get('tts')

        if params['type'] == 'echo':
            avatar_session.put_msg_txt(params['text'], datainfo)
        elif params['type'] == 'chat':
            llm_response = request.app.get("llm_response")
            if llm_response:
                asyncio.get_event_loop().run_in_executor(
                    None, llm_response, params['text'], avatar_session, datainfo
                )

        return json_ok()
    except Exception as e:
        logger.exception('human route exception:')
        return json_error(str(e))


async def interrupt_talk(request):
    """打断当前说话"""
    try:
        params = await request.json()
        sessionid = params.get('sessionid', '')
        avatar_session = get_session(request, sessionid)
        if avatar_session is None:
            return json_error("session not found")
        cancel_llm_session(sessionid)
        avatar_session.flush_talk()
        if hasattr(avatar_session, "runtime_metrics"):
            avatar_session.runtime_metrics["request_active"] = False
        avatar_session.send_msg(json.dumps(
            {"type": "llm", "status": "interrupted"}, ensure_ascii=False
        ))
        return json_ok()
    except Exception as e:
        logger.exception('interrupt_talk exception:')
        return json_error(str(e))


async def humanaudio(request):
    """上传音频文件"""
    try:
        form = await request.post()
        sessionid = str(form.get('sessionid', ''))
        fileobj = form["file"]
        filebytes = fileobj.file.read()

        datainfo = {}

        avatar_session = get_session(request, sessionid)
        if avatar_session is None:
            return json_error("session not found")
        avatar_session.put_audio_file(filebytes, datainfo)
        return json_ok()
    except Exception as e:
        logger.exception('humanaudio exception:')
        return json_error(str(e))


async def set_audiotype(request):
    """设置自定义状态（动作编排）"""
    try:
        params = await request.json()
        sessionid = params.get('sessionid', '')
        avatar_session = get_session(request, sessionid)
        if avatar_session is None:
            return json_error("session not found")
        avatar_session.set_custom_state(params['audiotype'])
        return json_ok()
    except Exception as e:
        logger.exception('set_audiotype exception:')
        return json_error(str(e))


async def record(request):
    """录制控制"""
    try:
        params = await request.json()
        sessionid = params.get('sessionid', '')
        avatar_session = get_session(request, sessionid)
        if avatar_session is None:
            return json_error("session not found")
        if params['type'] == 'start_record':
            avatar_session.start_recording()
        elif params['type'] == 'end_record':
            avatar_session.stop_recording()
        return json_ok()
    except Exception as e:
        logger.exception('record exception:')
        return json_error(str(e))


async def is_speaking(request):
    """查询是否正在说话"""
    params = await request.json()
    sessionid = params.get('sessionid', '')
    avatar_session = get_session(request, sessionid)
    if avatar_session is None:
        return json_error("session not found")
    return json_ok(data=avatar_session.is_speaking())


async def chat_history(request):
    sessionid = request.query.get("sessionid", "")
    if not session_manager.has_session(sessionid):
        return _api_error("会话不存在或已结束", 404)
    return web.json_response(
        {"sessionid": sessionid, "history": get_llm_history(sessionid)},
        dumps=lambda value: json.dumps(value, ensure_ascii=False),
    )


async def clear_chat(request):
    try:
        params = await request.json()
        sessionid = str(params.get("sessionid", ""))
        avatar_session = get_session(request, sessionid)
        if avatar_session is None:
            return _api_error("会话不存在或已结束", 404)
        cancel_llm_session(sessionid)
        avatar_session.flush_talk()
        clear_llm_session(sessionid)
        if hasattr(avatar_session, "runtime_metrics"):
            avatar_session.runtime_metrics["request_active"] = False
        avatar_session.send_msg(json.dumps(
            {"type": "llm", "status": "cleared"}, ensure_ascii=False
        ))
        return web.json_response({"code": 0, "message": "当前会话已清空"})
    except Exception:
        logger.error("Clear chat request failed")
        return _api_error("清空当前会话失败", 500)


async def runtime_status(request):
    sessionid = request.query.get("sessionid", "")
    avatar_session = session_manager.get_session(sessionid)
    if avatar_session is None:
        return web.json_response({"sessionid": sessionid, "active": False})
    try:
        import os
        import psutil
        import torch

        process = psutil.Process(os.getpid())
        gpu = {
            "available": bool(torch.cuda.is_available()),
            "allocated_mb": 0.0,
            "reserved_mb": 0.0,
            "peak_allocated_mb": 0.0,
            "total_mb": 0.0,
        }
        if gpu["available"]:
            gpu.update(
                {
                    "allocated_mb": round(torch.cuda.memory_allocated() / 1048576, 1),
                    "reserved_mb": round(torch.cuda.memory_reserved() / 1048576, 1),
                    "peak_allocated_mb": round(
                        torch.cuda.max_memory_allocated() / 1048576, 1
                    ),
                    "total_mb": round(
                        torch.cuda.get_device_properties(0).total_memory / 1048576,
                        1,
                    ),
                }
            )
        return web.json_response(
            {
                "sessionid": sessionid,
                "active": True,
                "speaking": avatar_session.is_speaking(),
                "metrics": dict(getattr(avatar_session, "runtime_metrics", {})),
                "gpu": gpu,
                "process_memory_mb": round(process.memory_info().rss / 1048576, 1),
                "system_memory_percent": psutil.virtual_memory().percent,
            }
        )
    except Exception:
        logger.error("Runtime status collection failed")
        return _api_error("运行状态暂时不可用", 500)


async def close_session(request):
    try:
        params = await request.json()
        sessionid = str(params.get("sessionid", "")).strip()
        if not sessionid:
            return _api_error("缺少 sessionid", 400)
        rtc_manager = request.app.get("rtc_manager")
        if rtc_manager is None:
            return _api_error("WebRTC 管理器不可用", 503)
        await rtc_manager.close_session(sessionid)
        return web.json_response({"code": 0, "message": "会话已关闭"})
    except Exception:
        logger.error("Close session request failed")
        return _api_error("关闭会话失败", 500)

async def sse_handler(request):
    """SSE 事件流，推送服务器状态更新到客户端"""
    sessionid = request.query.get('sessionid', '')
    avatar_session = session_manager.get_session(sessionid)
    if avatar_session is None:
        return json_error("session not found")

    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        }
    )
    await response.prepare(request)

    import queue
    msgqueue = queue.Queue()
    avatar_session.add_msgqueue(msgqueue)

    try:
        while True:
            try:
                msg = msgqueue.get_nowait()
                await response.write(f"data: {msg}\n\n".encode('utf-8'))
            except queue.Empty:
                await asyncio.sleep(0.01)
    except (asyncio.CancelledError, ConnectionResetError):
        logger.info('SSE connection closed for session: %s', sessionid)
    finally:
        if msgqueue in avatar_session.msgqueues:
            avatar_session.msgqueues.remove(msgqueue)

    return response


async def admin_config(request):
    """Admin: 获取全局配置参数"""
    try:
        opt = request.app.get("opt")
        if opt:
            safe_config = dict(vars(opt))
            for key in list(safe_config):
                if "KEY" in key.upper() or "TOKEN" in key.upper() or "SECRET" in key.upper():
                    safe_config[key] = "***" if safe_config[key] else ""
            return json_ok(data={"config": safe_config})
        return json_error("Config not found")
    except Exception as e:
        logger.exception('admin_config exception:')
        return json_error(str(e))


async def admin_sessions(request):
    """Admin: 获取活跃的会话及其配置"""
    try:
        sessions_info = []
        for sid, avatar_session in session_manager.sessions.items():
            if avatar_session:
                s_opt = getattr(avatar_session, 'opt', None)
                s_data = {
                    "sessionid": sid,
                    "speaking": avatar_session.is_speaking() if hasattr(avatar_session, 'is_speaking') else False,
                    "recording": getattr(avatar_session, 'recording', False),
                }
                if s_opt:
                    s_data.update({
                        "model": getattr(s_opt, "model", ""),
                        "avatar_id": getattr(s_opt, "avatar_id", ""),
                        "REF_FILE": getattr(s_opt, "REF_FILE", ""),
                        "transport": getattr(s_opt, "transport", ""),
                        "batch_size": getattr(s_opt, "batch_size", 0),
                        "customopt": getattr(s_opt, "customopt", []),
                    })
                sessions_info.append(s_data)
        return json_ok(data={"sessions": sessions_info})
    except Exception as e:
        logger.exception('admin_sessions exception:')
        return json_error(str(e))


def _edge_config(opt):
    return validate_edge_settings(
        voice=getattr(opt, "EDGE_TTS_VOICE", DEFAULT_VOICE),
        rate=getattr(opt, "EDGE_TTS_RATE", DEFAULT_RATE),
        volume=getattr(opt, "EDGE_TTS_VOLUME", DEFAULT_VOLUME),
        pitch=getattr(opt, "EDGE_TTS_PITCH", DEFAULT_PITCH),
        timeout_seconds=getattr(
            opt, "TTS_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS
        ),
    )


def _api_error(message: str, status: int):
    return web.json_response(
        {"code": -1, "message": str(message)}, status=status, dumps=lambda v: json.dumps(v, ensure_ascii=False)
    )


async def tts_config(request):
    """Read or update the non-sensitive runtime EdgeTTS settings."""
    opt = request.app.get("opt")
    if opt is None:
        return _api_error("TTS 配置不可用", 503)
    try:
        if request.method == "POST":
            payload = await request.json()
            current = _edge_config(opt)
            updated = validate_edge_settings(
                voice=payload.get("voice", current["voice"]),
                rate=payload.get("rate", current["rate"]),
                volume=payload.get("volume", current["volume"]),
                pitch=payload.get("pitch", current["pitch"]),
                timeout_seconds=payload.get(
                    "timeout_seconds", current["timeout_seconds"]
                ),
            )
            opt.EDGE_TTS_VOICE = updated["voice"]
            opt.EDGE_TTS_RATE = updated["rate"]
            opt.EDGE_TTS_VOLUME = updated["volume"]
            opt.EDGE_TTS_PITCH = updated["pitch"]
            opt.TTS_TIMEOUT_SECONDS = updated["timeout_seconds"]
        settings = _edge_config(opt)
        return web.json_response(
            {"provider": "edge", **settings},
            dumps=lambda v: json.dumps(v, ensure_ascii=False),
        )
    except EdgeTTSError as exc:
        return _api_error(str(exc), 400)
    except Exception:
        logger.exception("EdgeTTS config endpoint failed")
        return _api_error("TTS 配置处理失败", 500)


async def _get_edge_voices(request):
    opt = request.app.get("opt")
    try:
        timeout = getattr(opt, "TTS_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
        voices = await list_edge_voices(timeout)
        locale = request.query.get("locale", "").strip()
        if locale:
            voices = [voice for voice in voices if voice.get("Locale") == locale]
        return voices
    except EdgeTTSError:
        raise
    except Exception as exc:
        raise EdgeTTSError("无法获取语音列表，请检查网络连接") from exc


async def edge_voices_api(request):
    try:
        voices = await _get_edge_voices(request)
        return web.json_response(
            {"provider": "edge", "count": len(voices), "voices": voices},
            dumps=lambda v: json.dumps(v, ensure_ascii=False),
        )
    except EdgeTTSError as exc:
        status = 504 if "超时" in str(exc) else 503
        return _api_error(str(exc), status)


async def openai_voices_api(request):
    """Compatibility endpoint used by the existing TTS management page."""
    try:
        voices = await _get_edge_voices(request)
        return web.json_response(
            {
                "voices": [voice.get("ShortName") for voice in voices],
                "uploaded_voices": [],
                "details": voices,
            },
            dumps=lambda v: json.dumps(v, ensure_ascii=False),
        )
    except EdgeTTSError as exc:
        status = 504 if "超时" in str(exc) else 503
        return _api_error(str(exc), status)


async def openai_speech_api(request):
    """Synthesize a WAV preview using the same adapter as Wav2Lip."""
    opt = request.app.get("opt")
    try:
        payload = await request.json()
        if str(payload.get("response_format", "wav")).lower() != "wav":
            return _api_error("EdgeTTS 预览接口当前仅支持 WAV 格式", 400)
        defaults = _edge_config(opt)
        rate = payload.get("rate")
        if rate is None and "speed" in payload:
            rate = speed_to_rate(payload["speed"])
        settings = validate_edge_settings(
            voice=payload.get("voice", defaults["voice"]),
            rate=rate or defaults["rate"],
            volume=payload.get("volume", defaults["volume"]),
            pitch=payload.get("pitch", defaults["pitch"]),
            timeout_seconds=defaults["timeout_seconds"],
        )
        pcm = await asyncio.to_thread(
            synthesize_edge_pcm,
            text=payload.get("input", ""),
            sample_rate=16_000,
            **settings,
        )
        wav = pcm_to_wav_bytes(pcm)
        return web.Response(
            body=wav,
            content_type="audio/wav",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": 'inline; filename="edge-preview.wav"',
            },
        )
    except EdgeTTSError as exc:
        message = str(exc)
        if "超时" in message:
            status = 504
        elif "网络" in message:
            status = 503
        else:
            status = 400
        return _api_error(message, status)
    except (json.JSONDecodeError, TypeError):
        return _api_error("请求内容格式无效", 400)
    except Exception:
        logger.exception("EdgeTTS speech endpoint failed")
        return _api_error("语音合成失败，服务仍在运行，请稍后重试", 500)


# ─── 路由注册 ──────────────────────────────────────────────────────────────

def setup_routes(app):
    """注册所有路由到 aiohttp app"""
    app.router.add_post("/human", human)
    app.router.add_post("/humanaudio", humanaudio)
    app.router.add_post("/set_audiotype", set_audiotype)
    app.router.add_post("/record", record)
    app.router.add_post("/interrupt_talk", interrupt_talk)
    app.router.add_post("/is_speaking", is_speaking)
    app.router.add_get("/api/chat/history", chat_history)
    app.router.add_post("/api/chat/clear", clear_chat)
    app.router.add_get("/api/status", runtime_status)
    app.router.add_post("/api/session/close", close_session)
    app.router.add_get("/api/admin/config", admin_config)
    app.router.add_get("/api/admin/sessions", admin_sessions)
    app.router.add_get("/api/tts/config", tts_config)
    app.router.add_post("/api/tts/config", tts_config)
    app.router.add_get("/api/tts/voices", edge_voices_api)
    app.router.add_get("/v1/audio/voices", openai_voices_api)
    app.router.add_post("/v1/audio/speech", openai_speech_api)
    app.router.add_get('/sse', sse_handler)

    # ── Local ASR endpoint (SenseVoice/FunASR) ── Issue #604 ──
    try:
        from server.asr_server import asr_websocket_handler, is_funasr_available
        if is_funasr_available():
            app.router.add_get("/api/asr", asr_websocket_handler)
            logger.info("[ASR] Local SenseVoice ASR endpoint enabled at /api/asr")
        else:
            logger.info("[ASR] funasr not installed — local ASR endpoint disabled "
                        "(pip install funasr modelscope)")
    except Exception as e:
        logger.warning(f"[ASR] Failed to register ASR endpoint: {e}")

    # 注册 avatar 生成相关的路由
    setup_avatar_routes(app)

    app.router.add_static('/', path='web')
