"""Static image smoke test / repeated inference benchmark. Needs downloaded models and CUDA."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgeai.engine import TryOnEngine
from edgeai.imaging import load_rgb


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--person',required=True);p.add_argument('--garment',required=True)
    p.add_argument('--mask',help='Optional grayscale mask at EXACT person dimensions; white = edit')
    p.add_argument('--category',choices=['upper','lower','overall'],default='upper')
    p.add_argument('--preset',choices=['draft','balanced','quality','dress'],default='draft')
    p.add_argument('--seed',type=int,default=42);p.add_argument('--runs',type=int,default=1)
    p.add_argument('--output',default='data/benchmark')
    args=p.parse_args()
    if not 1<=args.runs<=20:p.error('--runs must be 1..20')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    person,garment=load_rgb(args.person),load_rgb(args.garment)
    mask=load_rgb(args.mask).convert('L') if args.mask else None
    engine=TryOnEngine();records=[]
    for i in range(args.runs):
        r=engine.generate(person,garment,category=args.category,mask=mask,
                          preset=args.preset,seed=args.seed,progress=print)
        r.image.save(out/f'result-{i+1}.png');r.mask.save(out/f'mask-{i+1}.png');r.raw.save(out/f'raw-{i+1}.png')
        if r.parsing:r.parsing.save(out/f'parsing-{i+1}.png')
        if r.condition:r.condition.save(out/f'condition-{i+1}.png')
        records.append({'run':i+1,'cold_start':i==0,**r.metrics})
        (out/'benchmark.json').write_text(json.dumps(records,indent=2))
    print(f'Wrote {out}. First run includes model startup; later runs reuse loaded weights.')

if __name__=='__main__':main()
