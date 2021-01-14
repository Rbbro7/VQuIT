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
    os = None

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

    # Import os module to retrieve work directory
    def ImportOS(self):
        if self.os is None:
            print("Importing OS")
            # Import module to read JSON files
            import os
            self.os = os
        return self.os

    # Convert GUI input field data to json object
    def JsonfyProductInfo(self, data, sn, remarks=None, lensData=None):
        # Work in progress
        datetime = self.ImportDateTime()
        os = self.ImportOS()

        # Get product info
        productName = data["ProductName"]
        acode = data["Acode"]

        cameraConfig = data["Configuration"]["TopCameras"]
        exposureTimeU = cameraConfig["ExposureTime"]
        gainU = cameraConfig["Gain"]
        blackLevelU = cameraConfig["BlackLevel"]
        lightsTop_U = cameraConfig["Lighting"]["U"]
        lightsTop_D = cameraConfig["Lighting"]["D"]

        cameraConfig = data["Configuration"]["BottomCameras"]
        exposureTimeD = cameraConfig["ExposureTime"]
        gainD = cameraConfig["Gain"]
        blackLevelD = cameraConfig["BlackLevel"]
        lightsBottom_U = cameraConfig["Lighting"]["U"]
        lightsBottom_D = cameraConfig["Lighting"]["D"]

        lightingTop = {
            "Lighting": []
        }

        lightingBottom = {
            "Lighting": []
        }

        # Add lights if not set at 0
        for light in range(0, len(lightsTop_U)):
            pwmValue = lightsTop_U[light]
            if pwmValue is not 0:
                lightID = light
                newLight = {"Lighting": [{
                    "ID": int(lightID),
                    "Intensity": int(pwmValue)
                }]}
                lightingTop["Lighting"].extend(newLight["Lighting"])

            pwmValue = lightsBottom_U[light]
            if pwmValue is not 0:
                lightID = light
                newLight = {"Lighting": [{
                    "ID": int(lightID),
                    "Intensity": int(pwmValue)
                }]}
                lightingBottom["Lighting"].extend(newLight["Lighting"])

        for light in range(0, len(lightsTop_D)):
            pwmValue = lightsTop_D[light]
            if pwmValue is not 0:
                lightID = light + len(lightsTop_U)
                newLight = {"Lighting": [{
                    "ID": int(lightID),
                    "Intensity": int(pwmValue)
                }]}
                lightingTop["Lighting"].extend(newLight["Lighting"])

            pwmValue = lightsBottom_D[light]
            if pwmValue is not 0:
                lightID = light + len(lightsBottom_U)
                newLight = {"Lighting": [{
                    "ID": int(lightID),
                    "Intensity": int(pwmValue)
                }]}
                lightingBottom["Lighting"].extend(newLight["Lighting"])

        # Get current time
        date = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        filenameDate = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d %H%M%S')

        # Get working directory of script
        path = os.path.dirname(os.path.realpath(__file__))

        # Hack / workaround to get to parent directory of the main script
        for i in range(0, 2):
            path = os.path.dirname(path)

        # Add image directory to folder
        path += "\\Image Database\\"

        # Check if subdirectory exists and create if not
        if not os.path.exists(path):
            print("Creating subdirectory: " + str(path))
            os.makedirs(path)

        filename = path + str(productName) + " (" + str(acode) + "_" + str(sn) + ") - " + str(
            filenameDate)

        if remarks is None:
            remarks = "No remarks for this scan"

        if lensData is None:
            lensData = "No lens data"

        jsonObject = {
            str(productName) + "-" + str(sn): {
                "ProductInfo": {
                    "Name": str(productName),
                    "Acode": int(acode),
                    "S/N": sn
                },
                "Images": [{
                    "FileLocation": str(filename) + ".png",
                    "Date": date,
                    "Remarks": remarks,
                    "Configuration": {
                        "Lens": lensData,
                        "TopCameras": {
                            "ExposureTime": int(exposureTimeU),
                            "Gain": int(gainU),
                            "BlackLevel": int(blackLevelU),
                            "Lighting": lightingTop["Lighting"]
                        },
                        "BottomCameras": {
                            "ExposureTime": int(exposureTimeD),
                            "Gain": int(gainD),
                            "BlackLevel": int(blackLevelD),
                            "Lighting": lightingBottom["Lighting"]
                        }
                    }
                }]
            }
        }

        return jsonObject, filename.replace(os.sep, '/')

    # Write to database file
    def WriteImageInfo(self, jsonObject):

        json = self.ImportJSON()

        # Retrieve original data
        with open('VQuIT_ImageDatabase.json', 'r') as database:
            databaseData = json.load(database)

        # Check if key or acode exists
        authenticProduct = True
        for key in jsonObject.keys():
            # Check for key
            if key in databaseData.keys():
                authenticProduct = False

        if authenticProduct:
            print("Adding product")

            # Add JSON object to original database
            databaseData.update(jsonObject)

        else:
            print("Adding to product")
            for key in jsonObject.keys():
                # Find matching product
                for databaseKey in databaseData.keys():
                    if key == databaseKey:
                        # Get image dict of product
                        imageList = databaseData[databaseKey]["Images"]

                        # Extend existing list with new list
                        imageList.extend(jsonObject[key]["Images"])

                        # Replace original list with updated list
                        databaseData[databaseKey]["Images"] = imageList

        # Write updated database to JSON file
        with open('VQuIT_ImageDatabase.json', 'w') as database:
            json.dump(databaseData, database)
