# Adimec VQuIT Software (Author: Robin Broeren)


#################
# ALL PROCESSES #
#################
#################
# ALL PROCESSES #
#################

from vquit import Timer
import warnings as warnings_SUB
from time import sleep

Timer = Timer()


# Get images from cameras
def mainProgram(communication_Vars):
    # Extract parameters
    (SendImages, GetData, guiImagePreviewVars, terminate_Vars) = communication_Vars
    (imgPreviewLock, imgPreviewQue) = guiImagePreviewVars
    (terminateLock, terminate) = terminate_Vars

    # Import custom module to extract data from config file
    from vquit import Configuration
    Config = Configuration()

    # Start Raspberry
    from vquit import RaspberryPi
    IO = RaspberryPi(Config_module=Config)  # Communicate with Raspberry Pi over ethernet

    # Start image acquirers
    from vquit import ImageAcquirer
    IA = ImageAcquirer(Config_module=Config,
                       Warnings_module=warnings_SUB)  # Used to retrieve data from the cameras
    IA.Start()  # Start image acquisition

    # Loop this process until termination is called
    terminationFlag = False
    while not terminationFlag:
        # Check for termination call
        with terminateLock:
            terminationFlag = terminate.value

        # Run normal loop
        if not terminationFlag:

            # Fetch images
            fetchedImages = [IA.RequestFrame(iteration) for iteration in range(0, len(IA.GigE))]

            # Send images to helpers
            SendImages(fetchedImages)

            # Send image to GUI
            with imgPreviewLock:
                imgPreviewQue.put(fetchedImages[0])

            # Request processed images from helpers
            processedImages = GetData()

        # Run exit code
        else:
            print("Terminating main helper...")
            # Terminate image acquirers
            IA.Stop()
            IA.Destroy()
            IA.Reset()

            # Disconnect Raspberry
            IO.Disconnect()


# Image processing function run on children
def imageProcessing(communication_Vars):
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
    (timeout, guiProgressbar_Vars, imagesIn_Vars, imagesOut_Vars, terminate_Vars) = communication_Vars
    (progressbarLock, progressbarValue) = guiProgressbar_Vars
    (imagesInLock, imagesIn) = imagesIn_Vars
    (imagesOutLock, imagesOut) = imagesOut_Vars
    (terminateLock, terminate) = terminate_Vars

    # Color correction values
    ccTable = []
    ccData = Config.Get("Cameras")["Advanced"]
    for i in range(0, Config.Get("QuickSettings")["ActiveCameras"]):
        ccTable.append([ccData[i]["ColorCorrection"]["Red"],
                        ccData[i]["ColorCorrection"]["Green"],
                        ccData[i]["ColorCorrection"]["Blue"]])

    # Start idle timer
    Timer.Start()

    # Loop this process until termination is called
    terminationFlag = False
    terminationMessage = None
    while not terminationFlag:
        # Check for termination call
        with terminateLock:
            terminationFlag = terminate.value

        # Check for timeout
        idleTime = Timer.Stop()
        if idleTime > timeout:
            terminationFlag = True
            terminationMessage = "(timeout reached)"

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
                # Preprocessing
                # cc = Image.NoiseReduction(Image.ColorCorrection(image, ccTable[dataID]))
                # gray = Image.Gray(cc)
                # grayBlur = Image.Blur(gray)

                # Get product data
                # [acode, sn] = ProductData.GetDataMatrixInfo(grayBlur)
                # if acode is not False:
                #     print("Camera ", dataID, " : Acode", acode, "& S/N", sn)
                sleep(5)
                # Perform image analysis
                # outputImage = CV.EdgeDetection(grayBlur)
                outputImage = image

                # Send processed image to parent
                with imagesOutLock:
                    imagesOut.put([dataID, outputImage])

                # Increment progressbar in GUI
                with progressbarLock:
                    progressbarValue.value += 10

                # Reset idle timer
                Timer.Start()

        # Run exit code
        else:
            if terminationMessage is None:
                terminationMessage = "(user abort request)"
            print("Terminating child..." + str(terminationMessage))


# Everything outside this if statement will run for every process due to the lack of fork() when creating child processes in Windows
if __name__ == '__main__':
    print("Main process created")

    #######################
    # MAIN PROCESS ONLY!! #
    #######################
    #######################
    # MAIN PROCESS ONLY!! #
    #######################

    ###########
    # Imports #
    ###########

    # Import user interface module
    from PyQt5.QtWidgets import QApplication

    # Import custom packages
    import vquit

    # Misc
    import sys
    import warnings


    ###########
    # Classes #
    ###########

    # System settings
    class System:
        # Start software
        print("\nStarting VQuIT Software", end='\r')

        print("WARNING thermalCondition check does not work now")

        # Check abort key & camera conditions
        # @staticmethod
        # def Abort():
        #     if IA.thermalCondition() is "Critical":
        #     # return True
        #     return False

        # Change formatting of warnings
        @staticmethod
        def CustomFormatWarning(msg, *args, **kwargs):
            # ignore everything except the message
            return "\n\nWarning: " + str(msg) + '\n\n'


    System = System()  # General system settings
    warnings.formatwarning = vquit.WarningFormat.SetCustom  # Set custom warning format

    # Start helper class instance
    Helpers = vquit.Helpers()  # Used to create parallel processes that help with image processing

    # Init user interface packages
    APP = QApplication(sys.argv)  # Pass commandline parameters to app
    progressbar, imagePreview = Helpers.GetGUI_Vars()
    GUI = vquit.Application(progressbar, imagePreview, Helpers.Start, Helpers.Terminated)

    # Timers to keep track of execution durations
    FetchTimer = vquit.Timer()
    FXTimer = vquit.Timer()

    #########
    # SETUP #
    #########

    # Create helper processes
    Helpers.CreateMain(mainProgram)  # Create main process
    Helpers.CreateProcessor(imageProcessing)  # Create a process for each camera

    # Show GUI window
    GUI.show()

    # Exit code on window exit
    sys.exit(APP.exec_())

else:
    print("Helper created")
