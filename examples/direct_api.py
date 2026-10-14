"""Run from project root: python examples/direct_api.py person.jpg garment.jpg"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
from tryon_engine import try_on_garment

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: python examples/direct_api.py person.jpg garment.jpg')
    frame=cv2.imread(sys.argv[1])
    if frame is None:raise SystemExit('Could not read person image')
    result=try_on_garment(frame,sys.argv[2],category='upper',preset='draft')
    Path('data').mkdir(exist_ok=True)
    cv2.imwrite('data/direct-result.png',result)
