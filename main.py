import sys
import cv2
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QComboBox, QMessageBox  
)
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import json


class VideoThread(QThread):
    frame_received = pyqtSignal(QImage)
    raw_frame = None

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.url)
        while self.running:
            ret, frame = cap.read()
            if ret:
                self.raw_frame = frame.copy()
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h,
                                  bytes_per_line, QImage.Format.Format_RGB888)
                self.frame_received.emit(qt_image)
        cap.release()

    def stop(self):
        self.running = False
        self.wait()


class CameraApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📷 Dual Camera Viewer")
        self.setStyleSheet("background-color: #f0f0f0;")
        self.setFixedSize(1000, 520)

        self.material_types = self.load_material_types("config/materials.json")
        self.cameras_config = self.load_camera_config("config/cameras.json")
        
        self.dropdown = QComboBox()
        self.dropdown.addItems(self.material_types)
        self.dropdown.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #888;
                border-radius: 6px;
                background-color: white;
                color: black; 
                font-size: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;  
                selection-background-color: #d0d0d0;
            }
        """)

        # Preview labels
        self.left_label = self.create_preview_label()
        self.right_label = self.create_preview_label()

        # Capture button
        self.capture_button = QPushButton("📸 Capture Image")
        self.capture_button.setFont(QFont("Arial", 14))
        self.capture_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.capture_button.clicked.connect(self.capture_images)

        # Layouts
        button_row = QHBoxLayout()
        button_row.addWidget(self.dropdown)
        button_row.addWidget(self.capture_button)

        preview_layout = QHBoxLayout()
        preview_layout.addWidget(self.left_label)
        preview_layout.addWidget(self.right_label)

        main_layout = QVBoxLayout()
        main_layout.addLayout(preview_layout)
        main_layout.addLayout(button_row)
        self.setLayout(main_layout)

        # Threads
        left_url = self.cameras_config.get("left", "")
        right_url = self.cameras_config.get("right", "")
        self.left_thread = VideoThread(left_url)
        self.right_thread = VideoThread(right_url)
        self.left_thread.frame_received.connect(self.update_left)
        self.right_thread.frame_received.connect(self.update_right)
        self.left_thread.start()
        self.right_thread.start()

    def create_preview_label(self):
        label = QLabel()
        label.setFixedSize(480, 360)
        label.setFrameShape(QFrame.Shape.Box)
        label.setStyleSheet("""
            QLabel {
                background-color: #ddd;
                border: 2px solid #aaa;
                border-radius: 10px;
            }
        """)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def update_left(self, image):
        self.left_label.setPixmap(QPixmap.fromImage(image).scaled(
            self.left_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def update_right(self, image):
        self.right_label.setPixmap(QPixmap.fromImage(image).scaled(
            self.right_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


    def capture_images(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = datetime.now().strftime("%d_%m_%Y")
        material = self.dropdown.currentText()
        os.makedirs(f"results/{folder_name}", exist_ok=True)

        saved_files = []

        if self.left_thread.raw_frame is not None:
            left_path = f"results/{folder_name}/{material}_left_{timestamp}.png"
            cv2.imwrite(left_path, self.left_thread.raw_frame)
            saved_files.append(left_path)

        if self.right_thread.raw_frame is not None:
            right_path = f"results/{folder_name}/{material}_right_{timestamp}.png"
            cv2.imwrite(right_path, self.right_thread.raw_frame)
            saved_files.append(right_path)

        if saved_files:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("✅ ถ่ายภาพสำเร็จ")
            msg.setText("บันทึกภาพแล้ว:\n\n" + "\n".join(saved_files))
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            msg.exec()
        else:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("⚠️ ไม่พบภาพ")
            msg.setText("ไม่สามารถบันทึกภาพได้ กรุณาตรวจสอบกล้อง")
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            msg.exec()

    def closeEvent(self, event):
        self.left_thread.stop()
        self.right_thread.stop()
        event.accept()

    def load_material_types(self, filepath):
        try:
            with open(filepath, "r") as file:
                data = json.load(file)
                return data.get("materials", [])
        except Exception as e:
            print(f"Error loading material types: {e}")
            return ["unknown"]
        
    def load_camera_config(self, filepath):
        try:
            with open(filepath, "r") as file:
                data = json.load(file)
                return data 
        except Exception as e:
            print(f"Error loading camera config: {e}")
            return {}

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec())
