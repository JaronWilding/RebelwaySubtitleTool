import logging, boto3, requests, threading, safeqthreads, queue, os, time, multiprocessing, random
from PyQt5.QtCore import QThread, pyqtSignal, QDir, QObject, QMutex, Qt
from PyQt5.QtWidgets import QTreeWidgetItem

from botocore.exceptions import ClientError, ParamValidationError
import modules.awsModules as awsModules
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed #ProcessPoolExecutor
import asyncio

from hurry.filesize import size
from collections import namedtuple


##################################################################################################
###
### Bucket threads. Load the buckets from the current region, and then check to make sure the
### buckets are currently valid.
### Create new Buckets, delete selected Buckets - I've made sure that the threads are properly
### run, but if something happens, please let me know and I'll try to sort out any threading
### issues.
###
##################################################################################################


##################################################################################################
## Load buckets - Grabs the list from the given region, and emit the buckets + status.
##################################################################################################
class LoadBucketsThread(QThread):

	BucketListResponse = pyqtSignal(list)
	currentStatus = pyqtSignal(str)

	def __init__(self, region):
		QThread.__init__(self)
		self.region = region

	def run(self):
		self.currentStatus.emit("Finding Buckets...")
		s3 = boto3.client('s3', region_name=self.region)
		myResponse = s3.list_buckets()
		
		self.BucketListResponse.emit(myResponse["Buckets"])
		self.currentStatus.emit(F"{len(myResponse['Buckets'])} Buckets found.")

##################################################################################################
## Check the given byckets, this is done by grabbing the list, and get the properties of given
## Bucket. If nothing is sent back, then the Bucket is invalid. If there is a valid Bucket, then
## add that to the list (which is a list of dictionaries), and sent that back to the main thread.
##################################################################################################
class CheckBucket(QThread):

	BucketCheckedResponse = pyqtSignal(list)
	BucketsChecked = pyqtSignal(int)
	mutex = QMutex()

	def __init__(self, buckets):
		QThread.__init__(self)
		self.buckets = buckets
		self.returning = []

	def run(self):
		self.mutex.lock()

		threads = []
		totalBuckets = 0
		QueueList = queue.Queue()

		for bucket in self.buckets:
			thread = threading.Thread(target=CheckBucketThread, args=(bucket["Name"], QueueList))
			threads.append(thread)

		for thread in threads:
			thread.start()
			response = QueueList.get()
			if response:
				totalBuckets += 1
				self.BucketsChecked.emit(totalBuckets)
				if response["IsValid"] == True:
					self.returning.append(response)

		for thread in threads:
			thread.join()

		self.BucketCheckedResponse.emit(self.returning)
		self.mutex.unlock()

##################################################################################################
## CheckBuckets actual Thread.
##################################################################################################
class CheckBucketThread():
	def __init__(self, bucket, inQueue):
		inQueue = inQueue
		bucketDict = {"Name": bucket, "IsValid": True}

		try:
			s3_client = boto3.client('s3')
			s3_client.get_bucket_acl(Bucket=str(bucket))
			bucketDict["IsValid"]=True
		except (ClientError, ParamValidationError):
			bucketDict["IsValid"]=False
		else:
			bucketDict["IsValid"]=True
		finally:
			inQueue.put(bucketDict)



##################################################################################################
## Create a Bucket, but some Bucket names are taken by default, and you must meet the requirements
## Requirements are here: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-s3-bucket-naming-requirements.html
## and here: https://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html
##################################################################################################
class CreateBucketsThread(QThread):

	BucketCreatedResponse = pyqtSignal(bool, str)

	def __init__(self, region, name):
		QThread.__init__(self)
		self.region = region
		self.bucket_name = name

	def run(self):
		try:
			if self.region is None:
				s3_client = boto3.client('s3')
				s3_client.create_bucket(Bucket=self.bucket_name)
			else:
				s3_client = boto3.client('s3', region_name=self.region)
				location = {'LocationConstraint': self.region}
				s3_client.create_bucket(Bucket=self.bucket_name, CreateBucketConfiguration=location)
		except ClientError as e:
			self.BucketCreatedResponse.emit(False, str(e))
		else:
			self.BucketCreatedResponse.emit(True, f"Bucket {self.bucket_name} Created Successfully")


##################################################################################################
## Deletes the given Bucket. Please note, that deleting a Bucket can take time to propergate
## across all the regions (all regions must be synced), so if you ask for a list or go onto AWS,
## it'll still show up, although no configurations are available and you aren't able to dive into
## the bucket on the AWS console.
##################################################################################################
class DeleteBucketsThread(QThread):

	BucketDeletedResponse = pyqtSignal(bool, str)

	def __init__(self, name):
		QThread.__init__(self)
		self.bucket_name = name

	def run(self):
		try:
			s3_client = boto3.client('s3')
			s3_client.delete_bucket(Bucket=self.bucket_name)
		except ClientError as e:
			self.BucketDeletedResponse.emit(False, str(e))
		else:
			self.BucketDeletedResponse.emit(True, f"Bucket {self.bucket_name} Deleted Successfully!\n")


##################################################################################################
## Loads up the Client Buckets and their files, and outputs them as a QTreeWidgetItem.
## This helps us to set checkboxes, progress bars, buttons, etc to each specific item and type
##################################################################################################
class ClientBuckets(QThread):
	allBucketItems =  pyqtSignal(object)
	def __init__(self, awsSettings):
		QThread.__init__(self)
		self.S3Obj = namedtuple('S3Obj', ['key', 'mtime', 'size', 'ETag'])

		self.accessKey = awsSettings["ACCESS_KEY"]
		self.secretKey = awsSettings["SECRET_KEY"]
		self.region = awsSettings["REGION"]

	def run(self):
		botoClient = boto3.client('s3', aws_access_key_id = self.accessKey, aws_secret_access_key = self.secretKey, region_name = self.region)
		botoResource = boto3.resource('s3', aws_access_key_id = self.accessKey, aws_secret_access_key = self.secretKey, region_name = self.region)
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



##################################################################################################
## Depricated, and will be removed when ready
##################################################################################################
class GetContentsThread(QThread):

	ContentReponse = pyqtSignal(list)

	def __init__(self, bucketName):
		QThread.__init__(self)
		self.bucket = bucketName

	def run(self):
		s3 = boto3.client('s3')
		objects = s3.list_objects(Bucket=str(self.bucket))
		if 'Contents' in objects.keys():
			key = objects['Contents']
			self.ContentReponse.emit(key)
		else:
			key = ["None"]
			self.ContentReponse.emit(key)


##################################################################################################
## Not currently implemented in the current build. This takes files, and starts to upload them
## synchoronously (one at a time, so internet traffic is not overloaded).
##################################################################################################
class UploadFiles(QThread):
	fileCompleted = pyqtSignal(int)
	fileProgress = pyqtSignal(int)
	bytesDetails = pyqtSignal(int, int)
	currentStatus = pyqtSignal(str)

	def __init__(self, files, bucket, region):
		QThread.__init__(self)
		self.bucket = bucket
		self.region = region
		self.files = files
		self.returning = []
		self.totalBytes = 0
		self.totalBytesFinished = 0
		for file in self.files:
			self.totalBytes += os.path.getsize(file["Filepath"])

	def run(self):
		threads = []
		totalFiles = 0
		QueueList = queue.Queue()
		for file in self.files:
			thread = threading.Thread(target=UploadFile, args=(self, file["Filepath"], self.bucket, self.region, file["Filename"], QueueList))
			threads.append(thread)

		for thread in threads:
			thread.start()
			response = QueueList.get()
			if response:
				self.totalBytesFinished += response
				self.returning.append(response)

		for thread in threads:
			thread.join()

##################################################################################################
## The actual worker thread to upload the files.
##################################################################################################
class UploadFile():
	def __init__(self, parent, file_name, bucket, region, object_name, inQueue):
		self.objectName = object_name
		self.fileName = file_name
		self.bucket = bucket
		self.region = region
		self.parent = parent
		self.queue = inQueue

		s3_client = boto3.client("s3", region_name=self.region)
		try:
			with open(self.fileName, "rb") as f:
				response = s3_client.upload_fileobj(f, str(self.bucket), str(self.objectName), Callback=Progress(str(self.fileName), self, self.parent))
		except ClientError as e:
			self.queue.put(False)
		else:
			self.queue.put(os.path.getsize(self.fileName))

##################################################################################################
## The progress amount for the upload sequence. It fires off a progress amount to the status bar
## This will need to be changed to add the progress amount to the listbox instead, and have a
## overall progress on the status bar.
##################################################################################################
class Progress():

	def __init__(self, filename, parent, upperParent):
		self.parent = parent
		self.upperParent = upperParent
		self.fileName = filename
		self.fileSize = float(os.path.getsize(filename))
		self.amountDone = 0
		self.upperParent.currentStatus.emit(f"Starting Upload for: {os.path.basename(filename)}")
		self._lock = threading.Lock()

	def __call__(self, byteAmount):
		with self._lock:
			self.amountDone += byteAmount
			percentage = (self.amountDone / self.fileSize) * 100
			overallPercent = ((self.amountDone + self.upperParent.totalBytesFinished) / self.upperParent.totalBytes) * 100

			self.upperParent.bytesDetails.emit(self.amountDone, self.fileSize)
			self.upperParent.fileCompleted.emit(overallPercent)
			self.upperParent.fileProgress.emit(percentage)

##################################################################################################
## The main workhorse. This takes a list of items from the checklist, and sends them to a
## Async thread (so no more waiting one at a time. Also, now, there is no memory leakage or 
## extra strain on the CPU by making multiple processes. This uses the Asyncio library, which
## fires off the loops properly, and no cross threading or things happen.
##
## This needs to have a second emitter added (replace the fileFinished), currentStatus is not used
## Also need to lock up the main threads "Transcribe", "Listview" and "Refresh" buttons, so that
## nothing is overwritten or submitted twice!!
##################################################################################################
class TranscribeAndDownload(QThread):

	currentStatus = pyqtSignal(str)
	fileFinished = pyqtSignal(str)
	itemToEmit = pyqtSignal(object, int, str) #TODO - Create a second finishing emitter!!


	def __init__(self, files, awsSettings, outputFolder):
		QThread.__init__(self)
		self.files = files
		self.outputFolder = outputFolder

		self.accessKey = awsSettings["ACCESS_KEY"]
		self.secretKey = awsSettings["SECRET_KEY"]
		self.region = awsSettings["REGION"]

	def run(self):

		#This must be run async, otherwise we'd submit a job and then wait until it finishes before we start another - VERY SLOW!
		#This speeds it up, by submitting multiple jobs at the same time, and awaiting the return.
		try:
			loop = asyncio.get_event_loop()
		except:
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)

		tasks = []
		for file in self.files:
			task = asyncio.ensure_future(self.transcribeJobCreator(file["bucket"], file["name"], self.outputFolder, file["item"]))
			task = self.add_success_callback(task, self.transcribeJobCallback)
			tasks.append(task)

		finished, unfinished = loop.run_until_complete(asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED))
		loop.close()

	
	## This creates a callback loop. Otherwise, the function won't register as finished with the "run_until_complete" loop.
	async def add_success_callback(self, fut, callback):
		result = await fut
		await callback(result)
		return result


	async def transcribeJobCallback(self, result):
		res = result["Result"]
		item = result["Item"]
		fileOutput = result["FileOutput"]
		message = result["Message"]

		#TODO - Make a different emitter!!!
		#self.itemToEmit.emit(item, 1,  message, res)


	async def transcribeJobCreator(self, inBucket, inMediaFile, outputFolder, item):
		try:
			transciptionJob = awsModules.Transcribe(self.accessKey, self.secretKey, self.region, inBucket, inMediaFile)
			response = transciptionJob.createJob() #TODO - Make a proper job name!!

			self.itemToEmit.emit(item, 1,  f"Working: {response['TranscriptionJob']['TranscriptionJobName']}")
			
			currentIt = 0
			dotStr = "." #program does not like me adding a . inside of where it is used, so I use this.
			while( response["TranscriptionJob"]["TranscriptionJobStatus"] == "IN_PROGRESS"):
				await asyncio.sleep(10)
				response = transciptionJob.getJobStatus( response["TranscriptionJob"]["TranscriptionJobName"] )

				self.itemToEmit.emit(item, 1,  f"Working: {response['TranscriptionJob']['TranscriptionJobName']} - {dotStr[:1]*currentIt}")
				currentIt += 1

			self.itemToEmit.emit(item, 1,  f"Finished: {response['TranscriptionJob']['TranscriptionJobName']}")

			transcript = transciptionJob.getTranscript( str(response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]) )
			awsModules.SRTModule(transcript, "en", os.path.abspath(os.path.join(outputFolder, f"{inMediaFile[:-4]}-en.srt")))

			return { "Result" : True, "FileOutput" : inMediaFile, "Item" : item , "Message" : "Subtitle downloaded!" }
		except:
			return { "Result" : False, "FileOutput" : "", "Item" : item , "Message" : "Error #001" }
