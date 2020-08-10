import os, json
from pathlib import Path
from modules.helperModules import LogOutput
from PyQt5.QtGui import QIcon


class MainSettings():
	def __init__(self):
		self.LoadSettings()

	def LoadSettings(self):
		def setupSettings(awsSettingsRead):
			self.logEnabled = bool(awsSettingsRead["AWSSettings"]["LOGGING"])

			self.accessKey = awsSettingsRead["AWSSettings"]["ACCESS_KEY"]
			self.secretKey = awsSettingsRead["AWSSettings"]["SECRET_KEY"]
			self.region = awsSettingsRead["AWSSettings"]["REGION"]
			self.uploadAsyncAmount = awsSettingsRead["AWSSettings"]["UPLOAD_ASYNC"]

				
			#Check if the user has set a Download area for SRT files, if not, it will create a temporary dictorary
			if jsonLoaded["AWSSettings"]["DOWNLOADAREA_SRT"].strip() == "":
				self.downloadArea_SRT = awsSettingsRead["AWSSettings"]["DOWNLOADAREA_TEMPSRT"]
				Path(self.downloadArea_SRT).mkdir(parents=True, exist_ok = True)
				LogOutput(self, "SRT Temp Path Created or Set!")
			else:
				self.downloadArea_SRT = awsSettingsRead["AWSSettings"]["DOWNLOADAREA_SRT"]


			#Check if the user has set a Download area for raw JSON files, if not, it will create a temporary dictorary
			if jsonLoaded["AWSSettings"]["DOWNLOADAREA_JSON"].strip() == "":
				self.downloadArea_JSON = awsSettingsRead["AWSSettings"]["DOWNLOADAREA_TEMPJSON"]
				Path(self.downloadArea_JSON).mkdir(parents=True, exist_ok = True)
				LogOutput(self, "JSON Temp Path Created or Set!")
			else:
				self.downloadArea_JSON = awsSettingsRead["AWSSettings"]["DOWNLOADAREA_JSON"]

			self.folderIcon_NoChecksum = QIcon("resources/icons/Folder.ico")
			self.folderIcon_Checksum = QIcon("resources/icons/FolderChecksum.ico")
			self.fileIcon_NoChecksum = self.fileIcon_Standard = QIcon("resources/icons/File.ico")
			self.fileIcon_Checksum  = self.fileIcon_JobAvailable = QIcon("resources/icons/FileChecksum.ico")
			self.fileIcon_JobRunning = QIcon("resources/icons/FileJobRunning.ico")

			LogOutput(self, "Settings loaded!")


		with open('config.json') as json_file:
			jsonLoaded = json.load(json_file)


		testing = []
		for ii in range(0, 2):
			testingPath = jsonLoaded["AWSSettings"][self.DownloadSwitcher(ii)]
			if testingPath.strip() == "":
				testing.append(self.DownloadSwitcher(ii))

		for ii in testing:
			if ii == "DOWNLOADAREA_SRT":
				TEMP_SRTDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.join("downloads", "rawSRTFiles"))
				if jsonLoaded["AWSSettings"]["DOWNLOADAREA_TEMPSRT"] != TEMP_SRTDIR:
					jsonLoaded["AWSSettings"]["DOWNLOADAREA_TEMPSRT"] = TEMP_SRTDIR
					jsonLoaded = self.SaveSettings(jsonLoaded)
			elif ii == "DOWNLOADAREA_JSON":
				TEMP_JSONDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.join("downloads", "rawJSONFiles"))
				if jsonLoaded["AWSSettings"]["DOWNLOADAREA_TEMPJSON"] != TEMP_JSONDIR:
					jsonLoaded["AWSSettings"]["DOWNLOADAREA_TEMPJSON"] = TEMP_JSONDIR
					jsonLoaded = self.SaveSettings(jsonLoaded)
				
		setupSettings(jsonLoaded)

	def SaveSettings(self, jsonInput):
		with open('config.json', "w") as json_file:
			json_file.write(json.dumps(jsonInput, indent=4))

		with open('config.json') as json_file:
			jsonLoaded = json.load(json_file)

		return jsonLoaded
		
	def DownloadSwitcher(self, ii):
		return { 0: "DOWNLOADAREA_SRT", 1: "DOWNLOADAREA_JSON" }.get(ii, "")