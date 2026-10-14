"""
Mock / Interface for Friend 2's Scraper & Friend 3's AI Try-On engine.
Enables Friend 1's UI to function standalone or dynamically integrate with real modules.
"""

import os
import time
import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal


class MockScraperWorker(QThread):
    """
    Simulates scraping clothing items in a background thread or calls
    Friend 2's `search_clothes` when available.
    """
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, event_text: str, budget_text: str, parent=None):
        super().__init__(parent)
        self.event_text = event_text
        self.budget_text = budget_text

    def run(self):
        # Check if Friend 2 has implemented scraper API
        try:
            from scraper import search_clothes
            results = search_clothes(self.event_text, self.budget_text)
            if results:
                self.results_ready.emit(results)
                return
        except ImportError:
            pass
        except Exception as e:
            self.error_occurred.emit(f"Scraper error: {str(e)}")
            return

        # Fallback Mock data for UI testing & demo
        time.sleep(1.2)  # Simulate network latency
        sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_clothes")
        os.makedirs(sample_dir, exist_ok=True)

        # Generate sample placeholder garment images if not present
        mock_items = [
            {"title": "Classic Navy Blazer", "brand": "Zara Man", "price": "₹3,499", "color": (130, 60, 40)},
            {"title": "Floral Party Dress", "brand": "H&M Studio", "price": "₹2,299", "color": (80, 160, 220)},
            {"title": "Casual Linen Shirt", "brand": "Roadster", "price": "₹1,199", "color": (180, 200, 150)},
            {"title": "Embroidered Kurta", "brand": "FabIndia", "price": "₹2,799", "color": (50, 100, 200)},
            {"title": "Oversized Street Hoodie", "brand": "Urbanic", "price": "₹1,899", "color": (70, 70, 70)},
            {"title": "Slim-Fit Formal Trousers", "brand": "Raymond", "price": "₹1,999", "color": (40, 40, 40)},
        ]

        results = []
        for i, item in enumerate(mock_items):
            img_path = os.path.join(sample_dir, f"garment_{i+1}.jpg")
            if not os.path.exists(img_path):
                # Create a sample garment swatch / mock image
                canvas = np.full((320, 240, 3), item["color"], dtype=np.uint8)
                cv2.rectangle(canvas, (10, 10), (230, 310), (255, 255, 255), 2)
                cv2.putText(canvas, item["brand"], (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(canvas, item["title"][:14], (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(canvas, item["price"], (20, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imwrite(img_path, canvas)

            results.append({
                "id": str(i + 1),
                "title": f"{item['title']} - {self.event_text or 'Event'}",
                "brand": item["brand"],
                "price": item["price"],
                "image_path": img_path,
                "rating": "4.3 ★",
                "source": "Ajio / Myntra"
            })

        self.results_ready.emit(results)


class MockTryOnWorker(QThread):
    """
    Simulates AI Try-on computation or calls Friend 3's `try_on_garment`.
    """
    tryon_completed = pyqtSignal(np.ndarray, str)
    tryon_failed = pyqtSignal(str)

    def __init__(self, frame: np.ndarray, garment_path: str, garment_title: str, parent=None):
        super().__init__(parent)
        self.frame = frame.copy() if frame is not None else None
        self.garment_path = garment_path
        self.garment_title = garment_title

    def run(self):
        if self.frame is None:
            self.tryon_failed.emit("Cannot run try-on: No live video frame captured.")
            return

        # Check for Friend 3's real try-on implementation
        try:
            from tryon import try_on_garment
            result_frame = try_on_garment(self.frame, self.garment_path)
            if result_frame is not None:
                self.tryon_completed.emit(result_frame, self.garment_title)
                return
        except ImportError:
            pass
        except Exception as e:
            self.tryon_failed.emit(f"AI Try-on engine error: {str(e)}")
            return

        # Mock try-on overlay with realistic chest/torso proportions
        time.sleep(0.8)
        out = self.frame.copy()
        h, w, _ = out.shape

        # Read garment preview
        g_img = cv2.imread(self.garment_path)
        if g_img is not None:
            gh, gw, _ = g_img.shape
            
            # Scale garment naturally to chest/torso area without extreme stretching
            target_w = int(w * 0.42)
            scale = target_w / float(gw)
            target_h = int(gh * scale)
            
            # Clamp height to fit reasonably on upper body
            max_h = int(h * 0.55)
            if target_h > max_h:
                target_h = max_h
                target_w = int(gw * (target_h / float(gh)))

            g_resized = cv2.resize(g_img, (target_w, target_h), interpolation=cv2.INTER_AREA)
            
            x_offset = max(0, int((w - target_w) / 2))
            y_offset = max(0, int(h * 0.38))
            
            # Make sure it stays within frame boundaries
            if y_offset + target_h > h:
                target_h = h - y_offset
                g_resized = g_resized[:target_h, :]

            # Smooth alpha blend for realistic preview
            roi = out[y_offset:y_offset+target_h, x_offset:x_offset+target_w]
            blended = cv2.addWeighted(roi, 0.35, g_resized, 0.65, 0)
            out[y_offset:y_offset+target_h, x_offset:x_offset+target_w] = blended

            # Subtle modern tag
            tag_text = f"✨ VTON: {self.garment_title.split('-')[0].strip()}"
            cv2.rectangle(out, (x_offset, max(0, y_offset - 26)), (x_offset + 220, y_offset), (15, 17, 23), -1)
            cv2.putText(out, tag_text, (x_offset + 8, max(12, y_offset - 8)),
                        cv2.FONT_HERSHEY_DUPLEX, 0.42, (56, 189, 248), 1, cv2.LINE_AA)

        self.tryon_completed.emit(out, self.garment_title)
