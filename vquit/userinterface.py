from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow

import ctypes

from time import sleep


class Application(QMainWindow):

    def __init__(self, guiProgressbarVars, guiImagePreviewVars, startFunction, abortFunction):
        # Bind to a QMainWindow instance
        super(Application, self).__init__()

        # Setup progressbar
        self.thread = ProgressbarThread()  # Create progressbar thread
        self.thread.Setup(guiProgressbarVars)  # Set variables of thread
        self.thread.progress.connect(self.SetProgressbar)  # Connect thread signal to class function
        self.thread.start()  # Start thread

        # Setup image preview
        self.imgThread = ImagePreviewThread()  # Create progressbar thread
        self.imgThread.Setup(guiImagePreviewVars)  # Set variables of thread
        self.imgThread.image.connect(self.UpdateImagePreview)  # Connect thread signal to class function
        self.imgThread.start()  # Start thread

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

        # Create start button
        self.startButton = QtWidgets.QPushButton(self)
        self.startButton.setText("Start Program")
        self.startButton.move(200, 700)
        self.startButton.clicked.connect(startFunction)

        # Create stop button
        self.abortButton = QtWidgets.QPushButton(self)
        self.abortButton.setText("Stop Program")
        self.abortButton.move(500, 700)
        self.abortButton.clicked.connect(abortFunction)

        # Image
        self.previewWindowWidth = round(self.windowWidth / 2)
        self.previewWindowHeight = round(self.windowHeight * (2 / 3))
        self.image = QtWidgets.QLabel(self)
        self.image.setGeometry(0, 0, self.previewWindowWidth, self.previewWindowHeight)
        self.image.setPixmap(QtGui.QPixmap("assets/previewWindow.png"))
        self.image.setScaledContents(True)

        # Create progressbar
        self.progressbarX = 20
        self.progressbarY = self.previewWindowHeight + self.progressbarX
        self.progressbarWidth = self.previewWindowWidth - self.progressbarX
        self.progressbar = QtWidgets.QProgressBar(self)
        self.progressbar.setRange(0, 100)
        self.progressbar.setGeometry(self.progressbarX, self.progressbarY, self.progressbarWidth, 20)
        self.SetProgressbar(0)

        self.show()

    # Set value of progressbar
    def SetProgressbar(self, value):
        self.progressbar.setValue(value)

    # Set value of progressbar
    def UpdateImagePreview(self, value):
        self.image.setPixmap(QtGui.QPixmap(value))


class ProgressbarThread(QThread):
    progressbarLock = None
    progressbarValue = None

    # Pass values for communication with multiprocessing
    def Setup(self, guiProgressbarVars):
        # Store multiprocessing value & lock objects
        [self.progressbarLock, self.progressbarValue] = guiProgressbarVars

    # Set signal that transports integers
    progress = pyqtSignal(int)

    # Executes when calling self.start()
    def run(self):
        # Keep looping
        while True:
            # Get current value
            with self.progressbarLock:
                currentProgress = self.progressbarValue.value

            # Send value to gui
            self.progress.emit(currentProgress)
            sleep(0.5)


class ImagePreviewThread(QThread):
    imgPreviewLock = None
    imgPreviewQue = None

    # Pass values for communication with multiprocessing
    def Setup(self, guiImagePreviewVars):
        # Store multiprocessing value & lock objects
        [self.imgPreviewLock, self.imgPreviewQue] = guiImagePreviewVars

    # Set signal that transports QImages
    image = pyqtSignal(QtGui.QImage)

    # Executes when calling self.start()
    def run(self):
        # Keep looping
        while True:
            # Rest new image
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

            sleep(0.5)
