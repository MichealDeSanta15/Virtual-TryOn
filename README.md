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

## Getting Started (with Virtual Environment)

It is recommended to work inside a **virtual environment** so that dependencies stay isolated and the `venv` folder is not committed to Git (already covered by `.gitignore`).

### 1. Clone the repository
```bash
git clone https://github.com/MichealDeSanta15/Virtual-TryOn.git
cd Virtual-TryOn
```

### 2. Create and activate a virtual environment
```bash
# Using venv (built‑in)
python -m venv venv
# Activate
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```
You should see `(venv)` prefix in your prompt.

### 3. Install dependencies
First upgrade pip, then install the base requirements:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install PyTorch with CUDA 12.8 (compatible with RTX 5060)
The `requirements.txt` lists `torch>=2.1.0`; to install the exact CUDA‑enabled build, run:
```bash
pip install torch==2.7.1+cu128 torchvision==0.22.1+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
```
*(If you prefer a different CUDA version, adjust the suffix accordingly.)*

### 5. Verify installation
```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```
Should print `CUDA available: True` if the GPU is detected.

### 6. (Optional) Install xformers for memory‑efficient attention
```bash
pip install xformers  # matches your CUDA version; see https://github.com/facebookresearch/xformers#installation
```

### 7. Prepare phone camera stream
- Install **IP Webcam** (Android) or **DroidCam** on your phone.
- Connect phone and laptop to the same Wi‑Fi.
- Note the IP address and port (default video: `http://<IP>:8080/video`).
- Update `PHONE_STREAM_URL` in `main.py` if needed (the default tries that URL, then falls back to laptop webcam).

### 8. Run the starter
```bash
python main.py
```
You should see a window titled **“Edge AI Virtual Try-On”** showing your phone’s video feed with placeholder text. Press **`q`** to quit.

## Next Steps (per 3MEMBER_PLAN.md)
- **Member 1 (Friend 1)**: Build PyQt6 GUI, inputs, thumbnail display, frame overlay.
- **Member 1 (Friend 1)**: Build PyQt6 GUI, inputs, thumbnail display, frame overlay.
- **Member 2 (Friend 2 - Completed ✅)**: Implemented `clothing_pipeline`: Playwright stealth scraper (Myntra, Ajio, Amazon), SQLite cache, LRU eviction, fallback demo dataset, and `search_clothes(event, budget)` API.
- **Member 3 (AI/Integration)**: Phone‑camera WebRTC receiver, pose estimation (MediaPipe/ControlNet), try‑on engine (SD+ControlNet), VRAM optimizations, integration.

## Clothing Pipeline API (Friend 2)

```python
from clothing_pipeline.api import search_clothes

# Search by occasion and budget
results = search_clothes(event="wedding", budget="5000")

for item in results:
    print(item["brand"], "-", item["title"])
    print(f"Price: Rs. {item['price']} | Image: {item['image_path']}")
```


## Notes
- This is a starting point; replace the placeholder processing with actual AI try‑on pipeline.
- For WebRTC streaming, consider using `aiortc` with a simple Android companion app.
- Respect robots.txt and rate limits when scraping.
- Everything runs locally; no API keys required after initial model download.

## License
MIT (or choose your own).