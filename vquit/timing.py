# Timer class
class Timer:
    time = None
    __tic = None  # Start time
    __toc = None  # Stop time

    def Setup(self):
        print("Importing time")
        import time
        self.time = time

    # Start timer
    def Start(self):
        # Import time module if not available
        if self.time is None:
            self.Setup()
        self.__tic = self.time.perf_counter()

    # Stop timer
    def Stop(self):
        self.__toc = self.time.perf_counter()
        result = self.__toc - self.__tic
        return result
