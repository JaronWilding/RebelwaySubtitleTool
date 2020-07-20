import boto3, uuid, requests, time, sys, logging, enum, threading, safeqthreads, queue, os
from botocore.exceptions import ClientError
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QThread, pyqtSignal, QDir, Qt
from PyQt5 import QtGui, uic

from modules.awsModules import *
from modules.threadingClasses import *

inRegion = "us-east-2"
inBucket = "jaron-bucket-here/"
outBucket = "robdac-aiml-test/"
inMediaFile = "1_intro.mp4"

checkFiles = False

class MessageType(enum.Enum):
	INFO = 0
	WARN = 1



class UI(QMainWindow):

	FU_NAME, FU_PATH = range(2)

	def __init__(self):
		super(UI, self).__init__()
		
		## Set the global variables to be used.
		self.filesToUpload = []
		self.transcribeList = []
		self.bucketFilesModel = QStandardItemModel()
		self.defaultRegion = "us-east-2"

		## Setup the window - get the buttons + set the button functions
		self.GetWidgets()
		self.SetFunctions()

		self.show()

	def GetWidgets(self):
		uic.loadUi("ui/RebDesignerv2.ui", self)
		self.setWindowIcon(QtGui.QIcon("icons/rw_logo.png"))
		self.setWindowTitle("Rebelway AWS Tool")

		self.W_uploadFilesView = self.findChild(QListWidget, "fileListWidg")
		self.W_bucketFileListView = self.findChild(QListView, "bucketFileListMod")
		self.W_bucketComboView = self.findChild(QComboBox, "bucketListCB")
		
		self.W_myStatusBar = self.findChild(QStatusBar, "statusbar")
		self.W_progressCurrentFile = self.findChild(QProgressBar, "progressCurrentFile")
		self.W_progressAllFiles = self.findChild(QProgressBar, "progressAllFiles")

		self.W_refreshBucketsBTN = self.findChild(QPushButton, "refreshBucketsBTN")
		self.W_createBucketsBTN = self.findChild(QPushButton, "createBucketsBTN")
		self.W_deleteBucketsBTN = self.findChild(QPushButton, "deleteBucketsBTN")

		self.W_addFileBTN = self.findChild(QPushButton, "addFileBTN")
		self.W_addFolderBTN = self.findChild(QPushButton, "addFolderBTN")
		self.W_uploadFilesBTN = self.findChild(QPushButton, "uploadFilesBTN")

		self.W_subDownFolderTXT = self.findChild(QLineEdit, "subDownFolderTXT")
		self.W_subDownFolderBTN = self.findChild(QToolButton, "subDownFolderBTN")

		self.W_getBucketContentBTN = self.findChild(QPushButton, "getBucketContentBTN")
		self.W_genSubtitleBTN = self.findChild(QPushButton, "genSubtitleBTN")

		self.tabW = self.findChild(QTabWidget, "tabW")

	def SetFunctions(self):
		self.W_bucketComboView.currentIndexChanged.connect(self.EnableBuckets)

		self.W_uploadFilesView.setContextMenuPolicy(Qt.CustomContextMenu)
		self.W_uploadFilesView.customContextMenuRequested.connect(self.ContextMenuUpload)

		self.W_bucketFileListView.setContextMenuPolicy(Qt.CustomContextMenu)
		self.W_bucketFileListView.customContextMenuRequested.connect(self.ContextMenuBuckets)

		self.W_refreshBucketsBTN.clicked.connect(self.RefreshBucketsClick)
		self.W_createBucketsBTN.clicked.connect(self.CreateBucket)
		self.W_deleteBucketsBTN.clicked.connect(self.DeleteBucket)

		self.W_addFileBTN.clicked.connect(self.AddFiles)
		self.W_addFolderBTN.clicked.connect(self.AddFolder)
		self.W_uploadFilesBTN.clicked.connect(self.UploadFiles)

		self.W_getBucketContentBTN.clicked.connect(self.listBucketContents)
		self.W_subDownFolderBTN.clicked.connect(self.SubtitleDownloadFolder)
		self.W_genSubtitleBTN.clicked.connect(self.TranscribeFiles)

		self.tabW.currentChanged.connect(self.curTabChange)

		self.RefreshBucketsClick()


	def curTabChange(self, tabID=None):
		self.tabW.resize(self.tabW.currentWidget().minimumSize())

##################################################################################################
##################################################################################################
###
### Helper functions, cannot be brought outside of the class without
### referencing a ton of parents and such.
###
##################################################################################################
##################################################################################################


##################################################################################################
## Override methods. Add context menus, and message boxes.
##################################################################################################
	def ContextMenuUpload(self, pos):
		def CheckItems():
			if len(self.filesToUpload) <= 0:
				self.SetWidgetState([self.W_uploadFilesBTN, self.W_uploadFilesView], False)

		def RemoveItem():
			items = self.W_uploadFilesView.selectedItems()
			if len(items) > 0:
				for item in items:
					self.filesToUpload.remove(item.text())

				self.CleanUploadList()
			CheckItems()

		def RemoveAll():
			self.filesToUpload.clear()
			self.CleanUploadList()
			CheckItems()

		menu = QMenu()

		actionAddFiles = QAction("Add Files")
		actionAddFiles.triggered.connect(self.AddFiles)

		actionAddFolder = QAction("Add Folder")
		actionAddFolder.triggered.connect(self.AddFolder)

		actionRemoveItem = QAction("Remove Item")
		actionRemoveItem.triggered.connect(RemoveItem)

		actionRemoveAll = QAction("Clear List")
		actionRemoveAll.triggered.connect(RemoveAll)

		actionUploadFiles = QAction("Upload Files")
		actionUploadFiles.triggered.connect(self.UploadFiles)

		menu.addActions([actionAddFiles, actionAddFolder])
		menu.addSeparator()
		menu.addActions([actionRemoveItem, actionRemoveAll])
		menu.addSeparator()
		menu.addAction(actionUploadFiles)

		menu.exec_(self.W_uploadFilesView.viewport().mapToGlobal(pos))


	def ContextMenuBuckets(self, pos):
		def UnCheckAll():
			for ii in range(self.bucketFilesModel.rowCount()):
				item = self.bucketFilesModel.item(ii)
				item.setCheckState(Qt.Unchecked)

		def CheckAll():
			for ii in range(self.bucketFilesModel.rowCount()):
				item = self.bucketFilesModel.item(ii)
				item.setCheckState(Qt.Checked)


		menu = QMenu()

		actionUnCheckAll = QAction("Uncheck All")
		actionUnCheckAll.triggered.connect(UnCheckAll)
		actionCheckAll = QAction("Check All")
		actionCheckAll.triggered.connect(CheckAll)
		
		menu.addActions([actionUnCheckAll, actionCheckAll])
		menu.exec_(self.W_bucketFileListView.viewport().mapToGlobal(pos))


	def closeEvent(self, event):
		quitMsg = QMessageBox.question(self, "Are you sure?", "You wanna quit?", QMessageBox.Yes, QMessageBox.No)
		if quitMsg == QMessageBox.Yes:
			event.accept() # let the window close
		else:
			event.ignore()

	def CustomMessageBox(self, title, text, infoText, icon):
		msg = QMessageBox(self)
		msg.setIcon(icon)
		msg.setWindowTitle(title)
		msg.setText(text)
		msg.setInformativeText(infoText)
		msg.setMinimumSize(300, 100)
		msg.show()
			
	def InputDialog(self, title, label, sizeX, sizeY):
		dlg = QInputDialog(self)
		dlg.setInputMode(QInputDialog.TextInput)
		dlg.setWindowTitle(title)
		dlg.setLabelText(label)
		dlg.resize(sizeX, sizeY)
		ok = dlg.exec_()
		text = dlg.textValue()
		return text, ok

##################################################################################################
## Cleaning up the upload file lists + remove any duplicates
##################################################################################################
	def CleanUploadList(self):
		self.filesToUpload = self.RemoveDuplicates(self.filesToUpload)
		self.W_uploadFilesView.clear()

		if len(self.filesToUpload) > 0 and self.W_uploadFilesView.isEnabled() == False:
			self.W_uploadFilesView.setEnabled(True)

		for file in self.filesToUpload:
			self.W_uploadFilesView.addItem(file)

	def RemoveDuplicates(self, incomingList):
		newList = []
		for file in incomingList:
			newList.append(os.path.abspath(os.path.join(os.path.dirname(file), os.path.basename(file))))
		return(list(dict.fromkeys(newList)))

##################################################################################################
## Smaller functions, ones that I was overusing below. Set widget states (enabled or disabled),
## Check the current state (IE, if it is greater than)
## Enable the different widgets, makes it easier for me to do so than implementing them repeatedly
##################################################################################################
	def EnableBuckets(self):
		if self.W_bucketComboView.currentText() != "":
			self.SetWidgetState([self.W_refreshBucketsBTN, self.W_createBucketsBTN, self.W_deleteBucketsBTN, self.W_getBucketContentBTN, 
						self.CheckState(self.W_uploadFilesView.count(), 0, self.W_genSubtitleBTN, None)], True)

	def EnableUploads(self):
		if self.W_uploadFilesView.count() > 0 and self.W_bucketComboView.currentText() != "":
			self.SetWidgetState([self.W_uploadFilesBTN], True)

	def SetWidgetState(self, functions, state):
		for item in functions:
			if item != None:
				item.setEnabled(state)

	def CheckState(self, incomingTotal, amount, A, B):
		if incomingTotal > amount:
			return A
		else:
			return B


##################################################################################################
##################################################################################################
###
### Bucket Group functions - These include all the functions required for
###
##################################################################################################
##################################################################################################

	def TranscribeFiles(self):
		self.transcribeList.clear()

		for ii in range(self.bucketFilesModel.rowCount()):
			content = self.bucketFilesModel.item(ii)
			if content.checkState() == Qt.Checked:
				self.transcribeList.append(content.text())

		self.TranscribeThread = TranscribeAndDownload(self.transcribeList, self.W_bucketComboView.currentText(), "us-east-2", self.W_subDownFolderTXT.text())
		self.TranscribeThread.currentStatus.connect(lambda response: self.W_myStatusBar.showMessage(response))
		self.TranscribeThread.start()

	def SubtitleDownloadFolder(self):
		folder = QFileDialog.getExistingDirectory(self, "Select Directory Containing Files:")
		if folder:
			self.W_subDownFolderTXT.setText(os.path.abspath(folder))
			if  self.bucketFilesModel.rowCount() > 0:
				self.SetWidgetState([self.W_genSubtitleBTN], True)

	def listBucketContents(self):
		def ContentFilter(contents):
			if contents:
				if contents[0] == "None":
					self.W_myStatusBar.showMessage("No files found!")
					
				else:
					for content in contents:
						contentFile = content["Key"]
						item = QStandardItem(str(contentFile))
						item.setCheckable(True)
						item.setCheckState(Qt.Checked)
						self.bucketFilesModel.appendRow(item)
					self.W_myStatusBar.showMessage(f"{len(contents)} files found!")
					self.W_bucketFileListView.setModel(self.bucketFilesModel)
					self.SetWidgetState([self.W_bucketFileListView], True)
					if self.W_subDownFolderTXT.text() != "":
						self.SetWidgetState([self.W_genSubtitleBTN], True)

			self.SetWidgetState([self.W_refreshBucketsBTN, self.W_createBucketsBTN, self.W_deleteBucketsBTN,
						self.W_getBucketContentBTN, self.W_bucketFileListView], True)

		self.SetWidgetState([self.W_refreshBucketsBTN, self.W_createBucketsBTN, self.W_deleteBucketsBTN,
				self.W_getBucketContentBTN, self.W_genSubtitleBTN, self.W_bucketFileListView], False)
		self.bucketFilesModel.clear()

		self.getContentsThread = GetContentsThread(str(self.W_bucketComboView.currentText()))
		self.getContentsThread.ContentReponse.connect(lambda res: ContentFilter(res))
		self.getContentsThread.start()

##################################################################################################
##################################################################################################
###
### Upload files section. Add individual files, and sort through folders.
###
##################################################################################################
##################################################################################################

	def AddFolder(self):
		folder = QFileDialog.getExistingDirectory(self, "Select Directory Containing Files:")
		if folder:
			for file in os.listdir(folder):
				if file.endswith(".mp4") or file.endswith(".mkv"):
					self.filesToUpload.append(os.path.join(folder, file))
			self.CleanUploadList()
			self.EnableUploads()


	def AddFiles(self):

		self.filesToUpload.extend(QFileDialog.getOpenFileNames(self, "Select files to upload", "./", "MP4 & MKV files (*.mp4 *.mkv)")[0])
		if self.filesToUpload:
			self.CleanUploadList()
			self.EnableUploads()


	def UploadFiles(self):
		def Done(progress):
			self.W_progressAllFiles.setValue(int(progress))
			if int(progress) >= 100:
				self.W_myStatusBar.showMessage(f"All files uploaded!")
				self.filesToUpload.clear()
				self.W_uploadFilesView.clear()

				# Enables all buttons after finishing uploading (also checks if there is already content from the bucket)
				self.SetWidgetState([self.W_bucketComboView, self.W_refreshBucketsBTN, self.W_createBucketsBTN, self.W_deleteBucketsBTN,
						  self.W_uploadFilesView, self.W_addFileBTN, self.W_addFolderBTN,
						  self.W_bucketFileListView, self.W_getBucketContentBTN, self.CheckState(self.bucketFilesModel.rowCount(), 0, self.W_genSubtitleBTN, None)], True)

				self.W_progressAllFiles.setValue(0)
				self.W_progressCurrentFile.setValue(0)
				
		def ByteProgress(amountDone, amountLeft):
			amountDoneCal = round(amountDone/float(1<<20), 2)
			amountLeftCal = round(amountLeft/float(1<<20), 2)
			self.W_myStatusBar.showMessage(f"{amountDoneCal} / {amountLeftCal} MB uploaded...")


		# Disables all buttons for uploading.
		self.SetWidgetState([self.W_bucketComboView, self.W_refreshBucketsBTN, self.W_createBucketsBTN, self.W_deleteBucketsBTN,
						self.W_uploadFilesView, self.W_addFileBTN, self.W_addFolderBTN, self.W_uploadFilesBTN,
						self.W_bucketFileListView, self.W_getBucketContentBTN, self.W_genSubtitleBTN], False)

		filesToThread = []
		for file in self.filesToUpload:
			fileDict = {"Filepath": file, "Filename": os.path.basename(file)}
			filesToThread.append(fileDict)

		self.uploadFilesThread = UploadFiles(filesToThread, self.W_bucketComboView.currentText(), "us-east-2")
		self.uploadFilesThread.fileProgress.connect(lambda progress: self.W_progressCurrentFile.setValue(progress))
		self.uploadFilesThread.bytesDetails.connect(ByteProgress)
		self.uploadFilesThread.fileCompleted.connect(Done)
		self.uploadFilesThread.currentStatus.connect(lambda response: self.W_myStatusBar.showMessage(response))
		self.uploadFilesThread.start()

##################################################################################################
##################################################################################################
###
### Bucket Group functions - These include all the functions required for
###
##################################################################################################
##################################################################################################

	def RefreshBucketsClick(self):
		## Create the children functions.
		def SecondaryCheck(response):
			self.checkBucketThread = CheckBucket(response)
			self.checkBucketThread.BucketCheckedResponse.connect(AddListItems)
			self.checkBucketThread.BucketsChecked.connect(lambda res: self.W_myStatusBar.showMessage(str(f"{res} / {len(response)} Buckets Checked...")))
			self.checkBucketThread.start()

		def AddListItems(buckets):
			if buckets:
				self.W_myStatusBar.showMessage(f"All Buckets checked! {len(buckets)} valid Buckets found!")
				for bucket in buckets:
					self.W_bucketComboView.addItem(bucket["Name"])
			else:
				self.W_myStatusBar.showMessage(f"No Buckets found! Please create one!")
				self.SetWidgetState([self.W_refreshBucketsBTN, self.W_createBucketsBTN], True)

		## Refresh the bucket list and do a check to make sure they are alive.
		self.SetWidgetState([self.W_refreshBucketsBTN, self.W_createBucketsBTN, self.W_deleteBucketsBTN,
				self.W_uploadFilesView, self.W_uploadFilesBTN, self.W_getBucketContentBTN, self.W_genSubtitleBTN, self.W_bucketFileListView], False)

		self.W_bucketComboView.clear()
		self.loadBucketThread = LoadBucketsThread(self.defaultRegion)
		self.loadBucketThread.BucketListResponse.connect(SecondaryCheck)
		self.loadBucketThread.currentStatus.connect(lambda response: self.W_myStatusBar.showMessage(response))
		self.loadBucketThread.start()


	def DeleteBucket(self):
		## Create the children functions.
		def bucketResponse(res, log):
			if res:
				self.CustomMessageBox("Successful", "Bucket deleted!", log, QMessageBox.Information)
				self.RefreshBucketsClick()
			else:
				self.CustomMessageBox("Error", "Could not delete bucket!", log, QMessageBox.Warning)

		## Ask if user wishes to delete the bucket, then deletes them when finished, or shows an error if cannot.
		delMsg = QMessageBox.question(self, "Are you sure?", f"Do you want to delete the bucket: {self.W_bucketListView.currentText()} ?", QMessageBox.Yes, QMessageBox.No)
		if delMsg == QMessageBox.Yes:
			print("Deleting")
			self.deleteBucketThread = DeleteBucketsThread(self.W_bucketComboView.currentText())
			self.deleteBucketThread.BucketDeletedResponse.connect(lambda res, log: bucketResponse(res, log))
			self.deleteBucketThread.start()


	def CreateBucket(self):
		## Create the children functions.
		def CheckBuckets(res, log):
			if res:
				self.CustomMessageBox("Successful", "Bucket created!", log, QMessageBox.Information)
				self.RefreshBucketsClick()
			else:
				self.CustomMessageBox("Error", "Could not create bucket!", log, QMessageBox.Warning)
				
		## Asks user what the bucket name should be, then creates it if able, and displays a error if not.
		text, ok = InputDialog("Create New Bucket", "Bucket name:", 500, 200)
		if ok and text:
			self.addBucketThread = CreateBucketsThread("us-east-2", text)
			self.addBucketThread.BucketCreatedResponse.connect(lambda res, log: CheckBuckets(res, log))
			self.addBucketThread.start()




	



if __name__ == "__main__":
	App = QApplication(sys.argv)
	window = UI()
	App.exec_()
	
		
#transciptionJob = awsModules.Transcribe(inRegion, inBucket, inMediaFile)
#response = transciptionJob.createJob()

## loop until the job successfully completes
#print( "\n==> Transcription Job: " + response["TranscriptionJob"]["TranscriptionJobName"] + "\n\tIn Progress"),

#while( response["TranscriptionJob"]["TranscriptionJobStatus"] == "IN_PROGRESS"):
#	print( "."),
#	time.sleep(10)
#	response = transciptionJob.getJobStatus( response["TranscriptionJob"]["TranscriptionJobName"] )

#print( "\nJob Complete")
#print( "\tStart Time: " + str(response["TranscriptionJob"]["CreationTime"]) )
#print( "\tEnd Time: "  + str(response["TranscriptionJob"]["CompletionTime"]) )
#print( "\tTranscript URI: " + str(response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]) )


#transcript = transciptionJob.getTranscript( str(response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]) ) 
#print( "\n==> Transcript: \n" + transcript)

## awsModules.SRTModule().writeTranscriptToSRT(transcript, "en", "subtitles-en.srt")
#awsModules.SRTModule(transcript, "en", "subtitles-en.srt")