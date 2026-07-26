###############################################################################
#  WebRTC 连接管理 + RTC 音频/视频接收
###############################################################################

import json
import asyncio
import random
import copy
from typing import Dict, Optional
import queue

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
from aiortc.rtcrtpsender import RTCRtpSender

from utils.logger import logger


# def _rand_session_id(n: int = 6) -> int:
#     """生成 N 位随机 session ID"""
#     return random.randint(10 ** (n - 1), 10 ** n - 1)


from server.session_manager import session_manager
from server.session_manager import MaxSessionError

class RTCManager:
    """
    WebRTC 连接管理器。
    
    管理 PeerConnection 生命周期、音视频轨道收发、DataChannel。
    """

    def __init__(self, opt):
        """
        Args:
            opt: 全局配置
        """
        self.opt = opt
        self.pcs: set = set()
        self.session_pcs: dict[str, RTCPeerConnection] = {}
        self.session_players: dict[str, object] = {}
        self.closing_sessions: set[str] = set()

    async def close_session(self, sessionid: str):
        """Close one peer and release only its matching avatar resources."""
        if sessionid in self.closing_sessions:
            return
        self.closing_sessions.add(sessionid)
        try:
            pc = self.session_pcs.pop(sessionid, None)
            player = self.session_players.pop(sessionid, None)
            if player is not None:
                # Release workers before closing the peer. The connection-state
                # callback can fire from pc.close(), so the closing guard also
                # prevents a re-entrant close from racing this cleanup.
                player.audio.stop()
                player.video.stop()
            session_manager.remove_session(sessionid)
            if pc is not None:
                self.pcs.discard(pc)
                if pc.connectionState != "closed":
                    try:
                        await asyncio.wait_for(pc.close(), timeout=5)
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Timed out closing peer for session=%s; resources were released",
                            sessionid,
                        )
        finally:
            self.closing_sessions.discard(sessionid)

    async def handle_offer(self, request):
        """处理 WebRTC offer 信令"""
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        previous_sessionid = str(params.get("previous_sessionid", "")).strip()
        if previous_sessionid:
            await self.close_session(previous_sessionid)

        # 通过 SessionManager 构建（内部会检查 max_session）
        try:
            sessionid = await session_manager.create_session(params)
        except MaxSessionError as e:
            logger.warning("Rejecting offer: %s", e)
            return web.Response(
                content_type="application/json",
                text=json.dumps({"code": -1, "msg": str(e)}),
            )
        logger.info('offer sessionid=%s', sessionid)
        avatar_session = session_manager.get_session(sessionid)

        # 创建 PeerConnection
        ice_server = RTCIceServer(urls=self.opt.stun) #'stun:stun.freeswitch.org:3478'
        pc = RTCPeerConnection(
            configuration=RTCConfiguration(iceServers=[ice_server])
        )
        self.pcs.add(pc)
        self.session_pcs[sessionid] = pc

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info("Connection state is %s", pc.connectionState)
            if pc.connectionState in ("failed", "disconnected", "closed"):
                if self.session_pcs.get(sessionid) is pc:
                    await self.close_session(sessionid)

        # 添加发送轨道
        from server.webrtc import HumanPlayer
        player = HumanPlayer(avatar_session)
        self.session_players[sessionid] = player
        pc.addTrack(player.audio)
        pc.addTrack(player.video)

        # 设置编解码器偏好
        capabilities = RTCRtpSender.getCapabilities("video")
        preferences = list(filter(lambda x: x.name == "H264", capabilities.codecs))
        preferences += list(filter(lambda x: x.name == "VP8", capabilities.codecs))
        preferences += list(filter(lambda x: x.name == "rtx", capabilities.codecs))
        transceiver = pc.getTransceivers()[1]
        transceiver.setCodecPreferences(preferences)

        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return web.Response(
            content_type="application/json",
            text=json.dumps({
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
                "sessionid": sessionid,
            }),
        )

    async def handle_rtcpush(self, push_url, sessionid: str):
        """RTCPush 模式：主动推流"""
        import aiohttp
        await session_manager.create_session({}, sessionid)
        avatar_session = session_manager.get_session(sessionid)

        pc = RTCPeerConnection()
        self.pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info("Connection state is %s", pc.connectionState)
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)

        from server.webrtc import HumanPlayer
        player = HumanPlayer(avatar_session)
        pc.addTrack(player.audio)
        pc.addTrack(player.video)

        await pc.setLocalDescription(await pc.createOffer())

        async with aiohttp.ClientSession() as session:
            async with session.post(push_url, data=pc.localDescription.sdp) as response:
                answer_sdp = await response.text()

        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=answer_sdp, type='answer')
        )

    async def shutdown(self):
        """关闭所有 PeerConnection"""
        sessionids = list(self.session_pcs)
        await asyncio.gather(*(self.close_session(sid) for sid in sessionids))
        coros = [pc.close() for pc in self.pcs if pc.connectionState != "closed"]
        if coros:
            await asyncio.gather(*coros)
        self.pcs.clear()
        self.session_players.clear()
        self.closing_sessions.clear()
