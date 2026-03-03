from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QProgressBar, QLabel, QGridLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from ui.ImageRatingWidget import ImageRatingWidget

class RatingScreen(QWidget):

    def __init__(self, next_callback, finish_callback):
        super().__init__()
        self.showFullScreen()
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        # ========= TOP TITLE BAR =========
        title_layout = QGridLayout()

        self.title = QLabel("MOS Measurement Experiment")
        self.title.setFont(QFont("Arial", 40))
        self.title.setAlignment(Qt.AlignCenter)

        self.exit_btn = QPushButton("End Session")
        self.exit_btn.setFont(QFont("Arial", 16))
        self.exit_btn.clicked.connect(finish_callback)

        # 3 cột: trái - giữa - phải
        title_layout.addWidget(self.title, 0, 1, alignment=Qt.AlignCenter)
        title_layout.addWidget(self.exit_btn, 0, 2, alignment=Qt.AlignRight)

        # Set stretch cho 3 cột
        title_layout.setColumnStretch(0, 1)
        title_layout.setColumnStretch(1, 2)
        title_layout.setColumnStretch(2, 1)

        self.main_layout.addLayout(title_layout)
        self.main_layout.addStretch()
        
        # ========= TOP STATUS BAR =========
        top_layout = QHBoxLayout()
        # top_layout.setSpacing(20)

        # Progress Text
        self.progress_label = QLabel("Sample 0 / 0")
        self.progress_label.setFont(QFont("Arial", 16))
        self.progress_label.setAlignment(Qt.AlignLeft)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(300)
        self.progress_bar.setFont(QFont("Arial", 16))

        # Push everything left
        top_layout.addWidget(self.progress_label)
        top_layout.addWidget(self.progress_bar)

        top_layout.addStretch()

        # # End Button (right side)
        # self.exit_btn = QPushButton("End Session")
        # self.exit_btn.setFont(QFont("Arial", 16))
        # self.exit_btn.clicked.connect(finish_callback)

        # top_layout.addWidget(self.exit_btn)

        self.main_layout.addLayout(top_layout)

        # Images
        self.main_layout.addStretch()

        self.images_layout = QHBoxLayout()
        self.images_layout.setSpacing(40)
        self.images_layout.addStretch()

        self.widgets = [
            ImageRatingWidget(),
            ImageRatingWidget(),
            ImageRatingWidget()
        ]

        for w in self.widgets:
            self.images_layout.addWidget(w)
            self.images_layout.addStretch()

        self.main_layout.addLayout(self.images_layout)
        self.main_layout.addStretch()

        # Next button
        self.next_btn = QPushButton("Next")
        self.next_btn.setFont(QFont("Arial", 20))
        self.next_btn.clicked.connect(next_callback)

        self.main_layout.addWidget(self.next_btn, alignment=Qt.AlignCenter)
        self.main_layout.addStretch()

    def set_images(self, paths, width):
        for i in range(3):
            self.widgets[i].set_image(paths[i], int(self.width()*0.3))

    def get_scores(self):
        return [w.get_score() for w in self.widgets]
    
    def update_progress(self, current, total):
        self.progress_label.setText(f"Sample {current:2d} / {total}")
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)