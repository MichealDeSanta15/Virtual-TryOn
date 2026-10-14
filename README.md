# Edge AI Virtual Try-On

Live virtual try-on system using phone camera as webcam, local Stable Diffusion + ControlNet for garment overlay, and web scraping for clothing search.

## Project Structure
- `main.py` - Entry point: captures video stream, placeholder for processing.
- `scraper/` - Web scraping module (Playwright + SQLite cache).
- `tryon/` - AI try-on engine (Stable Diffusion + ControlNet).
- `ui/` - PyQt6 GUI components (future).
- `requirements.txt` - Python dependencies.
- `mighty-dreaming-teacup.md` - Detailed 2-day plan (2 developers).
- `TECH_STACK.md` - Technology stack summary.
- `3MEMBER_PLAN.md` - Three‑person role split plan.

## Getting Started
1. Clone repository.
2. Install dependencies: `pip install -r requirements.txt`
3. For AI models, download Stable Diffusion weights (e.g., SG161222/RealVisXL_V4.0) and ControlNet models locally or rely on HuggingFace hub (first run will download).
4. Ensure phone camera is streamable:
   - Install IP Webcam (Android) or DroidCam and connect to same Wi‑Fi.
   - Note the IP address and port (default video: `http://<IP>:8080/video`).
   - Update `PHONE_STREAM_URL` in `main.py` if needed.
5. Run: `python main.py`
   - Should display live phone video stream with placeholder text.
   - Press 'q' to quit.

## Next Steps (per 3MEMBER_PLAN.md)
- **Member 1 (Friend 1)**: Build PyQt6 GUI, inputs, thumbnail display, frame overlay.
- **Member 2 (Friend 2)**: Implement Playwright scraper, SQLite cache, search API.
- **Member 3 (You)**: Phone‑camera WebRTC receiver, pose estimation (MediaPipe/ControlNet), try‑on engine (SD+ControlNet), VRAM optimizations, integration.

## Notes
- This is a starting point; replace the placeholder processing with actual AI try‑on pipeline.
- For WebRTC streaming, consider using aiortc with a simple Android companion app.
- Respect robots.txt and rate limits when scraping.
- Everything runs locally; no API keys required after initial model download.

## License
MIT (or choose your own).