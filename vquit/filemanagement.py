# Read and write data to files
class Configuration:
    json = None

    def Setup(self):
        print("Importing JSON")
        # Read JSON files
        import json
        self.json = json

    # Return data from configuration file
    def Get(self, category):
        # Import JSON module if not available
        if self.json is None:
            self.Setup()

        with open('VQuIT_Config.json', 'r') as configFile:
            data = self.json.load(configFile)[category]
        return data


# Save product info
class ProductData:
    acode = 0  # Article code
    sn = 0  # Serial number

    getDataMatrix = None

    # Import barcode scanner module
    def Setup(self):
        print("Importing DataMatrix scanner")
        from pylibdmtx.pylibdmtx import decode as getDataMatrix
        self.getDataMatrix = getDataMatrix

    # Scan images for dataMatrices QR-codes and barcodes
    def GetDataMatrixInfo(self, image):
        if self.getDataMatrix is None:
            self.Setup()

        data = None
        dataMatrix = self.getDataMatrix(image)

        for result in dataMatrix:
            data = result.data.split()

        if data is not None:
            self.acode = int(data[0].decode("utf-8"))
            self.sn = int(data[1].decode("utf-8"))
            return 1

        return 0
