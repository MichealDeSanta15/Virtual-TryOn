"""
Edge AI Virtual Try-On - Main Entry Point
TODO: Implement full pipeline per plan.
"""

import cv2
import threading
import queue
import time
from typing import Optional

# Configuration
PHONE_STREAM_URL = "http://192.168.1.236:8080/video"  # Replace with actual phone IP
# For testing, can use 0 for webcam
# PHONE_STREAM_URL = 0

def video_capture_thread(q: queue.Queue, stop_event: threading.Event):
    """Continuously capture frames from phone stream and put them in queue."""
    cap = cv2.VideoCapture(PHONE_STREAM_URL)
    if not cap.isOpened():
        print(f"Error: Could not open video stream at {PHONE_STREAM_URL}")
        # Fallback to default camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open any video source.")
            stop_event.set()
            return

    print("Video stream started. Press 'q' in video window to quit.")
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print("Warning: Failed to read frame.")
            time.sleep(0.01)
            continue
        # If queue is full, drop oldest frame to maintain latency
        if q.full():
            try:
                q.get_nowait()
            except queue.Empty:
                pass
        q.put(frame)
    cap.release()
    print("Video capture thread stopped.")

def main():
    frame_queue = queue.Queue(maxsize=5)
    stop_event = threading.Event()

    # Start video capture thread
    capture_thread = threading.Thread(target=video_capture_thread, args=(frame_queue, stop_event), daemon=True)
    capture_thread.start()

    try:
        while True:
            # Get frame with timeout
            try:
                frame = frame_queue.get(timeout=1.0)
            except queue.Empty:
                print("No frame received, checking...")
                continue

            # TODO: Process frame with pose estimation, try-on, etc.
            # For now, just display raw frame
            display_frame = frame.copy()
            cv2.putText(display_frame, "LIVE PHONE STREAM (PLACEHOLDER)", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, "Press 'q' to quit", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            cv2.imshow("Edge AI Virtual Try-On", display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        stop_event.set()
        capture_thread.join(timeout=2.0)
        cv2.destroyAllWindows()
        print("Application terminated.")

if __name__ == "__main__":
    main()