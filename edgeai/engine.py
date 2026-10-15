"""Actual garment-conditioned diffusion. No pasted-clothing/mock fallback."""
import gc
import threading
import time
from dataclasses import dataclass
from PIL import Image
import numpy as np
from .config import Settings, CATEGORIES, PRESETS
from .imaging import Letterbox, validate_mask, preserve_outside, bgr_to_pil, pil_to_bgr, load_rgb, to_rgb_white
from .masking import ClothingParser


@dataclass
class TryOnResult:
    image: Image.Image
    mask: Image.Image
    raw: Image.Image
    metrics: dict
    parsing: Image.Image | None = None
    condition: Image.Image | None = None


class TryOnEngine:
    def __init__(self, settings=None):
        self.settings = settings or Settings.from_env()
        self.settings.prepare_environment()
        self.pipeline = None
        self.parser = ClothingParser(self.settings.model_dir)
        self.lock = threading.Lock()
        self.load_seconds = None

    def load(self):
        """Call under engine.lock. Pipeline is loaded once, not on every frame."""
        if self.pipeline is not None:
            return
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("AI dependencies missing. Run scripts/setup_windows.ps1 first.") from exc
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU unavailable. Install the CUDA 12.8 PyTorch build and NVIDIA driver.")
        major, minor = torch.cuda.get_device_capability()
        if major >= 12 and tuple(map(int, (torch.version.cuda or '0.0').split('.')[:2])) < (12, 8):
            raise RuntimeError("RTX 50-series requires a Blackwell-compatible PyTorch CUDA build (12.8+).")
        base = self.settings.model_dir / "base"
        attn = self.settings.model_dir / "catvton"
        if not base.exists() or not attn.exists():
            raise RuntimeError("Model weights missing. Run python scripts/download_models.py with internet once.")
        from .vendor.catvton.model.pipeline import CatVTONPipeline
        start = time.perf_counter()
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        mode = self.settings.effective_memory_mode
        # Construct on CPU to avoid a transient all-model GPU allocation at startup.
        pipe = CatVTONPipeline(base_ckpt=str(base), attn_ckpt=str(attn),
                              vae_ckpt=str(self.settings.model_dir / "vae"),
                              attn_ckpt_version="mix", weight_dtype=dtype,
                              device="cpu" if mode != "resident" else "cuda",
                              compile=False, skip_safety_check=False, use_tf32=True)
        pipe.vae.enable_slicing()
        pipe.vae.enable_tiling()
        pipe.unet.eval()
        pipe.vae.eval()
        if mode == "sequential":
            from accelerate import cpu_offload
            # Sequential submodule hooks; slower but bounds GPU residency.
            for module in (pipe.unet, pipe.vae, pipe.safety_checker):
                cpu_offload(module, execution_device=torch.device("cuda"), offload_buffers=True)
            pipe.device = "cuda"
        elif mode == "staged":
            from .memory import StagedPlacement
            pipe.placement = StagedPlacement(pipe, execution_device="cuda")
            pipe.device = "cuda"
        self.pipeline = pipe
        self.load_seconds = time.perf_counter() - start

    def make_mask(self, person, category, profile="standard", hem_fraction=.92, flare=.2, sleeves=False):
        if category not in CATEGORIES:
            raise ValueError(f"Unknown category: {category}")
        with self.lock:
            # CPU parser, not retained on the 8 GB GPU.
            small = person.copy()
            small.thumbnail((768, 1024), Image.Resampling.LANCZOS)
            mask, parsing = self.parser(small, category, profile=profile, hem_fraction=hem_fraction, flare=flare, sleeves=sleeves)
            return (mask.resize(person.size, Image.Resampling.NEAREST),
                    parsing.resize(person.size, Image.Resampling.NEAREST))

    def prepare_garment(self, garment, category, mask=None, progress=None):
        from .garment import cloth_mask, prepare_from_mask
        notify = progress or (lambda stage: None)
        notes = []
        garment = to_rgb_white(garment)
        if mask is None:
            notify('extracting_clothing_on_cpu')
            with self.lock:
                small = garment.copy()
                small.thumbnail((768, 1024), Image.Resampling.LANCZOS)
                labels = self.parser.labels(small)
                mask, notes = cloth_mask(labels, category)
                mask = mask.resize(garment.size, Image.Resampling.NEAREST)
            method = 'semantic_clothing'
        else:
            notify('applying_reviewed_reference_mask')
            method = 'manual_mask'
        return prepare_from_mask(garment, mask, category, method, notes)

    def generate(self, person, garment, category="upper", mask=None, preset="draft", seed=42, progress=None):
        if category not in CATEGORIES or preset not in PRESETS:
            raise ValueError("Unsupported category or quality preset")
        if not 0 <= seed < 2**32:
            raise ValueError("Seed must be between 0 and 4294967295")
        person, garment = to_rgb_white(person), to_rgb_white(garment)
        notify = progress or (lambda stage: None)
        with self.lock:
            start = time.perf_counter()
            notify("loading")
            self.load()
            import torch
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            parsing = None
            notify("masking")
            if mask is None:
                # Run parsing at bounded resolution, then restore to input geometry.
                small = person.copy()
                small.thumbnail((768, 1024), Image.Resampling.LANCZOS)
                mask, parsing = self.parser(small, category)
                mask = mask.resize(person.size, Image.Resampling.NEAREST)
                parsing = parsing.resize(person.size, Image.Resampling.NEAREST)
            mask = validate_mask(mask, person.size)
            w, h, steps = PRESETS[preset]
            geometry = Letterbox.create(person.size, (w, h))
            p = geometry.apply(person)
            m = geometry.apply(mask, mask=True)
            c = Letterbox.create(garment.size, (w, h)).apply(garment)
            notify("generating")
            inference_start = time.perf_counter()
            placement = getattr(self.pipeline, "placement", None)
            if placement is not None:
                placement.reset_metrics()
            try:
                # Upstream VAE encoding samples global torch RNG, in addition to
                # generator-controlled denoising. Seed both for repeatable tests.
                with torch.inference_mode(), torch.random.fork_rng(devices=[torch.cuda.current_device()]):
                    torch.manual_seed(seed)
                    torch.cuda.manual_seed_all(seed)
                    generator = torch.Generator(device="cuda").manual_seed(seed)
                    image = self.pipeline(image=p, condition_image=c, mask=m,
                                          width=w, height=h, num_inference_steps=steps,
                                          guidance_scale=self.settings.guidance,
                                          generator=generator)[0]
                torch.cuda.synchronize()
            except torch.cuda.OutOfMemoryError as exc:
                gc.collect()
                torch.cuda.empty_cache()
                raise RuntimeError("GPU out of memory. Close GPU applications; restart with EDGEAI_MEMORY=sequential and use Draft. No fake output was produced.") from exc
            finally:
                if placement is not None:
                    placement.release()
            inference_seconds = time.perf_counter() - inference_start
            notify("finishing")
            raw = geometry.restore(image)
            result = preserve_outside(person, raw, mask)
            metrics = {"total_seconds": round(time.perf_counter()-start, 3),
                       "diffusion_seconds": round(inference_seconds, 3),
                       "model_load_seconds": round(self.load_seconds, 3),
                       "peak_allocated_gb": round(torch.cuda.max_memory_allocated()/1024**3, 3),
                       "peak_reserved_gb": round(torch.cuda.max_memory_reserved()/1024**3, 3),
                       "resolution": [w, h], "steps": steps, "seed": seed,
                       "category": category, "guidance_scale": self.settings.guidance,
                       "mask_fraction": round(float(np.asarray(mask).mean()/255), 4),
                       "offload": self.settings.effective_memory_mode != "resident",
                       "memory_mode": self.settings.effective_memory_mode,
                       "gpu": torch.cuda.get_device_name(), "torch": torch.__version__,
                       "cuda": torch.version.cuda, "mode": "diffusion_snapshot"}
            if placement is not None:
                metrics.update(placement.metrics())
            return TryOnResult(result, mask, raw, metrics, parsing, c.copy())

    def try_on_garment(self, frame, garment_path, category="upper", **kwargs):
        result = self.generate(bgr_to_pil(frame), load_rgb(garment_path), category, **kwargs)
        return pil_to_bgr(result.image)

    def generate_tryon(self, frame, garment_paths, category="upper", **kwargs):
        """Sequential independent alternatives; not stacked outfits or a batch on GPU."""
        return [self.try_on_garment(frame, path, category, **kwargs) for path in garment_paths]
