# Adimec VQuIT Software (Author: Robin Broeren)


#################
# ALL PROCESSES #
#################
#################
# ALL PROCESSES #
#################

from vquit import WarningFormat
import warnings

# Set custom warning format
warnings.formatwarning = WarningFormat.SetCustom


# Get images from cameras
def mainProcess(batchSize, communication_Vars):
    # Extract parameters
    (SendImages, GetImages, GUI_SetBatchSizeRemaining, GUI_ResetProgressbar, GUI_IncreaseProgressbar,
     GUI_UpdatePreviewWindow,
     UpdateTerminationFlag, SetFinishedFlag) = communication_Vars

    # Import custom module to extract data from config file
    from vquit import Configuration
    Config = Configuration()

    # Start Raspberry
    from vquit import RaspberryPi
    IO = RaspberryPi(Config_module=Config)  # Communicate with Raspberry Pi over ethernet

    # TEMPP
    from vquit import OpenCV
    CV = OpenCV()

    # Create timers to keep track of execution times
    from vquit import Timer
    FetchTimer = Timer()
    FXTimer = Timer()
    LoopTimer = Timer()

    # Start image acquirers
    from vquit import ImageAcquirer
    IA = ImageAcquirer(IO.SetCameraLighting, Config_module=Config,
                       Warnings_module=warnings)  # Used to retrieve data from the cameras
    IA.Start()  # Start image acquisition

    # Import image processing class
    from vquit import Image
    Image = Image()

    # Loop this process until termination is called or batch is finished
    terminationFlag = False
    terminationMessage = None

    remainingScans = batchSize
    while not terminationFlag:
        # Update termination flag
        if remainingScans <= 0:
            # Check if batch is complete
            terminationFlag = True
            terminationMessage = "Batch complete"
        else:
            # Check GUI from termination call
            terminationFlag = UpdateTerminationFlag()

            # Check thermal status of cameras
            if IA.thermalCondition() is "Critical":
                terminationFlag = True
                terminationMessage = "Critical camera temperatures"

        # Run normal loop
        if not terminationFlag:
            LoopTimer.Start()
            # Reset progressbar
            GUI_ResetProgressbar()

            # EXPERIMENTAL DYNAMIC ROI SIMULATION
            #
            # from random import randint
            #
            # # Change ROI for scanned product
            # xArr = [3000, 2000, 1000, 512, 2500, 2000, 1500, 1000, 512, 3000, 2000, 512, 1000, 2000]
            # yArr = [3000, 2000, 1000, 512, 2000, 2000, 2000, 2000, 2000, 1000, 1000, 1000, 512, 512]
            #
            # pos = randint(0, len(xArr)-1)
            #
            # height = xArr[pos]
            # width = yArr[pos]
            # print(height, width)
            #
            # > height = 2500
            # > width = 2500
            # > IA.SetROI(height, width, disableAcquisition=True)

            # Fetch images
            FetchTimer.Start()
            IO.KickstartLights()
            fetchedImages = [IA.RequestFrame(iteration) for iteration in range(0, len(IA.GigE))]
            print("Fetch time: ", "{0:.3f}".format(FetchTimer.Stop()), "s")

            # print(len(fetchedImages[0]), len(fetchedImages[0][0]))  # Temporary (shows actual ROI)

            # Set lights in idle mode
            IO.IdleLights()

            # Send original images to GUI
            fetchedGrid = Image.Grid(fetchedImages)
            GUI_UpdatePreviewWindow(fetchedGrid)

            # Update progressbar
            GUI_IncreaseProgressbar(20)

            # Send images to helpers
            SendImages(fetchedImages)

            # Request processed images from helpers
            FXTimer.Start()
            processedImages = GetImages()
            print("Process time: ", "{0:.3f}".format(FXTimer.Stop()), "s")

            # Decrease remaining scans to one (currently being phased out in favor of continuous scanning)
            # <<remainingScans -= 1
            # <<GUI_SetBatchSizeRemaining(remainingScans)

            # Send image to GUI
            processedGrid = Image.Grid(processedImages)
            GUI_UpdatePreviewWindow(processedGrid)

            #################################
            # Temporary requirement testing #
            #################################

            loopTime = LoopTimer.Stop()
            loopTime = round(loopTime, 2)

            c = Config.Get("Cameras")
            acquisition = c["Generic"]["AcquisitionControl"]
            cameraInfo = c["Advanced"]

            exposureTime = acquisition["ExposureTime"]["Value"]
            gain = cameraInfo[0]["Gain"]["Value"]
            blackLevel = cameraInfo[0]["BlackLevel"]["Value"]

            # Color correction values
            ccTable = []
            ccData = Config.Get("Cameras")["Advanced"]
            for i in range(0, Config.Get("QuickSettings")["ActiveCameras"]):
                ccTable.append([ccData[i]["ColorCorrection"]["Red"],
                                ccData[i]["ColorCorrection"]["Green"],
                                ccData[i]["ColorCorrection"]["Blue"]])

            lightingConfigUp = Config.Get("Lighting")["PWM_value"]["TopCamera"]["U"]
            lightingConfigDown = Config.Get("Lighting")["PWM_value"]["TopCamera"]["D"]

            title = "CameraEGB(" + str(exposureTime) + "," + str(gain) + "," + str(blackLevel) + ").Lighting(" + str(
                lightingConfigUp) + str(lightingConfigDown) + ").CC(" + str(ccTable[0]) + ").Time(" + str(
                loopTime) + ")."

            # Save images to png
            CV.SaveAsPNG((str(title) + "Original"), fetchedGrid)
            CV.SaveAsPNG((str(title) + "Processed"), processedGrid)

        # Run exit code
        else:
            if terminationMessage is None:
                terminationMessage = "User abort request"
            print("Terminating main process...(" + str(terminationMessage) + ")")

            # Terminate image acquirers
            IA.Stop()
            IA.Destroy()
            IA.Reset()

            # Disconnect Raspberry
            IO.Disconnect()

            # Let other progresses know the main process is finished
            SetFinishedFlag()


# Image processing function run on children
def analysisProcess(communication_Vars):
    from vquit import Configuration, Image, ProductData, OpenCV

    # Extract data from config file
    Config = Configuration()

    # Perform actions on images
    Image = Image()

    # Extract product data from images
    ProductData = ProductData()

    # Perform image analysis
    CV = OpenCV()

    # Extract parameters
    (CheckTimeout, GUI_IncreaseProgressbar, imagesIn_Vars, SendProcessedData, SetIdleAnalysisHelpers,
     UpdateTerminationFlag) = communication_Vars
    (imagesInLock, imagesIn) = imagesIn_Vars

    # Color correction values
    ccTable = []
    ccData = Config.Get("Cameras")["Advanced"]
    for i in range(0, Config.Get("QuickSettings")["ActiveCameras"]):
        ccTable.append([ccData[i]["ColorCorrection"]["Red"],
                        ccData[i]["ColorCorrection"]["Green"],
                        ccData[i]["ColorCorrection"]["Blue"]])

    # Start idle timer
    from vquit import Timer
    IdleTimer = Timer()
    IdleTimer.Start()

    # Loop this process until termination is called
    terminationFlag = False
    terminationMessage = None
    SetIdleAnalysisHelpers(1)  # Increase available helpers by 1
    while not terminationFlag:
        # Check for termination call
        terminationFlag = UpdateTerminationFlag()

        # Check for timeout
        if CheckTimeout(IdleTimer.Stop()) is True:
            terminationFlag = True
            terminationMessage = "Timeout reached"

        # Run normal loop
        if not terminationFlag:
            # Reset image
            image = None

            # Check for new image
            with imagesInLock:
                if imagesIn.empty() is False:
                    [dataID, image] = imagesIn.get()

            # Process new image if found
            if image is not None:
                # Decrease available helpers by 1
                SetIdleAnalysisHelpers(-1)

                # Preprocessing
                cc = Image.NoiseReduction(Image.ColorCorrection(image, ccTable[dataID]))
                gray = Image.Gray(cc)
                grayBlur = Image.Blur(gray)

                GUI_IncreaseProgressbar(5)  # Increment progressbar in GUI

                # Get product data
                # [acode, sn] = ProductData.GetDataMatrixInfo(grayBlur)
                # if acode is not False:
                #     print("Camera ", dataID, " : Acode", acode, "& S/N", sn)

                # Perform image analysis
                analyzedImage = CV.EdgeDetection(grayBlur)

                GUI_IncreaseProgressbar(5)  # Increment progressbar in GUI

                # Convert result to RGB
                outputImage = Image.GraytoRGB(analyzedImage)

                # Send processed image to parent
                SendProcessedData(dataID, outputImage)

                GUI_IncreaseProgressbar(5)  # Increment progressbar in GUI

                # Reset idle timer
                IdleTimer.Start()

                # Increase available helpers by 1
                SetIdleAnalysisHelpers(1)

        # Run exit code
        else:
            # Decrease available helpers by 1
            SetIdleAnalysisHelpers(-1)

            if terminationMessage is None:
                terminationMessage = "Main process finished"
            print("Terminating child...(" + str(terminationMessage + ")"))


# Everything outside this if statement will run for every process due to the lack of fork() when creating child processes in Windows
if __name__ == '__main__':
    print("Main process created")
    print("\nStarting VQuIT Software", end='\r')

    #######################
    # MAIN PROCESS ONLY!! #
    #######################
    #######################
    # MAIN PROCESS ONLY!! #
    #######################

    # Import GUI module
    from PyQt5.QtWidgets import QApplication

    # Import custom packages
    from vquit import Application, Helpers

    # Misc
    import sys

    # Start helper class instance
    Helpers = Helpers(mainProcess, analysisProcess)

    # Init user interface packages
    APP = QApplication(sys.argv)  # Pass commandline parameters to app
    GUI = Application(Helpers.GUI_GetVars(), Helpers.GUI_GetFunc())

    # Show GUI window
    GUI.show()

    # Exit code on window exit
    sys.exit(APP.exec_())

else:
    print("Subprocess created")
