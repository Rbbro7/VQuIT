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


# Manage product info
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

    # Return data from database file
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

    # Convert GUI input field data to json object
    @staticmethod
    def JsonfyProductInfo(data):
        productName = data[0][1]
        acode = data[1][1]
        exposureTimeU = data[2][1]
        gainU = data[3][1]
        blackLevelU = data[4][1]
        exposureTimeD = data[5][1]
        gainD = data[6][1]
        blackLevelD = data[7][1]

        jsonObject = {
            str(productName): {
                "ProductName": str(productName),
                "Acode": int(acode),
                "Configuration": {
                    "TopCameras": {
                        "ExposureTime": int(exposureTimeU),
                        "Gain": int(gainU),
                        "BlackLevel": int(blackLevelU),
                        "Lighting": {
                            "U": [
                                255,
                                0,
                                0,
                                255
                            ],
                            "D": [
                                0,
                                0,
                                0,
                                0
                            ]
                        }
                    },
                    "BottomCameras": {
                        "ExposureTime": int(exposureTimeD),
                        "Gain": int(gainD),
                        "BlackLevel": int(blackLevelD),
                        "Lighting": {
                            "U": [
                                0,
                                0,
                                0,
                                0
                            ],
                            "D": [
                                255,
                                0,
                                0,
                                255
                            ]
                        }
                    }
                }
            }
        }
        return jsonObject

    # Write to database file
    def WriteProductInfo(self, jsonObject, append=False, overwrite=False):
        # Check if append or overwrite is set and not both/neither
        if (append or overwrite) and (append != overwrite):
            json = self.ImportJSON()

            # Retrieve original data
            with open('VQuIT_Database.json', 'r') as database:
                databaseData = json.load(database)

            # Check if key or acode exists
            authenticProductName = True
            authenticAcode = True
            for key in jsonObject.keys():
                # Check for key
                if key in databaseData.keys():
                    authenticProductName = False

                # Check for acode
                for databaseKey in databaseData.keys():
                    if jsonObject[key]["Acode"] == databaseData[databaseKey]["Acode"]:
                        authenticAcode = False

            if append:
                if authenticProductName and authenticAcode:
                    print("Appending")

                    # Add JSON object to original database
                    databaseData.update(jsonObject)

                    # Write appended database to JSON file
                    with open('VQuIT_Database.json', 'w') as database:
                        json.dump(databaseData, database)
                else:
                    print("Product name or Acode already in use")
                    return False
            elif overwrite:
                if not authenticProductName:
                    print("Overwriting")

                    for key in jsonObject.keys():
                        for databaseKey in databaseData.keys():
                            if key == databaseKey:
                                databaseData[databaseKey] = jsonObject[key]

                    # Rewrite database with new data
                    with open('VQuIT_Database.json', 'w') as database:
                        json.dump(databaseData, database)
                else:
                    print("Existing product not found")
                    return False
            else:
                print("Unknown error")
                return False
        else:
            print("Set append or overwrite to True in order to write to the database")
            return False

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


# Store image info
class ImageData:
    json = None
    datetime = None

    def ImportJSON(self):
        if self.json is None:
            print("Importing JSON")
            # Import module to read JSON files
            import json
            self.json = json
        return self.json

    # Import module to retrieve current time
    def ImportDateTime(self):
        if self.json is None:
            print("Importing Datetime")
            # Import module to read JSON files
            from datetime import datetime
            self.datetime = datetime
        return self.datetime

    # Convert GUI input field data to json object
    def JsonfyProductInfo(self, data, sn, filename, remarks=None, lensData=None):
        # Work in progress          <----------------------------------------HEREE
        datetime = self.ImportDateTime()

        productName = data[0][1]
        acode = data[1][1]

        exposureTimeU = data[2][1]
        gainU = data[3][1]
        blackLevelU = data[4][1]

        exposureTimeD = data[5][1]
        gainD = data[6][1]
        blackLevelD = data[7][1]

        if remarks is None:
            remarks = "No remarks for this scan"

        if lensData is None:
            lensData = "No lens data"

        jsonObject = {
            "ProductInfo": {
                "Name": str(productName),
                "Acode": int(acode),
                "S/N": sn
            },
            "Images": {
                "FileLocation": str(filename) + ".png",
                "Date": datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                "Remarks": remarks,
                "Configuration": {
                    "Lens": lensData,
                    "TopCameras": {
                        "ExposureTime": int(exposureTimeU),
                        "Gain": int(gainU),
                        "BlackLevel": int(blackLevelU),
                        "Lighting": [
                            {
                                "ID": 0,
                                "Intensity": 100
                            }
                        ]
                    },
                    "BottomCameras": {
                        "ExposureTime": int(exposureTimeD),
                        "Gain": int(gainD),
                        "BlackLevel": int(blackLevelD),
                        "Lighting": [
                            {
                                "ID": 0,
                                "Intensity": 100
                            }
                        ]
                    }
                }
            }
        }
        return jsonObject

    # Write to database file
    def WriteImageInfo(self, jsonObject, append=False, overwrite=False):
        # Work in progress          <----------------------------------------HEREE
        # Check if append or overwrite is set and not both/neither
        if (append or overwrite) and (append != overwrite):
            json = self.ImportJSON()

            # Retrieve original data
            with open('VQuIT_ImageDatabase.json', 'r') as database:
                databaseData = json.load(database)

            # Check if key or acode exists
            authenticProductName = True
            authenticAcode = True
            for key in jsonObject.keys():
                # Check for key
                if key in databaseData.keys():
                    authenticProductName = False

                # Check for acode
                for databaseKey in databaseData.keys():
                    if jsonObject[key]["Acode"] == databaseData[databaseKey]["Acode"]:
                        authenticAcode = False

            if append:
                if authenticProductName and authenticAcode:
                    print("Appending")

                    # Add JSON object to original database
                    databaseData.update(jsonObject)

                    # Write appended database to JSON file
                    with open('VQuIT_ImageDatabase.json', 'w') as database:
                        json.dump(databaseData, database)
                else:
                    print("Product name or Acode already in use")
                    return False
            elif overwrite:
                if not authenticProductName:
                    print("Overwriting")

                    for key in jsonObject.keys():
                        for databaseKey in databaseData.keys():
                            if key == databaseKey:
                                databaseData[databaseKey] = jsonObject[key]

                    # Rewrite database with new data
                    with open('VQuIT_ImageDatabase.json', 'w') as database:
                        json.dump(databaseData, database)
                else:
                    print("Existing product not found")
                    return False
            else:
                print("Unknown error")
                return False
        else:
            print("Set append or overwrite to True in order to write to the database")
            return False
