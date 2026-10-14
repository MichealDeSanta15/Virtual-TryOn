"""One-time networked setup. Runtime is offline and fails rather than auto-downloading."""
import argparse
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgeai.config import Settings, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--accept-research-licenses", action="store_true")
    args = parser.parse_args()
    if not args.accept_research_licenses:
        raise SystemExit("Review docs/LICENSES.md first. Then rerun with --accept-research-licenses (academic/non-commercial only).")
    settings = Settings.from_env()
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    os.environ["HF_HOME"] = str(settings.model_dir / "hub")
    from huggingface_hub import snapshot_download
    lock = json.loads((ROOT / "models.lock.json").read_text())
    settings.model_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"downloaded_at": datetime.now(timezone.utc).isoformat(), "models": {}}
    for name, spec in lock.items():
        print(f"\nDownloading {name}: {spec['repo']} @ {spec['revision']}…", flush=True)
        path = snapshot_download(repo_id=spec["repo"], revision=spec["revision"],
                                 allow_patterns=spec["files"], local_dir=str(settings.model_dir/name))
        manifest["models"][name] = {**spec, "local_path": str(path)}
    (settings.model_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("\nAll model snapshots downloaded. Next: python scripts/doctor.py")

if __name__ == "__main__":
    main()
