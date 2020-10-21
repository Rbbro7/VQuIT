# Multiprocessing
from multiprocessing import Process, Queue, Lock, Value


class Helpers:
    helpers = []
    pendingReturns = 0

    Main_Process = None  # POSSIBLY TEMPORARY

    # Function runs when initializing class
    def __init__(self):
        # Retrieve settings from configuration file
        from vquit import Configuration
        Config_module = Configuration()

        self.helperTimeout = Config_module.Get("ImageProcessing")["HelperTimeout"]
        self.n_cameras = Config_module.Get("QuickSettings")["ActiveCameras"]

        ##################################################
        # Create objects for communication with children #
        ##################################################
        # Queue: Used to distribute to/combine from multiple processes
        # Value: Used for sharing a value between processes
        # Lock: Used for uninterruptible communication with children

        self.guiProgressbar_Vars = (Lock(), Value('i', 0))  # Used for communicating with GUI progressbar
        self.guiImagePreviewVars = (Lock(), Queue())  # Used to update GUI image preview

        self.terminate_Vars = (Lock(), Value('b', False))  # Used to terminate children
        self.imagesIn_Vars = (Lock(), Queue())  # Used for sending raw pictures to children
        self.dataOut_Vars = (Lock(), Queue())  # Used for retrieving processed pictures from children

    # Return values that are used for communication between UI and processes
    def GetGUI_Vars(self):
        return self.guiProgressbar_Vars, self.guiImagePreviewVars

    # Create child processes to offload parent
    def CreateProcessor(self, function):
        # Bind variables
        communication_Vars = (
            self.helperTimeout, self.guiProgressbar_Vars, self.imagesIn_Vars, self.dataOut_Vars, self.terminate_Vars)

        # Create child processes
        for _ in range(0, self.n_cameras):
            newHelper = Process(target=function, args=(communication_Vars,))
            self.helpers.append(newHelper)

    # Start main program (called before GUI)
    def CreateMain(self, function):
        # Bind variables
        communication_Vars = (self.SendImages, self.GetData, self.guiImagePreviewVars, self.terminate_Vars,)

        # Create process
        self.Main_Process = Process(target=function, args=(communication_Vars,))

    # Prevent data transfer from helpers until unlocked
    def Lock(self):
        (imagesInLock, _) = self.imagesIn_Vars
        (dataOutLock, _) = self.dataOut_Vars
        (terminateLock, _) = self.terminate_Vars

        imagesInLock.acquire()
        dataOutLock.acquire()
        terminateLock.acquire()

    # Revert Lock function
    def Unlock(self):
        [imagesInLock, _] = self.imagesIn_Vars
        [dataOutLock, _] = self.dataOut_Vars
        [terminateLock, _] = self.terminate_Vars

        imagesInLock.release()
        dataOutLock.release()
        terminateLock.release()

    # Start child processes
    def Start(self):
        # Start main process
        self.Main_Process.start()

        # Start image processors
        for helper in self.helpers:
            helper.start()

    # Insert all images in queue to children
    def SendImages(self, images):
        [imagesInLock, imagesIn] = self.imagesIn_Vars

        # Create data ID (used to sort asynchronous return values)
        dataID = 0
        for data in images:
            with imagesInLock:
                imagesIn.put([dataID, data])

            # Update expected returns from children
            self.pendingReturns += 1

            # Increment data ID
            dataID += 1
        print("Images sent to helpers...", end='\r')

    # Retrieve data from children
    def GetData(self):
        (terminateLock, terminate) = self.terminate_Vars
        (dataOutLock, dataOut) = self.dataOut_Vars

        print("Waiting for helpers...", end='\r')
        returnedData = []
        # Keep looking for returned data from children until all expected returns are received or until terminate is called
        terminationFlag = False
        while self.pendingReturns > 0 and not terminationFlag:
            # Reset image
            newData = None

            # Check for new image in queue
            with dataOutLock:
                if dataOut.empty() is False:
                    newData = dataOut.get()

            # Append result if available
            if newData is not None:
                returnedData.append(newData)

                # Update expected returns from children
                self.pendingReturns -= 1

            with terminateLock:
                terminationFlag = terminate.value

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
        (terminateLock, terminate) = self.terminate_Vars
        # Terminate children
        print("Terminating children...", end='\r')
        with terminateLock:
            terminate.value = True

        print("Waiting on main program to be terminated...", end='\r')
        # Prevent script from exiting before main program is finished
        self.Main_Process.join()

        print("Waiting on children to be terminated...", end='\r')
        for helper in self.helpers:
            # Prevent script from exiting before children are finished
            helper.join()

        print("Children properly terminated")
        return

    # Increase Progressbar in GUI
    def GUI_IncreaseProgressbar(self, increaseValue):
        (progressbarLock, progressbarValue) = self.guiProgressbar_Vars
        with progressbarLock:
            progressbarValue.value += increaseValue

    # Reset Progressbar in GUI to zero
    def GUI_ResetProgressbar(self):
        (progressbarLock, progressbarValue) = self.guiProgressbar_Vars
        with progressbarLock:
            progressbarValue.value = 0
