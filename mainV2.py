# Adimec VQuIT Software (Author: Robin Broeren)


#################
# ALL PROCESSES #
#################
#################
# ALL PROCESSES #
#################


if __name__ is not '__main__':
    print("Subprocess created")

#################
# ALL PROCESSES #
#################
#################
# ALL PROCESSES #
#################

from vquit import Image, ProductData, OpenCV

Image_SUB = Image()
ProductData_SUB = ProductData()
CV_SUB = OpenCV()


def imageProcessing(iteration, image, ccValues):
    if image is not 0:
        # Preprocessing
        cc = Image_SUB.NoiseReduction(Image_SUB.ColorCorrection(image, ccValues))
        gray = Image_SUB.Gray(cc)
        grayBlur = Image_SUB.Blur(gray)

        # Get product data
        [acode, sn] = ProductData_SUB.GetDataMatrixInfo(grayBlur)
        if acode is not False:
            print("Camera ", iteration, " : Acode", acode, "& S/N", sn)

        # Perform image analysis
        output = CV_SUB.EdgeDetection(grayBlur)
        output = cc

        # queue.put([cc, grayBlur])
        return [iteration, output]
    else:
        return [iteration, False]


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

    # Multiprocessing
    from multiprocessing import Process  # , Queue
    import concurrent.futures as futures

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


    # Start classes from custom package
    Config = vquit.Configuration()
    ProductData = vquit.ProductData()
    FetchTimer = vquit.Timer()
    FXTimer = vquit.Timer()
    IA = vquit.ImageAcquirer()
    IO = vquit.RaspberryPi()
    Image = vquit.Image()
    CV = vquit.OpenCV()
    System = System()
    warnings.formatwarning = vquit.WarningFormat.SetCustom  # Set custom warning format

    #########
    # Setup #
    #########

    IA.Setup(Config_module=Config, Warnings_module=warnings)  # Run setup for cameras
    IO.Setup(Config_module=Config)  # Run setup for raspberry

    System.ConfigScaling(IA.GigE[0])  # configure scaling based on monitors

    # Init other variables used in main loop
    quickSettings = Config.Get("QuickSettings")  # Get configuration data
    imgPlots = quickSettings["ImagePlots"]  # 0 = no plots
    compact = quickSettings["ReducedImageDetection"]  # 1 = less filters & plots

    #############
    # Main loop #
    #############

    # Color correction values
    ccTable = []
    ccData = Config.Get("Cameras")["Advanced"]
    for i in range(0, Config.Get("QuickSettings")["ActiveCameras"]):
        ccTable.append([ccData[i]["ColorCorrection"]["Red"],
                        ccData[i]["ColorCorrection"]["Green"],
                        ccData[i]["ColorCorrection"]["Blue"]])


    def serialFX(fetchedImages):
        output = [
            imageProcessing(iteration, fetchedImages[iteration], ccTable[iteration]) for iteration in
            range(0, len(fetchedImages))]

        return output


    def concurrentFX(mode, fetchedImages):
        output = []
        if mode is "Threads":
            concurrentExecutor = futures.ThreadPoolExecutor()
        elif mode is "Processes":
            concurrentExecutor = futures.ProcessPoolExecutor()
        else:
            print("Enter valid concurrent mode")
            return output

        with concurrentExecutor as executor:
            results = [executor.submit(imageProcessing, iteration, fetchedImages[iteration], ccTable[iteration]) for
                       iteration in range(0, len(fetchedImages))]

            # Read result of finished tasks
            for f in futures.as_completed(results):
                output.append(f.result())
        return output


    # Normal loop
    def mainLoop():
        # image = IA.RequestFrame(0)
        # print(np.max(image))

        # Request frame from all connected cameras ans store them in imgsIn
        FetchTimer.Start()
        fetchedImages = [IA.RequestFrame(iteration) for iteration in range(0, len(IA.GigE))]
        print("Fetch time: ", "{0:.3f}".format(FetchTimer.Stop()), "s")

        # out = concurrentFX("Threads", fetchedImages)  # ThreadPoolExecutor 3.5 - ProcessPoolExecutor: 4.3
        out = serialFX(fetchedImages)  # 4.5

        # showImage = out[0][1]
        # showName = str(out[0][0])
        #
        # showImage = Image.Scale(showImage, newHeight=400, newWidth=400)
        #
        # try:
        #     if showImage is not False:
        #         cv2.imshow(showName, showImage)
        # except:
        #     pass


    # Main code loop trigger
    input("Press ENTER to start...\n")

    IA.Start()  # Start image acquisition
    run = True
    while run:
        # Run main loop
        FetchTimer.Start()
        fetchedImages = [IA.RequestFrame(iteration) for iteration in range(0, len(IA.GigE))]
        print("Fetch time: ", "{0:.3f}".format(FetchTimer.Stop()), "s")

        FXTimer.Start()
        out = serialFX(fetchedImages)  # 4.5
        # out = concurrentFX("Threads", fetchedImages)  # ThreadPoolExecutor 3.5 - ProcessPoolExecutor: 4.3
        print("Process time: ", "{0:.3f}".format(FXTimer.Stop()), "s")

        print(out[0][1])
        # CV.SaveAsPNG("V2 Threads", out[0][1])
        exit()

        # Check abort parameters
        run = not System.Abort()

    ################
    # System reset #
    ################

    IA.Stop()
    IA.Destroy()
    IA.Reset()

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