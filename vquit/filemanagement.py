# Read and write data to files
class Configuration:
    json = None

    def ImportJSON(self):
        if self.json is None:
            print("Importing JSON")
            # Import module to read JSON files
            import json
            self.json = json
        return self.json

    # Return data from configuration file
    def Get(self, category):
        json = self.ImportJSON()

        with open('VQuIT_Config.json', 'r') as configFile:
            data = json.load(configFile)[category]
        return data

    # Write to database file
    def Write(self, data):
        json = self.ImportJSON()

        with open('VQuIT_Database.json', 'rw') as database:
            print("Database currently under construction")


# Save product info
class ProductData:
    getDataMatrix = None
    json = None

    def ImportJSON(self):
        if self.json is None:
            print("Importing JSON")
            # Import module to read JSON files
            import json
            self.json = json
        return self.json

    # Return data from configuration file
    def GetProductInfo(self, productName):
        json = self.ImportJSON()

        with open('VQuIT_Database.json', 'r') as database:
            data = json.load(database)["ProductData"][productName]
        return data

    # Import barcode scanner module
    def ImportDataMatrixDecode(self):
        if self.getDataMatrix is None:
            print("Importing DataMatrix scanner")
            from pylibdmtx.pylibdmtx import decode as getDataMatrix
            self.getDataMatrix = getDataMatrix
        return self.getDataMatrix

    # Scan images for dataMatrices QR-codes and barcodes
    def GetDataMatrixInfo(self, image):
        getDataMatrix = self.ImportDataMatrixDecode()

        data = None
        dataMatrix = getDataMatrix(image)

        for result in dataMatrix:
            data = result.data.split()

        if data is not None:
            acode = int(data[0].decode("utf-8"))
            sn = int(data[1].decode("utf-8"))
            return [acode, sn]

        return [False, False]
