from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class HomeScreen(QWidget):

    def __init__(self, start_callback, exit_callback):
        super().__init__()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("MOS Image Quality Evaluation Tool")
        title.setFont(QFont("Arial", 40))
        title.setAlignment(Qt.AlignCenter)

        start_btn = QPushButton("Start")
        start_btn.setFont(QFont("Arial", 20))
        start_btn.clicked.connect(start_callback)

        exit_btn = QPushButton("Exit")
        exit_btn.setFont(QFont("Arial", 20))
        exit_btn.clicked.connect(exit_callback)
        start_btn.setMinimumWidth(150)
        exit_btn.setMinimumWidth(150)

        layout.addWidget(title)
        layout.addSpacing(40)
        layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(exit_btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)