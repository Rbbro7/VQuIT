# Multiprocessing
from multiprocessing import Process, Queue, Lock, Value


class Helpers:
    # Variables
    imagesIn = None
    dataOut = None
    terminate = None

    imagesInLock = None
    dataOutLock = None
    terminateLock = None

    helpers = []
    pendingReturns = 0

    # Function runs when initializing class
    def __init__(self, Config_module=None):
        # Retrieve settings from configuration file
        self.helperTimeout = Config_module.Get("ImageProcessing")["HelperTimeout"]

    # Create child processes to offload parent
    def Create(self, function, data, n_helpers):
        # Create queues for communication with children
        self.imagesIn = Queue()  # Used for sending raw pictures to children
        self.dataOut = Queue()  # Used for retrieving processed pictures from children
        self.terminate = Value('b', False)  # Used to terminate children

        # Create locks for uninterruptible communication with children
        self.imagesInLock = Lock()
        self.dataOutLock = Lock()
        self.terminateLock = Lock()

        # Create child processes
        for _ in range(0, n_helpers):
            newHelper = Process(target=function, args=(
                self.helperTimeout, self.imagesIn, self.dataOut, self.imagesInLock, self.dataOutLock, self.terminate,
                self.terminateLock, data,))
            self.helpers.append(newHelper)

    # Prevent data transfer from helpers until unlocked
    def Lock(self):
        self.imagesInLock.acquire()
        self.dataOutLock.acquire()
        self.terminateLock.acquire()

    # Revert Lock function
    def Unlock(self):
        self.imagesInLock.release()
        self.dataOutLock.release()
        self.terminateLock.release()

    # Start child processes
    def Start(self):
        for helper in self.helpers:
            helper.start()

    # Insert all images in queue to children
    def SendImages(self, images):
        # Create data ID (used to sort asynchronous return values)
        dataID = 0
        for data in images:
            with self.imagesInLock:
                self.imagesIn.put([dataID, data])

            # Update expected returns from children
            self.pendingReturns += 1

            # Increment data ID
            dataID += 1
        print("Images sent to helpers...", end='\r')

    # Retrieve data from children
    def GetData(self):
        print("Waiting for helpers...", end='\r')
        returnedData = []
        # Keep looking for returned data from children until all expected returns are received
        while self.pendingReturns > 0:
            # Reset image
            newData = None

            # Check for new image in queue
            with self.dataOutLock:
                if self.dataOut.empty() is False:
                    newData = self.dataOut.get()

            # Append result if available
            if newData is not None:
                returnedData.append(newData)

                # Update expected returns from children
                self.pendingReturns -= 1

        print("Processing incoming data from helpers...", end='\r')

        # Sort returned data by dataID
        returnedData = sorted(returnedData, key=lambda x: x[0])

        # Disregard dataID
        for dataID in returnedData:
            del dataID[0]

        # Extract images
        returnedImages = [image[0] for image in returnedData]
        return returnedImages

    # Terminate children
    def Terminated(self):
        # Terminate children
        print("Terminating children...", end='\r')
        with self.terminateLock:
            self.terminate.value = True

        print("Waiting on children to be terminated...", end='\r')
        for helper in self.helpers:
            # Prevent script from exiting before children are finished
            helper.join()

        print("Children properly terminated")
        return True
