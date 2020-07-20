from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QTreeWidgetItem
import boto3, pprint
from hurry.filesize import size
from collections import namedtuple
from operator import attrgetter

class clientBuckets(QThread):
	allBucketItems =  pyqtSignal(object)
	def __init__(self):
		QThread.__init__(self)
		self.S3Obj = namedtuple('S3Obj', ['key', 'mtime', 'size', 'ETag'])

	def run(self):
		botoClient = boto3.client('s3')
		botoResource = boto3.resource('s3')
		response = botoClient.list_buckets()

		topItems = []
		topItems.clear()
		for bucket in response['Buckets']:
			parentBucket = QTreeWidgetItem([bucket["Name"]])
			parentBucket.setFlags(parentBucket.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)

			child, childSize = self.CheckItems(botoClient.list_objects_v2(Bucket=bucket["Name"])['Contents'], bucket["Name"])
			
			parentBucket.addChildren(child)
			parentBucket.setText(3, childSize)
			topItems.append(parentBucket)
			
		self.allBucketItems.emit(topItems)

	def CheckItems(self, currentBucket, bucket):
		currentItems = []
		# ETag, Key, LastModified, Size, StorageClass
		completeFileSize = 0
		for item in currentBucket:
			if item["Key"].endswith("/") == False:
				completeFileSize += item["Size"]
				fileSize = size(item["Size"])
				child = QTreeWidgetItem([ item["Key"] , "Unknown", item["ETag"], f'{fileSize}'])
				child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
				child.setCheckState(0, Qt.Unchecked)
				currentItems.append(child)
		return currentItems, size(completeFileSize)


#class transcribeService(QThread):
