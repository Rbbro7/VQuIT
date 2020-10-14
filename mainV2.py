# Adimec VQuIT Software (Author: Robin Broeren)


#################
# ALL PROCESSES #
#################
#################
# ALL PROCESSES #
#################

def imageProcessing(iteration, image, ccValues, screenHeight, Image_module, ProductData_module, OpenCV_module):
    if image is not 0:
        # Conversion
        image = Image_module.BayerRGtoRGB(image)  # BayerRG -> RGB

        # Preprocessing
        cc = Image_module.NoiseReduction(Image_module.ColorCorrection(image, ccValues))
        gray = Image_module.Gray(cc)
        grayBlur = Image_module.Blur(gray)

        # Get product data
        if ProductData_module.GetDataMatrixInfo(grayBlur) is 1:
            print("Camera ", iteration, " : Acode", ProductData_module.acode, "& S/N", ProductData_module.sn)

        # Perform image analysis
        output = OpenCV_module.EdgeDetection(grayBlur, screenHeight, Image_module)

        # queue.put([cc, grayBlur])
        return image
    else:
        return False


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
    from multiprocessing import Process, Queue
    import concurrent.futures

    # Image processing
    import numpy as np
    from scipy import ndimage
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
    Timer = vquit.Timer()
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
    Image.Setup(OpenCV_module=cv2, NP_module=np, ndimage_module=ndimage)  # Setup image processing
    CV.Setup(OpenCV_module=cv2, NP_module=np)  # Setup OpenCV

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
            imageProcessing(iteration, fetchedImages[iteration], ccTable[iteration], System.imgH_px, Image, ProductData,
                            CV) for iteration in range(0, len(fetchedImages))]

        print(output[0])
        #cv2.imwrite("t", output[0], [cv2.IMWRITE_PNG_COMPRESSION, 0])
        #cv2.imshow('Output', np.hstack(output))


    def parallelFX(fetchedImages):

        # after importing numpy, reset the CPU affinity of the parent process so that it will use all cores
        queue = Queue()

        # Create all processes
        processes = [
            Process(target=imageProcessing,
                    args=(iteration, fetchedImages[iteration], ccTable[iteration], System.imgH_px, Image, ProductData,
                          CV)) for iteration in range(0, len(fetchedImages))]

        for process in processes:
            process.start()  # Start all processes
            process.join()  # Stop script from going further until process is finished

        # processedImages = []
        # while not queue.empty():
        #     processedImages.append(queue.get())
        #
        # print(processedImages)


    def parallelFXAlt(fetchedImages):
        output = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = [executor.submit(imageProcessing, iteration, fetchedImages[iteration], ccTable[iteration],
                                       System.imgH_px, Image, ProductData, CV) for iteration in
                       range(0, len(fetchedImages))]

            # Read result of finished tasks
            for f in concurrent.futures.as_completed(results):
                output.append(f.result())

        cv2.imshow('Output', np.hstack(output))


    # Normal loop
    def mainLoop():
        # Request frame from all connected cameras ans store them in imgsIn
        fetchedImages = [IA.RequestFrame(iteration) for iteration in range(0, len(IA.GigE))]

        # parallelFXAlt(fetchedImages)  # ThreadPoolExecutor 3.5 - ProcessPoolExecutor: 4.3
        serialFX(fetchedImages)  # 4.5
        # parallelFX(fetchedImages)     # 6.5 -> Update: Error


    # Main code loop trigger
    input("Press ENTER to start...\n")

    IA.Start()  # Start image acquisition
    run = True
    while run:
        # Start monitor timer
        Timer.Start()

        # Run main loop
        mainLoop()

        # Check abort parameters
        run = not System.Abort()

        # End monitor timer
        deltaTime = Timer.Stop()
        print("Refresh time: ", "{0:.3f}".format(deltaTime), "s")

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
