# Phone → laptop camera

<<<<<<< HEAD
**Portrait update:** See [CAMERA_ORIENTATION.md](CAMERA_ORIENTATION.md) for the new
Frame orientation controls. Preview and saved capture now share an optional pixel
rotation; this does not infer physical phone tilt from an MJPEG feed.

=======
>>>>>>> origin/main
## Path A: IP Webcam / DroidCam / laptop webcam (start here)

1. Phone and laptop use the same **trusted** private Wi-Fi.
2. Start the phone camera app's local video server. Follow that app's privacy and
   permission settings. Do not enable a cloud relay for this project.
3. In the studio, open **Camera** and enter its actual video stream endpoint.
   Example only: `http://192.168.1.8:8080/video` for common IP Webcam configurations.
   Use the URL shown by your app—not the HTML control-page URL.
4. Click Connect, wait for the live view, then **Capture frame**.
5. The captured photo becomes the person image. Review its mask and generate.

A virtual webcam installed by DroidCam can be opened using its OpenCV device index.
`0` typically means the first laptop webcam, not necessarily the phone.
The OpenCV source runs on the **laptop server**, not inside your browser.

A plain HTTP MJPEG stream is not encrypted. Use only your trusted LAN and app-supported
credentials/security; never forward its port to the public internet. The OpenCV path
reconnects with bounded backoff and flags stale frames after 3 seconds. Native camera
drivers can still block or be device-specific; see diagnostics rather than hiding errors.

## Path B: Browser publisher + WebRTC

The phone browser needs a **secure context**. `http://192.168.x.x:8000` is not enough.
An untrusted/self-signed warning bypass is not a reliable secure-context setup.

One local approach is [mkcert](https://github.com/FiloSottile/mkcert):

1. Install mkcert from its official distribution instructions.
2. Find the laptop's private IPv4 address with `ipconfig`.
3. Generate a local certificate, replacing the example address with yours:

```powershell
mkcert -install
mkcert -cert-file local-cert.pem -key-file local-key.pem localhost 127.0.0.1 192.168.1.20
```

4. Install **only the public root CA certificate** on your phone using its supported
   trust/certificate settings. Android and iOS procedures differ; iOS may require
   explicitly enabling full trust. Do not copy or disclose the CA private key.
   Remove this development CA from the phone after the project if no longer needed.
5. Start the server:

```powershell
.\.venv\Scripts\python.exe main.py --host 0.0.0.0 --port 8000 --cert local-cert.pem --key local-key.pem
```

6. Allow this Python executable through Windows Firewall for **Private networks only**.
   WebRTC uses UDP media ports as well as TCP 8000 for signaling. A rule allowing only
   TCP 8000 may load the page but fail to carry video.
7. Open `https://192.168.1.20:8000/phone` on the phone, enter the terminal pairing token,
   choose front/rear camera and Connect. Grant video permission; microphone is not requested.
8. On the laptop studio, pair the browser separately and open Camera. The current
   phone frame appears; click Capture frame when the subject is steady.
9. Disconnect explicitly before changing phone/camera. Stop also releases the camera.

The phone remains the camera source; the AI runs on the laptop. Keep the phone page in
the foreground because mobile OSes throttle/suspend background tabs.

## Network properties and limits

- No STUN/TURN servers configured; no media relay or port-forwarding built in.
- Works only when local ICE candidates can communicate. Guest-network isolation,
  VPNs, browser mDNS behavior and local firewalls can prevent pairing.
- A failed connection times out and can be retried. Use MJPEG rather than spending your
  entire demo setup debugging school Wi-Fi.
- One active WebRTC phone publisher. One global camera source per service.
- Codec is negotiated by browser/aiortc (usually VP8 or H.264); WebRTC is not WebM-file transfer.
- aiortc receives decoded video, converts to BGR and replaces the latest-frame slot.
- Browser studio monitor polls small JPEG previews; this is for inspection, not a
  guaranteed 30 FPS renderer. Qt can use a native capture path for higher preview throughput.
- Camera capture rate, WebRTC latency, UI preview rate and diffusion latency are
  separate measurements. Do not substitute one for another in your report.

## Test status

Automated local aiortc sender→receiver negotiation and synthetic frame delivery passed.
Physical Android/iOS pairing, Windows firewall behavior, phone orientation and exact
codec support still require testing on your phone/laptop/network.

The Arena-hosted UI preview cannot reach your phone's private LAN as if it were your
laptop. Run this project locally for actual phone integration and private photographs.
