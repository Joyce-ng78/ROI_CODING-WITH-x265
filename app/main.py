import random
import pandas as pd
import sys
from PyQt5.QtWidgets import QWidget, QStackedLayout
from PyQt5.QtWidgets import QApplication
from config import OUTPUT_CSV
from utils.data_loader import load_image_triplets
from ui.HomeScreen import HomeScreen
from ui.RatingScreen import RatingScreen
from ui.FinalScreen import FinishScreen

class MOSController(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("MOS Evaluation Tool")
        # self.showFullScreen()

        self.stack = QStackedLayout()
        self.setLayout(self.stack)

        self.triplets = load_image_triplets()
        self.current_index = 0
        self.results = []

        self.home = HomeScreen(self.start, self.close)
        self.rating = RatingScreen(self.next_sample, self.finish)
        self.finish_screen = FinishScreen(self.return_home, self.close)

        self.stack.addWidget(self.home)
        self.stack.addWidget(self.rating)
        self.stack.addWidget(self.finish_screen)

    def start(self):
        self.showFullScreen()
        self.current_index = 0
        self.results = []
        self.show_sample()
        self.stack.setCurrentWidget(self.rating)

    def show_sample(self):
        if self.current_index >= len(self.triplets):
            self.finish()
            return

        triplet = list(self.triplets[self.current_index])
        labels = ["reference", "method1", "method2"]
        combined = list(zip(triplet, labels))
        random.shuffle(combined)

        self.current_display = combined

        width = int(self.width() * 0.3)
        paths = [combined[i][0] for i in range(3)]

        self.rating.set_images(paths, width)
        self.rating.update_progress(self.current_index + 1, len(self.triplets))

    def next_sample(self):
        scores = self.rating.get_scores()

        result = {}
        for i in range(3):
            label = self.current_display[i][1]
            result[label] = scores[i]

        result["index"] = self.current_index
        self.results.append(result)

        self.current_index += 1
        self.show_sample()

    def finish(self):
        df = pd.DataFrame(self.results)
        df.to_csv(OUTPUT_CSV, index=False)
        self.stack.setCurrentWidget(self.finish_screen)

    def return_home(self):
        self.stack.setCurrentWidget(self.home)
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MOSController()
    window.show()
    sys.exit(app.exec_())