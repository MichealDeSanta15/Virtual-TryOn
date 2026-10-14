import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
from edgeai.pose import PoseEstimator
p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('--model',default='models/pose_landmarker_lite.task');p.add_argument('--output',default='data/pose-debug.png');args=p.parse_args()
frame=cv2.imread(args.image)
if frame is None:raise SystemExit('Cannot read image')
estimator=PoseEstimator(args.model)
try:
    landmarks=estimator.estimate(frame)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    cv2.imwrite(args.output,estimator.draw(frame,landmarks))
    print(f'{len(landmarks)} landmarks. Debug image: {args.output}')
finally:estimator.close()
