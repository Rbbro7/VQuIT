# Adimec VQuIT Software (Author: Robin Broeren)

# Print whenever a process is created
if __name__ is '__main__':
    print("Main process created")
else:
    print("Helper created")

#################
# ALL PROCESSES #
#################
#################
# ALL PROCESSES #
#################

from vquit import Image, ProductData, OpenCV, Timer

Image_SUB = Image()
ProductData_SUB = ProductData()
CV_SUB = OpenCV()
Timer_SUB = Timer()


# Image processing function run on children
def imageProcessing(communication_Vars, parameters):
    # Extract parameters
    (timeout, guiProgressbar_Vars, imagesIn_Vars, imagesOut_Vars, terminate_Vars) = communication_Vars

    (progressbarLock, progressbarValue) = guiProgressbar_Vars
    (imagesInLock, imagesIn) = imagesIn_Vars
    (imagesOutLock, imagesOut) = imagesOut_Vars
    (terminateLock, terminate) = terminate_Vars

    [ccValues] = parameters

    # Start idle timer
    Timer_SUB.Start()

    # Loop this process until abort is called
    while True:
        # Reset image
        image = None

        # Check for new image
        with imagesInLock:
            if imagesIn.empty() is False:
                [dataID, image] = imagesIn.get()

        # Process new image if found
        if image is not None:
            # Preprocessing
            cc = Image_SUB.NoiseReduction(Image_SUB.ColorCorrection(image, ccValues[dataID]))
            gray = Image_SUB.Gray(cc)
            grayBlur = Image_SUB.Blur(gray)

            # Get product data
            # [acode, sn] = ProductData_SUB.GetDataMatrixInfo(grayBlur)
            # if acode is not False:
            #     print("Camera ", dataID, " : Acode", acode, "& S/N", sn)

            # Perform image analysis
            outputImage = CV_SUB.EdgeDetection(grayBlur)

            # Send processed image to parent
            with imagesOutLock:
                imagesOut.put([dataID, outputImage])

            # Increment progressbar in GUI
            with progressbarLock:
                progressbarValue.value += 1

            # Reset idle timer
            Timer_SUB.Start()

        # Terminate child if idle time too long
        idleTime = Timer_SUB.Stop()
        if idleTime > timeout:
            print("Terminating child... (timeout reached)")
            return

        # Check for termination call
        with terminateLock:
            if terminate.value is True:
                print("Terminating child...")
                return


# Everything outside this if statement will run for every process due to the lack of fork() when creating child processes in Windows
if __name__ == '__main__':
    #######################
    # MAIN PROCESS ONLY!! #
    #######################
    #######################
    # MAIN PROCESS ONLY!! #
    #######################

    ###########
    # Imports #
    ###########

    # Import custom packages
    import vquit

    # Image processing
    import cv2

    # Misc
    import ctypes
    import warnings


    ###########
    # Classes #
    ###########

    # System settings
    class System:
        # Start software
        print("\nStarting VQuIT Software", end='\r')

        # configure scaling based on monitors
        def ConfigScaling(self, imageAcquirer):
            # get screen size
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            [screenWidth, screenHeight] = [user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)]
            print('SYSTEM: screenSize = {0:d}x{1:d}'.format(screenWidth, screenHeight))

            # Screen size parameters
            self.imgH = (screenHeight / 3) - 10
            self.imgH_px = int(self.imgH)
            self.imgW_px = int(self.imgH_px * (4096 / 3008))

            # get camera image size
            imageHeight = imageAcquirer.remote_device.node_map.Height.value
            imageWidth = imageAcquirer.remote_device.node_map.Width.value
            print('CAMERA: image size = {0:d}x{1:d}'.format(imageWidth, imageHeight))

            # calculate scale factor
            HScale = screenHeight / 2 / imageHeight
            WScale = screenWidth / 2 / imageWidth

            # determine which scale to use
            if HScale <= WScale:
                self.imgScale = HScale
            elif WScale <= HScale:
                self.imgScale = WScale
            else:
                self.imgScale = 1
            print('SYSTEM: imgScale =', "{0:.3f}".format(self.imgScale), "\n")

        # Variables
        # Screen size parameters
        imgH = imgH_px = imgW_px = 0
        imgScale = 0

        # Check abort key & camera conditions
        @staticmethod
        def Abort():
            if CV.Abort():
                return True
            elif IA.thermalCondition() is "Critical":
                return True
            return False

        # Change formatting of warnings
        @staticmethod
        def CustomFormatWarning(msg, *args, **kwargs):
            # ignore everything except the message
            return "\n\nWarning: " + str(msg) + '\n\n'


    System = System()  # General system settings
    warnings.formatwarning = vquit.WarningFormat.SetCustom  # Set custom warning format

    # Start classes from custom package
    Config = vquit.Configuration()  # Extracts data from config file
    ProductData = vquit.ProductData()  # Used to extract product data from images
    IA = vquit.ImageAcquirer(Config_module=Config, Warnings_module=warnings)  # Used to retrieve data from the cameras
    IO = vquit.RaspberryPi(Config_module=Config)  # Communicate with Raspberry Pi over ethernet
    Image = vquit.Image()  # Used for image processing
    CV = vquit.OpenCV()  # Uses OpenCV to analyze images
    Helpers = vquit.Helpers(Config_module=Config)  # Used to create parallel processes that help with image processing

    # Timers to keep track of execution durations
    FetchTimer = vquit.Timer()
    FXTimer = vquit.Timer()

    #########
    # SETUP #
    #########

    System.ConfigScaling(IA.GigE[0])  # configure scaling based on monitors

    # Init other variables used in main loop
    quickSettings = Config.Get("QuickSettings")  # Get configuration data
    imgPlots = quickSettings["ImagePlots"]  # 0 = no plots
    compact = quickSettings["ReducedImageDetection"]  # 1 = less filters & plots

    # Color correction values
    ccTable = []
    ccData = Config.Get("Cameras")["Advanced"]
    for i in range(0, Config.Get("QuickSettings")["ActiveCameras"]):
        ccTable.append([ccData[i]["ColorCorrection"]["Red"],
                        ccData[i]["ColorCorrection"]["Green"],
                        ccData[i]["ColorCorrection"]["Blue"]])

    # Create helper processes to offload parent process
    Helpers.Create(imageProcessing, [ccTable], len(IA.GigE))  # Create a helper for each camera

    # Main code loop trigger
    input("Press ENTER to start...\n")

    IA.Start()  # Start image acquisition
    Helpers.Start()  # Start helper processes
    run = True
    while run:
        ###################
        # START MAIN LOOP #
        ###################

        Helpers.Lock()
        # Request frame from all connected cameras ans store them in imgsIn
        FetchTimer.Start()
        fetchedImages = [IA.RequestFrame(iteration) for iteration in range(0, len(IA.GigE))]
        print("Fetch time: ", "{0:.3f}".format(FetchTimer.Stop()), "s")

        # Send data to helpers
        Helpers.Unlock()
        FXTimer.Start()
        Helpers.SendImages(fetchedImages)

        # Retrieve data from helpers
        processedImages = Helpers.GetData()
        print("Process time: ", "{0:.3f}".format(FXTimer.Stop()), "s")

        # Show result of first image
        try:
            showImage = Image.Scale(processedImages[0], newHeight=301, newWidth=410)
            cv2.imshow("Test", showImage)
        except:
            print("Could not preview image")
            pass

        #################
        # END MAIN LOOP #
        #################

        # Check abort parameters
        run = not System.Abort()

    ################
    # System reset #
    ################

    # Terminate image acquirers
    IA.Stop()
    IA.Destroy()
    IA.Reset()

    # Disconnect Raspberry
    IO.Disconnect()

    # Terminate Helpers
    if Helpers.Terminated() is True:
        # Exit script
        exit()

else:
    ##########################
    # CHILD PROCESSES ONLY!! #
    ##########################
    ##########################
    # CHILD PROCESSES ONLY!! #
    ##########################

    pass

#################
# ALL PROCESSES #
#################
#################
# ALL PROCESSES #
#################
