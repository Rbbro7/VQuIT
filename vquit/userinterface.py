from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRegularExpression
from PyQt5.QtWidgets import QMainWindow

import ctypes

from time import sleep

from vquit import ProductData

ProductData = ProductData()


class Application(QMainWindow):

    def __init__(self, helperVariables, executionFunctions):
        # Bind to a QMainWindow instance
        super(Application, self).__init__()

        # Init GUI parameter data
        self.data_productName = None
        self.data_acode = None
        self.data_sn = None

        self.data_Top_ExposureTime = None
        self.data_Top_Gain = None
        self.data_Top_BlackLevel = None
        self.data_Top_Lighting = None

        self.data_Bottom_ExposureTime = None
        self.data_Bottom_Gain = None
        self.data_Bottom_BlackLevel = None
        self.data_Bottom_Lighting = None

        # Standard messages
        self.productInfoLabel1_Text = "Choose of one the following methods to scan a product:"
        self.productInfoLabel1_Text += "\n- Scan article code"
        self.productInfoLabel1_Text += "\n- Select a product in the drop down menu"
        self.productInfoLabel1_Text += "\n- Enter article code manually"

        # Setup execution handler thread
        self.exeHandlerThread = ExecutionHandler()  # Create update thread
        self.exeHandlerThread.Setup(executionFunctions, self.GetBatchSize)  # Set variables of thread
        self.exeHandlerThread.executionState.connect(self.UpdateGUI_state)  # Connect thread signal to class function
        self.exeHandlerThread.start()  # Start thread

        # Setup GUI update thread
        self.updateThread = UpdateThread()  # Create update thread
        self.updateThread.Setup(helperVariables)  # Set variables of thread
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
        self.previewWindowHeight = round(0.5 * (((self.windowWidth / 3) * 2) - (2 * self.previewWindowOffset)))
        self.previewWindowWidth = self.previewWindowHeight * 2

        self.image = QtWidgets.QLabel(self)
        self.image.setScaledContents(True)
        self.image.setGeometry(self.previewWindowOffset, self.previewWindowOffset, self.previewWindowWidth,
                               self.previewWindowHeight)
        self.image.setPixmap(QtGui.QPixmap("assets/previewWindow.png"))

        # Tool visualisation
        self.toolStateOffset = 20
        self.toolStateWidth = round(self.windowWidth / 5) - (2 * self.toolStateOffset)
        self.toolStateX = self.windowWidth - (self.toolStateWidth + self.toolStateOffset)
        self.toolStateY = self.windowHeight - (self.toolStateWidth + self.toolStateOffset)

        self.toolState = QtWidgets.QLabel(self)
        self.toolState.setScaledContents(True)
        self.toolState.setGeometry(self.toolStateX, self.toolStateY, self.toolStateWidth,
                                   self.toolStateWidth)
        self.toolState.setPixmap(QtGui.QPixmap("assets/openState.png"))

        ############
        # TAB MENU #
        ############
        ####################
        # Product Info Tab #
        ####################

        # Create widgets
        # Product selector label
        self.productSelector_PI_Label = QtWidgets.QLabel(self)
        self.productSelector_PI_Label.setText("Product type: ")
        self.productSelector_PI_Label.adjustSize()

        self.productSelector_S_Label = QtWidgets.QLabel(self)
        self.productSelector_S_Label.setText("Product type: ")
        self.productSelector_S_Label.adjustSize()

        # Product selector dropdown menu
        self.productSelector_PI = QtWidgets.QComboBox()
        self.productSelector_PI.setMinimumHeight(35)

        self.productSelector_S = QtWidgets.QComboBox()
        self.productSelector_S.setMinimumHeight(35)

        # Get data for dropdown menu
        dropDownList_PI = ["Automatic", "Manual"]
        dropDownList_S = ["New product"]
        for product in ProductData.GetProductList():
            # Don't add default to drop down menu
            if product != "DEFAULT":
                dropDownList_PI.append(product)
                dropDownList_S.append(product)

        # Add data to dropdown
        self.productSelector_PI.addItems(dropDownList_PI)
        self.productSelector_PI.currentIndexChanged.connect(self.OnChange_PI_Dropdown)

        self.productSelector_S.addItems(dropDownList_S)
        self.productSelector_S.currentIndexChanged.connect(self.OnChange_S_Dropdown)

        # Create product selector group
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.productSelector_PI_Label, 0, 0)
        layout.addWidget(self.productSelector_PI, 0, 1)
        layout.setColumnStretch(1, 1)  # Stretch selector
        self.productSelectorGroup_PI = QtWidgets.QWidget()
        self.productSelectorGroup_PI.setLayout(layout)
        self.productSelectorGroup_PI.setStyleSheet("QLabel { color: white }")

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.productSelector_S_Label, 0, 0)
        layout.addWidget(self.productSelector_S, 0, 1)
        layout.setColumnStretch(1, 1)  # Stretch selector
        self.productSelectorGroup_S = QtWidgets.QWidget()
        self.productSelectorGroup_S.setLayout(layout)
        self.productSelectorGroup_S.setStyleSheet("QLabel { color: white }")

        # Create widgets
        self.productInfoLabel1 = QtWidgets.QLabel(self)
        self.productInfoLabel1.setText(self.productInfoLabel1_Text)
        self.productInfoLabel1.adjustSize()

        self.productInfoLabel2 = QtWidgets.QLabel(self)
        self.productInfoLabel2.setText("")
        self.productInfoLabel2.adjustSize()

        self.acodeInputField = QtWidgets.QLineEdit(self)
        self.acodeInputField.setPlaceholderText("Type acode here")
        self.acodeInputField.setStyleSheet("QLineEdit { background-color: #4f4f4f };")
        self.acodeInputField.setVisible(False)
        self.acodeInputField.adjustSize()

        validator = QtGui.QRegularExpressionValidator(self)
        # Allowed: numbers (4 to 26 characters and first character cannot be 0)
        validator.setRegularExpression(QRegularExpression("([1-9]{1}[0-9]{3,25})"))
        self.acodeInputField.setValidator(validator)

        self.snInputField = QtWidgets.QLineEdit(self)
        self.snInputField.setPlaceholderText("Type serial number here")
        self.snInputField.setStyleSheet("QLineEdit { background-color: #4f4f4f };")
        self.snInputField.setVisible(False)
        self.snInputField.adjustSize()

        validator = QtGui.QRegularExpressionValidator(self)
        # Allowed: numbers and letters (4 to 26 characters)
        validator.setRegularExpression(QRegularExpression("([A-Za-z0-9]{4,26})"))
        self.snInputField.setValidator(validator)

        self.settingsInputFields = []
        settingsInputFieldsPlaceholder = ["product name", "acode", "exposure time", "gain", "black level",
                                          "exposure time", "gain", "black level"]

        # Create input fields for each placeholder
        for field in range(0, len(settingsInputFieldsPlaceholder)):
            settingsInputField = QtWidgets.QLineEdit(self)
            settingsInputField.setPlaceholderText(settingsInputFieldsPlaceholder[field])
            settingsInputField.setStyleSheet("QLineEdit { background-color: #4f4f4f };")
            settingsInputField.adjustSize()
            self.settingsInputFields.append(settingsInputField)

        self.confirmButton = QtWidgets.QPushButton(self)
        self.confirmButton.setText("Confirm")
        self.confirmButton.setMinimumHeight(50)
        self.confirmButton.clicked.connect(self.OnConfirmButtonClick)
        self.confirmButton.setStyleSheet("QPushButton { color: black }")
        self.confirmButton.setVisible(False)
        self.confirmButton.adjustSize()

        self.saveButton = QtWidgets.QPushButton(self)
        self.saveButton.setText("Save")
        self.saveButton.setMinimumHeight(50)
        self.saveButton.clicked.connect(self.OnSaveButtonClick)
        self.saveButton.setStyleSheet("QPushButton { color: black }")
        self.saveButton.adjustSize()

        # Combine widgets in layouts
        # Add widgets to info group
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.productInfoLabel1, 0, 0)
        layout.addWidget(self.acodeInputField, 1, 0)
        layout.addWidget(self.snInputField, 2, 0)
        layout.addWidget(self.productInfoLabel2, 3, 0)
        layout.addWidget(self.confirmButton, 5, 0)
        layout.setRowStretch(4, 1)  # Makes sure content is aligned to top and confirm button is placed at the bottom
        self.productInfoGroup = QtWidgets.QGroupBox("Product info")
        self.productInfoGroup.setLayout(layout)
        self.productInfoGroup.setStyleSheet("color: white")

        # Add widgets to settings group
        layout = QtWidgets.QGridLayout()

        row = 0  # Keep track of rows
        field = 0  # Keep track of input fields

        # Product name
        validator = QtGui.QRegularExpressionValidator(self)
        # First char: uppercase or number
        # Other char: letters, numbers, and -
        # Max 5 words, start word with uppercase or number,max 19 char per word
        validator.setRegularExpression(QRegularExpression(
            "([A-Z0-9]{1}[A-Za-z0-9-]{0,18})( {1}[A-Z0-9]{1}[A-Za-z0-9-]{0,18}){0,4}"))
        self.settingsInputFields[field].setValidator(validator)
        layout.addWidget(QtWidgets.QLabel("Product name"), row, 0)
        layout.addWidget(self.settingsInputFields[field], row, 1)
        row += 1
        field += 1

        # Acode
        validator = QtGui.QRegularExpressionValidator(self)
        # Allowed: numbers (4 to 26 characters and first character cannot be 0)
        validator.setRegularExpression(QRegularExpression("([1-9]{1}[0-9]{3,25})"))
        self.settingsInputFields[field].setValidator(validator)
        layout.addWidget(QtWidgets.QLabel("Acode"), row, 0)
        layout.addWidget(self.settingsInputFields[field], row, 1)
        row += 1
        field += 1

        # Top camera settings
        layout.addWidget(QtWidgets.QLabel("\nTop camera settings"), row, 0, 1, 2)
        row += 1

        # Exposure time (Top)
        validator = QtGui.QIntValidator(40, 2000000, self)  # Set validation properties of field
        self.settingsInputFields[field].setValidator(validator)
        layout.addWidget(QtWidgets.QLabel("Exposure time"), row, 0)
        layout.addWidget(self.settingsInputFields[field], row, 1)
        row += 1
        field += 1

        # Gain (Top)
        validator = QtGui.QIntValidator(0, 480, self)  # Set validation properties of field
        self.settingsInputFields[field].setValidator(validator)
        layout.addWidget(QtWidgets.QLabel("Gain"), row, 0)
        layout.addWidget(self.settingsInputFields[field], row, 1)
        row += 1
        field += 1

        # Black level (Top)
        validator = QtGui.QIntValidator(0, 4095, self)  # Set validation properties of field
        self.settingsInputFields[field].setValidator(validator)
        layout.addWidget(QtWidgets.QLabel("Black level"), row, 0)
        layout.addWidget(self.settingsInputFields[field], row, 1)
        row += 1
        field += 1

        # Lighting (Top)
        layout.addWidget(QtWidgets.QLabel("Lighting"), row, 0)
        layout.addWidget(QtWidgets.QLabel("Coming soon"), row, 1)
        row += 1

        # Bottom camera settings
        layout.addWidget(QtWidgets.QLabel("\nBottom camera settings"), row, 0, 1, 2)
        row += 1

        # Exposure time (Bottom)
        validator = QtGui.QIntValidator(40, 2000000, self)  # Set validation properties of field
        self.settingsInputFields[field].setValidator(validator)
        layout.addWidget(QtWidgets.QLabel("Exposure time"), row, 0)
        layout.addWidget(self.settingsInputFields[field], row, 1)
        row += 1
        field += 1

        # Gain (Bottom)
        validator = QtGui.QIntValidator(0, 480, self)  # Set validation properties of field
        self.settingsInputFields[field].setValidator(validator)
        layout.addWidget(QtWidgets.QLabel("Gain"), row, 0)
        layout.addWidget(self.settingsInputFields[field], row, 1)
        row += 1
        field += 1

        # Black level (Bottom)
        validator = QtGui.QIntValidator(0, 4095, self)  # Set validation properties of field
        self.settingsInputFields[field].setValidator(validator)
        layout.addWidget(QtWidgets.QLabel("Black level"), row, 0)
        layout.addWidget(self.settingsInputFields[field], row, 1)
        row += 1
        field += 1

        # Lighting (Bottom)
        layout.addWidget(QtWidgets.QLabel("Lighting"), row, 0)
        layout.addWidget(QtWidgets.QLabel("Coming soon"), row, 1)
        row += 2

        # Lighting (Bottom)
        layout.addWidget(self.saveButton, row, 0, 1, 2)

        layout.setRowStretch(row - 1, 1)  # Makes sure content is aligned to top and button to bottom
        layout.setColumnStretch(1, 1)  # Makes sure content is aligned to left
        self.settingsGroup = QtWidgets.QGroupBox("Settings")
        self.settingsGroup.setLayout(layout)
        self.settingsGroup.setStyleSheet("color: white")

        # Create product info tab
        # Combine drop down menu and info group
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.productSelectorGroup_PI, 0, 0)
        layout.addWidget(self.productInfoGroup, 1, 0)
        layout.setRowMinimumHeight(0, 70)
        self.productInfoTab = QtWidgets.QWidget()
        self.productInfoTab.setLayout(layout)

        # Create settings tab
        # Combine drop down menu and info group
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.productSelectorGroup_S, 0, 0)
        layout.addWidget(self.settingsGroup, 1, 0)
        layout.setRowMinimumHeight(0, 70)
        self.settingsTab = QtWidgets.QWidget()
        self.settingsTab.setLayout(layout)

        #################################################################

        self.tabMenuOffset = 20
        self.tabMenuX = self.previewWindowWidth + self.tabMenuOffset + 20
        self.tabMenuHeight = self.previewWindowHeight - self.tabMenuOffset
        self.tabMenuWidth = self.windowWidth - self.previewWindowWidth - (self.tabMenuOffset * 2) - 20

        self.tabMenu = QtWidgets.QTabWidget(self)
        self.tabMenu.addTab(self.productInfoTab, "Product Info")
        self.tabMenu.addTab(self.settingsTab, "Settings")
        self.productInfoTab.setObjectName("tab1")
        self.settingsTab.setObjectName("tab2")

        self.tabMenu.setStyleSheet("QWidget#tab1 { background-color: #4f4f4f };")
        self.tabMenu.setStyleSheet("QWidget#tab2 { background-color: #4f4f4f };")
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

        # Prevent program from being started prematurely
        self.executionButton.setEnabled(False)

        # Shutdown button
        self.shutdownButtonOffset = 20
        self.shutdownButtonHeight = 60
        self.shutdownButtonWidth = 60
        self.shutdownButtonX = self.shutdownButtonOffset
        self.shutdownButtonY = self.windowHeight - (self.shutdownButtonHeight + self.shutdownButtonOffset)

        self.shutdownButton = QtWidgets.QPushButton(self)
        self.shutdownButton.setGeometry(self.shutdownButtonX, self.shutdownButtonY, self.shutdownButtonWidth,
                                        self.shutdownButtonHeight)
        self.shutdownButton.setText("Shutdown")
        self.shutdownButton.setStyleSheet("color: white; background-color: red")
        self.shutdownButton.clicked.connect(self.OnShutdownButtonClick)

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

        # Prefill settings tab with data
        self.OnChange_S_Dropdown()

    # Set slider based on remaining batch
    def SetRemainingBatch(self, value):
        if value > 0:
            self.slider.setValue(value)
        else:
            # Change execution mode to Idle
            self.exeHandlerThread.RequestExecutionChange(0)

    # Used by external threads to get the current batchSize
    def GetBatchSize(self):
        return self.slider.value()

    # Set value of progressbar
    def SetProgressbar(self, value):
        self.progressbar.setValue(value)

    # Set value of progressbar
    def UpdateImagePreview(self, value):
        self.image.setPixmap(QtGui.QPixmap(value))

    # Set value of progressbar
    def UpdateToolStateImage(self, state):
        if state == "open":
            self.toolState.setPixmap(QtGui.QPixmap("assets/openState.png"))
        elif state == "closed":
            self.toolState.setPixmap(QtGui.QPixmap("assets/closedState.png"))

    # Enable or disable GUI settings
    def EnableSettings(self, value):
        self.productSelector_PI.setEnabled(value)
        self.slider.setEnabled(value)
        self.confirmButton.setVisible(value)

    # Update signal based GUI elements (used by executionHandler)
    def UpdateGUI_state(self, state):
        if state is 1:
            # Update GUI to active mode
            self.Processing = True

            # Update slider text
            self.sliderLabel.setText("Remaining batch: " + str(self.slider.value()))
            self.sliderLabel.adjustSize()

            # Set button text
            self.executionButton.setText("Stop Program")

            # Resize objects
            # Work in progress potential solution:
            # https://stackoverflow.com/questions/50611712/qt-resize-layout-during-widget-property-animation
            # self.tabMenu.resize(QSize(250, self.tabMenuHeight))

            # Update tool image
            self.UpdateToolStateImage("closed")

            # Disable settings
            self.EnableSettings(False)
        elif state is 0:
            # Update GUI to idle mode

            # Update slider text
            self.sliderLabel.setText("Batch size: " + str(self.slider.value()))
            self.sliderLabel.adjustSize()

            # Set button text
            self.executionButton.setText("Start Program")

            # Resize objects
            # self.tabMenu.resize(QSize(self.tabMenuWidth, self.tabMenuHeight))

            # Update tool image
            self.UpdateToolStateImage("open")

            # Enable settings
            self.EnableSettings(True)

            # Make execution button available again
            self.executionButton.setEnabled(True)

            self.Processing = False

    Processing = False

    # Update data shown in the GUI
    def UpdateGUI_data(self):
        if self.data_productName is not None:
            # Set new label text for selected product
            productInfoLabel1 = "Product name: " + str(self.data_productName) + \
                                "\nAcode: " + str(self.data_acode)
            if self.data_sn is not None:
                productInfoLabel1 += "\nSerial number: " + str(self.data_sn)

            productInfoLabel2 = "\nTop camera settings:"
            productInfoLabel2 += "\nExposure time: " + str(self.data_Top_ExposureTime)
            productInfoLabel2 += "\nGain: " + str(self.data_Top_Gain)
            productInfoLabel2 += "\nBlack level: " + str(self.data_Top_BlackLevel)
            productInfoLabel2 += "\nLighting: " + str(self.data_Top_Lighting)

            productInfoLabel2 += "\n\nBottom camera settings:"
            productInfoLabel2 += "\nExposure time: " + str(self.data_Bottom_ExposureTime)
            productInfoLabel2 += "\nGain: " + str(self.data_Bottom_Gain)
            productInfoLabel2 += "\nBlack level: " + str(self.data_Bottom_BlackLevel)
            productInfoLabel2 += "\nLighting: " + str(self.data_Bottom_Lighting)

        else:
            # Set label text to default
            productInfoLabel1 = self.productInfoLabel1_Text
            productInfoLabel2 = ""

        self.productInfoLabel1.setText(productInfoLabel1)
        self.productInfoLabel2.setText(productInfoLabel2)

        # Update fields
        self.productInfoLabel1.adjustSize()
        self.productInfoLabel2.adjustSize()
        self.snInputField.adjustSize()
        self.acodeInputField.adjustSize()
        self.confirmButton.adjustSize()

    # Update dropdown menus
    def UpdateDropDownMenus(self):

        # Get data for dropdown menu
        dropDownList_PI = ["Automatic", "Manual"]
        dropDownList_S = ["New product"]
        for product in ProductData.GetProductList():
            # Don't add default to drop down menu
            if product != "DEFAULT":
                dropDownList_PI.append(product)
                dropDownList_S.append(product)

        # Store original index length
        originalIndexLength_PI = self.productSelector_PI.count()
        originalIndexLength_S = self.productSelector_S.count()

        # Add data to dropdown
        self.productSelector_PI.addItems(dropDownList_PI)
        self.productSelector_S.addItems(dropDownList_S)

        # Remove all old indices
        for index in range(0, originalIndexLength_PI):
            self.productSelector_PI.removeItem(0)

        for index in range(0, originalIndexLength_S):
            self.productSelector_S.removeItem(0)

    # Retrieve data from database
    def GetProductData(self, productName=None, acode=None, returnValues=None):
        if acode is not None:
            # Get product data based on acode
            productInfo = ProductData.GetProductInfo(acode=acode)
        elif productName is not None:
            # Get product data based on product name
            productInfo = ProductData.GetProductInfo(productName=productName)
        else:
            raise ValueError("Enter a product name or serial number to retrieve product data from the database")

        # Check if retrieved data is valid
        if isinstance(productInfo, dict):

            # Check if data should be stored or returned
            if returnValues is None:
                self.data_productName = productInfo["ProductName"]
                self.data_acode = productInfo["Acode"]

                # Top camera settings
                topCameraConfig = productInfo["Configuration"]["TopCameras"]
                self.data_Top_ExposureTime = topCameraConfig["ExposureTime"]
                self.data_Top_Gain = topCameraConfig["Gain"]
                self.data_Top_BlackLevel = topCameraConfig["BlackLevel"]

                self.data_Top_Lighting = []
                for lights in topCameraConfig["Lighting"]["U"]:
                    self.data_Top_Lighting.append(lights)
                for lights in topCameraConfig["Lighting"]["D"]:
                    self.data_Top_Lighting.append(lights)

                # Bottom camera settings
                bottomCameraConfig = productInfo["Configuration"]["BottomCameras"]
                self.data_Bottom_ExposureTime = bottomCameraConfig["ExposureTime"]
                self.data_Bottom_Gain = bottomCameraConfig["Gain"]
                self.data_Bottom_BlackLevel = bottomCameraConfig["BlackLevel"]

                self.data_Bottom_Lighting = []
                for lights in bottomCameraConfig["Lighting"]["U"]:
                    self.data_Bottom_Lighting.append(lights)
                for lights in bottomCameraConfig["Lighting"]["D"]:
                    self.data_Bottom_Lighting.append(lights)

                # Verify successful data retrieval
                return True
            else:
                return productInfo
        else:
            # Product not found in database
            return False

    # Reset local product data
    def ClearProductData(self):
        self.data_productName = None
        self.data_acode = None
        self.data_sn = None

        self.data_Top_ExposureTime = None
        self.data_Top_Gain = None
        self.data_Top_BlackLevel = None
        self.data_Top_Lighting = None

        self.data_Bottom_ExposureTime = None
        self.data_Bottom_Gain = None
        self.data_Bottom_BlackLevel = None
        self.data_Bottom_Lighting = None

    # Default selection state
    currentIdentifierMethod = "auto"
    selectionState = "fixed"

    # Set state of GUI (confirmed vs unconfirmed state)
    def ChangeSelectionState(self):
        if self.selectionState is "malleable":
            # Prevent program from being started
            self.executionButton.setEnabled(False)

            # Enable tabs
            self.tabMenu.setTabEnabled(1, True)

            # Enable product selector
            self.productSelector_PI.setEnabled(True)

            # Clear previous data
            self.ClearProductData()

            # Show input fields and confirm button
            if self.currentIdentifierMethod is not "auto":
                self.snInputField.setVisible(True)
                self.data_sn = None

                # Show confirmation button
                self.confirmButton.setVisible(True)
                self.confirmButton.setText("Confirm")

                if self.currentIdentifierMethod == "dropdown":
                    # Hide field to enter acode
                    self.acodeInputField.setVisible(False)

                    # Update GUI with product data from dropdown menu
                    self.GetProductData(productName=self.productSelector_PI.currentText())
                else:
                    # Show input fields for manual mode
                    self.acodeInputField.setVisible(True)
            else:
                # Hide input fields
                self.confirmButton.setVisible(False)
                self.acodeInputField.setVisible(False)
                self.snInputField.setVisible(False)

        elif self.selectionState is "fixed":
            invalidSn = False
            invalidAcode = False

            if self.currentIdentifierMethod == "auto":
                # Hide change/confirm button on automatic mode
                self.confirmButton.setVisible(False)
            else:
                # Get location of sn validator
                validatorLocation = self.snInputField.validator()

                # Check if location exists
                if validatorLocation is not None:

                    # Retrieve state and value from validator
                    state, value, _ = validatorLocation.validate(self.snInputField.text(), 0)

                    # Store value if input is valid
                    if state == QtGui.QValidator.Acceptable:
                        self.data_sn = value
                    else:
                        invalidSn = True
                else:
                    print("Missing validator")
                    invalidSn = True

                # Search for product if manual
                if self.currentIdentifierMethod == "manual":

                    # Get location of acode validator
                    validatorLocation = self.acodeInputField.validator()

                    # Check if location exists
                    if validatorLocation is not None:

                        # Retrieve state and value from validator
                        state, value, _ = validatorLocation.validate(self.acodeInputField.text(), 0)

                        # Check if input value is valid
                        if state == QtGui.QValidator.Acceptable:
                            # Search for product
                            verification = self.GetProductData(acode=value)

                            # Check if product is found in database
                            if verification is False:
                                invalidAcode = True
                        else:
                            invalidAcode = True
                    else:
                        print("Missing validator")
                        invalidSn = True

            # Only continue if data is valid
            if invalidSn is False and invalidAcode is False:
                # Change button text
                self.confirmButton.setText("Change")

                # Go to main tab and lock tabs
                self.tabMenu.setCurrentIndex(0)
                self.tabMenu.setTabEnabled(1, False)

                # Disable product selector
                self.productSelector_PI.setEnabled(False)

                # Allow program to start
                self.executionButton.setEnabled(True)

            if invalidSn is False:
                self.snInputField.setVisible(False)
            if invalidAcode is False:
                self.acodeInputField.setVisible(False)

        # Update GUI data
        self.UpdateGUI_data()

    # Execute when pressing start button
    def OnButtonClick(self):
        # Disable stop button when pressed and program is not finished
        if self.executionButton.text() == "Stop Program":
            self.executionButton.setText("Aborting...")
            self.executionButton.setEnabled(False)
            state = 0
        else:
            state = 1

        # Request Execution change
        self.exeHandlerThread.RequestExecutionChange(state)

    # Execute when pressing confirm button
    def OnConfirmButtonClick(self):
        # Only update when identifier method is not automatic
        if self.currentIdentifierMethod != "auto":
            buttonText = self.confirmButton.text()

            if buttonText == "Change":
                self.selectionState = "malleable"
            elif buttonText == "Confirm":
                self.selectionState = "fixed"

            self.ChangeSelectionState()

    def OnShutdownButtonClick(self):
        print(self.shutdownButton.text())

    # Execute when pressing save button
    def OnSaveButtonClick(self):
        # Get array of input fields
        inputFields = self.settingsInputFields

        # Create array to store field inputs
        fieldValues = []

        # Track invalid fields
        invalidFields = 0

        # Retrieve and validate data from input fields
        for field in range(0, len(inputFields)):
            # Get location of linked validator
            validatorLocation = inputFields[field].validator()

            # Check if location exists
            if validatorLocation is not None:

                # Retrieve state and value from validator
                state, value, _ = validatorLocation.validate(inputFields[field].text(), 0)

                # Disregard value if input is invalid
                if state != QtGui.QValidator.Acceptable:
                    value = None
                    invalidFields += 1
            else:
                # Field does not have validator
                value = inputFields[field].text()
                print("No validator found")

            # Store value
            fieldValues.append([field, value])

        if invalidFields == 0:
            # Convert GUI input field data to json object
            jsonObject = ProductData.JsonfyProductInfo(fieldValues)

            # Append or modify database
            if self.addingNewProduct:
                # Append new product
                ProductData.WriteProductInfo(jsonObject, append=True)

            else:
                # modify Existing product
                ProductData.WriteProductInfo(jsonObject, overwrite=True)

            # Update drop down menus
            self.UpdateDropDownMenus()

            # Go to modified/added section
            newIndex_PI = self.productSelector_PI.findText(fieldValues[0][1])
            newIndex_S = self.productSelector_S.findText(fieldValues[0][1])
            self.productSelector_PI.setCurrentIndex(newIndex_PI)
            self.productSelector_S.setCurrentIndex(newIndex_S)

            # Go to main tab
            self.tabMenu.setCurrentIndex(0)

        else:
            print(str(invalidFields) + " invalid input(s)")  # Improve by specifying which field is invalid

    # Execute when Dropdown menu has changed
    def OnChange_PI_Dropdown(self):
        # Get selected product
        selectedProduct = self.productSelector_PI.currentText()

        # Make product data editable
        self.selectionState = "malleable"

        # Retrieve information on product from database
        if selectedProduct != "Automatic":
            if selectedProduct != "Manual":
                self.currentIdentifierMethod = "dropdown"
            else:
                self.currentIdentifierMethod = "manual"
        else:
            # Clear previous data
            self.currentIdentifierMethod = "auto"

        # Update selection state and update product data
        self.ChangeSelectionState()

    # Determine if new product is added or existing product is altered
    addingNewProduct = True

    # Execute when Dropdown menu has changed
    def OnChange_S_Dropdown(self):
        selectedProduct = self.productSelector_S.currentText()
        if selectedProduct == "New product":
            self.addingNewProduct = True
            self.settingsInputFields[0].setEnabled(True)  # Enable product name field
            selectedProduct = "DEFAULT"
        else:
            self.addingNewProduct = False
            self.settingsInputFields[0].setEnabled(False)  # Prevent product name from being changed
        productData = self.GetProductData(productName=selectedProduct, returnValues=True)

        # Prefill input fields
        if self.addingNewProduct:
            self.settingsInputFields[0].setText(str(""))
            self.settingsInputFields[1].setText(str(""))
        else:
            self.settingsInputFields[0].setText(str(selectedProduct))
            self.settingsInputFields[1].setText(str(productData["Acode"]))

        productData = productData["Configuration"]

        self.settingsInputFields[2].setText(str(productData["TopCameras"]["ExposureTime"]))
        self.settingsInputFields[3].setText(str(productData["TopCameras"]["Gain"]))
        self.settingsInputFields[4].setText(str(productData["TopCameras"]["BlackLevel"]))

        self.settingsInputFields[5].setText(str(productData["BottomCameras"]["ExposureTime"]))
        self.settingsInputFields[6].setText(str(productData["BottomCameras"]["Gain"]))
        self.settingsInputFields[7].setText(str(productData["BottomCameras"]["BlackLevel"]))

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
                if self.newExeState is 1:
                    # Execute start function
                    self.startFunction(self.getBatchSizeFunction())
                elif self.newExeState is 0:
                    # Execute abort function
                    self.abortFunction()

                # Send trigger to UI that execution mode has changed
                self.executionState.emit(self.newExeState)

                # Update internal state variable
                self.currentExeState = self.newExeState

            ####################
            # Update frequency #
            ####################

            sleep(0.1)

    def RequestExecutionChange(self, state):
        self.newExeState = state
