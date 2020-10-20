# GigE Camera drivers
class ImageAcquirer:

    # Storage for camera modules
    GigE = []

    # Maximum fetch tries until reconnect and abort
    fetchTimeout = None
    fetchSoftReboot = None
    fetchAbort = None

    cv2 = None

    # Function runs when initializing class
    def __init__(self, Config_module=None, Warnings_module=None):

        # Misc
        from time import sleep
        import sys

        self.sleep = sleep
        self.warnings = Warnings_module
        self.sys = sys

        # Store custom module
        self.FileConfig = Config_module

        # GenICam helper
        from harvesters.core import Harvester, TimeoutException

        # Init harvester
        self.harvester = Harvester()
        self.TimeoutException = TimeoutException

        # Temperature
        self.criticalTemp = self.FileConfig.Get("Cameras")["Generic"]["Temperature"]["Critical"]
        self.warningTemp = self.FileConfig.Get("Cameras")["Generic"]["Temperature"]["Warning"]

        # Storage for camera modules
        self.n_camera = self.FileConfig.Get("QuickSettings")["ActiveCameras"]

        self.ImportCTI()  # import cti file
        self.Scan()  # check if producer is available)
        self.Create()  # define image Acquirer objects from discovered devices
        self.Config()  # configure image acquirer objects

        self.ImportOpenCV()  # Create opencv module

    # Import cti file from GenTL producer
    def ImportCTI(self):
        # path to GenTL producer
        CTIPath = self.FileConfig.Get("Cameras")["Generic"]["CTIPath"]

        from os import path
        if path.isfile(CTIPath):
            self.harvester.add_file(CTIPath)
        else:
            print(
                "\nCould not find the GenTL producer for GigE\nCheck the file path given in VQuIT_config.json>Cameras>Generic>CTIPath")
            self.sys.exit(1)

    def ImportOpenCV(self):
        if self.cv2 is None:
            print("Importing OpenCV")
            import cv2
            self.cv2 = cv2
        return self.cv2

    # Scan for available producers
    def Scan(self):
        tries = 100
        for i in range(0, tries):
            self.harvester.update()
            foundDevices = len(self.harvester.device_info_list)
            print('Scanning for available cameras... ' + str(foundDevices) + " of " + str(
                self.n_camera) + " (Attempt " + str(i + 1) + " of " + str(tries) + ")", end='\r')
            if foundDevices >= self.n_camera:
                break
            self.sleep(1)

        if len(self.harvester.device_info_list) < self.n_camera:
            print("Error: Found ", len(self.harvester.device_info_list), " of ", self.n_camera,
                  "requested producers in network")
            self.sys.exit(1)
        # print(self.harvester.device_info_list)     # Show details of connected devices

    # Create image acquirer objects
    def Create(self):
        cameraInfo = self.FileConfig.Get("Cameras")["Advanced"]
        for i in range(0, self.n_camera):
            try:
                # Create camera instances in order written in VQuIT_Config.json>Cameras>Advanced
                newIA = self.harvester.create_image_acquirer(id_=cameraInfo[i]["ID"])
                self.GigE.append(newIA)
            except:
                print("Error: ID '" + str(
                    cameraInfo[i]["ID"]) + "' not found\nMake sure no other instances are connected to the cameras")
                exit()

    # Configure image acquirer objects
    def Config(self):
        # Load configuration file (Use ["Description"] instead of ["Value"] to get a description of said parameter)
        qs = self.FileConfig.Get("QuickSettings")
        c = self.FileConfig.Get("Cameras")

        cameraInfo = c["Advanced"]
        imgFormat = c["Generic"]["ImageFormatControl"]
        acquisition = c["Generic"]["AcquisitionControl"]
        transport = c["Generic"]["TransportLayerControl"]
        trigger = c["Generic"]["TimedTriggered_Parameters"]
        fetchError = c["Generic"]["FetchError"]

        # Maximum fetch tries per camera
        self.fetchTimeout = fetchError["Timeout"]
        self.fetchSoftReboot = fetchError["SoftReboot"]
        self.fetchAbort = fetchError["Abort"]

        # Jumbo packets
        jumboPackets = qs["JumboPackets"]
        if jumboPackets:
            print("Jumbo packets Active\n")
            packetSize = transport["GevSCPSPacketSize"]["Value"][0]
        else:
            print("\r")
            self.warnings.warn("Running script without jumbo packets can cause quality and reliability issues")
            self.sleep(0.2)
            packetSize = transport["GevSCPSPacketSize"]["Value"][1]

        # Binning
        binning = qs["Binning"]
        if binning:
            print("Binning Active")
            imgWidth = int(imgFormat["Resolution"]["Width"] / 4)
            imgHeight = int(imgFormat["Resolution"]["Height"] / 4)
            binningType = imgFormat["BinningType"]["Value"][1]
        else:
            imgWidth = imgFormat["Resolution"]["Width"]
            imgHeight = imgFormat["Resolution"]["Height"]
            binningType = imgFormat["BinningType"]["Value"][0]

        # Set standard camera parameters
        for i in range(0, len(self.GigE)):
            print("Setting up camera " + cameraInfo[i]["Camera"] + "...", end="\r")
            # ImageFormatControl
            self.GigE[i].remote_device.node_map.PixelFormat.value = imgFormat["PixelFormat"]["Value"][0]
            self.GigE[i].remote_device.node_map.Binning.value = binningType
            self.GigE[i].remote_device.node_map.Width.value = imgWidth
            self.GigE[i].remote_device.node_map.Height.value = imgHeight

            # AcquisitionControl
            self.GigE[i].remote_device.node_map.ExposureMode.value = acquisition["ExposureMode"]["Value"][0]
            self.GigE[i].remote_device.node_map.ExposureTimeRaw.value = acquisition["ExposureTime"]["Value"]

            # AnalogControl
            self.GigE[i].remote_device.node_map.GainRaw.value = cameraInfo[i]["Gain"]["Value"]
            self.GigE[i].remote_device.node_map.BlackLevelRaw.value = cameraInfo[i]["BlackLevel"]["Value"]

            # TransportLayerControl
            self.GigE[
                i].remote_device.node_map.GevSCPSPacketSize.value = packetSize  # Stock: 1060 | recommended 8228

            # TimedTriggered parameters
            self.GigE[i].remote_device.node_map.FrameAverage.value = trigger["FrameAverage"]["Value"]
            self.GigE[i].remote_device.node_map.MultiExposureNumber.value = trigger["MultiExposureNumber"]["Value"]
            self.GigE[i].remote_device.node_map.MultiExposureInactiveRaw.value = trigger["MultiExposureInactive"][
                "Value"]

            # Not in use
            # AcquisitionPeriod (Integration time - irrelevant when using TimedTriggered)
            # value: microseconds (min: 102775 µs @4096 x 3008 - BayerRG8 - Binning Disabled (Max frame rate 9.73 Hz) , max: 60s)

    # Start image acquisition
    def Start(self):
        print("\nStart image acquisition\n")
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
            self.GigE[
                camNr].remote_device.node_map.MultiExposureInactiveRaw.value = multiExposureInactive  # time between exposures in a single frame

    # Retrieve camera data
    def RequestFrame(self, camNr):
        cv2 = self.ImportOpenCV()

        # Loop process until successful
        loop = 0
        fetchImage = True
        while fetchImage:
            loop += 1
            try:
                if loop > 1 and (loop % 2) is not 0:
                    # Wait before sending new trigger every odd try that is not the first
                    self.sleep(0.5)
                # Trigger camera
                self.GigE[camNr].remote_device.node_map.TriggerSoftware.execute()

                # Wait for buffer until timeout
                print("Camera " + str(camNr) + ": Fetch buffer (try " + str(loop) + ")...", end='\r')
                with self.GigE[camNr].fetch_buffer(timeout=self.fetchTimeout) as buffer:
                    print("Camera " + str(camNr) + ": Fetched (try " + str(loop) + ")", end='\r')
                    # access the image payload
                    component = buffer.payload.components[0]

                    if component is not None:
                        image = component.data.reshape(component.height, component.width)
                        # BayerRG -> RGB (Does not work proper when scaled down)
                        image = cv2.cvtColor(image, cv2.COLOR_BayerRG2RGB)
                        return image
            except self.TimeoutException:
                print("Camera " + str(camNr) + ": Fetch timeout (try " + str(loop) + ")")
            except KeyboardInterrupt:
                print("Camera " + str(camNr) + ": Fetch interrupted by user (try " + str(loop) + ")")
            except:
                print("Camera " + str(camNr) + ": Unexpected error (try " + str(loop) + ")")

            if loop >= self.fetchSoftReboot:
                print("Camera" + str(camNr) + ": Failed...trying soft reboot (try " + str(loop) + ")")
                self.SoftReboot()

            if loop >= self.fetchAbort:
                print("Check camera" + str(camNr) + ": Too manny tries (try " + str(loop) + " of " + str(
                    self.fetchAbort) + ")")
                fetchImage = False

        # Something went wrong
        return False

    # Get camera temperature
    def getTemperature(self, camNr):
        return float(self.GigE[camNr].remote_device.node_map.DeviceTemperatureRaw.value / 100)

    # Return thermal performance of the camera
    def thermalCondition(self):
        for i in range(0, self.n_camera):
            temp = self.getTemperature(i)
            if temp > self.criticalTemp:
                self.warnings.warn("Camera temperature critical")
                return "Critical"
            elif temp > self.warningTemp:
                self.warnings.warn("Camera temperature above " + str(self.warningTemp))
                return "Warning"
        return "Normal"

    # Get camera features
    def getCameraAttributes(self):
        return dir(self.GigE[0].remote_device.node_map)

    # Stop image acquisition
    def Stop(self):
        print("Stop image acquisition")
        for i in range(0, len(self.GigE)):
            self.GigE[i].stop_acquisition()

    # Stop image acquisition
    def Destroy(self):
        print("Destroy image acquire objects")
        for i in range(0, len(self.GigE)):
            self.GigE[i].destroy()

    # Reset harvester
    def Reset(self):
        self.harvester.reset()

    # Soft reboot
    def SoftReboot(self):
        self.Stop()
        self.Start()
