# Edge AI Virtual Try-On - Technology Stack

## Overview
This document outlines the technology stack chosen for the Edge AI Virtual Try-On application, focusing on local hardware utilization, cross-platform compatibility, and free/open-source solutions.

## Core Application Framework

### PyQt6/PySide6
- **Purpose**: Main GUI framework for desktop application
- **Why Chosen**:
  - Excellent Python integration with PyTorch/CUDA/TensorRT
  - Cross-platform (Windows, macOS, Linux)
  - Mature and well-documented
  - Lower overhead compared to Electron/Tauri for ML-intensive applications
  - Direct access to GPU computing capabilities
- **Version**: PyQt6 >= 6.5.0
- **Key Modules**: QtWidgets, QtCore, QtGui, QtMultimedia

## Phone-to-Laptop Camera Streaming

### aiortc (Python WebRTC Library)
- **Purpose**: Receive video stream from Android phone via WebRTC
- **Why Chosen**:
  - Pure Python implementation
  - Good WebRTC support
  - Can be extended for custom signaling
  - Active maintenance
- **Version**: aiortc >= 1.5.0
- **Alternative Fallback**: 
  - HTTP/MJPEG stream using existing apps (IP Webcam, DroidCam)
  - Simpler to implement, higher latency but functional for MVP

### Android Companion Approach
- **Primary**: Modified open-source WebRTC publisher
  - [android-webcam-publisher](https://github.com/genebyte/android-webcam-publisher)
  - Custom signaling server (simple WebSocket-based)
- **Fallback**: Use IP Webcam/DroidCam apps with HTTP/MJPEG endpoint

## Virtual Try-On Engine

### Stable Diffusion + ControlNet
- **Purpose**: Generate realistic virtual try-on images
- **Base Model**: 
  - SG161222/RealVisXL_V4.0 (or similar photorealistic model)
  - Alternative: stabilityai/stable-diffusion-xl-base-1.0
- **ControlNet Models**:
  - lllyasviel/ControlNet-v1-1 (OpenPose for pose estimation)
  - lllyasviel/ControlNet-v1-1 (Segmentation for clothing area)
  - Alternative: tencentarc/controlnet-canny-sdxl-1.0 (for edge guidance)
- **VTON-Specific Options**:
  - CatVTON (if available and licensed appropriately)
  - Or use segmentation-based inpainting approach
- **Version**: 
  - diffusers >= 0.21.0
  - transformers >= 4.30.0
  - accelerate >= 0.20.0

### Optimization Techniques for 8GB VRAM
- **Memory Efficiency**:
  - xformers for memory-efficient attention
  - torch.compile() (PyTorch 2.0+) for faster training/inference
  - CPU offloading for text encoder and VAE
  - Batch size = 1 (optimized for single image processing)
  - Use 512x512 or 768x768 resolution (not 1024)
- **Speed Optimization**:
  - LCM LoRA for 2-4 step inference (vs 20-30 steps)
  - TDDIF or other consistency models
  - TensorRT optimization (if deployment target allows)

## Clothing Search System

### Free/Local Approaches
Since API costs must be zero:

#### Option A: Pre-downloaded Datasets
- **DeepFashion2**: Comprehensive fashion attribute dataset
- **FashionGen**: High-quality fashion images with attributes
- **Local SQLite Database**: For fast searching and filtering

#### Option B: Public Data Sources
- **RSS/XML Feeds**: From retailers that provide public feeds
- **Affiliate Networks**: Some offer free tiers for product data
- **Open Data Portals**: Government or industry datasets

#### Option C: Ethical Scraping (with Caching)
- **Playwright**: For stealth-mode browser automation
- **BeautifulSoup4**: For HTML parsing when appropriate
- **Requests**: For HTTP handling
- **Rate Limiting**: Respectful scraping practices
- **Aggressive Caching**: Minimize repeat requests
- **robots.txt Compliance**: Always check and respect

### Target Sites (for scraping option)
- Myntra (respect robots.txt and rate limits)
- Ajio 
- Amazon.in (via public product advertising API alternatives)
- Fashion-specific directories with open data

## Supporting Technologies

### Computer Vision & Image Processing
- **OpenCV**: Video capture, image processing, preprocessing
- **MediaPipe**: Pose estimation fallback (if ControlNet not available)
- **PIL/Pillow**: Image manipulation and format conversion
- **numpy**: Numerical computations

### Database
- **SQLite**: Lightweight, file-based database for:
  - Product catalog (when using local datasets)
  - Search history
  - User preferences
  - Cache for scraped data
- **SQLAlchemy**: ORM for Pythonic database interactions (optional)

### Configuration
- **Pydantic-settings**: For type-safe configuration management
- **Alternative**: python-dotenv + YAML/TOML files
- **Environment Variables**: For sensitive configuration

### Testing
- **pytest**: Unit and integration testing framework
- **pytest-qt**: Qt-specific testing utilities
- **mock**: For external dependency mocking

### Build & Distribution
- **PyInstaller**: Create standalone executables
- **Alternative**: cx_Freeze or Briefcase
- **Platform-specific**:
  - Windows: MSI/EXE
  - macOS: APP bundle
  - Linux: AppImage or distro packages

## Development Tools & Practices

### Code Quality
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Static type checking
- **pre-commit**: Git hooks for automatic formatting/linting

### IDE/Editor
- **VS Code** with Python extensions
- **PyCharm Community Edition** (optional)

### Version Control
- **Git**: Standard version control
- **GitHub/GitLab**: For repository hosting (if desired)

## Hardware Requirements

### Minimum
- **GPU**: NVIDIA GPU with CUDA capability (RTX 3060 or better recommended)
- **VRAM**: 6GB minimum, 8GB+ recommended
- **RAM**: 16GB system memory
- **Storage**: 10GB SSD space (for models, cache, and datasets)
- **OS**: Windows 10/11, macOS 12+, or Linux (Ubuntu 20.04+)

### Recommended for Development
- **GPU**: NVIDIA RTX 4060 Ti or better (8GB+ VRAM)
- **RAM**: 32GB
- **Storage**: NVMe SSD

## Software Dependencies

### Python Packages (Core)
```
PyQt6>=6.5.0
aiortc>=1.5.0
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0
torch>=2.0.0+cu118
torchvision>=0.15.0+cu118
diffusers>=0.21.0
transformers>=4.30.0
accelerate>=0.20.0
xformers>=0.0.20
playwright>=1.35.0
beautifulsoup4>=4.12.0
requests>=2.31.0
SQLAlchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

### System Dependencies
- **FFmpeg**: For video processing (used by OpenCV)
- **Git**: For version control
- **C++ Build Tools**: For compiling some Python extensions

## Architecture Decision Records

### Why PyQt6 over Electron/Tauri?
- **Performance**: Direct GPU access without webview overhead
- **Memory**: Lower memory footprint for ML workloads
- **Integration**: Seamless Python/PyTorch integration
- **Maturity**: Stable API for desktop applications

### Why WebRTC over Simple HTTP Streaming?
- **Latency**: WebRTC provides ~100-200ms vs ~500ms+ for HTTP
- **Adaptability**: Handles varying network conditions better
- **Scalability**: Peer-to-peer potential for future enhancements
- **Standards**: Industry standard for real-time communication

### Why Local Models over Cloud APIs?
- **Requirement**: Zero API costs as specified
- **Privacy**: All processing happens locally
- **Latency**: No network round-trip to cloud services
- **Availability**: Works offline once models are downloaded
- **Control**: Full control over model versions and optimization

## Future Technology Considerations

### When Budget Allows
- **Actual E-commerce APIs**: Myntra, Ajio, Flipkart APIs
- **Cloud Fallback**: For peak load handling
- **Advanced Try-on**: TryOnDiffusion, VITON-HD, or similar
- **Body Measurement**: 3D body estimation from photos
- **AR Mirror**: Real-time try-on using device camera

### Performance Enhancements
- **TensorRT**: For optimized inference on NVIDIA GPUs
- **Model Quantization**: INT8/FP16 for faster inference
- **Parallel Processing**: Batch try-on for multiple garments
- **Preprocessing Pipeline**: Optimized image preparation

## Licensing Considerations
- **PyQt6**: GPLv3 or commercial license
- **Stable Diffusion Models**: Check individual model licenses (often Creative ML OpenRAIL-M)
- **ControlNet**: Typically same license as base model
- **Dataset Licenses**: Vary by source (check DeepFashion2, FashionGen, etc.)
- **Application**: Can be proprietary if using GPL-compatible dependencies appropriately

## References & Resources
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [aiortc GitHub](https://github.com/jazzband/aiortc)
- [Diffusers Library](https://huggingface.co/docs/diffusers)
- [ControlNet GitHub](https://github.com/lllyasviel/ControlNet)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Playwright Python](https://playwright.dev/python/)