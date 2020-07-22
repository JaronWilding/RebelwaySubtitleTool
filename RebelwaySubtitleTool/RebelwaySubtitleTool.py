import sys, os, boto3, pprint, json
from modules.helperModules import *
from modules.threadingClasses import *

from botocore.config import Config

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor
from PyQt5.QtCore import QThread, pyqtSignal, QDir, Qt
from PyQt5 import QtGui, uic

class UI(QMainWindow):
	def __init__(self):
		super(UI, self).__init__()

		self.GetWidgets()
		self.Settings()
		self.SetFunctions()

		

		self.show()



	def GetWidgets(self):
		uic.loadUi("resources/mainUI.ui", self)
		self.setWindowIcon(QtGui.QIcon("icons/rw_logo.png"))
		self.setWindowTitle("Rebelway Subtitle Tool")

		


		self.wBucketList = self.findChild(QTreeWidget, "bucketList")
		self.wStatusBar = self.findChild(QStatusBar, "statusbar")
		self.btnRefreshBucketList = self.findChild(QPushButton, "refreshBucketList")
		self.btnTranscribe = self.findChild(QPushButton, "btnTranscribe")

		
		

		#self.W_DwnProgress = self.findChild(QProgressBar, "downloadPGRS")
		#self.W_DwnBtn = self.findChild(QPushButton, "downloadBTN")
		#self.W_myStatusBar = self.findChild(QStatusBar, "Status")


	def SetFunctions(self):
		self.btnRefreshBucketList.clicked.connect(self.RefreshClientBuckets)
		self.btnTranscribe.clicked.connect(self.TranscribeFiles)


		
		self.RefreshClientBuckets()
		
		
		#self.W_linksTxt.textChanged.connect(self.LinksChanged)
		#self.W_DwnBtn.clicked.connect(self.DownloadFiles)
		

	def Settings(self):
		with open('config.json') as json_file:
			awsSettingsRead = json.load(json_file)
			
		self.awsSettings = awsSettingsRead["AWSSettings"]


	def RefreshClientBuckets(self):
		self.wStatusBar.showMessage("Getting Bucket + files list...")
		self.wBucketList.setDisabled(True);
		self.btnRefreshBucketList.setDisabled(True)
		def SetItems(items):
			self.wBucketList.clear()
			self.wBucketList.addTopLevelItems(items)
			self.wBucketList.expandAll()
			self.wBucketList.setDisabled(False);
			self.btnRefreshBucketList.setDisabled(False)
			self.wStatusBar.showMessage("Client Bucket(s) list loaded!")

		
		self.GetBucketList = ClientBuckets(self.awsSettings)
		self.GetBucketList.allBucketItems.connect(SetItems)
		self.GetBucketList.start()


##################################################################################################
##################################################################################################
###
### Transcribe Functions!
###
##################################################################################################
##################################################################################################


	def TranscribeFiles(self):

		def emitterConnection(item, row, message):
			item.setText(row, message)


		# Will return a QTreeWidgetItem -> So we can set some things in the item if needed, such as a progressbar!
		selectedItems = get_selected_items(self.wBucketList)
		transcribeItems = []
		if len(selectedItems) > 0:
			for item in selectedItems:

				itemParent = item.parent()
				if itemParent:
					dictItem = {}
					dictItem["name"] = item.text(0)
					dictItem["bucket"] = itemParent.text(0)
					dictItem["item"] = item;
					transcribeItems.append(dictItem)

			self.TranscribeThread = TranscribeAndDownload(transcribeItems, "us-east-2", "C:\\Users\\Jaron\\Documents\\GitHub\\RebelwaySubtitleTool\\RebelwaySubtitleTool\\subs")
			self.TranscribeThread.currentStatus.connect(lambda response: self.wStatusBar.showMessage(response))
			self.TranscribeThread.itemToEmit.connect(emitterConnection)
			self.TranscribeThread.start()


		else:
			self.wStatusBar.showMessage("No items selected!")



		


if __name__ == "__main__":
	App = QApplication(sys.argv)
	window = UI()
	App.exec_()