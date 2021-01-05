# Image manipulation & analysis
class Image:
    # Filter parameters
    NR_Blur = 25

    # Packages
    cv2 = None
    np = None
    scipy = None
    ndimage = None

    def ImportOpenCV(self):
        if self.cv2 is None:
            print("Importing OpenCV")
            import cv2
            self.cv2 = cv2
        return self.cv2

    def ImportNumpy(self):
        if self.np is None:
            print("Importing Numpy")
            import numpy
            self.np = numpy
        return self.np

    def ImportScipy(self, ndimageOnly=None):
        if ndimageOnly is True:
            if self.ndimage is None:
                print("Importing ndimage")
                from scipy import ndimage
                self.ndimage = ndimage
            return self.ndimage
        elif self.np is None:
            print("Importing Scipy")
            import scipy
            self.scipy = scipy
        return self.scipy

    def BayerRGtoRGB(self, image):
        cv2 = self.ImportOpenCV()

        image = cv2.cvtColor(image, cv2.COLOR_BayerRG2RGB)
        return image

    def GraytoRGB(self, image):
        cv2 = self.ImportOpenCV()
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        return image

    # Color correction
    def ColorCorrection(self, image, ccTable):
        cv2 = self.ImportOpenCV()
        np = self.ImportNumpy()

        b, g, r = cv2.split(image)

        # Multiply color array by ID specific gain and clip at 255
        b = np.array(np.clip(b * ccTable[2], 0, 255), dtype=np.uint8)
        g = np.array(np.clip(g * ccTable[1], 0, 255), dtype=np.uint8)
        r = np.array(np.clip(r * ccTable[0], 0, 255), dtype=np.uint8)
        image = cv2.merge([b, g, r])

        return image

    def Blur(self, image):
        cv2 = self.ImportOpenCV()
        return cv2.blur(image, (5, 5))

    # Reduce binary noise by removing data groups smaller than the mask size
    def BinaryNoiseReduction(self, binaryImage):
        ndimage = self.ImportScipy(ndimageOnly=True)
        np = self.ImportNumpy()

        return ndimage.binary_opening(binaryImage, structure=np.ones((2, 2))).astype(self.np.bool)

    # Crop image to perform actions on specific parts
    @staticmethod
    def Crop(im, x0, x1, y0, y1):
        im = im[y0:y1, x0:x1]
        return im

    def Scale(self, image, multiplier=None, newHeight=None, newWidth=None):
        cv2 = self.ImportOpenCV()

        # Set new resolution
        if newHeight is not None and newWidth is not None:
            width = int(newWidth)
            height = int(newHeight)
        else:
            width = image.shape[1]
            height = image.shape[0]

        # Scale resolution with factor
        if multiplier is not None:
            width = int(width * multiplier)
            height = int(height * multiplier)

        dim = (width, height)
        image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

        return image

    def Gray(self, image):
        cv2 = self.ImportOpenCV()
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def Inverted(self, image):
        np = self.ImportNumpy()
        return np.array(image * 255, dtype=np.uint8)

    def NoiseReduction(self, image):
        cv2 = self.ImportOpenCV()
        return cv2.bilateralFilter(image, 7, 50, 50)

    # combine images into a grid
    def Grid(self, imageArray):
        np = self.ImportNumpy()
        r1 = np.hstack((imageArray[3], imageArray[1]))
        r2 = np.hstack((imageArray[2], imageArray[0]))
        return np.vstack((r1, r2))


ImageModule = Image()


# Image analysis
class OpenCV:
    cv2 = None
    np = None
    ksize = 25

    def ImportOpenCV(self):
        if self.cv2 is None:
            print("Importing OpenCV")
            import cv2
            self.cv2 = cv2
        return self.cv2

    def ImportNumpy(self):
        if self.np is None:
            print("Importing Numpy")
            import numpy
            self.np = numpy
        return self.np

    def ShowImage(self, title, image):
        cv2 = self.ImportOpenCV()
        cv2.imshow(title, image)

    def SaveAsPNG(self, name, image):
        cv2 = self.ImportOpenCV()
        cv2.imwrite(str(name) + '.png', image, [cv2.IMWRITE_PNG_COMPRESSION, 0])

    def Abort(self):
        self.ImportOpenCV()
        if self.cv2.waitKey(1) > 0:
            return True

    def Laplacian(self, im, filterScale, threshold, thresholdBlockSize):
        cv2 = self.ImportOpenCV()
        np = self.ImportNumpy()

        laplacian = cv2.Laplacian(im, cv2.CV_8U, self.ksize, filterScale)  # Apply filter
        laplacianThresh = laplacian > threshold * np.max(laplacian)  # Convert to binary
        laplacianThresh = ImageModule.BinaryNoiseReduction(laplacianThresh)
        laplacianThresh = np.array(laplacianThresh * 255, dtype=np.uint8)  # Convert to numerical
        thresholdConstant = 0  # Should be a value for non binary
        laplacianThresh = cv2.adaptiveThreshold(laplacianThresh, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
                                                thresholdBlockSize, thresholdConstant)
        return laplacian, laplacianThresh

    # OpenCV Image processing
    def EdgeDetection(self, image):

        # Sobel/Laplace parameters
        threshold = 0.05  # Stock recommended 0.3
        scale = 1
        thresholdBlockSize = 3

        laplacian, laplacianThresh = self.Laplacian(image, scale, threshold, thresholdBlockSize)

        return laplacianThresh

    # Variables
    imgW_px = 0
