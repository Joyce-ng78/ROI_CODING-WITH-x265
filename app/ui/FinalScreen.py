from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class FinishScreen(QWidget):

    def __init__(self, home_callback, exit_callback):
        super().__init__()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Session Finished")
        title.setFont(QFont("Arial", 40))
        title.setAlignment(Qt.AlignCenter)

        thank = QLabel("Thanks!")
        thank.setFont(QFont("Arial", 40))
        thank.setAlignment(Qt.AlignCenter)

        home_btn = QPushButton("Return Home")
        home_btn.setFont(QFont("Arial", 20))
        home_btn.clicked.connect(home_callback)
        
        exit_home_btn = QPushButton("Exit")
        exit_home_btn.setFont(QFont("Arial", 20))
        exit_home_btn.clicked.connect(exit_callback)
        
        home_btn.setMinimumWidth(300)
        exit_home_btn.setMinimumWidth(300)
        
        layout.addWidget(title)
        layout.addWidget(thank)
        layout.addSpacing(40)
        layout.addWidget(home_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(exit_home_btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)