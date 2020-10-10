# Adimec D12A09 python script


###########
# Imports #
###########

# GenICam helper
from harvesters.core import Harvester

# Image processing
import cv2

# Raspberry controller
import pigpio as gpio

# Data container
from scipy import ndimage
import numpy as np

# Barcode scanner
from pylibdmtx.pylibdmtx import decode as getDataMatrix
from pyzbar.pyzbar import decode as getBarcode

# Read JSON files
import json

# Misc
import os
import sys
import ctypes
import time


####################
# Quick parameters #
####################

codeScanning = 0    # Enable scan increases runtime significantly

jumboPackets = 0
compact = 1         # 1 = less filters & plots
imgPlots = 1        # 0 = no plots

binning = 0

imgLabel = 'test6'  # image label name for cameraTest

# Original
camID = [  # Comment out cameras when not in use
    "D-12A09c_GV-S01(70:b3:d5:85:40:3d)",   # A
    "D-12A09c_GV-S01(70:b3:d5:85:40:3e)",   # B
    "D-12A09c_GV-S01(70:b3:d5:85:40:3f)",   # C
    "D-12A09c_GV-S01(70:b3:d5:85:40:40)",   # D
    "D-12A09c_GV-S01(70:b3:d5:85:40:41)",   # E
    "D-12A09c_GV-S01(70:b3:d5:85:40:42)"    # F
]

# Assign parameters linked to cameraID
camInfo = [[  # ID
    "D-12A09c_GV-S01(70:b3:d5:85:40:3d)",   # A
    "D-12A09c_GV-S01(70:b3:d5:85:40:3e)",   # B
    "D-12A09c_GV-S01(70:b3:d5:85:40:3f)",   # C
    "D-12A09c_GV-S01(70:b3:d5:85:40:40)",   # D
    "D-12A09c_GV-S01(70:b3:d5:85:40:41)",   # E
    "D-12A09c_GV-S01(70:b3:d5:85:40:42)"    # F
], [  # GainRaw
    240, 24, 0, 0, 0, 0
], [  # BlackLevelRaw
    64, 64, 0, 0, 0, 0
], [  # Correction R
    1.118, 1.762, 0, 0, 0, 0
], [  # Correction G
    0.949, 1.525, 0, 0, 0, 0
], [  # Correction B
    1.152, 3.558, 0, 0, 0, 0
]]


#############
# Functions #
#############

# Read and write data to files
class Files:
    configData = ""

    def Temp(self):
        # Read Configuration File
        with open('VQuIT_Config.json', 'r') as configFile:
            self.configData = json.load(configFile)

        # Append to database
        with open('VQuIT_Database.json', 'a') as database:
            data = "New Data"
            json.dump(data, database)


Files = Files()


# System settings
class System:
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
        print('CAMERA: Image size = {0:d}x{1:d}'.format(imageWidth, imageHeight))

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
        print('SYSTEM: imgScale = ', self.imgScale)

    # Variables
    # Screen size parameters
    imgH = imgH_px = imgW_px = 0
    imgScale = 0


System = System()


# Timer class
class Timer:
    # Start timer
    def Start(self):
        self.__tic = time.perf_counter()

    # Stop timer
    def Stop(self):
        self.__toc = time.perf_counter()
        result = self.__toc - self.__tic
        return result

        # Variables

    __tic = 0  # Start time
    __toc = 0  # Stop time


Timer = Timer()


# GigE Camera drivers
class ImageAcquirer:
    # Init harvester
    harvester = Harvester()

    # Storage for camera modules
    GigE = []

    # Import cti file from GenTL producer
    def ImportCTI(self):
        # path to GenTL producer
        CTIPath = r'C:\Program Files\MATRIX VISION\mvIMPACT Acquire\bin\x64\mvGenTLProducer.cti'

        if os.path.isfile(CTIPath):
            self.harvester.add_file(CTIPath)
        else:
            print("Could not find the GenTL producer for GigE")
            sys.exit(1)

    # Scan for available producers
    def Scan(self, n_camera):
        print('Scanning for available producers..', end='')
        for i in range(0, 100):
            print('.', end='')
            self.harvester.update()
            if len(self.harvester.device_info_list) >= n_camera:
                break
            time.sleep(1)
        print("\n")

        if len(self.harvester.device_info_list) < n_camera:
            print("Error: Found ", n_camera, " of ", len(self.harvester.device_info_list),
                  "requested producers in network")
            sys.exit(1)
        print(self.harvester.device_info_list)

    # Create image acquirer objects
    def Create(self):
        n_camera = len(camID)
        print("Creating", n_camera, "IA's")

        for i in range(0, n_camera):
            try:
                # Create camera instances in order of camID array
                newIA = self.harvester.create_image_acquirer(id_=camID[i])
                self.GigE.append(newIA)
            except:
                print("Error: ID - ", camID[i], " not found")
                exit()
        return self.GigE

    # Configure image acquirer objects
    def Config(self, cameraID, cameraInfo, jumboPacketsEnabled, binningActive):
        if jumboPacketsEnabled:
            packetSize = 8228
        else:
            packetSize = 1060
            print("Warning: Running script without jumbo packets can cause quality and reliability issues")

        # Binning
        print("Binning: ", binningActive)
        imgWidth = 4096  # 4096  | Compressed = 1024
        imgHeight = 3008  # 3008  | Compressed = 752
        binningType = "Disabled"

        if binningActive:
            imgWidth = int(imgWidth / 4)
            imgHeight = int(imgHeight / 4)
            binningType = "Bayer4x4"

        # Set standard camera parameters
        for i in range(0, len(self.GigE)):
            # ImageFormatControl
            self.GigE[i].remote_device.node_map.PixelFormat.value = "BayerRG8"  # Stock: BayerRG12Packed | Recommended: BayerRG8
            self.GigE[i].remote_device.node_map.Binning.value = binningType
            self.GigE[i].remote_device.node_map.Width = imgWidth
            self.GigE[i].remote_device.node_map.Height = imgHeight

            # AcquisitionControl
            self.GigE[i].remote_device.node_map.ExposureMode.value = "TimedTriggered"  # Stock: "Timed" | Recommended: "TimedTriggered"
            self.GigE[i].remote_device.node_map.ExposureTimeRaw.value = 153770  # Stock: 153770

            # AnalogControl
            self.GigE[i].remote_device.node_map.GainRaw.value = cameraInfo[1][
                cameraInfo[0].index(cameraID[i])]  # Assign right value by matching ID between camID and camInfo
            self.GigE[i].remote_device.node_map.BlackLevelRaw.value = cameraInfo[2][
                cameraInfo[0].index(cameraID[i])]  # Stock: 64

            # TransportLayerControl   
            self.GigE[i].remote_device.node_map.GevSCPSPacketSize.value = packetSize  # Stock: 1060 | recommended 8228

            # TimedTriggered parameters
            self.GigE[i].remote_device.node_map.FrameAverage.value = 1                  # number of frames, image is created by averaging the frames
            self.GigE[i].remote_device.node_map.MultiExposureNumber.value = 1           # number of exposures, frame is created by adding the exposures
            self.GigE[i].remote_device.node_map.MultiExposureInactiveRaw.value = 250    # time between exposures in a single frame

            # Not in use
            # AcquisitionPeriod (Integration time - irrelevant when using TimedTriggered)
            # value: microseconds (min: 102775 µs @4096 x 3008 - BayerRG8 - Binning Disabled (Max frame rate 9.73 Hz) , max: 60s)
            # self.GigE[i].remote_device.node_map.AcquisitionFramePeriodRaw.value = 154010

    # Start image acquisition
    def Start(self):
        print("start image acquisition")
        for i in range(0, len(self.GigE)):
            self.GigE[i].start_acquisition()

    # Tweak camera settings on the go
    def camConfig(self, camNr, exposure=None, gain=None, blackLevel=None,
                  frameAveraging=None, multiExposureNumber=None, multiExposureInactive=None):
        if exposure:
            self.GigE[camNr].remote_device.node_map.ExposureTimeRaw.value = exposure
        if gain:
            self.GigE[camNr].remote_device.node_map.GainRaw.value = gain
        if blackLevel:
            self.GigE[camNr].remote_device.node_map.BlackLevelRaw.value = blackLevel
        if frameAveraging:
            self.GigE[camNr].remote_device.node_map.FrameAverage.value = frameAveraging
        if multiExposureNumber:
            self.GigE[camNr].remote_device.node_map.MultiExposureNumber.value = multiExposureNumber
        if multiExposureInactive:
            self.GigE[camNr].remote_device.node_map.MultiExposureInactiveRaw.value = multiExposureInactive  # time between exposures in a single frame

    # Retrieve camera data
    def RequestFrame(self, camNr):
        im = 0
        try:
            self.GigE[camNr].remote_device.node_map.TriggerSoftware.execute()  # Trigger camera

            # get a buffer
            print("fetch buffer...", end='')
            with self.GigE[camNr].fetch_buffer() as buffer:
                print("fetched")
                # access the image payload
                component = buffer.payload.components[0]

                if component is not None:
                    im = component.data.reshape(component.height, component.width)
                    im = cv2.cvtColor(im,
                                      cv2.COLOR_BayerRG2RGB)  # BayerRG -> RGB (Does not work proper when scaled down)
                return im

        except:
            print("Something went wrong during buffering")
            im = 0
        return im

    # Get camera temperature
    def getTemperature(self, camNr):
        return float(self.GigE[camNr].remote_device.node_map.DeviceTemperatureRaw.value/100)

    # Get camera features
    def getCameraAttributes(self):
        return dir(self.GigE[0].remote_device.node_map)

    # Stop image acquisition
    def Stop(self):
        print("stop image acquisition")
        for i in range(0, len(self.GigE)):
            self.GigE[i].stop_acquisition()

    # Stop image acquisition
    def Destroy(self):
        print("destroy image acquire objects")
        for i in range(0, len(self.GigE)):
            self.GigE[i].destroy()

    # Reset harvester        
    def Reset(self):
        self.harvester.reset()


IA = ImageAcquirer()


# Raspberry Pi remote access
class RaspberryPi:
    # Connect to pi
    rpi = gpio.pi('192.168.7.239')     # VQuIT-RemoteIO

    def Disconnect(self):
        self.rpi.stop()

    def PinMode(self, pin, state):
        if state is 'input':
            self.rpi.set_mode(pin, gpio.INPUT)
        elif state is 'output':
            self.rpi.set_mode(pin, gpio.OUTPUT)
        else:
            print("Bad state for GPIO pin")

    def Write(self, pin, value):
        self.rpi.write(pin, value)

    def Read(self, pin):
        return self.rpi.read(pin)

    def Setup(self):
        self.PinMode(4, 'input')


IO = RaspberryPi()


# Image manipulation & analysis
class Image:
    # Original images
    original = []

    # Color corrected images
    cc = []         # Original
    cc_s = []       # Original scaled
    ccNR = []       # Noise reduction
    ccNR_s = []     # Noise reduction scaled

    # Gray scaled images
    gray = []       # Original
    gray_s = []     # Original scaled
    grayInv = []    # Inverted
    grayInv_s = []  # Inverted scaled
    grayNR = []     # Noise reduction
    grayNR_s = []   # Noise reduction scaled

    # Filter parameters
    NR_Blur = 25

    # Color correction
    @staticmethod
    def ColorCorrection(im, targetCam):
        b, g, r = cv2.split(im)

        # Multiply color array by ID specific gain and clip at 255
        b = np.array(np.clip(b * camInfo[5][camInfo[0].index(camID[targetCam])], 0, 255), dtype=np.uint8)
        g = np.array(np.clip(g * camInfo[4][camInfo[0].index(camID[targetCam])], 0, 255), dtype=np.uint8)
        r = np.array(np.clip(r * camInfo[3][camInfo[0].index(camID[targetCam])], 0, 255), dtype=np.uint8)
        im = cv2.merge([b, g, r])
        return im

    # Reduce binary noise by removing data groups smaller than the mask size
    @staticmethod
    def BinaryNoiseReduction(imgBinary):
        imgBinary = ndimage.binary_opening(imgBinary, structure=np.ones((2, 2))).astype(np.bool)
        return imgBinary

    # Crop image to perform actions on specific parts
    @staticmethod
    def Crop(im, x0, x1, y0, y1):
        im = im[y0:y1, x0:x1]
        return im

    # Scale
    @staticmethod
    def Scale(im, multiplier=None, newHeight=None, newWidth=None):
        # Set new resolution
        if newHeight is not None and newWidth is not None:
            width = int(newWidth)
            height = int(newHeight)
        else:
            width = im.shape[1]
            height = im.shape[0]

        # Scale resolution with factor
        if multiplier is not None:
            width = int(width * multiplier)
            height = int(height * multiplier)

        dim = (width, height)
        im = cv2.resize(im, dim, interpolation=cv2.INTER_AREA)
        return im

    # Reset image arrays
    def ResetImage(self):
        self.original = []
        self.cc = []
        self.cc_s = []
        self.ccNR = []
        self.ccNR_s = []
        self.gray = []
        self.gray_s = []
        self.grayInv = []
        self.grayInv_s = []
        self.grayNR = []
        self.grayNR_s = []

    # Image Processing
    def Processing(self, imIn):
        self.ResetImage()
        self.original = imIn
        for i in range(0, len(self.original)):
            cc, cc_s, ccNR, ccNR_s, gray, gray_s, grayInv, grayInv_s, grayNR, grayNR_s = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

            if self.original[i] is not 0:
                # Color adjustments
                cc = np.array(self.ColorCorrection(self.original[i], i), dtype=np.uint8)
                gray = np.array(cv2.cvtColor(cc, cv2.COLOR_BGR2GRAY), dtype=np.uint8)
                grayInv = np.array(gray * 255, dtype=np.uint8)

                # Noise reduction
                ccNR = np.array(cv2.bilateralFilter(cc, 7, 50, 50), dtype=np.uint8)
                grayNR = np.array(cv2.bilateralFilter(gray, 7, 50, 50), dtype=np.uint8)
                #ccNR = np.array(GaussianBlur(image, (blur, blur), 0), dtype=np.uint8)

                # Scaling
                cc_s = np.array(self.Scale(cc, multiplier=System.imgScale), dtype=np.uint8)
                ccNR_s = np.array(self.Scale(ccNR, multiplier=System.imgScale), dtype=np.uint8)
                gray_s = np.array(self.Scale(gray, multiplier=System.imgScale), dtype=np.uint8)
                grayInv_s = np.array(self.Scale(grayInv, multiplier=System.imgScale), dtype=np.uint8)
                grayNR_s = np.array(self.Scale(grayNR, multiplier=System.imgScale), dtype=np.uint8)

            # Append images
            self.cc.append(cc)
            self.cc_s.append(cc_s)
            self.ccNR.append(ccNR)
            self.ccNR_s.append(ccNR_s)
            self.gray.append(gray)
            self.gray_s.append(gray_s)
            self.grayInv.append(grayInv)
            self.grayInv_s.append(grayInv_s)
            self.grayNR.append(grayNR)
            self.grayNR_s.append(grayNR_s)


Image = Image()


# Save product info
class Product:
    acode = 0  # Article code
    sn = 0  # Serial number

    # Scan images for dataMatrices QR-codes and barcodes
    def GetDataMatrixInfo(self, im):
        data = 0

        dataMatrix = getDataMatrix(im)
        barcodes = getBarcode(im)

        for result in dataMatrix:
            data = result.data.split()

        if data == 0:
            for result in barcodes:
                data = result.data

        if data is not 0:
            self.acode = int(data[0].decode("utf-8"))
            self.sn = int(data[1].decode("utf-8"))
            return 1
        return 0


Product = Product()


# Image analysis
class OpenCV:
    ksize = 25
    ddepth = cv2.CV_8U

    def Sobel(self, im, scale, threshold, orientation):
        if orientation == 0:
            sobel = cv2.Sobel(im, self.ddepth, 1, 0, self.ksize, scale)  # Sobel X
        else:
            sobel = cv2.Sobel(im, self.ddepth, 0, 1, self.ksize, scale)  # Sobel Y

        sobelThresh = sobel > threshold * np.max(sobel)  # Remove values under threshold
        sobelThresh = Image.BinaryNoiseReduction(sobelThresh)
        sobelThresh = np.array(sobelThresh * 255, dtype=np.uint8)  # Convert to UMat type
        sobelThresh = cv2.adaptiveThreshold(sobelThresh, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 3, 0)
        return sobel, sobelThresh

    def Laplacian(self, im, filterScale, threshold, thresholdBlockSize):
        laplacian = cv2.Laplacian(im, self.ddepth, self.ksize, filterScale)  # Apply filter
        laplacianThresh = laplacian > threshold * np.max(laplacian)  # Convert to binary
        laplacianThresh = Image.BinaryNoiseReduction(laplacianThresh)
        laplacianThresh = np.array(laplacianThresh * 255, dtype=np.uint8)  # Convert to numerical
        thresholdConstant = 0  # Should be a value for non binary
        laplacianThresh = cv2.adaptiveThreshold(laplacianThresh, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
                                                thresholdBlockSize, thresholdConstant)
        return laplacian, laplacianThresh

    @staticmethod
    def Canny(im):
        canny = cv2.Canny(im, 60, 120)
        return canny

    # OpenCV Image processing
    def EdgeDetection(self, imageNr):
        output = -1
        imgHeight = len(Image.grayNR_s[imageNr])
        imgWidth = len(Image.grayNR_s[imageNr][0])
        imgW_px = int(System.imgH_px * (imgWidth / imgHeight))

        # Sobel/Laplace parameters
        threshold = 0.05  # Stock recommended 0.3
        scale = 1
        thresholdBlockSize = 3

        if compact == 0:
            sobelx, sobelxThresh = self.Sobel(Image.grayNR_s[imageNr], scale, threshold, 0)
            sobely, sobelyThresh = self.Sobel(Image.grayNR_s[imageNr], scale, threshold, 1)
            laplacian, laplacianThresh = self.Laplacian(Image.grayNR_s[imageNr], scale, threshold, thresholdBlockSize)
            # cannyImg = self.Canny(im)

            # Combine filters (or gate)
            allThresh = (sobelxThresh | sobelyThresh | laplacianThresh)
            allThresh = np.array(allThresh * 255, dtype=np.uint8)
            allThresh = cv2.adaptiveThreshold(allThresh, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 3, 0)

            sobelx = Image.Scale(sobelx, newWidth=imgW_px, newHeight=System.imgH_px)
            sobelxThresh = Image.Scale(sobelxThresh, newWidth=imgW_px, newHeight=System.imgH_px)

            sobely = Image.Scale(sobely, newWidth=imgW_px, newHeight=System.imgH_px)
            sobelyThresh = Image.Scale(sobelyThresh, newWidth=imgW_px, newHeight=System.imgH_px)

            laplacian = Image.Scale(laplacian, newWidth=imgW_px, newHeight=System.imgH_px)
            laplacianThresh = Image.Scale(laplacianThresh, newWidth=imgW_px, newHeight=System.imgH_px)

            #cannyImg = Image.Scale(cannyImg, newWidth=imgW_px, newHeight=System.imgH_px)

            # Merge images
            row0 = np.hstack([Image.grayNR_s[imageNr], Image.grayInv_s[imageNr]])
            row1 = np.hstack([laplacian, sobelx, sobely])
            row2 = np.hstack([laplacianThresh, sobelxThresh, sobelyThresh])

            # Show images      
            cv2.imshow(('Filter' + str(imageNr)), row1)
            cv2.imshow(('Threshold' + str(imageNr)), row2)
            cv2.imshow(('Preprocessed' + str(imageNr)), row0)
            cv2.imshow(('Original (cc)' + str(imageNr)), Image.ccNR_s[imageNr])

            cv2.namedWindow(('Threshold (combined)' + str(imageNr)), cv2.WINDOW_NORMAL)  # Make window resizable
            cv2.imshow(('Threshold (combined)' + str(imageNr)), allThresh)
        elif compact == 1:
            laplacian, laplacianThresh = self.Laplacian(Image.grayNR[imageNr], scale, threshold, thresholdBlockSize)
            laplacianThresh = Image.Scale(laplacianThresh, newWidth=imgW_px, newHeight=System.imgH_px)
            output = laplacianThresh
        else:
            # im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)         # Gray scale
            # im = cv2.bilateralFilter(Image.grayNR_s[imageNr], 7, 50, 50)  # Blur for smoothing
            edgesThresh = self.Canny(Image.grayNR_s[imageNr])

            # Scale down images for viewer    
            edgesThresh = cv2.resize(edgesThresh, (self.imgW_px, System.imgH_px))

            output = edgesThresh
        return output

    # Variables
    imgW_px = 0


CV = OpenCV()


#########
# Setup #
#########

IA.ImportCTI()                                      # import cti file
IA.Scan(len(camID))                                 # check if producer is available
IA.Create()                                         # define image Acquirer objects from discovered devices

IA.Config(camID, camInfo, jumboPackets, binning)    # configure image acquirer objects
IO.Setup()                                          # run setup for raspberry pi

System.ConfigScaling(IA.GigE[0])                    # configure scaling based on monitors


#############
# Main loop #
#############

# Normal loop
def mainLoop():
    # Request camera frames
    imgsIn = []
    for iteration in range(0, len(IA.GigE)):
        print("Camera ", iteration, ": ", end='')
        IA.camConfig(iteration, exposure=90000, gain=5, blackLevel=0)
        #IA.camConfig(iteration, acqPeriod=154010, exposure=93770, gain=1, blackLevel=None)
        imgData = IA.RequestFrame(iteration)
        imgsIn.append(imgData)

    # Process images
    Image.Processing(imgsIn)

    # Show processed images
    if compact and imgPlots:
        cv2.imshow('Input', np.hstack(Image.ccNR_s))

    # Analyze camera frames
    imgsOut = []
    for iteration in range(0, len(imgsIn)):
        if imgsIn[iteration] is not 0:
            # Crop image
            #img = Image.Crop(img, 450, 600, 375, 525)

            if codeScanning:
                # Scan for barcodes
                dataDetected = Product.GetDataMatrixInfo(Image.grayNR_s[iteration])
                if dataDetected:
                    print("Camera ", iteration, " : Acode", Product.acode, "& S/N", Product.sn)

            # Perform edge detection
            img = CV.EdgeDetection(iteration)
            if compact:
                imgsOut.append(img)

    # Show results
    if compact and imgPlots:
        cv2.imshow('Output', np.hstack(imgsOut))


# Camera Test
def cameraTestLoop(camera):
    imgsIn = []

    testSettings = [[                       # Exposure (Time during which the sensor is exposed to light)
        80000, 85000, 90000, 102000      # Microseconds (Datasheet {min: 40 µs, max: acq - 226µs}, Software {min:15})
    ], [                                    # Gain (more gain = more noise) Analog gain: 0->24dB Digital gain: 24->48dB
        5, 5, 5, 5                  # 1 = 0.1 dB
    ], [  # Black level - Prevent clipping of the minimum value above 0 (Used to bring the minimum values closer to 0 if they are shifted up by gain)
        0, 0, 0, 0                      # 0 to 4095 (higher = brighter picture)
    ]]

    # Live preview until interrupted by Ctrl+c
    preview = True
    IA.camConfig(camera, exposure=9000, gain=1, blackLevel=0)
    while preview:
        imgData = IA.RequestFrame(camera)
        imgData = np.array(Image.Scale(imgData, newHeight=1050, newWidth=1430), dtype=np.uint8)
        cv2.imshow('Preview', imgData)

        stop = cv2.waitKey(1)
        if stop > 0:
            preview = False

    # Retrieve images
    for iteration in range(0, len(testSettings[0])):
        IA.camConfig(camera, exposure=testSettings[0][iteration],
                     gain=testSettings[1][iteration], blackLevel=testSettings[2][iteration])
        imgData = IA.RequestFrame(camera)
        imgsIn.append(imgData)

    # Save images
    for iteration in range(0, len(imgsIn)):
        name = str(imgLabel) + '_exp' + str(testSettings[0][iteration]) + \
               '_gain' + str(testSettings[1][iteration]) + '_bgain' + str(testSettings[2][iteration]) +\
               '.png'
        cv2.imwrite(name, imgsIn[iteration], [cv2.IMWRITE_PNG_COMPRESSION, 0])
    return False    # Abort code after running


IA.Start()  # start image acquisition
run = True
input("Press ENTER to start...")

# Main code loop
while run:
    # Start monitor timer
    Timer.Start()

    #mainLoop()
    #run = cameraTestLoop(0)

    # Check abort key
    key = cv2.waitKey(1)
    if key > 0:
        run = False

    # End monitor timer
    deltaTime = Timer.Stop()
    print("Refresh time: ", deltaTime, "s")


################
# System reset #
################

IA.Stop()
IA.Destroy()
IA.Reset()

exit()
