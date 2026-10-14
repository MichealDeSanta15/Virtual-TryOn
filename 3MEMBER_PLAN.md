# 3‑Member Plan: Live Video Virtual Try‑On (Edge AI)

## Context
We are building a local‑only, GPU‑accelerated virtual try‑on system that:
- Uses a phone camera as a live webcam for the laptop (WebRTC via aiortc or HTTP/MJPEG fallback).
- Lets the user specify an event and budget (e.g., “freshers dress under 5000”).
- Scrapes the web for matching clothing items (with caching).
- Overlays those garments onto the live video in real‑time using Stable Diffusion + ControlNet (pose & segmentation).
- Everything runs on the user’s hardware (RTX 5060, 8 GB VRAM) with no ongoing API costs.

The work is split among three collaborators as described below.

## Role Division

### **Friend 1 – Frontend (PyQt6 GUI & Live Video Display)**
- **Goal**: Build the user interface that shows the live phone camera feed, handles user inputs, displays scraped clothing thumbnails, and renders the live try‑on overlay.
- **Responsibilities**:
  - Set up PyQt6/QML‑like main window with video display widget (updated via OpenCV‑to‑Qt image conversion).
  - Implement input fields for **Event** and **Budget**, a **Scrape** button, and a thumbnail panel for results.
  - Receive composited frames from the AI thread (via thread‑safe queue) and overlay them onto the live display.
  - Add UI polish: tooltips, animations, responsive layout, FPS counter, settings panel (GPU optimization, output quality).
  - Implement multi‑view try‑on (show 2‑3 results side‑by‑side) and drag‑to‑try‑on or click‑to‑apply gestures.
  - Handle error states (no camera, no results, processing failures) with user‑friendly dialogs.
  - Provide logging and basic diagnostics.
- **Key Deliverables**:
  - By **mid‑day 1**: Functional window showing live video stream (fallback to laptop webcam if needed) with input controls.
  - By **end of Day 1**: Integrated UI that can trigger scraping and display thumbnails.
  - By **end of Day 2**: Polished UI with live try‑on overlay, multi‑view comparison, settings, and logging.

### **Friend 2 – Web Scraping & Data Management**
- **Goal**: Given an event and budget, fetch clothing items from the web, cache them, and make them available for the try‑on engine.
- **Responsibilities**:
  - Develop a Playwright‑based scraper (stealth mode) targeting Myntra, Ajio, Amazon India (respect robots.txt, rate‑limit ≈1 req/s).
  - Extract product images, title, price, brand, category, and optionally size info.
  - Design and populate a SQLite database schema for products (images stored as blobs or file paths, metadata indexed).
  - Implement a search interface with filters: price range, brand, category, occasion (derived from event keyword), color (if available).
  - Add caching layer with LRU eviction and persistent storage to minimize repeated requests.
  - Provide a simple Python API: `search_clothes(event: str, budget: str) -> List[Dict]` returning local image paths and metadata.
  - Prepare fallback: bundle a small local dataset (e.g., DeepFashion2 subset) for demo if scraping fails.
  - Handle network errors, timeouts, and site‑specific changes gracefully.
- **Key Deliverables**:
  - By **mid‑day 1**: Working scraper that can retrieve a few product images for a test query.
  - By **end of Day 1**: SQLite cache populated, search API functional, basic error handling.
  - By **end of Day 2**: Robust scraping with rate‑limit handling, caching, and fallback dataset integration.

### **You – Phone Camera Integration, AI Try‑On Engine, Optimization & Integration**
- **Goal**: Get the phone camera feed onto the laptop, run pose estimation & garment warping using Stable Diffusion + ControlNet, and feed composited frames back to the frontend.
- **Responsibilities**:
  - **Phone‑to‑Laptop Streaming**:
    - Use **aiortc** (Python WebRTC) to receive H.264/WebM from a simple Android companion app (or modify an open‑source WebRTC publisher).
    - Provide an OpenCV `VideoCapture`‑like interface; fallback to IP Webcam / DroidCam (HTTP/MJPEG) for quick testing.
  - **Pose Estimation & Segmentation**:
    - Primary: ControlNet OpenPose model for pose landmarks.
    - Fallback: MediaPipe Pose (if ControlNet unavailable or too slow).
    - Segmentation model (ControlNet segmentation or SAM/DeepLab) to isolate clothing region for better inpainting.
  - **Try‑On Engine**:
    - Base model: SG161222/RealVisXL_V4.0 (or similar photorealistic SDXL).
    - Conditioning: ControlNet (OpenPose + Segmentation) + optional Canny/Depth for detail.
    - Optimizations for 8 GB VRAM:
      - `xformers` for memory‑efficient attention.
      - `torch.compile()` (PyTorch 2.0+).
      - CPU offloading for text encoder.
      - Gradient checkpointing, model quantization.
      - Use **LCM LoRA** or **TDDIF** for 2‑4 step inference (~2‑4 sec per try‑on).
      - Resolution 512×512 or 768×768.
    - Inpainting workflow: generate mask from segmentation, align garment to pose, run SD‑CN to inpaint clothing region.
    - Batch processing: ability to try multiple garments sequentially with warm‑up caching.
    - Post‑processing: color correction, blending, face enhancement (GFPGAN optional), realism tweaks.
  - **Integration & Performance**:
    - Thread‑safe queue to send raw frames to AI worker thread(s) and receive composited frames.
    - Simple API for frontend: `generate_tryon(frame, garment_paths) -> composited_frame`.
    - Performance monitoring: track end‑to‑end latency, VRAM usage, FPS.
    - Implement model warm‑up caching so that after first try‑on, subsequent ones are faster.
    - Provide debug view: show pose landmarks, segmentation mask, intermediate outputs.
    - Prepare optional AR mirror mode prototype (real‑time try‑on at reduced FPS).
- **Key Deliverables**:
  - By **mid‑day 1**: Working phone‑camera stream into OpenCV, basic pose estimation (MediaPipe) on a static image.
  - **End of Day 1**: Stable Diffusion + ControlNet installed and optimized; able to generate a try‑on from a static person image and a garment image (≥10 s per try‑on on RTX 5060).
  - **End of Day 2**: Integrated pipeline: live video → pose/segmentation → try‑on → composited frame → frontend UI, running at ≥5 FPS with latency <2 s per garment (aiming for real‑time). Polished UI shows live overlay, multi‑view, settings, and logging.

## Timeline (2‑Day Non‑Stop Development – Adjusted for 3 Members)

### Day 1: Foundations, Search Infrastructure & Initial AI Setup (≈16 hours non‑stop)
- **Hours 1‑4**:
  - Friend 1: PyQt6 project skeleton, main window with video placeholder.
  - Friend 2: SQLite schema, basic scraper prototype (Playwright) for one site.
  - You: Set up aiortc WebRTC receiver, test OpenCV frame capture; install MediaPipe and test pose on sample image.
- **Hours 5‑8**:
  - Friend 1: Add input fields, scrape button, thumbnail display; connect to Friend 2’s search API (stub).
  - Friend 2: Enhance scraper to extract images and metadata, implement caching; begin price/brand filtering.
  - You: Install Stable Diffusion + ControlNet suite; apply VRAM optimizations (xformers, torch.compile, CPU offload); test text‑to‑image generation.
- **Hours 9‑12**:
  - Friend 1: Implement threading for video capture and UI update; prepare to receive composited frames.
  - Friend 2: Finalize scraper with robust error handling, rate limiting, multi‑site support; integrate with SQLite cache.
  - You: Build pose estimation pipeline (MediaPipe fallback → ControlNet OpenPose); create segmentation mask workflow; develop initial try‑on engine (inpainting with mask).
- **Hours 13‑16+**:
  - Friend 1: Polish UI: styling, tooltips, settings panel, FPS counter.
  - Friend 2: Add advanced search filters (occasion, color), local fallback dataset, export/import of cache.
  - You: Refine try‑on engine: garment alignment/resizing based on pose, lighting adjustment, batch processing, model warm‑up caching; begin integration with UI thread.

### Day 2: Integration, Polish, Deployment & Advanced Features (≈16 hours non‑stop)
- **Hours 1‑4**:
  - All: Integrate modules into a single `main.py`.
  - Friend 1: Wire up scrape button → call Friend 2’s search → display thumbnails; receive composited frames from you and overlay on live video.
  - Friend 2: Ensure scraper returns local image paths ready for you.
  - You: Finalize AI try‑on thread, handshake with frontend via queue; add error handling (no stream, no results).
  - Joint: End‑to‑end test: phone camera → capture → search → try‑on → display.
- **Hours 5‑8**:
  - Friend 1: Multi‑view try‑on (2‑3 results side‑by‑side), drag‑to‑try‑on or click‑to‑apply, responsive design.
  - Friend 2: Optimize scraper speed, add query‑result caching, implement search history.
  - You: Performance tuning: measure latency, VRAM usage, FPS; apply further optimizations (TensorRT, lower resolution if needed); add logging & diagnostics.
- **Hours 9‑12**:
  - Friend 1: User guidance system (tooltips, walkthrough, contextual help); logging integration.
  - Friend 2: Schedule background refresh of cache, implement data export for backup.
  - You: Experiment with AR mirror mode (real‑time try‑on at reduced FPS); consider additional ControlNet models (depth, canny) for improved realism.
- **Hours 13‑16+**:
  - All: Final bug fixing, performance benchmarking, prepare demo script and presentation slides.
  - Create platform‑specific installers (PyInstaller/cx_Freeze).
  - Write brief user manual and deployment notes.
  - Conduct dry‑run of the live demo with test data.

## Integration Points
- **Data Contract**: Friend 2’s `search_clothes(event, budget)` → returns list of dicts: `{“image_path”: str, “title”: str, “price”: float, …}`.
- **AI Interface**: You provide a function `try_on_garment(frame: np.ndarray, garment_path: str) → np.ndarray` (same dimensions as input frame) that runs pose/seg, runs SD‑CN, outputs composited frame.
- **Threading**: Use `queue.Queue(maxsize=5)` between video capture thread → AI worker thread → GUI update thread.
- **Error Handling**: Each layer returns `None` or raises specific exceptions; UI shows placeholders or messages.

## Risks & Mitigations
- **Phone Stream Failure** → fallback to laptop webcam or pre‑recorded video.
- **Scraping Blocked/No Results** → use bundled local dataset, show message to refine query.
- **Pose Estimation Failure** → prompt user to adjust position; allow manual drag‑to‑position of garment as fallback.
- **VRAM Overrun** → lower resolution, enable xformers/torch.compile, use LCM LoRA, consider TensorRT.
- **UX Lag** → asynchronous processing, loading spinners, progressive refinement (show low‑res try‑on first).
- **Legal/Ethical Scraping** → respect robots.txt, rate‑limit, cache aggressively, focus on public data or RSS feeds.

## Conclusion
This three‑person plan splits the work clearly: Friend 1 handles the frontend and user experience, Friend 2 manages the web scraping and data layer, and you take care of the phone‑camera input, AI try‑on engine, optimizations, and system integration. Following the outlined two‑day non‑stop schedule (with flexibility for breaks) should yield a functional live‑video virtual try‑on demo that runs entirely on local hardware, meets the privacy and latency goals, and can be showcased with a polished UI.

--- 
*Refer to `TECH_STACK.md` for a concise summary of the libraries, models, and tools used.*