import sys
import os

def run_gui():
    from PyQt6.QtWidgets import QApplication
    from ui import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

def main():
    try:
        run_gui()
    except Exception as e:
        print(f"Error launching GUI: {e}")
        print("Falling back to placeholder CLI stream...")
        import cv2
        cap = cv2.VideoCapture(0)
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Fallback Camera Stream", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()