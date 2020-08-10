import sys, os, boto3, pprint, json, enum
from modules.helperModules import *
from modules.threadingClasses import *
from modules.MainSettings import * 
from pathlib import Path

from botocore.config import Config
from hurry.filesize import size
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QIcon
from PyQt5.QtCore import QThread, pyqtSignal, QDir, Qt
from PyQt5 import QtGui, uic



class UI(QMainWindow):
	def __init__(self):
		super(UI, self).__init__()

		self.settings = MainSettings()
		self.GetWidgets()
		self.SetFunctions()

		

		self.show()


##################################################################################################
##################################################################################################
###
### Initilization Functions!
###
##################################################################################################
##################################################################################################

	def SettingsSet(self):
		pass

	def About(self):
		pass

	def LoadUI(self):
		with open("resources/mainStyle.css","r") as style:
			self.setStyleSheet(style.read())


	def GetWidgets(self):
		#self.folderIcon_NC = QIcon("resources/icons/Folder.ico")
		#self.folderIcon_C = QIcon("resources/icons/FolderChecksum.ico")
		#self.fileIcon_NC = QIcon("resources/icons/File.ico")
		#self.fileIcon_C = QIcon("resources/icons/FileChecksum.ico")

		uic.loadUi("resources/mainUI.ui", self)
		with open("resources/mainStyle.css","r") as style:
			self.setStyleSheet(style.read())

		#SetterA()


		self.setWindowIcon(QtGui.QIcon("resources/icons/rw_logo.png"))
		self.setWindowTitle("Rebelway Subtitle Tool")


		#We prefer Tree widgets, as we can then view folders.
		self.wBucketList = self.findChild(QTreeWidget, "bucketList")
		self.wLocalFileTree = self.findChild(QTreeWidget, "localFileTree")
		self.wTranscriptJobTree = self.findChild(QTreeView, "transcriptJobTree")


		self.cbBucketCombo = self.findChild(QComboBox, "bucketCombo")


		self.btnRefreshBucketList = self.findChild(QPushButton, "refreshBucketList")
		self.btnTranscribe = self.findChild(QPushButton, "btnTranscribe")
		self.btnMultiTool = self.findChild(QPushButton, "btnMultiTool")

		self.btnAddLocalFiles = self.findChild(QPushButton, "btnAddLocalFiles")
		self.btnCheckAll = self.findChild(QPushButton, "btnCheckAll")
		self.btnUnCheckAll = self.findChild(QPushButton, "btnUnCheckAll")

		self.btnUpload = self.findChild(QPushButton, "btnUpload")

		self.menu = self.findChild(QMenuBar, "menubar")
		self.wStatusBar = self.findChild(QStatusBar, "statusbar")
		self.detailLabel = self.findChild(QLabel, "detailLabel")



	def SetFunctions(self):
		self.btnRefreshBucketList.clicked.connect(self.RefreshClientBuckets)
		self.btnTranscribe.clicked.connect(self.TranscribeFiles)
		self.btnMultiTool.clicked.connect(self.LoadUI)


		self.btnAddLocalFiles.clicked.connect(self.LoadFiles)
		self.btnCheckAll.clicked.connect(lambda: LoadFilesCheckStatus(self.wLocalFileTree, Qt.Checked))
		self.btnUnCheckAll.clicked.connect(lambda: LoadFilesCheckStatus(self.wLocalFileTree, Qt.Unchecked))
		self.btnUpload.clicked.connect(self.UploadFiles)


		self.wBucketList.itemClicked.connect(self.DisplayBucketInfo)
		self.wLocalFileTree.itemClicked.connect(self.DisplayLocalInfo)
		self.wTranscriptJobTree.itemClicked.connect(self.DisplayJobInfo)
		self.wLocalFileTree.customContextMenuRequested.connect(self.LocalFileTreeMenu)




		## Setting up the menubar properly!!
		btnSettings = QAction("Settings", self)
		btnSettings.setStatusTip("Help setup your main settings!")
		btnSettings.triggered.connect(self.SettingsSet)
		self.menu.addAction(btnSettings)

		btnSettings = QAction("About", self)
		btnSettings.setStatusTip("Help and About!")
		btnSettings.triggered.connect(self.About)
		self.menu.addAction(btnSettings)

		
		self.RefreshClientBuckets()
		

	def DisplayBucketInfo(self, item):
		self.detailLabel.setText(InfoWriter(FILEPATH = GetItemData(item, DT.FilePath),
									  CHECKSUM = GetItemData(item, DT.ETagChecksum),
									  FILESIZE = GetItemData(item, DT.FileSize),
									  FILETYPE = GetItemData(item, DT.FileType),
									  JOBNAME = GetItemData(item, DT.JobName)))

	def DisplayLocalInfo(self, item):
		self.detailLabel.setText(InfoWriter(FILEPATH = GetItemData(item, DT.FilePath),
									  CHECKSUM = GetItemData(item, DT.ETagChecksum),
									  FILESIZE = GetItemData(item, DT.FileSize),
									  FILETYPE = GetItemData(item, DT.FileType),
									  JOBNAME = GetItemData(item, DT.JobName)))

	def DisplayJobInfo(self, item):
		self.detailLabel.setText(InfoWriter(JOBNAME = GetItemData(item, DT.JobName),
									  CREATIONTIME = GetItemData(item, DT.CreationTime),
									  COMPLETEDTIME = GetItemData(item, DT.CompletionTime),
									  LANGUAGE = GetItemData(item, DT.LanguageCode)))


	def LocalFileTreeMenu(self, point):
		# Infos about the node selected.
		index = self.wLocalFileTree.indexAt(point)

		item = self.wLocalFileTree.itemAt(point)

		menu = QMenu()
		addFiles = menu.addAction("Add Files or Folders")
		menu.addSeparator()
		removeFiles = menu.addAction("Remove Selected")
		SetItemsDisabled([removeFiles], not index.isValid())

		addFiles.triggered.connect(self.LoadFiles)


		menu.exec_(self.wLocalFileTree.mapToGlobal(point))



##################################################################################################
##################################################################################################
###
### Local files segment! This includes loading files, uploading files, and menu contexts for all
### local functions.
###
##################################################################################################
##################################################################################################


## Primary looping function. Checks if there are files \ folders in the given path. If its a file, add it to the files, and create a checksum gatherer.
## If a folder, loop into another iteration of this function to fully get all the files in a folder.
## !! THIS CAN BE SLOW IF YOU DO A WHOLE DRIVE, AS IT IS ON THE MAIN THREAD !!
	def LoadFilesInFolder(self, filePath):
		files = []
		fileChecksum = []
		for file in os.listdir(filePath):
			fileDir = os.path.abspath(os.path.join(filePath, file))
			child = QTreeWidgetItem([os.path.basename(fileDir)])
			if os.path.isfile(fileDir):
				if checkFile(file) == False:
					continue
				child.setIcon(0, self.settings.fileIcon_NoChecksum)
				child = SetItemData(child, 
						  FILENAME = os.path.basename(file), 
						  FILETYPE = GetFileType(file).value,
						  FILEPATH = fileDir,
						  FILESIZE = size(os.path.getsize(fileDir)),
						  OSFILETYPE = OS_Type.File
						  )
				fileChecksum.append(child)
			elif os.path.isdir(fileDir):
				child.setIcon(0, self.settings.folderIcon_NoChecksum)
				child = SetItemData(child, 
						  FILENAME = os.path.basename(file), 
						  FILETYPE = FileType.unknown.value,
						  FILEPATH = fileDir,
						  FILESIZE = size(get_directory_size(fileDir)),
						  OSFILETYPE = OS_Type.Folder
						  )

				extraFiles, secondaryCheckSum = self.LoadFilesInFolder(fileDir)
				fileChecksum = [*fileChecksum, *secondaryCheckSum]
				child.addChildren(extraFiles)
			child.setFlags(child.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
			child.setCheckState(0, Qt.Unchecked)

			files.append(child)

		return files, fileChecksum


	def LoadFiles(self):
		## Gets the checksum callback, and sets it to the 2nd data slot of the item
		## One issue is that it can only go 1 proper search depth, otherwise a folder will be called back, and I have no wish of setting a loop backwards.
		def setChecksum(item, checksum):
			
			item = SetItemData(item, CHECKSUM = checksum,
					  JOBNAME = calculate_job_name(GetItemData(item, DT.FileName), checksum))
			item.setIcon(0, self.settings.fileIcon_Checksum)

			LogOutput(self.settings, f"ETag Checksum Generated for {item.data(DT.FileName, Qt.UserRole)}: {checksum}")

			parent = item.parent()
			if parent != None:
				children = get_subtree_nodes(parent)
				childrenCount = len(children)
				childrenCheck = 0
				for child in children:
					if child.data(DT.ETagChecksum, Qt.UserRole) != "Generating Checksum...":
						childrenCheck += 1
					else:
						break
				if childrenCheck == childrenCount:
					parent.setIcon(0, self.settings.folderIcon_Checksum)

		## The final callback (although it SHOULDN'T be) where we get the update that every single file has had its checksum created.
		def checkSumsCompleted(ret):
			if ret == True:
				self.wStatusBar.showMessage("All files finished processing!!")

		## This was infurating to actually implement. The standard QFileDialog only allows either File or Folder, not both!
		## The implementation is located inside the helperModules, and it reconnects the open button to a custom function.
		## This searches through the folders and files. I still need to make a proper filter for it. I can implement it here, or in the custom FileDialog.
		fileDialog = FileDialog()
		if fileDialog.exec() != None:
			## When filedialog returns anything, it places files into a variable. This function just returns said variable.
			files = fileDialog.filesSelected()
			if type(files) is list and len(files) > 0:

				fileChecksum = []
				for file in files:
					fileDir = os.path.abspath(file)
					child = QTreeWidgetItem([os.path.basename(file)])
					
					if os.path.isfile(file):
						if checkFile(file) == False:
							continue

						child.setIcon(0, self.settings.fileIcon_NoChecksum)
						child = SetItemData(child, 
						  FILENAME = os.path.basename(file), 
						  FILETYPE = GetFileType(file).value,
						  FILEPATH = fileDir,
						  FILESIZE = size(os.path.getsize(fileDir)),
						  OSFILETYPE = OS_Type.File
						  )
						fileChecksum.append(child)

					elif os.path.isdir(file):
						child.setIcon(0, self.settings.folderIcon_NoChecksum)
						child = SetItemData(child, 
						  FILENAME = os.path.basename(file), 
						  FILETYPE = FileType.unknown.value,
						  FILEPATH = fileDir,
						  FILESIZE = size(get_directory_size(fileDir)),
						  OSFILETYPE = OS_Type.Folder
						  )
						extraFiles, secondaryCheckSum = self.LoadFilesInFolder(file)
						fileChecksum = [*fileChecksum, *secondaryCheckSum]
						child.addChildren(extraFiles)

					child.setFlags(child.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
					child.setCheckState(0, Qt.Unchecked)
					self.wLocalFileTree.addTopLevelItem(child)
				
				self.CreateCheckSum = CreateChecksum(fileChecksum)
				self.CreateCheckSum.fileChecksum.connect(setChecksum)
				self.CreateCheckSum.allChecksumsFinished.connect(checkSumsCompleted)
				self.CreateCheckSum.start()

				header = self.wLocalFileTree.header()

				header.setSectionResizeMode(QHeaderView.ResizeToContents)
				header.setStretchLastSection(False)

				#LogOutput(self.settings, files)


	## Uploading Files main definition!
	def UploadFiles(self):
		def fileUploaded(item):
			
			progressBar = self.wLocalFileTree.itemWidget(item, 0)
			progressBar.setValue(100)

			if item.childCount() == 0:
				root = self.wLocalFileTree.invisibleRootItem()
				(item.parent() or root).removeChild(item)

		def fileProgress(item, progress):
			progressBar = self.wLocalFileTree.itemWidget(item, 0)
			progressBar.setValue(progress)

		def allFilesUploaded(filesUploaded):
			if filesUploaded == True:
				self.wLocalFileTree.clear()
				# Renable everything
				self.RefreshClientBuckets()
				SetItemsDisabled([self.wLocalFileTree, self.cbBucketCombo, self.btnAddLocalFiles, self.btnCheckAll, self.btnUnCheckAll, self.btnUpload], False)
				self.wLocalFileTree.customContextMenuRequested.connect(self.LocalFileTreeMenu)
			

		# I make two lists, one to check if the item is a file, not a folder.
		items = get_selected_items(self.wLocalFileTree)
		allFiles = []
		
		for item in items:
			osType = GetItemData(item, DT.OSType)
			if osType == OS_Type.File:
				progress = QProgressBar()
				progress.setFixedWidth(180)
				progress.setFormat(GetItemData(item, DT.FileName))
				item.setText(0, "")
				self.wLocalFileTree.setItemWidget(item, 0, progress)
				allFiles.append(item)

		# Make sure that there are files!!
		if len(allFiles) > 0:

			# I make sure to disable everything to do with the uploading, so that the user can't add then lose stuff
			# This does not include the tree itself, as I still want the user to scroll!!
			self.wLocalFileTree.expandAll()
			self.wLocalFileTree.customContextMenuRequested.disconnect()
			SetItemsDisabled([self.cbBucketCombo, self.btnAddLocalFiles, self.btnCheckAll, self.btnUnCheckAll, self.btnUpload], True)
			SetTreeItems(self.wLocalFileTree, False)


			self.UploadFiles = UploadToBucketTEST(allFiles, self.settings, self.bucketCombo.currentText())
			self.UploadFiles.currentProgress.connect(fileProgress)
			self.UploadFiles.fileFinished.connect(fileUploaded)
			self.UploadFiles.allFilesUploaded.connect(allFilesUploaded)
			self.UploadFiles.logMessage.connect(lambda message: LogOutput(self.settings, message))
			self.UploadFiles.start()



			

		


##################################################################################################
##################################################################################################
###
### Transcribe Functions!
###
##################################################################################################
##################################################################################################

	def RefreshClientBuckets(self):
		self.wStatusBar.showMessage("Getting Bucket + files list...")
		SetItemsDisabled([self.wBucketList, self.wTranscriptJobTree, self.btnRefreshBucketList, self.btnMultiTool, self.cbBucketCombo], True)

		def SetBucketItems(items):
			self.wBucketList.clear()
			self.wBucketList.addTopLevelItems(items)
			self.wBucketList.expandAll()

			SetItemsDisabled([self.wBucketList, self.wTranscriptJobTree, self.btnRefreshBucketList, self.btnMultiTool], False)


			LogOutput(self.settings, "List of files and folders from buckets loaded!")
			self.wStatusBar.showMessage("Client Bucket(s) list loaded!")

		def UpdateBuckets(items):
			self.cbBucketCombo.clear()
			for item in items:
				self.cbBucketCombo.addItem(item["Name"])
			SetItemsDisabled([self.cbBucketCombo], False)
			LogOutput(self.settings, "Bucket list loaded!")

		def UpdateJobList(items):
			self.wTranscriptJobTree.clear()
			self.wTranscriptJobTree.addTopLevelItems(items)
			self.wTranscriptJobTree.expandAll()

		
		self.GetBucketList = ClientBucketFiles(self.settings)
		self.GetBucketList.allBucketItems.connect(SetBucketItems)
		self.GetBucketList.currentBuckets.connect(UpdateBuckets)
		self.GetBucketList.allJobItems.connect(UpdateJobList)
		self.GetBucketList.start()


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
					dictItem["name"] = item.data(DT.FileName, Qt.UserRole)
					dictItem["bucket"] = item.data(DT.Bucket, Qt.UserRole)
					dictItem["jobname"] = item.data(DT.JobName, Qt.UserRole)
					dictItem["item"] = item;
					LogOutput(self.settings, dictItem)
					transcribeItems.append(dictItem)

			self.TranscribeThread = TranscribeAndDownload(transcribeItems, self.settings)
			self.TranscribeThread.currentStatus.connect(lambda response: self.wStatusBar.showMessage(response))
			self.TranscribeThread.itemToEmit.connect(emitterConnection)
			self.TranscribeThread.start()
		else:
			self.wStatusBar.showMessage("No items selected!")


if __name__ == "__main__":
	App = QApplication(sys.argv)
	window = UI()
	App.exec_()