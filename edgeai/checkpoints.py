"""Explicit local format selection; never silently fall back from safe to pickle."""
from pathlib import Path


def local_weight_options(root, subfolder=None, transformers_model=False):
    path = Path(root) / subfolder if subfolder else Path(root)
    safe = 'model.safetensors' if transformers_model else 'diffusion_pytorch_model.safetensors'
    binary = 'pytorch_model.bin' if transformers_model else 'diffusion_pytorch_model.bin'
    if (path / safe).is_file():
        return {'use_safetensors': True, 'local_files_only': True}
    if (path / binary).is_file():
        # The project downloader supplies pinned upstream .bin files. This is an
        # explicit format choice, NOT a conversion/security guarantee for pickle.
        # Never load arbitrary/untrusted replacements. Prefer safetensors if available.
        return {'use_safetensors': False, 'local_files_only': True}
    raise FileNotFoundError(f'Expected {safe} or {binary} in {path}. Run the model downloader.')
