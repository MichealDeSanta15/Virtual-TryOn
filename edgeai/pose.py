"""Optional MediaPipe Tasks debugging. Not a substitute for clothing segmentation."""
from pathlib import Path
import cv2
import numpy as np


class PoseEstimator:
    def __init__(self, model_path):
        import mediapipe as mp
        path=Path(model_path)
        if not path.exists():
            raise FileNotFoundError('Download pose_landmarker_lite.task; see docs/SETUP_WINDOWS.md')
        self.mp=mp
        self.detector=mp.tasks.vision.PoseLandmarker.create_from_options(
            mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(path)),
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_poses=1, min_pose_detection_confidence=.5,
                output_segmentation_masks=False))

    def estimate(self, frame):
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        image=self.mp.Image(image_format=self.mp.ImageFormat.SRGB,data=rgb)
        result=self.detector.detect(image)
        return result.pose_landmarks[0] if result.pose_landmarks else []

    def draw(self, frame, landmarks):
        output=frame.copy();h,w=frame.shape[:2]
        edges=[(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),
               (23,25),(25,27),(24,26),(26,28)]
        for a,b in edges:
            if not landmarks:break
            if min(landmarks[a].visibility,landmarks[b].visibility)<.5:continue
            pa,pb=landmarks[a],landmarks[b]
            cv2.line(output,(int(pa.x*w),int(pa.y*h)),(int(pb.x*w),int(pb.y*h)),(150,240,190),2)
        return output

    def close(self):self.detector.close()
