from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

class ImageRatingWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)

        self.score_group = QButtonGroup(self)

        score_layout = QHBoxLayout()
        score_layout.setAlignment(Qt.AlignCenter)

        self.buttons = []

        for i in range(1, 6):
            btn = QRadioButton(str(i))
            btn.setFont(QFont("Arial", 16))
            self.score_group.addButton(btn, i)
            score_layout.addWidget(btn)
            self.buttons.append(btn)

        self.layout.addLayout(score_layout)

    def set_image(self, path, target_width):
        pixmap = QPixmap(path)
        scaled = pixmap.scaledToWidth(target_width, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.reset_score()

    def get_score(self):
        return self.score_group.checkedId()

    def reset_score(self):
        for btn in self.buttons:
            btn.setChecked(False)