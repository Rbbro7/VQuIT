# Multiprocessing
from multiprocessing import Process, Queue, Lock, Value, Array


class Helpers:
    analysisHelpers = []  # Object to store all analyze helpers
    idleAnalysisHelpers = 0  # Number of idle analysis helpers
    pendingReturns = 0

    Main_Process = None

    # Communication objects that need to be reset per run
    idleAnalysisHelpers_Vars = None  # Check number of idle analysis helpers
    terminate_Vars = None  # Terminate main program
    mainProcessFinished_Vars = None  # Terminate children

    # Function runs when initializing class
    def __init__(self, mainProcess, analysisProcess):
        # Retrieve settings from configuration file
        from vquit import Configuration
        Config_module = Configuration()

        self.helperTimeout = Config_module.Get("ImageProcessing")["HelperTimeout"]
        self.n_cameras = Config_module.Get("QuickSettings")["ActiveCameras"]

        self.mainProcess = mainProcess  # Function which is run by analysis helpers
        self.analysisProcess = analysisProcess  # Function which is run by analysis helpers

        ##################################################
        # Create objects for communication with children #
        ##################################################
        # Queue: Used to distribute to/combine from multiple processes
        # Value: Used for sharing a value between processes
        # Lock: Used for uninterruptible communication with children

        self.guiProgressbar_Vars = (Lock(), Value('i', 0))  # Used for communicating with GUI progressbar
        self.guiPreviewWindow_Vars = (Lock(), Queue())  # Used to update GUI image preview
        self.toolState_Vars = (Lock(), Value('i', 0))  # Number of product scans left in batch
        self.productID_Vars = (Lock(), Array('i', [0, 0]))  # Used to retrieve product data from GUI

        self.imagesIn_Vars = (Lock(), Queue())  # Send raw pictures to children
        self.dataOut_Vars = (Lock(), Queue())  # Retrieve processed pictures from children

    ############################
    # Graphical User Interface #
    ############################

    # Return values that are used for communication between UI and processes
    def GUI_GetVars(self):
        return self.toolState_Vars, self.guiProgressbar_Vars, self.guiPreviewWindow_Vars

    # Return functions that control the script execution via the GUI
    def GUI_GetFunc(self):
        functions = (self.Start, self.Terminated, self.SetProductID)
        return functions

    # Sent new image to GUI's preview window
    def GUI_UpdatePreviewWindow(self, image):
        (lock, queue) = self.guiPreviewWindow_Vars
        with lock:
            queue.put(image)

    # Increase Progressbar in GUI
    def GUI_IncreaseProgressbar(self, increaseValue):
        (lock, variable) = self.guiProgressbar_Vars
        with lock:
            variable.value += increaseValue

    # Reset Progressbar in GUI to zero
    def GUI_ResetProgressbar(self):
        (lock, variable) = self.guiProgressbar_Vars
        with lock:
            variable.value = 0

    # Communicate tool state between main process and GUI
    def ToolState(self, value):
        (lock, variable) = self.toolState_Vars
        with lock:
            variable.value = value

    ###################
    # AnalysisHelpers #
    ###################

    # Increase (or decrease with negative number) number of idle helpers
    def SetIdleAnalysisHelpers(self, addValue):
        (lock, variable) = self.idleAnalysisHelpers_Vars
        with lock:
            variable.value += addValue

    # Get number of idle helpers
    def GetIdleAnalysisHelpers(self):
        (lock, variable) = self.idleAnalysisHelpers_Vars
        with lock:
            idleHelpers = variable.value
        return idleHelpers

    # Check for idle helpers and create if not available
    def RequestAnalysisHelper(self, n_helpers):
        # Calculate number of new helpers to be created
        newHelpers = n_helpers - self.GetIdleAnalysisHelpers()
        if newHelpers > 0:
            # Create new helpers
            self.CreateAnalysisHelper(newHelpers)

    # Create helper processes for analyzing images
    def CreateAnalysisHelper(self, n_helpers):
        # Bind variables
        communication_Vars = (
            self.CheckTimeout, self.GUI_IncreaseProgressbar, self.imagesIn_Vars, self.SendProcessedData,
            self.SetIdleAnalysisHelpers, self.GetFinishedFlag)

        print("Creating " + str(n_helpers) + " new analysis helpers")

        # Create child processes
        for _ in range(0, n_helpers):
            newHelper = Process(target=self.analysisProcess, args=(communication_Vars,))
            newHelper.start()
            self.analysisHelpers.append(newHelper)

    # Send processed image to main process
    def SendProcessedData(self, dataID, outputImage):
        (lock, queue) = self.dataOut_Vars

        with lock:
            queue.put([dataID, outputImage])

    # Check if main process is finished
    def GetFinishedFlag(self):
        (lock, variable) = self.mainProcessFinished_Vars
        with lock:
            updatedFlag = variable.value
        return updatedFlag

    # Check analysis helpers for timeout
    def CheckTimeout(self, idleTime):
        if idleTime > self.helperTimeout:
            return True
        else:
            return False

    ################
    # Main Process #
    ################

    # Start main program
    def CreateMain(self):
        # Bind variables
        communication_Vars = (
            self.SendRawImages, self.GetProcessedData, self.GetProductID, self.UpdateToolState,
            self.GUI_ResetProgressbar,
            self.GUI_IncreaseProgressbar, self.GUI_UpdatePreviewWindow, self.UpdateTerminationFlag,
            self.SetFinishedFlag)

        # Create process
        self.Main_Process = Process(target=self.mainProcess, args=(communication_Vars,))

    # Start main process
    def Start(self):
        # Reset variable that could exist from previous runs
        self.ResetMain()

        # Create main process
        self.CreateMain()

        # Start main process
        self.Main_Process.start()

    # Reset parameters if the code has been run before
    def ResetMain(self):
        # self.GUI_SetBatchSizeRemaining(batchSize)
        self.idleAnalysisHelpers_Vars = (Lock(), Value('i', 0))  # Reset number of idle analysis helpers
        self.terminate_Vars = (Lock(), Value('i', 0))  # Terminate main program
        self.mainProcessFinished_Vars = (Lock(), Value('b', False))  # Terminate children

    # Update tool state
    def UpdateToolState(self, setState=None):

        (lock, variable) = self.toolState_Vars
        if setState is not None:
            # Set new state
            with lock:
                variable.value = setState
        else:
            # Request current state
            with lock:
                updatedState = variable.value
            return updatedState

    # Check for termination call on main process
    def UpdateTerminationFlag(self):
        (lock, variable) = self.terminate_Vars
        with lock:
            updatedFlag = variable.value
        return updatedFlag

    # Set finished flag
    def SetFinishedFlag(self):
        # Terminate subprocess
        print("Terminating subprocess...", end='\r')

        (lock, variable) = self.mainProcessFinished_Vars
        with lock:
            variable.value = True

    # Insert all images in queue to children
    def SendRawImages(self, images):
        (lock, queue) = self.imagesIn_Vars

        # Request an idle helper per image
        self.RequestAnalysisHelper(len(images))

        # Create data ID (used to sort asynchronous return values)
        dataID = 0
        for data in images:
            with lock:
                queue.put([dataID, data])

            # Update expected returns from children
            self.pendingReturns += 1

            # Increment data ID
            dataID += 1
        print("Images sent to helpers...", end='\r')

    def GetProductID(self):
        (lock, array) = self.productID_Vars
        with lock:
            arrayData = array
        return arrayData

    def SetProductID(self, acode, sn):
        (lock, array) = self.productID_Vars
        with lock:
            array[0] = int(acode)
            array[1] = int(sn)

    # Retrieve data from children
    def GetProcessedData(self):
        (lock, queue) = self.dataOut_Vars

        print("Waiting for helpers...", end='\r')
        returnedData = []
        # Keep looking for returned data from children until all expected returns are received or until terminate is called
        while self.pendingReturns > 0:
            # Reset image
            newData = None

            # Check for new image in queue
            with lock:
                if queue.empty() is False:
                    newData = queue.get()

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
    def Terminated(self, terminateMode):
        # Convert abort mode from GUI to terminator mode
        if terminateMode == 0:
            terminateMode = 1
        else:
            terminateMode = 2

        (mainLock, mainVariable) = self.terminate_Vars

        # Terminate main process
        print("Terminating main process...", end='\r')
        with mainLock:
            mainVariable.value = terminateMode

        print("Waiting on main program to be terminated...", end='\r')

        # Don't call join function before before the process is finished (prevent freeze)
        while self.Main_Process.is_alive() is True:
            pass

        # Prevent script from exiting before main process is finished
        self.Main_Process.join()

        print("Waiting on subprocess to be terminated...", end='\r')
        # Prevent script from exiting before subVariable is finished
        for helper in self.analysisHelpers:
            # Prevent script from exiting before children are finished
            helper.join()

        print("Processes properly terminated")
        return
