"""CPU-only reference extraction using the existing local parser. Review output!"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgeai.engine import TryOnEngine
from edgeai.imaging import load_rgb

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--garment',required=True)
    p.add_argument('--category',choices=['upper','lower','overall'],required=True)
    p.add_argument('--mask',help='Optional manually drawn garment-selection mask, original reference geometry')
    p.add_argument('--output',default='data/prepared-garment')
    args=p.parse_args()
    source=load_rgb(args.garment)
    if max(source.size)>2048: p.error('Resize source and reference mask together to at most 2048px')
    mask=load_rgb(args.mask).convert('L') if args.mask else None
    result=TryOnEngine().prepare_garment(source,args.category,mask=mask,progress=print)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    result.image.save(out/'garment.png');result.mask.save(out/'reference-mask.png')
    (out/'preparation.json').write_text(json.dumps(result.metadata,indent=2))
    print(f'Review {out}/garment.png before use. Hidden cloth is NOT reconstructed; no try-on was generated.')
