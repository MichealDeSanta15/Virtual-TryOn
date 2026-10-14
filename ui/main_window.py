#!/usr/bin/env python3
"""
Main Window for Edge AI Virtual Try-On Application
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QSplitter, QFrame, QScrollArea,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QImage, QFont
import cv2
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CameraThread(QThread):
    """Thread for capturing video frames"""
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.running = False
        self.cap = None

    def run(self):
        """Capture frames from camera"""
        self.running = True
        self.cap = cv2.VideoCapture(self.camera_id)

        if not self.cap.isOpened():
            logger.error(f"Could not open camera {self.camera_id}")
            return

        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Convert BGR to RGB for Qt
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.frame_ready.emit(frame_rgb)
            self.msleep(30)  # ~30 FPS

        if self.cap:
            self.cap.release()

    def stop(self):
        """Stop the camera thread"""
        self.running = False
        self.wait()


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edge AI Virtual Try-On")
        self.setGeometry(100, 100, 1400, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Left panel: Video feed and controls
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 2)

        # Right panel: Search and results
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)

        # Status bar
        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # Initialize camera thread
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self.update_video_frame)

        # Current frame
        self.current_frame = None

        # Sample dataset path (will be populated later)
        self.sample_dataset_path = Path("sample_dataset")
        self.sample_dataset_path.mkdir(exist_ok=True)

        logger.info("Main window initialized")

    def create_left_panel(self):
        """Create left panel with video feed and controls"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)

        # Video display
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                background-color: #f0f0f0;
            }
        """)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setText("Camera Feed\n(Click Start Camera)")
        layout.addWidget(self.video_label)

        # Controls
        controls_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.start_camera)
        controls_layout.addWidget(self.start_button)

        self.capture_button = QPushButton("Capture Photo")
        self.capture_button.clicked.connect(self.capture_photo)
        self.capture_button.setEnabled(False)
        controls_layout.addWidget(self.capture_button)

        layout.addLayout(controls_layout)

        # Captured photo display
        self.captured_label = QLabel()
        self.captured_label.setMinimumSize(320, 240)
        self.captured_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                background-color: #f0f0f0;
            }
        """)
        self.captured_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.captured_label.setText("Captured Photo\n(Will appear here)")
        layout.addWidget(self.captured_label)

        return panel

    def create_right_panel(self):
        """Create right panel with search and results"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)

        # Search section
        search_label = QLabel("Search for Clothing:")
        search_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g., freshers dress under 5000")
        self.search_input.returnPressed.connect(self.search_clothing)
        layout.addWidget(self.search_input)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_clothing)
        layout.addWidget(self.search_button)

        # Results section
        results_label = QLabel("Search Results:")
        results_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(results_label)

        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(200)
        self.results_list.itemClicked.connect(self.result_selected)
        layout.addWidget(self.results_list)

        # Try-on section
        tryon_label = QLabel("Virtual Try-On:")
        tryon_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(tryon_label)

        self.tryon_button = QPushButton("Generate Try-On")
        self.tryon_button.clicked.connect(self.generate_tryon)
        self.tryon_button.setEnabled(False)
        layout.addWidget(self.tryon_button)

        # Try-on results
        self.tryon_label = QLabel()
        self.tryon_label.setMinimumSize(300, 400)
        self.tryon_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                background-color: #f0f0f0;
            }
        """)
        self.tryon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tryon_label.setText("Try-on Result\n(Will appear here)")
        layout.addWidget(self.tryon_label)

        return panel

    def start_camera(self):
        """Start the camera feed"""
        if not self.camera_thread.isRunning():
            self.camera_thread.start()
            self.start_button.setText("Stop Camera")
            self.capture_button.setEnabled(True)
            self.status_bar.showMessage("Camera started")
            logger.info("Camera started")
        else:
            self.stop_camera()

    def stop_camera(self):
        """Stop the camera feed"""
        self.camera_thread.stop()
        self.start_button.setText("Start Camera")
        self.capture_button.setEnabled(False)
        self.status_bar.showMessage("Camera stopped")
        logger.info("Camera stopped")

    def update_video_frame(self, frame):
        """Update the video display with new frame"""
        self.current_frame = frame

        # Convert to QImage and display
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

        # Scale to fit label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

    def capture_photo(self):
        """Capture the current frame as a photo"""
        if self.current_frame is not None:
            # Convert RGB to BGR for OpenCV saving
            frame_bgr = cv2.cvtColor(self.current_frame, cv2.COLOR_RGB2BGR)

            # Save captured photo
            capture_path = Path("captured_photo.jpg")
            cv2.imwrite(str(capture_path), frame_bgr)

            # Display captured photo
            height, width, channel = self.current_frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(self.current_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.captured_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.captured_label.setPixmap(scaled_pixmap)

            self.status_bar.showMessage(f"Photo captured and saved to {capture_path}")
            logger.info(f"Photo captured: {capture_path}")

            # Enable search and try-on buttons
            self.search_button.setEnabled(True)
            self.tryon_button.setEnabled(True)
        else:
            QMessageBox.warning(self, "Warning", "No frame available to capture")

    def search_clothing(self):
        """Search for clothing based on user input"""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a search query")
            return

        self.status_bar.showMessage(f"Searching for: {query}")
        logger.info(f"Searching for: {query}")

        # Clear previous results
        self.results_list.clear()

        # For now, use sample data - in real implementation this would query database
        sample_results = [
            f"{query} - Option 1",
            f"{query} - Option 2",
            f"{query} - Option 3",
            f"{query} - Option 4",
            f"{query} - Option 5"
        ]

        for result in sample_results:
            item = QListWidgetItem(result)
            self.results_list.addItem(item)

        self.status_bar.showMessage(f"Found {len(sample_results)} results for: {query}")

    def result_selected(self, item):
        """Handle selection of a search result"""
        selected_text = item.text()
        self.status_bar.showMessage(f"Selected: {selected_text}")
        logger.info(f"Selected result: {selected_text}")

        # In a real implementation, this would load the actual garment image
        # For now, we'll just enable the try-on button
        self.tryon_button.setEnabled(True)

    def generate_tryon(self):
        """Generate virtual try-on result"""
        if self.current_frame is None:
            QMessageBox.warning(self, "Warning", "Please capture a photo first")
            return

        selected_items = self.results_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a clothing item from search results")
            return

        selected_item = selected_items[0].text()
        self.status_bar.showMessage(f"Generating try-on for: {selected_item}")
        logger.info(f"Generating try-on for: {selected_item}")

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Simulate processing time (in real implementation, this would call the try-on engine)
        QTimer.singleShot(3000, self.complete_tryon)  # 3 second delay for demo

    def complete_tryon(self):
        """Complete the try-on generation (called after simulated processing)"""
        self.progress_bar.setVisible(False)

        # For demo, we'll just show a placeholder or the original image with some text overlay
        if self.current_frame is not None:
            # Create a copy of the frame for display
            display_frame = self.current_frame.copy()

            # Add some text to indicate this is a try-on result
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(display_frame, "TRY-ON RESULT", (50, 50), font, 1, (0, 255, 0), 2)
            cv2.putText(display_frame, "(Simulated - Real AI coming soon)", (50, 100), font, 0.5, (255, 255, 0), 1)

            # Convert to QImage and display
            height, width, channel = display_frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(display_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.tryon_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.tryon_label.setPixmap(scaled_pixmap)

        self.status_bar.showMessage("Try-on generation complete")
        logger.info("Try-on generation complete (demo)")


def main():
    """Test the main window standalone"""
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())