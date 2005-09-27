"""Implementation of the Timer class."""

import time

class Timer:
    """A class for measuring a time interval."""

    def __init__(self):
        self.__time = None
        self.reset()

    def reset(self):
        """Reset the timer."""
        self.__time = time.time()

    def get(self):
        """Get the number of seconds since the timer was last reset (or
        created)."""
        return time.time() - self.__time

    def getAndReset(self):
        """Get the number of seconds since the timer was last reset (or
        created) and then reset the timer."""
        t = time.time() - self.__time
        self.reset()
        return t
