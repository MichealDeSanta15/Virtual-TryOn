import asyncio
from .camera import LatestFrame


class WebRTCReceiver:
    def __init__(self, frames: LatestFrame):
        self.frames = frames
        self.peers = set()
        self.tasks = set()

    async def offer(self, sdp, kind):
        from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration
        from aiortc.mediastreams import MediaStreamError
        if kind != "offer" or len(sdp) > 100_000:
            raise ValueError("Invalid WebRTC offer")
        if len(self.peers) >= 1:
            raise ValueError("A phone is already paired. Disconnect it before pairing another.")
        # Local LAN only. No public STUN or TURN: no third-party camera relay.
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        self.peers.add(pc)

        @pc.on("track")
        def on_track(track):
            if track.kind != "video":
                return
            async def consume():
                try:
                    while True:
                        frame = await track.recv()
                        self.frames.put(frame.to_ndarray(format="bgr24"), "webrtc")
                except MediaStreamError:
                    self.frames.error = "Phone stream ended"
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.frames.error = f"Phone stream failed: {exc}"
            task = asyncio.create_task(consume())
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)

        @pc.on("connectionstatechange")
        async def changed():
            if pc.connectionState in ("failed", "closed"):
                await pc.close()
                self.peers.discard(pc)

        async def handshake_watchdog():
            await asyncio.sleep(25)
            if pc.connectionState != "connected":
                await pc.close()
                self.peers.discard(pc)
        watchdog = asyncio.create_task(handshake_watchdog())
        self.tasks.add(watchdog)
        watchdog.add_done_callback(self.tasks.discard)
        try:
            await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=kind))
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        except BaseException:
            await pc.close()
            self.peers.discard(pc)
            raise

    async def close(self):
        peers = list(self.peers)
        self.peers.clear()
        await asyncio.gather(*(pc.close() for pc in peers), return_exceptions=True)
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.tasks.clear()
        self.frames.clear()
