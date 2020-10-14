# Image manipulation & analysis
class Image:
    # Filter parameters
    NR_Blur = 25
    cv2 = None
    np = None
    ndimage = None

    def Setup(self, OpenCV_module=None, NP_module=None, ndimage_module=None):
        # Store modules
        self.cv2 = OpenCV_module
        self.np = NP_module
        self.ndimage = ndimage_module

    def BayerRGtoRGB(self, image):
        image = self.cv2.cvtColor(image, self.cv2.COLOR_BayerRG2RGB)
        return image

    # Color correction
    def ColorCorrection(self, image, ccTable):
        b, g, r = self.cv2.split(image)

        # Multiply color array by ID specific gain and clip at 255
        b = self.np.array(self.np.clip(b * ccTable[2], 0, 255), dtype=self.np.uint8)
        g = self.np.array(self.np.clip(g * ccTable[1], 0, 255), dtype=self.np.uint8)
        r = self.np.array(self.np.clip(r * ccTable[0], 0, 255), dtype=self.np.uint8)
        image = self.cv2.merge([b, g, r])

        return image

    def Blur(self, image):
        return self.cv2.blur(image, (5, 5))

    # Reduce binary noise by removing data groups smaller than the mask size
    def BinaryNoiseReduction(self, imgBinary):
        imgBinary = self.ndimage.binary_opening(imgBinary, structure=self.np.ones((2, 2))).astype(self.np.bool)
        return imgBinary

    # Crop image to perform actions on specific parts
    @staticmethod
    def Crop(im, x0, x1, y0, y1):
        im = im[y0:y1, x0:x1]
        return im

    def Scale(self, image, multiplier=None, newHeight=None, newWidth=None):
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
        image = self.cv2.resize(image, dim, interpolation=self.cv2.INTER_AREA)

        return image

    def Gray(self, image):
        return self.cv2.cvtColor(image, self.cv2.COLOR_BGR2GRAY)

    def Inverted(self, image):
        return self.np.array(image * 255, dtype=self.np.uint8)

    def NoiseReduction(self, image):
        return self.cv2.bilateralFilter(image, 7, 50, 50)


# Image analysis
class OpenCV:
    cv2 = None
    np = None
    ksize = 25

    def Setup(self, OpenCV_module=None, NP_module=None):
        self.cv2 = OpenCV_module
        self.np = NP_module

    def Abort(self):
        if self.cv2.waitKey(1) > 0:
            return True

    def Sobel(self, im, scale, threshold, orientation, cv2=None, np=None):
        if orientation == 0:
            sobel = cv2.Sobel(im, cv2.CV_8U, 1, 0, self.ksize, scale)  # Sobel X
        else:
            sobel = cv2.Sobel(im, cv2.CV_8U, 0, 1, self.ksize, scale)  # Sobel Y

        sobelThresh = sobel > threshold * np.max(sobel)  # Remove values under threshold
        sobelThresh = Image.BinaryNoiseReduction(sobelThresh)
        sobelThresh = np.array(sobelThresh * 255, dtype=np.uint8)  # Convert to UMat type
        sobelThresh = cv2.adaptiveThreshold(sobelThresh, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 3, 0)
        return sobel, sobelThresh

    def Laplacian(self, im, filterScale, threshold, thresholdBlockSize, Image_module):
        laplacian = self.cv2.Laplacian(im, self.cv2.CV_8U, self.ksize, filterScale)  # Apply filter
        laplacianThresh = laplacian > threshold * self.np.max(laplacian)  # Convert to binary
        laplacianThresh = Image_module.BinaryNoiseReduction(laplacianThresh)
        laplacianThresh = self.np.array(laplacianThresh * 255, dtype=self.np.uint8)  # Convert to numerical
        thresholdConstant = 0  # Should be a value for non binary
        laplacianThresh = self.cv2.adaptiveThreshold(laplacianThresh, 255, self.cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                     self.cv2.THRESH_BINARY, thresholdBlockSize, thresholdConstant)
        return laplacian, laplacianThresh

    @staticmethod
    def Canny(im, cv2=None):
        canny = cv2.Canny(im, 60, 120)
        return canny

    # OpenCV Image processing
    def EdgeDetection(self, image, screenHeight, Image_module):
        imgHeight = len(image)
        imgWidth = len(image[0])
        imgW_px = int(screenHeight * (imgWidth / imgHeight))

        # Sobel/Laplace parameters
        threshold = 0.05  # Stock recommended 0.3
        scale = 1
        thresholdBlockSize = 3

        laplacian, laplacianThresh = self.Laplacian(image, scale, threshold, thresholdBlockSize, Image_module)
        laplacianThresh = Image_module.Scale(laplacianThresh, newWidth=imgW_px, newHeight=screenHeight)

        return laplacianThresh

    def EdgeDetectionOLD(self, imageNr, screenHeight, compact, cv2=None, np=None):
        output = -1
        imgHeight = len(Image.grayNR_s[imageNr])
        imgWidth = len(Image.grayNR_s[imageNr][0])
        imgW_px = int(screenHeight * (imgWidth / imgHeight))

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

            sobelx = Image.Scale(sobelx, newWidth=imgW_px, newHeight=screenHeight)
            sobelxThresh = Image.Scale(sobelxThresh, newWidth=imgW_px, newHeight=screenHeight)

            sobely = Image.Scale(sobely, newWidth=imgW_px, newHeight=screenHeight)
            sobelyThresh = Image.Scale(sobelyThresh, newWidth=imgW_px, newHeight=screenHeight)

            laplacian = Image.Scale(laplacian, newWidth=imgW_px, newHeight=screenHeight)
            laplacianThresh = Image.Scale(laplacianThresh, newWidth=imgW_px, newHeight=screenHeight)

            # cannyImg = Image.Scale(cannyImg, newWidth=imgW_px, newHeight=System.imgH_px)

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
            laplacianThresh = Image.Scale(laplacianThresh, newWidth=imgW_px, newHeight=screenHeight)
            output = laplacianThresh
        else:
            # im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)         # Gray scale
            # im = cv2.bilateralFilter(Image.grayNR_s[imageNr], 7, 50, 50)  # Blur for smoothing
            edgesThresh = self.Canny(Image.grayNR_s[imageNr])

            # Scale down images for viewer
            edgesThresh = cv2.resize(edgesThresh, (self.imgW_px, screenHeight))

            output = edgesThresh
        return output

    # Variables
    imgW_px = 0
