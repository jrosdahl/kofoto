import time

class Timer:
    def __init__(self):
        self.reset()

    def reset(self):
        self.time = time.time()

    def get(self):
        return time.time() - self.time

    def getAndReset(self):
        t = time.time() - self.time
        self.reset()
        return t
