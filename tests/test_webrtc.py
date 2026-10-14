"""Real aiortc negotiation and synthetic video over local UDP; no phone required."""
import asyncio
import pytest
from edgeai.camera import LatestFrame
from edgeai.webrtc import WebRTCReceiver


def test_webrtc_loopback():
    pytest.importorskip('aiortc')
    from aiortc import RTCPeerConnection, RTCConfiguration, RTCSessionDescription, VideoStreamTrack
    from av import VideoFrame
    import numpy as np

    class SyntheticVideo(VideoStreamTrack):
        async def recv(self):
            pts,base=await self.next_timestamp()
            frame=VideoFrame.from_ndarray(np.full((120,160,3),140,np.uint8),format='bgr24')
            frame.pts=pts;frame.time_base=base
            return frame

    async def check():
        frames=LatestFrame();receiver=WebRTCReceiver(frames)
        sender=RTCPeerConnection(RTCConfiguration(iceServers=[]))
        track=SyntheticVideo();sender.addTrack(track)
        try:
            await sender.setLocalDescription(await sender.createOffer())
            answer=await receiver.offer(sender.localDescription.sdp,sender.localDescription.type)
            await sender.setRemoteDescription(RTCSessionDescription(**answer))
            ok,frame,seq=await asyncio.to_thread(frames.read_new,0,12)
            assert ok and frame.shape==(120,160,3) and seq>=1
            assert abs(float(frame.mean())-140)<8
        finally:
            track.stop();await sender.close();await receiver.close()
    asyncio.run(check())
