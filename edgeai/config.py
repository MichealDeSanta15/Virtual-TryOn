from dataclasses import dataclass
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    model_dir: Path = ROOT / "models"
    data_dir: Path = ROOT / "data"
    width: int = 384
    height: int = 512
    steps: int = 30
    guidance: float = 2.5
    seed: int = 42
    offload: bool = True
    memory_mode: str | None = None
    offline: bool = True
    max_upload_mb: int = 15

    @property
    def effective_memory_mode(self):
        # Retain the direct Python Settings(offload=...) API.
        mode = self.memory_mode or ('sequential' if self.offload else 'resident')
        if mode not in ('staged', 'sequential', 'resident'):
            raise ValueError('EDGEAI_MEMORY must be staged, sequential or resident')
        return mode

    @classmethod
    def from_env(cls):
        mode = os.getenv('EDGEAI_MEMORY')
        if mode is None:
            legacy = os.getenv('EDGEAI_OFFLOAD')
            mode = ('sequential' if legacy == '1' else 'resident') if legacy is not None else 'staged'
        if mode not in ('staged', 'sequential', 'resident'):
            raise ValueError('EDGEAI_MEMORY must be staged, sequential or resident')
        return cls(model_dir=Path(os.getenv("EDGEAI_MODELS", ROOT / "models")),
                   data_dir=Path(os.getenv("EDGEAI_DATA", ROOT / "data")),
                   offload=mode != "resident", memory_mode=mode)

    def prepare_environment(self):
        # Set before importing transformers / huggingface_hub.
        os.environ.setdefault("HF_HOME", str(self.model_dir / "hub"))
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        if self.offline:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

CATEGORIES = ("upper", "lower", "overall")
PRESETS = {"draft": (384, 512, 20), "balanced": (512, 768, 30),
           "quality": (768, 1024, 50), "dress": (576, 768, 35)}
