"""
Thread and worker components for video feed handling.
Converts OpenCV frames into Qt QImage / QPixmap and emits signals to the GUI.
"""

import time
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap


class VideoCaptureThread(QThread):
    """
    Background worker thread to continuously read frames from a video stream
    (webcam index or IP camera / phone stream URL) without freezing the GUI.
    """
    frame_ready = pyqtSignal(np.ndarray)
    fps_updated = pyqtSignal(float)
    status_changed = pyqtSignal(str)
    connection_failed = pyqtSignal(str)

    def __init__(self, source=0, mirror=True, parent=None):
        super().__init__(parent)
        self.source = source
        self.mirror = mirror
        self.running = False
        self.paused = False
        self._cap = None

    def set_source(self, new_source):
        """Update stream source (int camera index or string stream URL)."""
        self.source = new_source
        if self.running and self._cap:
            self._reconnect()

    def _reconnect(self):
        if self._cap:
            self._cap.release()
            self._cap = None
        self.status_changed.emit("Reconnecting to video source...")
        try:
            # Handle string vs integer source
            src = int(self.source) if isinstance(self.source, str) and self.source.isdigit() else self.source
            self._cap = cv2.VideoCapture(src)
            if self._cap.isOpened():
                self.status_changed.emit("Live Stream Connected")
            else:
                self.connection_failed.emit(f"Failed to open source: {self.source}")
        except Exception as e:
            self.connection_failed.emit(str(e))

    def run(self):
        self.running = True
        src = int(self.source) if isinstance(self.source, str) and self.source.isdigit() else self.source
        
        self.status_changed.emit(f"Connecting to: {self.source}")
        self._cap = cv2.VideoCapture(src)

        if not self._cap.isOpened() and src != 0:
            self.status_changed.emit("Fallback: Opening default camera (0)...")
            self._cap = cv2.VideoCapture(0)

        if not self._cap.isOpened():
            self.connection_failed.emit("Unable to open any video camera or stream.")
            self.running = False
            return

        self.status_changed.emit("Streaming Active")
        frame_count = 0
        start_time = time.time()

        while self.running:
            if self.paused:
                time.sleep(0.05)
                continue

            ret, frame = self._cap.read()
            if not ret or frame is None:
                # If reading fails, retry briefly
                time.sleep(0.02)
                continue

            frame_count += 1
            elapsed = time.time() - start_time
            if elapsed >= 0.5:
                fps = frame_count / elapsed
                self.fps_updated.emit(fps)
                frame_count = 0
                start_time = time.time()

            # Mirror frame horizontally (natural selfie / mirror view for virtual try-on)
            if self.mirror:
                frame = cv2.flip(frame, 1)

            self.frame_ready.emit(frame)
            # Sleep slightly to throttle to ~30-60 FPS max
            time.sleep(0.015)

        if self._cap:
            self._cap.release()
            self._cap = None
        self.status_changed.emit("Stream Disconnected")

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False
        self.wait(2000)


def cv_frame_to_pixmap(cv_img: np.ndarray, target_size=None) -> QPixmap:
    """
    Safely converts an OpenCV BGR numpy ndarray frame into a PyQt6 QPixmap,
    preserving natural aspect ratio to avoid distortion.
    """
    if cv_img is None or cv_img.size == 0:
        return QPixmap()

    h, w, ch = cv_img.shape
    bytes_per_line = ch * w
    # Convert BGR (OpenCV format) to RGB
    rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    q_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(q_img)
    if target_size and not target_size.isEmpty():
        pixmap = pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
    return pixmap
