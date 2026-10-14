# Technology Stack for Edge AI Virtual Try-On (Live Video)

## Overview
This stack enables a local‑only, GPU‑accelerated virtual try‑on system that uses a phone camera as a live webcam, processes frames with Stable Diffusion + ControlNet, and sources clothing items via web scraping. Everything runs on the user’s hardware (RTX 5060, 8 GB VRAM) with no API costs after setup.

## 1. Application Framework
- **PyQt6 / PySide6**
  - Provides direct access to PyTorch/CUDA/TensorRT.
  - Lower overhead than Electron/Tauri for ML workloads.
  - Mature, cross‑platform, excellent for real‑time video processing.

## 2. Phone‑to‑Laptop Camera Streaming
- **WebRTC via aiortc (Python)**
  - Streams H.264/WebM from an Android companion app (simple WebRTC publisher).
  - Latency ~100‑200 ms, acceptable for live try‑on.
  - **Fallback**: HTTP/MJPEG using IP Webcam / DroidCam apps for quick setup.

## 3. Virtual Try‑On Core
- **Stable Diffusion Base Model**
  - SG161222/RealVisXL_V4.0 or similar photorealistic SDXL model.
- **ControlNet**
  - `lllyasviel/ControlNet-v1-1` (OpenPose for pose estimation).
  - `lllyasviel/ControlNet-v1-1` (Segmentation for clothing area).
  - Optional: Canny, Depth for additional conditioning.
- **VTON‑Specific Alternatives** (if available)
  - CatVTON (zhengchong/CatVTON on HuggingFace).
  - Or use inpainting with segmentation mask.
- **Optimizations for 8 GB VRAM**
  - `xformers` for memory‑efficient attention.
  - `torch.compile()` (PyTorch 2.0+).
  - CPU offloading for text encoder.
  - Gradient checkpointing, model quantization.
  - LCM LoRA or TDDIF for 2‑4 step inference (~2‑4 sec/step).
  - Batch size = 1, resolution 512×512 or 768×768.

## 4. Clothing Search & Data
- **Playwright‑based scraper** (stealth mode)
  - Targets: Myntra, Ajio, Amazon India (respect robots.txt, rate‑limit).
  - Extracts product images, metadata, price.
- **SQLite database**
  - Caches scraped products, search history.
  - Enables fast faceted search (price range, brand, category, occasion).
- **Pre‑downloaded datasets** (optional)
  - DeepFashion2, FashionGen for offline operation.
- **Public RSS/XML feeds** (no API key) where available.

## 5. Supporting Technologies
- **OpenCV** – video frame capture, conversion, basic preprocessing.
- **MediaPipe** – fallback pose estimation (if ControlNet unavailable).
- **PIL/Pillow, numpy** – image processing, resizing, blending.
- **Pydantic‑settings / TOML/YAML** – configuration management.
- **Logging** – structured logs for debugging and performance monitoring.

## 6. Build & Distribution
- **PyInstaller / cx_Freeze / Briefcase** – create platform‑specific installers.
  - Windows: MSI or EXE.
  - macOS: APP bundle.
  - Linux: AppImage or distro packages.
- **Dependencies**: Python 3.10+, NVIDIA drivers (CUDA 12.x compatible), ~5 GB storage for models and cache.

## 7. Optional Enhancements (Future Work)
- Body‑measurement estimation from photos.
- Virtual wardrobe management.
- Social sharing (privacy‑first, local‑only).
- AR mirror mode (real‑time try‑on experimentation).
- Integration with actual e‑commerce APIs when budget allows.

--- 
*This stack is derived from the “mighty‑dreaming‑teacup.md” plan and tuned for a realistic, local‑only implementation on modest GPU hardware.*