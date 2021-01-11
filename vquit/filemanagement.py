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
    # Set custom warning format
    from vquit.system import WarningFormat
    import warnings
    warnings.formatwarning = WarningFormat.SetCustom

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
    def GetProductInfo(self, productName=None, acode=None):
        json = self.ImportJSON()

        with open('VQuIT_Database.json', 'r') as database:
            if acode is not None:

                # Ensure variable is integer
                acode = int(acode)

                # Search database for acode
                rawData = json.load(database)
                for product in rawData:
                    if rawData[product]["Acode"] == acode:
                        return rawData[product]
            elif productName is not None:
                # Search database for product name
                return json.load(database)[productName]
            else:
                self.warnings.warn("Enter a product name or serial number to retrieve product data from the database")
            self.warnings.warn("Acode not found in database")

    # Return list of all known products
    def GetProductList(self):
        json = self.ImportJSON()

        with open('VQuIT_Database.json', 'r') as database:
            # Get list of all objects names in database (product names)
            data = list(json.load(database).keys())

        # Sort alphabetically
        data.sort()
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
