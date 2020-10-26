from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow

import ctypes

from time import sleep

from vquit import ProductData

ProductData = ProductData()


class Application(QMainWindow):

    def __init__(self, helperVariables, executionFunctions):
        # Bind to a QMainWindow instance
        super(Application, self).__init__()

        # Setup execution handler thread
        self.exeHandlerThread = ExecutionHandler()  # Create update thread
        self.exeHandlerThread.Setup(executionFunctions, self.GetBatchSize)  # Set variables of thread
        self.exeHandlerThread.executionState.connect(self.UpdateGUI)  # Connect thread signal to class function
        self.exeHandlerThread.start()  # Start thread

        # Setup GUI update thread
        self.updateThread = UpdateThread()  # Create update thread
        self.updateThread.Setup(helperVariables)  # Set variables of thread
        self.updateThread.remainingBatch.connect(self.SetRemainingBatch)
        self.updateThread.progress.connect(self.SetProgressbar)
        self.updateThread.image.connect(self.UpdateImagePreview)
        self.updateThread.start()  # Start thread

        # Get screen size
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        [screenWidth, screenHeight] = [user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)]

        # Set window position and size
        xPosition = 100
        yPosition = 100
        self.windowWidth = screenWidth - (2 * xPosition)
        self.windowHeight = screenHeight - (2 * yPosition)
        self.setGeometry(xPosition, yPosition, self.windowWidth, self.windowHeight)

        # Set window title and icon
        self.setWindowTitle("Adimec VQuIT GUI")
        self.setWindowIcon(QtGui.QIcon("assets/icon.png"))

        # Set layout colors
        self.palette = QtGui.QPalette()
        self.palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
        self.palette.setColor(QtGui.QPalette.WindowText, Qt.white)
        self.setPalette(self.palette)

        #################
        # Create layout #
        #################

        # Image
        self.previewWindowOffset = 20
        self.previewWindowWidth = round(self.windowWidth / 2) - (2 * self.previewWindowOffset)
        self.previewWindowHeight = round(self.windowHeight * (2 / 3)) - (2 * self.previewWindowOffset)

        self.image = QtWidgets.QLabel(self)
        self.image.setScaledContents(True)
        self.image.setGeometry(self.previewWindowOffset, self.previewWindowOffset, self.previewWindowWidth,
                               self.previewWindowHeight)
        self.image.setPixmap(QtGui.QPixmap("assets/previewWindow.png"))

        ############
        # TAB MENU #
        ############
        ####################
        # Product Info Tab #
        ####################

        # Create widgets
        # Product selector label
        self.productSelectorLabel = QtWidgets.QLabel(self)
        self.productSelectorLabel.setText("Product type: ")
        self.productSelectorLabel.adjustSize()

        # Product selector dropdown menu
        self.productSelector = QtWidgets.QComboBox()
        self.productSelector.setMinimumHeight(35)
        self.productSelector.addItems(["Automatic", "Adimec Camera 1", "Adimec Camera 2"])
        self.productSelector.currentIndexChanged.connect(self.OnDropdownChange)

        # Create product selector group
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.productSelectorLabel, 0, 0)
        layout.addWidget(self.productSelector, 0, 1)
        layout.setColumnStretch(1, 1)  # Stretch selector
        self.productSelectorGroup = QtWidgets.QWidget()
        self.productSelectorGroup.setLayout(layout)
        self.productSelectorGroup.setStyleSheet("QLabel { color: white }")

        # Create widgets for info group
        # Product info labels
        self.acodeLabel = QtWidgets.QLabel(self)
        self.acodeLabel.setText("Acode: retrieving from image...")
        self.acodeLabel.adjustSize()

        self.otherLabel = QtWidgets.QLabel(self)
        self.otherLabel.setText("Other: retrieving from image...")
        self.otherLabel.adjustSize()

        # Combine widgets in layouts
        # Add widgets to info group
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.acodeLabel, 0, 0)
        layout.addWidget(self.otherLabel, 1, 0)
        layout.setRowStretch(2, 1)  # Makes sure content is aligned to top
        self.productInfoGroup = QtWidgets.QGroupBox("Product info")
        self.productInfoGroup.setLayout(layout)
        self.productInfoGroup.setStyleSheet("color: white")

        # Combine drop down menu and info group
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.productSelectorGroup, 0, 0)
        layout.addWidget(self.productInfoGroup, 1, 0)
        layout.setRowMinimumHeight(0, 70)
        self.productInfoTab = QtWidgets.QWidget()
        self.productInfoTab.setLayout(layout)

        #################################################################

        self.tabMenuOffset = 20
        self.tabMenuX = self.previewWindowWidth + self.tabMenuOffset + 20
        self.tabMenuHeight = self.previewWindowHeight - self.tabMenuOffset
        self.tabMenuWidth = self.windowWidth - self.previewWindowWidth - (self.tabMenuOffset * 2) - 20

        self.tabMenu = QtWidgets.QTabWidget(self)

        self.tabMenu.addTab(self.productInfoTab, "Product")
        self.tabMenu.addTab(QtWidgets.QLabel("Coming soon"), "Advanced settings")
        self.productInfoTab.setObjectName("tab1")

        self.tabMenu.setStyleSheet("QWidget#tab1 { background-color: #4f4f4f };")
        self.tabMenu.setGeometry(self.tabMenuX, self.tabMenuOffset, self.tabMenuWidth, self.tabMenuHeight)
        self.tabMenu.setAutoFillBackground(True)

        # layout = QtWidgets.QGridLayout()
        # layout.setContentsMargins(5, 5, 5, 5)
        #
        # layout.setColumnMinimumWidth(1, 200)
        # layout.setRowMinimumHeight(0, 500)
        # layout.setColumnStretch(0, 1)
        # layout.setRowStretch(0, 1)
        #
        # layout.addWidget(self.image, 0, 0)
        # layout.addWidget(self.tabMenu, 0, 1)
        #
        # self.mainLayout = QtWidgets.QWidget(self)
        # self.mainLayout.setLayout(layout)
        #
        # self.image.setPixmap(QtGui.QPixmap("assets/previewWindow.png"))
        # self.image.setScaledContents(True)

        #################################################################

        # Progressbar
        self.progressbarX = 20
        self.progressbarY = self.previewWindowHeight + self.progressbarX + 20
        self.progressbarWidth = self.previewWindowWidth - self.progressbarX
        self.progressbarHeight = 20

        self.progressbar = QtWidgets.QProgressBar(self)
        self.progressbar.setRange(0, 100)
        self.progressbar.setGeometry(self.progressbarX, self.progressbarY, self.progressbarWidth,
                                     self.progressbarHeight)
        self.SetProgressbar(0)

        # Slider
        self.sliderY = self.progressbarY + self.progressbarX + self.progressbarHeight
        self.sliderWidth = (self.progressbarWidth - self.progressbarX)

        self.slider = QtWidgets.QSlider(self)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setGeometry(self.progressbarX, self.sliderY, self.sliderWidth,
                                self.progressbarHeight)
        self.slider.setMinimum(1)
        self.slider.setMaximum(32)
        self.slider.setValue(1)
        self.slider.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.slider.setTickInterval(1)
        self.slider.setSingleStep(1)

        self.slider.valueChanged.connect(self.OnSliderChange)

        # Slider label
        self.sliderLabelX = self.progressbarWidth + 20
        self.sliderLabelY = self.sliderY
        self.sliderLabel = QtWidgets.QLabel(self)
        self.sliderLabel.move(self.sliderLabelX, self.sliderLabelY)
        self.sliderLabel.setText("Batch size: " + str(self.slider.value()))
        self.sliderLabel.adjustSize()

        # Execution button
        self.executionButtonHeight = 40
        self.executionButtonWidth = 350
        self.executionButtonX = round((self.previewWindowWidth / 2) - (self.executionButtonWidth / 2))
        self.executionButtonY = self.sliderY + 40

        self.executionButton = QtWidgets.QPushButton(self)
        self.executionButton.setGeometry(self.executionButtonX, self.executionButtonY, self.executionButtonWidth,
                                         self.executionButtonHeight)
        self.executionButton.setText("Start Program")
        self.executionButton.clicked.connect(self.OnButtonClick)

        # mainLayout = QtWidgets.QGridLayout()
        # mainLayout.addWidget(self.topLeftGroupBox, 0, 0)  # R1 C1
        # mainLayout.addWidget(self.topLeftGroupBox, 0, 1)  # R1 C2
        # mainLayout.setRowStretch(0, 1)
        # # mainLayout.setRowStretch(2, 1)
        # # mainLayout.setColumnStretch(0, 1)
        # # mainLayout.setColumnStretch(1, 1)
        # self.setLayout(mainLayout)

        self.setPalette(self.palette)
        self.show()

    # Set slider based on remaining batch
    def SetRemainingBatch(self, value):
        if value > 0:
            self.slider.setValue(value)
        else:
            # Change execution mode to Idle
            self.exeHandlerThread.RequestExecutionChange()

    # Used by external threads to get the current batchSize
    def GetBatchSize(self):
        return self.slider.value()

    # Set value of progressbar
    def SetProgressbar(self, value):
        self.progressbar.setValue(value)

    # Set value of progressbar
    def UpdateImagePreview(self, value):
        self.image.setPixmap(QtGui.QPixmap(value))

    # Enable or disable GUI settings
    def EnableSettings(self, value):
        self.productSelector.setEnabled(value)
        self.slider.setEnabled(value)

    # Update the GUI (called on signal state of executionHandler
    def UpdateGUI(self, state):
        if state is 1:
            # Update GUI to active mode
            self.Processing = True

            # Update slider text
            self.sliderLabel.setText("Remaining batch: " + str(self.slider.value()))
            self.sliderLabel.adjustSize()

            # Set button text
            self.executionButton.setText("Stop Program")

            # Disable settings
            self.EnableSettings(False)
        elif state is -1:
            # Update GUI to idle mode

            # Update slider text
            self.sliderLabel.setText("Batch size: " + str(self.slider.value()))
            self.sliderLabel.adjustSize()

            # Set button text
            self.executionButton.setText("Start Program")

            # Enable settings
            self.EnableSettings(True)

            # Make execution button available again
            self.executionButton.setEnabled(True)

            self.Processing = False

    Processing = False

    # Execute when pressing button
    def OnButtonClick(self):
        # Disable stop button when pressed and program is not finished
        if self.executionButton.text() == "Stop Program":
            self.executionButton.setText("Aborting...")
            self.executionButton.setEnabled(False)

        # Request Execution change
        self.exeHandlerThread.RequestExecutionChange()

    # Execute when Dropdown menu has changed
    def OnDropdownChange(self):
        # Get selected product
        selectedProduct = self.productSelector.currentText()

        # Retrieve information on product from database
        if selectedProduct != "Automatic":
            productInfo = ProductData.GetProductInfo(selectedProduct)
            acode = productInfo["Acode"]
            other = productInfo["Other"]
        else:
            acode = "retrieving from image..."
            other = "retrieving from image..."

        # Set new label text
        self.acodeLabel.setText("Acode: " + str(acode))
        self.otherLabel.setText("Other: " + str(other))

        # Update label size
        self.acodeLabel.adjustSize()
        self.otherLabel.adjustSize()

    # Execute when slider changes
    def OnSliderChange(self, value):
        if self.Processing is True:
            labelText = "Remaining batch: "
        else:
            labelText = "Batch size: "

        self.sliderLabel.setText(labelText + str(value))
        self.sliderLabel.adjustSize()


# Update GUI with data from software
class UpdateThread(QThread):
    # Batch
    batchLock = None
    batchValue = None
    currentRemainingBatch = 0

    # Progressbar
    progressbarLock = None
    progressbarValue = None
    currentProgress = 0

    # Image preview
    imgPreviewLock = None
    imgPreviewQue = None

    # Pass values for communication with multiprocessing
    def Setup(self, helperVariables):

        # Extract parameters from helper object
        guiBatchSizeRemainingVars, guiProgressbarVars, guiImagePreviewVars = helperVariables

        # Store multiprocessing value & lock objects
        [self.batchLock, self.batchValue] = guiBatchSizeRemainingVars
        [self.progressbarLock, self.progressbarValue] = guiProgressbarVars
        [self.imgPreviewLock, self.imgPreviewQue] = guiImagePreviewVars

    # Set signals that transport data
    remainingBatch = pyqtSignal(int)
    progress = pyqtSignal(int)
    image = pyqtSignal(QtGui.QImage)

    # Executes when calling self.start()
    def run(self):
        # Keep looping
        while True:

            #############
            # BatchSize #
            #############

            # Get current value
            with self.batchLock:
                newRemaining = self.batchValue.value

            # When value is different sent signal
            if newRemaining is not self.currentRemainingBatch:
                # Send value to gui
                self.remainingBatch.emit(newRemaining)
                self.currentRemainingBatch = newRemaining

            ###############
            # Progressbar #
            ###############

            # Get current value
            with self.progressbarLock:
                newProgress = self.progressbarValue.value

            # Cap progress at 100
            if newProgress > 100:
                newProgress = 100

            # When value is different sent signal
            if newProgress is not self.currentProgress:
                # Send value to gui
                self.progress.emit(newProgress)
                self.currentProgress = newProgress

            #################
            # Image preview #
            #################

            # Reset new image
            newImage = None

            # Check for new image in queue
            with self.imgPreviewLock:
                if self.imgPreviewQue.empty() is False:
                    newImage = self.imgPreviewQue.get()

            if newImage is not None:
                # Convert numpy array (opencv image) to QImage
                height, width, channel = newImage.shape
                bytesPerLine = 3 * width
                qImg = QtGui.QImage(newImage.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888).rgbSwapped()
                self.image.emit(qImg)

            ####################
            # Update frequency #
            ####################

            sleep(0.1)


# Control execution of software through GUI
class ExecutionHandler(QThread):
    # Execution handler
    startFunction = None
    abortFunction = None

    getBatchSizeFunction = None

    currentExeState = None
    newExeState = None

    # Pass values for communication with multiprocessing
    def Setup(self, executionFunctions, getBatchSizeFunction):
        # Store external execution functions
        (self.startFunction, self.abortFunction) = executionFunctions
        self.getBatchSizeFunction = getBatchSizeFunction

    # Set signal that transports data
    executionState = pyqtSignal(int)

    # Executes when calling self.start()
    def run(self):
        # Keep looping
        while True:

            #####################
            # Execution Handler #
            #####################

            # Check for a  request for execution state
            if self.currentExeState is not self.newExeState:
                if self.currentExeState is None or self.currentExeState is -1:
                    # Execute start function
                    self.startFunction(self.getBatchSizeFunction())
                    self.newExeState = 1
                else:
                    # Execute abort function
                    self.abortFunction()
                    self.newExeState = -1

                # Send trigger to UI that execution mode has changed
                self.executionState.emit(self.newExeState)

                # Update internal state variable
                self.currentExeState = self.newExeState

            ####################
            # Update frequency #
            ####################

            sleep(0.1)

    def RequestExecutionChange(self):
        if self.currentExeState is None or self.currentExeState is -1:
            self.newExeState = 1
        else:
            self.newExeState = -1
