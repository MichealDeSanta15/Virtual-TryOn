# Edge AI Virtual Try-On Project Plan

## Context
User wants to create an AI tool that:
1. Uses phone camera as laptop camera (via phone-to-laptop streaming)
2. Takes photo of person
3. User specifies dress requirements (e.g., "freshers dress under 5000 INR")
4. AI searches for matching clothing items
5. Shows virtual try-on of how person would look in those clothes
6. Must use local hardware (RTX 5060 GPU, 8GB VRAM)
7. Cross-platform with full GPU access
8. Free/local only (no API costs)

## Tech Stack Recommendations

### 1. Application Framework: **PyQt6/PySide6**
- **Why**: Best Python integration for GPU/ML workloads, cross-platform, mature
- Direct access to PyTorch/CUDA/TensorRT
- Lower overhead than Electron/Tauri for ML apps
- Good performance for real-time video processing

### 2. Phone-to-Laptop Camera Streaming: **WebRTC via aiortc**
- **Solution**: Use aiortc (Python WebRTC library) + simple Android companion app
- **Alternative**: Modify open-source projects like:
  - [android-webcam-publisher](https://github.com/genebyte/android-webcam-publisher) 
  - [webrtc-android](https://github.com/webrtc/googlewebrtc/tree/master/examples/androidapp)
- Phone streams H.264/WebM via WebRTC to laptop
- Latency: ~100-200ms acceptable for this use case

### 3. Virtual Try-On: **Local Stable Diffusion + ControlNet**
- **Base Model**: SG161222/RealVisXL_V4.0 or similar photorealistic model
- **ControlNet**: 
  - lllyasviel/ControlNet-v1-1 (OpenPose for pose estimation)
  - lllyasviel/ControlNet-v1-1 (Segmentation for clothing area)
- **VTON-Specific**: Look for fine-tuned models like:
  - [CatVTON](https://huggingface.co/zhengchong/CatVTON) (if available)
  - Or use inpainting approach with segmentation mask
- **Optimization for 8GB VRAM**:
  - xformers for memory-efficient attention
  - torch.compile() for PyTorch 2.0+
  - CPU offloading for text encoder
  - Batch size = 1
  - Use TDDIF or LCM LoRA for faster inference (~2-4 sec/step)

### 4. Clothing Search: **Free/Local Approaches**
Since we need free/local only:
- **Option A**: Pre-downloaded fashion datasets
  - DeepFashion2 (local database)
  - FashionGen
  - Or scrape and cache during setup
- **Option B**: Public RSS/XML feeds (no API key needed)
  - Some Indian retailers have public feeds
  - Affiliate networks with free tiers
- **Option C**: Playwright-based scraping with rate limiting
  - Target: Myntra, Ajio, Amazon India (respect robots.txt)
  - Cache results locally
  - Search by keywords + price filters

### 5. Supporting Technologies
- **Computer Vision**: OpenCV, MediaPipe (for pose estimation fallback)
- **Image Processing**: PIL/Pillow, numpy
- **Web Scraping**: Playwright (stealth mode) or requests+BeautifulSoup
- **Database**: SQLite for cached products/search history
- **Configuration**: Pydantic-settings or TOML/YAML

## Architecture Overview

```
┌─────────────────┐    WebRTC Stream    ┌──────────────────┐
│  Android Phone  │◀───────────────────▶│   Laptop App     │
│  (Camera App)   │                     │  (PyQt6)         │
└─────────────────┘                     │                  │
                                        │  ┌─────────────┐  │
                                        │  │ Video Feed  │  │
                                        │  │ (OpenCV)    │  │
                                        │  └─────────────┘  │
                                        │          │        │
                                        │  ┌─────────────┐  │
                                        │  │  Capture    │  │
                                        │  │  Button     │  │
                                        │  └─────────────┘  │
                                        │          ▼        │
                                        │  ┌─────────────┐  │
                                        │  │ Person Photo  │  │
                                        │  └─────────────┘  │
                                        │          │        │
                   ┌────────────────────┼──────────┼────────┐
                   │                      │          │        │
                   ▼                      ▼          ▼        │
           ┌─────────────┐        ┌─────────────┐ ┌─────────┐│
           │Text Input   │        │Search       │ │Try-On   ││
           │("freshers   │        │Worker       │ │Worker   ││
           │ dress under  │        │(Playwright) │ │(SD+CN)  ││
           │ 5000")       │        │             │ │         ││
           └─────────────┘        └─────────────┘ └─────────┘│
                   │                      │          │        │
                   │   ┌─────────────┐    │    ┌─────────────┐│
                   └──►│ Products    │    │    │ Try-on      ││
                       │ Database    │    │    │ Results     ││
                       └─────────────┘    │    └─────────────┘│
                                          │                   │
                                          └───────────────────┘
```

## Implementation Phases (2-Day Non-Stop Schedule - All 5-Week Features Included)

### Day 1: Foundation, Search Infrastructure & Initial AI Setup (16+ hours non-stop)
**Hours 1-4:**
- Set up PyQt6 project structure with comprehensive logging, configuration, and error handling
- Implement dual camera interface: OpenCV for testing + aiortc WebRTC receiver for actual phone camera
- Create main window with video display, capture button, and frame buffering
- Save captured frames with metadata and multiple format support

**Hours 5-8:**
- Design and implement robust SQLite database schema for fashion products (images, metadata, pricing, categories)
- Build Playwright-based scraper with stealth mode for Myntra, Ajio, and Amazon India
- Create search interface with advanced filtering (price range, category, brand, color, occasion)
- Implement caching layer with LRU eviction and persistent storage
- Set up background scraping with progress tracking and error recovery

**Hours 9-12:**
- Install and configure Stable Diffusion + ControlNet suite (Base Model: SDXL, ControlNet: OpenPose, Segmentation, Canny, Depth)
- Implement pose estimation pipeline using MediaPipe as fallback and ControlNet OpenPose as primary
- Create segmentation-based clothing masking system using SAM (Segment Anything Model) and DeepLab
- Develop VRAM optimization techniques: xformers, torch.compile, CPU offloading, gradient checkpointing, model quantization

**Hours 13-16+:**
- Build try-on engine with inpainting workflow: precise garment alignment, lighting adjustment, texture preservation
- Implement batch processing for multiple garment try-ons (parallel inference where possible)
- Create result enrichment system with pose correction, cloth simulation, and realism enhancement
- Set up model warm-up caching and inference optimization for sub-5 second try-on generation

### Day 2: Integration, Polish, Deployment & Advanced Features (16+ hours non-stop)
**Hours 1-4:**
- Integrate all modules into seamless pipeline: phone camera → capture → search → try-on → display
- Implement multi-view try-on system showing 3+ garments simultaneously with comparison tools
- Add advanced UI features: drag-to-try-on, garment customization (color/size), side-by-side comparisons
- Create threading architecture with priority queues for camera, search, and try-on processes
- Implement comprehensive error handling, fallback systems, and graceful degradation

**Hours 5-8:**
- Polish UI/UX with professional styling, animations, and responsive design
- Add user guidance system with tooltips, walkthrough tutorials, and contextual help
- Implement settings panel for GPU optimization, camera preferences, and output quality
- Create logging and diagnostics system for performance monitoring and troubleshooting

**Hours 9-12:**
- Build cross-platform installer system (Windows MSI, macOS APP, Linux AppImage) with dependency bundling
- Implement automated testing suite: unit tests, integration tests, and end-to-end scenario tests
- Create performance benchmarking system with VRAM usage tracking, latency measurement, and FPS monitoring
- Add system requirements checker and hardware compatibility validation

**Hours 13-16+:**
- Implement advanced features: body measurement estimation from photos, virtual wardrobe management
- Add social sharing system with privacy-first controls (local-only sharing options)
- Create AR mirror mode prototype for real-time try-on experimentation
- Set up API integration framework for future e-commerce partner connections (structure ready for when budget allows)
- Finalize documentation, user manuals, and deployment guides
- Conduct comprehensive testing across different hardware configurations and use cases

## Critical Files to Create/Modify

1. `main.py` - Application entry point, PyQt6 setup
2. `camera_receiver.py` - WebRTC receiver using aiortc
3. `clothing_scraper.py` - Playwright-based scraper with SQLite cache
4. `tryon_engine.py` - Stable Diffusion + ControlNet wrapper
5. `ui_mainwindow.py` - Main PyQt6 interface
6. `models/product.py` - SQLAlchemy/SQLite models
7. `utils/optimization.py` - VRAM optimization helpers

## Key Technical Challenges & Solutions

### Challenge 1: WebRTC Latency & Complexity
**Solution**: Start with simpler HTTP/MJPEG fallback (IP Webcam app) then upgrade to WebRTC for better latency

### Challenge 2: 8GB VRAM Limitations for SD+ControlNet
**Solution**: 
- Use 512x512 or 768x768 resolution (not 1024)
- Enable xformers and torch.compile
- Offload text encoder to CPU
- Use LCM LoRA for 2-4 step inference
- Consider TensorRT optimization

### Challenge 3: Realistic Virtual Try-On Quality
**Solution**:
- Use segmentation (not just pose) for better clothing masking
- Try multiple ControlNet models (pose + canny + depth)
- Post-processing with GFPGAN for face enhancement
- Batch similar garments for efficiency

### Challenge 4: Legal/Ethical Scraping
**Solution**:
- Respect robots.txt and rate limits
- Cache aggressively to minimize requests
- Focus on sites with public APIs or RSS feeds
- Consider building local dataset from public sources

## Verification & Testing

### Unit Tests:
- Test each module independently
- Mock external dependencies (WebRTC, web requests, ML models)

### Integration Tests:
- End-to-end flow: capture → search → try-on → display
- Test with sample images and known products

### Performance Benchmarks:
- End-to-end latency target: <10 seconds
- VRAM usage: <6GB to leave headroom
- FPS for video feed: ≥15 FPS

### User Testing:
- Test with different body types, lighting conditions
- Various clothing styles (ethnic, western, formal)
- Different price ranges

## Deployment

### Distribution:
- Create platform-specific installers:
  - Windows: MSI or EXE (via cx_Freeze or PyInstaller)
  - macOS: APP bundle
  - Linux: AppImage or distro packages

### Requirements:
- Python 3.10+
- NVIDIA GPU with drivers (CUDA 12.x compatible)
- ~5GB storage for models and cache
- Android 8.0+ for companion app

## Future Enhancements
1. Add body measurements for better fit prediction
2. Virtual wardrobe management
3. Social sharing features
4. AR mirror mode (real-time try-on)
5. Integration with actual e-commerce APIs (when budget allows)

## Risks & Mitigations

### Risk 1: Model Quality on Limited Hardware
**Mitigation**: Start with lower resolution, use LoRAs, prioritize speed over perfection initially

### Risk 2: Scraping Legal Issues
**Mitigation**: Use only public data, respect TOS, build opt-in dataset approach

### Risk 3: User Experience Lag
**Mitigation**: Async processing, loading indicators, progressive refinement

### Risk 4: Android Companion App Complexity
**Mitigation**: Start with existing IP Webcam/DroidCam apps, build custom only if needed

## Estimated Timeline: 2 Days Non-Stop Development
- **Day 1 (16+ hours):** Foundation, Search Infrastructure & Initial AI Setup
- **Day 2 (16+ hours):** Integration, Polish, Deployment & Advanced Features
- **Total:** Approximately 32+ hours of continuous development work
- **Note:** This aggressive schedule assumes sustained focus, minimal breaks, and leverages the developer's expertise to compress what would normally take 5-6 weeks into 2 days through non-stop work.

## Work Division for 2 Developers (Parallel Execution)
To maximize efficiency in the 2-day timeline, we recommend splitting work by functional domains with clear integration points:

### **Developer A: Frontend, Camera & Search Systems**
**Primary Responsibilities:**
- PyQt6 application architecture and main window implementation
- Camera interface (OpenCV fallback → WebRTC/aiortc for phone camera)
- Photo capture, storage, and basic image processing
- Search interface design and implementation (keyword input, price filtering)
- Results display system (grid/list view with thumbnails)
- SQLite database schema design and implementation for product catalog
- Playwright-based web scraper setup for fashion sites (Myntra, Ajio, Amazon)
- Basic UI/UX styling and layout
- Initial integration testing of camera → capture → search pipeline

**Key Deliverables by End of Day 1:**
- Functional camera interface showing phone/laptop video feed
- Working search interface with text input and price filter
- Basic SQLite database with sample fashion dataset
- Playwright scraper capable of fetching product data from 1-2 sites
- Integrated UI allowing: camera view → capture photo → search query → view results

### **Developer B: AI, Try-on Engine & Optimization**
**Primary Responsibilities:**
- Stable Diffusion + ControlNet installation and environment setup
- VRAM optimization techniques (xformers, torch.compile, CPU offloading, LCM LoRA)
- Try-on engine core: segmentation-based clothing masking and inpainting workflow
- Pose estimation integration (MediaPipe fallback → ControlNet OpenPose primary)
- Garment alignment, scaling, and texture preservation systems
- Batch processing capabilities for multiple try-ons
- Performance monitoring and latency optimization
- Model warm-up/caching systems
- Advanced image post-processing (blending, face enhancement, color correction)

**Key Deliverables by End of Day 1:**
- Stable Diffusion + ControlNet successfully installed and optimized for 8GB VRAM
- Working try-on pipeline: person photo + garment image → try-on result
- Segmentation-based clothing masking functional
- Basic inpainting generating recognizable try-on outputs
- Performance benchmarks showing <10 second try-on generation on RTX 5060
- System ready to accept inputs from Developer A's search results

### **Integration Points (End of Day 1 / Start of Day 2):**
1. **Data Interface:** Developer B provides a simple Python API/function: `generate_tryon(person_image_path, garment_image_path) -> result_image_path`
2. **File Format:** Standardized image formats and locations for handoff
3. **Integration Testing:** Both developers work together to connect:
   - Developer A's search results → provide garment images to Developer B's try-on engine
   - Developer B's try-on outputs → return to Developer A's UI for display

### **Day 2: Parallel Workstreams with Continuous Integration**
**Developer A Focus (Day 2):**
- Advanced UI/UX: polishing, styling, animations, responsive design
- Multi-view try-on comparison system (showing 2-3 results simultaneously)
- Drag-and-drop or click-to-try-on interface enhancements
- Settings panel for GPU optimization and output quality
- User guidance system (tooltips, walkthroughs, contextual help)
- Logging and diagnostics implementation
- Begin work on virtual wardrobe management concepts

**Developer B Focus (Day 2):**
- Advanced try-on features: garment alignment improvements, lighting matching
- Batch processing optimization for trying multiple garments quickly
- Experimentation with additional ControlNet models (depth, canny) for better results
- Post-processing enhancements (face restoration, cloth simulation)
- Begin work on body measurement estimation from photos
- Performance tuning and memory optimization refinement
- AR mirror mode prototype exploration (real-time try-on concept)

**Continuous Integration (Throughout Day 2):**
- Regular check-ins to integrate progress (every 2-3 hours)
- Joint testing of full pipeline: phone camera → capture → search → try-on → display
- Rapid bug fixing and issue resolution
- Performance benchmarking and optimization together
- Preparation of final demo and presentation materials

### **Shared Responsibilities (Both Developers):**
- Daily stand-up meetings (15 min start/end of day)
- Joint problem-solving for integration challenges
- Mutual code review for critical components
- Shared testing and validation of end-to-end workflow
- Combined work on final demo preparation and presentation
- Documentation and knowledge transfer between domains

This division minimizes blocking dependencies while ensuring both developers have meaningful, parallelizable work streams that converge into a cohesive product by the end of Day 2.