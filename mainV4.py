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
def mainProcess(communication_Vars):
    # Extract parameters
    (SendImages, GetImages, GUI_ResetProgressbar, GUI_IncreaseProgressbar, GUI_UpdatePreviewWindow,
     UpdateTerminationFlag, SetFinishedFlag) = communication_Vars

    # Import custom module to extract data from config file
    from vquit import Configuration
    Config = Configuration()

    # Start Raspberry
    from vquit import RaspberryPi
    IO = RaspberryPi(Config_module=Config)  # Communicate with Raspberry Pi over ethernet

    # Create timers to keep track of execution times
    from vquit import Timer
    FetchTimer = Timer()
    FXTimer = Timer()

    # Start image acquirers
    from vquit import ImageAcquirer
    IA = ImageAcquirer(Config_module=Config, Warnings_module=warnings)  # Used to retrieve data from the cameras
    IA.Start()  # Start image acquisition

    # Loop this process until termination is called
    terminationFlag = False
    terminationMessage = None
    while not terminationFlag:
        # Check for termination call
        terminationFlag = UpdateTerminationFlag()

        # Check thermal status of cameras
        if IA.thermalCondition() is "Critical":
            terminationFlag = True
            terminationMessage = "Critical camera temperatures"

        # Run normal loop
        if not terminationFlag:
            # Reset progressbar
            GUI_ResetProgressbar()

            # Fetch images
            FetchTimer.Start()
            fetchedImages = [IA.RequestFrame(iteration) for iteration in range(0, len(IA.GigE))]
            print("Fetch time: ", "{0:.3f}".format(FetchTimer.Stop()), "s")

            # Update progressbar
            GUI_IncreaseProgressbar(20)

            # Send images to helpers
            SendImages(fetchedImages)

            # Request processed images from helpers
            FXTimer.Start()
            processedImages = GetImages()
            print("Process time: ", "{0:.3f}".format(FXTimer.Stop()), "s")

            # Send image to GUI
            GUI_UpdatePreviewWindow(processedImages[0])

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
    GUI = Application(Helpers.GUI_GetVars(), Helpers.Start, Helpers.Terminated)

    # Show GUI window
    GUI.show()

    # Exit code on window exit
    sys.exit(APP.exec_())

else:
    print("Subprocess created")
