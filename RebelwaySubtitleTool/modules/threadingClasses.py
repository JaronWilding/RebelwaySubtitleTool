import logging, boto3, requests, threading, safeqthreads, queue, os, time
from PyQt5.QtCore import QThread, pyqtSignal, QDir, QObject, QMutex
from botocore.exceptions import ClientError, ParamValidationError
import modules.awsModules as awsModules


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










class TranscribeAndDownload(QThread):

	currentStatus = pyqtSignal(str)
	fileFinished = pyqtSignal(str)

	def __init__(self, files, bucket, region, outputFolder):
		QThread.__init__(self)
		self.bucket = bucket
		self.region = region
		self.files = files
		self.outputFolder = outputFolder

	def run(self):
		threads = []
		totalFiles = 0

		QueueList = queue.Queue()
		for file in self.files:
			thread = threading.Thread(target=TranscribeThread, args=(self, self.region,  self.bucket, file, self.outputFolder , QueueList))
			threads.append(thread)

		for thread in threads:
			thread.start()
			res, returnFile = QueueList.get()
			if res == True:
				self.fileFinished.emit(returnFile)

		for thread in threads:
			thread.join()

class TranscribeThread():
	def __init__(self, parent, inRegion, inBucket, inMediaFile, outputFolder, inQueue):
		try:
			transciptionJob = awsModules.Transcribe(inRegion, inBucket, inMediaFile)
			response = transciptionJob.createJob()

			parent.currentStatus.emit(f"Transcription Job: {response['TranscriptionJob']['TranscriptionJobName']} - In Progress")
			currentIt = 0
			dotStr = "."
			while( response["TranscriptionJob"]["TranscriptionJobStatus"] == "IN_PROGRESS"):
				time.sleep(10)
				response = transciptionJob.getJobStatus( response["TranscriptionJob"]["TranscriptionJobName"] )
				parent.currentStatus.emit(f"Transcription Job: {response['TranscriptionJob']['TranscriptionJobName']} - In Progress{dotStr[:1]*currentIt}")
				currentIt += 1

			parent.currentStatus.emit(f"Transcription Job: {response['TranscriptionJob']['TranscriptionJobName']} - Job Complete - Start Time: {str(response['TranscriptionJob']['CreationTime'])} - End Time: {str(response['TranscriptionJob']['CompletionTime'])}")

			transcript = transciptionJob.getTranscript( str(response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]) )
			awsModules.SRTModule(transcript, "en", os.path.abspath(os.path.join(outputFolder, f"{inMediaFile[:-4]}-en.srt")))
			inQueue.put(True, inMediaFile)
		except:
			inQueue.put(False, "")


#print( "\nJob Complete")
#print( "\tStart Time: " + str(response["TranscriptionJob"]["CreationTime"]) )
#print( "\tEnd Time: "  + str(response["TranscriptionJob"]["CompletionTime"]) )
#print( "\tTranscript URI: " + str(response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]) )


#transcript = transciptionJob.getTranscript( str(response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]) ) 
#print( "\n==> Transcript: \n" + transcript)

## awsModules.SRTModule().writeTranscriptToSRT(transcript, "en", "subtitles-en.srt")
#awsModules.SRTModule(transcript, "en", "subtitles-en.srt")