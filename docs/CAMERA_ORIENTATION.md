# Portrait phone camera — preview and captured pixels

## Install the update

Stop the server. Back up local code edits, then extract **edgeai-portrait-camera-fix.zip**
into your existing live-catalog project folder containing `main.py`, replacing source
files. The patch also includes the previous garment/dress update. Preserve `.venv`,
models and data. No new dependencies or model downloads are required on your laptop.

```powershell
$env:EDGEAI_MEMORY="staged"
.\.venv\Scripts\python.exe main.py
```

Reload the studio with **Ctrl+F5** and pair if prompted. For the entire current source,
use **edgeai-portrait-camera-project.zip**. The earlier source/publishing-kit archives
remain older versions and do not contain this camera update.

## Use with IP Webcam

1. Open **Camera**, enter the actual video endpoint, e.g. your phone's working
   `http://10.195.159.212:8080/video` (use the scheme/port enabled by your app).
2. Under **Frame orientation**, choose **Portrait · rotate landscape clockwise**
   if the image is arriving sideways in a landscape-shaped stream.
3. If that makes the person upside down, choose **Portrait · rotate landscape
   anticlockwise** instead.
4. Connect if necessary. Orientation can also be changed while the stream is running.
5. Once upright, **Capture frame**. The saved person image and mask/AI input have the
   same orientation as the preview, not merely a rotated CSS display.

The Portrait modes rotate only when incoming width is greater than height. If the
phone app already sends upright portrait frames, leave **As sent by camera** selected;
Portrait modes also leave those dimensions unchanged. A square frame is unchanged.
For a portrait frame that is upside down, use the explicit **Rotate 180°** option.
Explicit 90° options rotate regardless of input shape.

**Important distinction:** a landscape-shaped picture that is ALREADY upright must
not simply be rotated to make it portrait—that would turn the person sideways. In
that case, configure portrait video output in the phone app. This update intentionally
does not crop/stretch an upright wide image into a tall frame and lose body details.

## Does it follow how I hold the phone automatically?

A plain IP Webcam MJPEG stream commonly provides JPEG frames but no phone-screen
orientation sensor data. Width/height alone cannot tell which way the phone is held
or whether a person is upright. The portrait option is a conditional rotation, NOT
physical orientation detection.

For automatic switching when you rotate your phone, use the IP Webcam app's
video-orientation/rotation setting (wording varies by version) so its streamed video
follows the phone orientation. A webpage may rotate its own display without changing
the stream pixels; check the actual `/video` output. Reconnect after changing app
settings if necessary. With correctly oriented stream pixels, choose **As sent by
camera**, and the dashboard preserves each frame's incoming portrait/landscape shape.

If your app cannot do that, choose the appropriate dashboard rotation once for your
portrait recording setup. It is remembered in that browser tab's session storage,
including reloads. It is not automatically synchronized to a phone tilt sensor.

## Implementation

- `LatestFrame` retains the raw decoded BGR frame and transforms a copy on read.
  Repeated orientation changes therefore do not accumulate rotations.
- Preview, PNG capture and native `read_new` consumers use the same transform.
- Supported modes: `source`, `portrait_cw`, `portrait_ccw`, `cw90`, `ccw90`, `180`.
- Preview JPEGs are bounded to 800 pixels on their longest side. Saved captures keep
  the oriented resolution, up to the existing 2048px maximum side. No portrait crop.
- The monitor sizes itself to the actual image instead of a fixed short landscape box.
- In-flight old-orientation preview responses are discarded. Capture is blocked while
  an orientation update is pending or has failed. An orientation change during capture
  requires recapture rather than displaying the old-oriented snapshot.
- Changing orientation doesn't make an old frame fresh or increment the received-frame
  count. Stale-frame refusal remains in force.
- One global camera/rotation setting per running server. Multiple paired browsers share
  that camera; don't have two operators change orientation simultaneously.
- Camera controls are separate from the AI and garment extraction; no GPU work added.

## API

Authenticated `POST /api/camera/orientation`:

```json
{"orientation":"portrait_cw"}
```

Response/status includes raw `input_size`, oriented `output_size` (both `[width,height]`),
clockwise `rotation_degrees`, orientation and revision. `/api/camera/open` also accepts
optional `orientation`; omission preserves the existing setting. Original clients
remain compatible, with server default `source`.

`/api/camera/capture` returns the existing asset `id` plus saved `width` and `height`.
Already-captured photos/masks/results are not retroactively rotated; take a new capture
after correcting orientation. Rotation applies to OpenCV and WebRTC frames stored by
the shared service, but the phone publisher itself is unchanged in this update.

## Verification and limits

- **16 new orientation tests passed:** exact directional pixel rotation, raw-frame
  preservation, no double rotation of portrait/square frames, no artificial freshness,
  API auth/validation, camera-open orientation, preview/snapshot consistency and
  portrait-preview resolution bounds.
- Browser test used a clearly synthetic sideways 768×512 frame. The actual API returned
  a 512×768 portrait preview and saved person asset; the mask editor used 512×768.
  Reload preference, source-mode reset, mobile width and no JS errors were checked.
- Current sandbox suite: **137 passed, 2 skipped, 1 dependency warning**. Torch is not
  installed in this refreshed sandbox, so the earlier offload runtime module and one
  staged-placement test were skipped. These are not newly validated GPU tests.
- Python compilation and JavaScript syntax checks passed.
- Physical phone orientation, Windows/OpenCV video input and GPU inference were not
  tested here. Run locally: the hosted preview cannot reach your phone's private LAN.

Evidence: `camera-orientation-verification.json`. Synthetic test frames/server are not
installed or bundled as a production camera source.
