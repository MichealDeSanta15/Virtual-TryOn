"""
Main Window implementation for Friend 1's Virtual Try-On GUI.
Includes live phone/webcam feed display, controls, scraping triggers,
garment thumbnails, and AI try-on overlay rendering.
"""

import os
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame, QSplitter,
    QMessageBox, QGridLayout, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QIcon

from .styles import STYLESHEET
from .video_thread import VideoCaptureThread, cv_frame_to_pixmap
from .mock_services import MockScraperWorker, MockTryOnWorker


class GarmentCard(QFrame):
    """
    Card representing a scraped clothing item with image, title, price,
    and a 'Try-On' button.
    """
    def __init__(self, item_data: dict, on_tryon_click, parent=None):
        super().__init__(parent)
        self.setObjectName("garmentCard")
        self.item_data = item_data
        self.on_tryon_click = on_tryon_click
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Garment Thumbnail Image
        self.img_label = QLabel()
        self.img_label.setFixedHeight(140)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("background-color: #0d111a; border-radius: 6px;")

        img_path = self.item_data.get("image_path", "")
        if os.path.exists(img_path):
            pix = QPixmap(img_path).scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(pix)
        else:
            self.img_label.setText("No Preview")

        # Garment Title & Details
        title_label = QLabel(self.item_data.get("title", "Clothing Item"))
        title_label.setObjectName("garmentTitle")
        title_label.setWordWrap(True)

        brand_label = QLabel(self.item_data.get("brand", "Brand"))
        brand_label.setObjectName("garmentBrand")

        price_label = QLabel(self.item_data.get("price", "₹0"))
        price_label.setObjectName("garmentPrice")

        # Action Button
        tryon_btn = QPushButton("✨ Try On")
        tryon_btn.setObjectName("btnAccent")
        tryon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        tryon_btn.clicked.connect(lambda: self.on_tryon_click(self.item_data))

        layout.addWidget(self.img_label)
        layout.addWidget(brand_label)
        layout.addWidget(title_label)
        layout.addWidget(price_label)
        layout.addWidget(tryon_btn)


class MainWindow(QMainWindow):
    """
    Main Application Window for Edge AI Virtual Try-On.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edge AI Virtual Try-On - Friend 1 Frontend")
        self.resize(1280, 800)
        self.setMinimumSize(960, 640)
        self.setStyleSheet(STYLESHEET)

        # State
        self.current_frame = None
        self.latest_tryon_frame = None
        self.active_garment = None
        self.camera_source = "0"  # default to webcam, or IP URL

        # Threads & Workers
        self.video_thread = None
        self.scraper_worker = None
        self.tryon_worker = None

        self._build_ui()
        self._start_video_stream()

    def _build_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top Header Bar
        header = self._create_header_bar()
        main_layout.addWidget(header)

        # 2. Splitter: Left (Live Stream & Multi-view) | Right (Input Controls & Clothing Gallery)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        left_panel = self._create_video_panel()
        right_panel = self._create_control_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter)

        # 3. Status Bar
        self.status_label = QLabel("Ready. Connected to Edge AI virtual try-on engine.")
        self.statusBar().addWidget(self.status_label)

    def _create_header_bar(self) -> QWidget:
        header_widget = QWidget()
        header_widget.setMaximumHeight(64)
        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(4, 2, 4, 8)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("Edge AI Virtual Try-On")
        title.setObjectName("headerTitle")
        subtitle = QLabel("RTX 5060 Local Real-time Try-On • Phone Stream & Web Scraper Integration")
        subtitle.setObjectName("headerSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        layout.addLayout(title_box)
        layout.addStretch()

        # Badges & Status - fixed compact dimensions
        self.live_badge = QLabel("● LIVE")
        self.live_badge.setObjectName("liveBadge")
        self.live_badge.setFixedHeight(28)
        self.live_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.fps_badge = QLabel("FPS: --")
        self.fps_badge.setObjectName("fpsBadge")
        self.fps_badge.setFixedHeight(28)
        self.fps_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.live_badge)
        layout.addWidget(self.fps_badge)

        return header_widget

    def _create_video_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("streamCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Title bar for stream
        stream_header = QHBoxLayout()
        st_title = QLabel("Live Camera Feed & Try-On View")
        st_title.setObjectName("sectionTitle")
        stream_header.addWidget(st_title)
        stream_header.addStretch()

        # Flip / Mirror toggle
        self.btn_toggle_mirror = QPushButton("🪞 Mirror: ON")
        self.btn_toggle_mirror.setObjectName("btnSecondary")
        self.btn_toggle_mirror.setToolTip("Toggle horizontal mirror view (like a real mirror)")
        self.btn_toggle_mirror.clicked.connect(self._toggle_mirror)
        stream_header.addWidget(self.btn_toggle_mirror)

        # View Mode Toggle: Single Live vs Split Side-by-side
        self.btn_toggle_multiview = QPushButton("⇄ Side-by-Side")
        self.btn_toggle_multiview.setObjectName("btnSecondary")
        self.btn_toggle_multiview.clicked.connect(self._toggle_multiview)
        self.is_multiview = False
        stream_header.addWidget(self.btn_toggle_multiview)

        layout.addLayout(stream_header)

        # Video Containers
        self.video_container = QWidget()
        self.video_layout = QHBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_layout.setSpacing(10)

        # Primary live feed
        self.live_display = QLabel("Initializing Video Stream...")
        self.live_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live_display.setStyleSheet("background-color: #0b0d13; border-radius: 8px; color: #64748b; font-size: 14px;")
        self.live_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_layout.addWidget(self.live_display)

        # Comparison try-on feed (hidden by default)
        self.tryon_display = QLabel("Selected Garment Try-On Will Appear Here")
        self.tryon_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tryon_display.setStyleSheet("background-color: #0b0d13; border-radius: 8px; color: #64748b; font-size: 14px;")
        self.tryon_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tryon_display.setVisible(False)
        self.video_layout.addWidget(self.tryon_display)

        layout.addWidget(self.video_container)

        # Stream source settings row
        source_row = QHBoxLayout()
        src_label = QLabel("Camera / Phone URL:")
        src_label.setObjectName("fieldLabel")
        self.source_input = QLineEdit("0")
        self.source_input.setPlaceholderText("0 or http://192.168.1.X:8080/video")
        self.source_input.setToolTip("Enter camera index (0, 1) or IP Webcam/Droidcam RTSP/HTTP URL")

        btn_connect = QPushButton("Switch Source")
        btn_connect.clicked.connect(self._on_switch_source)

        source_row.addWidget(src_label)
        source_row.addWidget(self.source_input)
        source_row.addWidget(btn_connect)
        layout.addLayout(source_row)

        return card

    def _create_control_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("controlCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # 1. Search Query Section
        query_title = QLabel("Find Outfits (Friend 2 Scraper)")
        query_title.setObjectName("sectionTitle")
        layout.addWidget(query_title)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        lbl_event = QLabel("Event / Occasion:")
        lbl_event.setObjectName("fieldLabel")
        self.input_event = QLineEdit("Freshers Party Dress")
        self.input_event.setPlaceholderText("e.g. Wedding reception, Formal interview, Gym")

        lbl_budget = QLabel("Budget (INR):")
        lbl_budget.setObjectName("fieldLabel")
        self.input_budget = QLineEdit("Under 5000")
        self.input_budget.setPlaceholderText("e.g. Under 3000, 5000-10000")

        self.btn_scrape = QPushButton("🔍 Search & Scrape Clothes")
        self.btn_scrape.setObjectName("btnPrimary")
        self.btn_scrape.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scrape.clicked.connect(self._on_search_clicked)

        form_layout.addWidget(lbl_event)
        form_layout.addWidget(self.input_event)
        form_layout.addWidget(lbl_budget)
        form_layout.addWidget(self.input_budget)
        form_layout.addWidget(self.btn_scrape)

        layout.addLayout(form_layout)

        # 2. Results Section
        results_header = QHBoxLayout()
        self.results_title = QLabel("Available Garments (0 items)")
        self.results_title.setObjectName("sectionTitle")
        results_header.addWidget(self.results_title)
        results_header.addStretch()
        layout.addLayout(results_header)

        # Scrollable gallery
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        # Settings Summary
        info_label = QLabel("✨ Tip: Click 'Try On' on any outfit to overlay it onto your live stream.")
        info_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(info_label)

        return card

    # ==========================
    # Video & Stream Handling
    # ==========================
    def _start_video_stream(self):
        if self.video_thread is not None and self.video_thread.isRunning():
            self.video_thread.stop()

        self.video_thread = VideoCaptureThread(source=self.camera_source, parent=self)
        self.video_thread.frame_ready.connect(self._on_frame_received)
        self.video_thread.fps_updated.connect(self._on_fps_updated)
        self.video_thread.status_changed.connect(self._on_stream_status)
        self.video_thread.connection_failed.connect(self._on_stream_failed)
        self.video_thread.start()

    def _on_switch_source(self):
        new_source = self.source_input.text().strip()
        if new_source:
            self.camera_source = new_source
            self._start_video_stream()

    def _on_frame_received(self, frame: np.ndarray):
        self.current_frame = frame
        pix = cv_frame_to_pixmap(frame, target_size=self.live_display.size())
        if not pix.isNull():
            self.live_display.setPixmap(pix)

    def _on_fps_updated(self, fps: float):
        self.fps_badge.setText(f"FPS: {fps:.1f}")

    def _on_stream_status(self, msg: str):
        self.status_label.setText(f"Status: {msg}")

    def _on_stream_failed(self, error: str):
        self.status_label.setText(f"Camera Alert: {error}")
        self.live_display.setText(f"Camera Stream Unavailable\n({error})\nEnter valid phone URL or webcam index below.")

    def _toggle_mirror(self):
        if self.video_thread is not None:
            self.video_thread.mirror = not self.video_thread.mirror
            state = "ON" if self.video_thread.mirror else "OFF"
            self.btn_toggle_mirror.setText(f"🪞 Mirror: {state}")
            self.status_label.setText(f"Camera mirror mode: {state}")

    def _toggle_multiview(self):
        self.is_multiview = not self.is_multiview
        self.tryon_display.setVisible(self.is_multiview)
        if self.is_multiview:
            self.btn_toggle_multiview.setText("⊞ Single View")
        else:
            self.btn_toggle_multiview.setText("⇄ Side-by-Side")

    # ==========================
    # Scraping & Outfits
    # ==========================
    def _on_search_clicked(self):
        event = self.input_event.text().strip()
        budget = self.input_budget.text().strip()

        if not event:
            QMessageBox.warning(self, "Input Required", "Please enter an event or occasion.")
            return

        self.btn_scrape.setEnabled(False)
        self.btn_scrape.setText("⏳ Scraping Products...")
        self.status_label.setText(f"Scraping garments for '{event}' (budget: {budget})...")

        self.scraper_worker = MockScraperWorker(event, budget, parent=self)
        self.scraper_worker.results_ready.connect(self._on_scraper_results)
        self.scraper_worker.error_occurred.connect(self._on_scraper_error)
        self.scraper_worker.start()

    def _on_scraper_results(self, results: list):
        self.btn_scrape.setEnabled(True)
        self.btn_scrape.setText("🔍 Search & Scrape Clothes")
        self.results_title.setText(f"Available Garments ({len(results)} items)")
        self.status_label.setText(f"Successfully loaded {len(results)} garments.")

        # Clear existing items
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Populate cards in a 2-column responsive layout
        for idx, item in enumerate(results):
            card = GarmentCard(item, on_tryon_click=self._on_garment_tryon_selected)
            row = idx // 2
            col = idx % 2
            self.grid_layout.addWidget(card, row, col)

    def _on_scraper_error(self, err_msg: str):
        self.btn_scrape.setEnabled(True)
        self.btn_scrape.setText("🔍 Search & Scrape Clothes")
        self.status_label.setText(f"Error scraping outfits: {err_msg}")
        QMessageBox.warning(self, "Scraper Error", err_msg)

    # ==========================
    # AI Try-On Integration
    # ==========================
    def _on_garment_tryon_selected(self, item_data: dict):
        if self.current_frame is None:
            QMessageBox.warning(self, "No Video Frame", "Waiting for video stream frame before running try-on.")
            return

        self.active_garment = item_data
        title = item_data.get("title", "Selected Garment")
        img_path = item_data.get("image_path", "")

        self.status_label.setText(f"Generating AI Try-On for '{title}' (ControlNet + SDXL)...")

        # Automatically open side-by-side mode so user can inspect both
        if not self.is_multiview:
            self._toggle_multiview()

        self.tryon_display.setText(f"Generating Try-On for {title}...\nPlease hold still.")

        self.tryon_worker = MockTryOnWorker(self.current_frame, img_path, title, parent=self)
        self.tryon_worker.tryon_completed.connect(self._on_tryon_completed)
        self.tryon_worker.tryon_failed.connect(self._on_tryon_failed)
        self.tryon_worker.start()

    def _on_tryon_completed(self, composited_frame: np.ndarray, title: str):
        self.latest_tryon_frame = composited_frame
        pix = cv_frame_to_pixmap(composited_frame, target_size=self.tryon_display.size())
        if not pix.isNull():
            self.tryon_display.setPixmap(pix)
        self.status_label.setText(f"Try-On updated for: {title}")

    def _on_tryon_failed(self, error_msg: str):
        self.status_label.setText(f"Try-On Failed: {error_msg}")
        self.tryon_display.setText(f"Try-On Error:\n{error_msg}")

    def closeEvent(self, event):
        """Cleanup threads when closing the application."""
        if self.video_thread is not None:
            self.video_thread.stop()
        if self.scraper_worker is not None and self.scraper_worker.isRunning():
            self.scraper_worker.quit()
        if self.tryon_worker is not None and self.tryon_worker.isRunning():
            self.tryon_worker.quit()
        event.accept()
