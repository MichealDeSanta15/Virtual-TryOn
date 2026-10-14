"""
Modern Dark Theme QSS Stylesheet for Edge AI Virtual Try-On GUI.
"""

STYLESHEET = """
QMainWindow {
    background-color: #0f1117;
    color: #e2e8f0;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QWidget {
    color: #e2e8f0;
    font-size: 13px;
}

/* Glassmorphism / Modern Card Panels */
QFrame#cardPanel, QFrame#streamCard, QFrame#controlCard, QFrame#resultsCard {
    background-color: #171b26;
    border: 1px solid #283146;
    border-radius: 12px;
}

QFrame#statusCard {
    background-color: #131722;
    border-top: 1px solid #283146;
}

/* Headings */
QLabel#headerTitle {
    font-size: 20px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 0.5px;
}

QLabel#headerSubtitle {
    font-size: 12px;
    color: #94a3b8;
}

QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #f1f5f9;
}

QLabel#fieldLabel {
    font-size: 12px;
    font-weight: 500;
    color: #94a3b8;
}

/* Inputs */
QLineEdit {
    background-color: #0d111a;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 13px;
    selection-background-color: #38bdf8;
}

QLineEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #131b2c;
}

/* Buttons */
QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    color: #f8fafc;
}

QPushButton:hover {
    background-color: #2e3d54;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #172033;
}

QPushButton#btnPrimary {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
    border: none;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 18px;
    border-radius: 8px;
}

QPushButton#btnPrimary:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
}

QPushButton#btnPrimary:disabled {
    background-color: #334155;
    color: #64748b;
}

QPushButton#btnAccent {
    background-color: #059669;
    border: none;
    color: #ffffff;
    font-weight: 600;
    border-radius: 8px;
}

QPushButton#btnAccent:hover {
    background-color: #047857;
}

QPushButton#btnSecondary {
    background-color: #1e293b;
    border: 1px solid #475569;
}

/* Badges */
QLabel#fpsBadge {
    background-color: rgba(6, 78, 59, 0.7);
    color: #34d399;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid #059669;
    max-height: 24px;
}

QLabel#liveBadge {
    background-color: rgba(127, 29, 29, 0.7);
    color: #f87171;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid #b91c1c;
    max-height: 24px;
}

/* Scroll Area & Garment Cards */
QScrollArea {
    border: none;
    background: transparent;
}

QWidget#scrollContent {
    background: transparent;
}

QFrame#garmentCard {
    background-color: #1e2433;
    border: 1px solid #2c364c;
    border-radius: 10px;
    padding: 8px;
}

QFrame#garmentCard:hover {
    border: 1px solid #38bdf8;
    background-color: #232c3f;
}

QLabel#garmentTitle {
    font-size: 12px;
    font-weight: 600;
    color: #f1f5f9;
}

QLabel#garmentBrand {
    font-size: 11px;
    color: #94a3b8;
}

QLabel#garmentPrice {
    font-size: 13px;
    font-weight: 700;
    color: #38bdf8;
}

/* Status Bar & Tooltips */
QStatusBar {
    background-color: #0b0e14;
    color: #94a3b8;
}

QToolTip {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #475569;
    padding: 4px 8px;
    border-radius: 4px;
}
"""
