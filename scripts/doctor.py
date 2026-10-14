"""Hardware and model checks. Includes a real CUDA op, not only is_available()."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgeai.config import Settings, ROOT


def diagnose():
    s=Settings.from_env()
    report={"python":sys.version,"platform":platform.platform(),"models":{},"packages":{},"warnings":[]}
    for package in ['torch','torchvision','diffusers','transformers','accelerate','aiortc','opencv-python']:
        try: report['packages'][package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: report['packages'][package]='NOT INSTALLED'
    try:
        import torch
        report['cuda_available']=torch.cuda.is_available()
        report['torch_cuda']=torch.version.cuda
        if torch.cuda.is_available():
            report['gpu']=torch.cuda.get_device_name()
            report['compute_capability']=list(torch.cuda.get_device_capability())
            report['vram_gb']=round(torch.cuda.get_device_properties(0).total_memory/1024**3,2)
            report['supported_arches']=torch.cuda.get_arch_list()
            # Force an actual CUDA kernel; catches sm_120 / driver mismatches.
            x=torch.randn(128,128,device='cuda'); y=x@x; torch.cuda.synchronize()
            report['cuda_kernel_ok']=bool(torch.isfinite(y).all().item())
        else: report['warnings'].append('No CUDA device. Real try-on is unavailable in this environment.')
    except Exception as exc:
        report['cuda_error']=str(exc)
        report['warnings'].append('CUDA check failed. Install matched cu128 torch/torchvision and a recent NVIDIA driver.')
    lock=json.loads((ROOT/'models.lock.json').read_text())
    for name,spec in lock.items():
        path=s.model_dir/name
        required=[pattern for pattern in spec['files'] if not pattern.startswith(('README','LICENSE'))]
        missing=[pattern for pattern in required if not list(path.glob(pattern))]
        report['models'][name]={'ready':not missing,'missing':missing}
    report['ready_for_gpu_trial']=report.get('cuda_kernel_ok',False) and all(x['ready'] for x in report['models'].values())
    report['note']='Readiness checks are not a successful inference or quality benchmark. Run scripts/tryon.py next.'
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args()
    report=diagnose();text=json.dumps(report,indent=2)
    print(text)
    if args.output:
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        Path(args.output).write_text(text)
    sys.exit(0 if report['ready_for_gpu_trial'] else 1)
