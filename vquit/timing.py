# Timer class
class Timer:
    time = None
    tic = None  # Start time
    toc = None  # Stop time

    def ImportTime(self):
        if self.time is None:
            print("Importing time")
            import time
            self.time = time
        return self.time

    # Start timer
    def Start(self):
        time = self.ImportTime()
        self.tic = time.perf_counter()

    # Stop timer
    def Stop(self):
        time = self.ImportTime()
        self.toc = time.perf_counter()
        result = (self.toc - self.tic)
        return result
