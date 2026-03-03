import os
import random
from config import PATH1, PATH2, PATH3, MAX_SAMPLES

def load_image_triplets():

    files = sorted(os.listdir(PATH1))
    triplets = []

    for f in files:
        p1 = os.path.join(PATH1, f)
        p2 = os.path.join(PATH2, f)
        p3 = os.path.join(PATH3, f)

        if os.path.exists(p1) and os.path.exists(p2) and os.path.exists(p3):
            triplets.append((p1, p2, p3))

    random.shuffle(triplets)

    return triplets[:MAX_SAMPLES]