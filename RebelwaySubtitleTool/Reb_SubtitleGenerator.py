
import boto3
import uuid
import requests
import time
from transcribeUtils import *

inRegion = "us-east-2"
inBucket = "jaron-bucket-here/"
outBucket = "robdac-aiml-test/"
inMediaFile = "1_intro.mp4"

response = createTranscribeJob(inRegion, inBucket, inMediaFile)

# loop until the job successfully completes
print( "\n==> Transcription Job: " + response["TranscriptionJob"]["TranscriptionJobName"] + "\n\tIn Progress"),

while( response["TranscriptionJob"]["TranscriptionJobStatus"] == "IN_PROGRESS"):
	print( "."),
	time.sleep( 30 )
	response = getTranscriptionJobStatus( response["TranscriptionJob"]["TranscriptionJobName"] )

print( "\nJob Complete")
print( "\tStart Time: " + str(response["TranscriptionJob"]["CreationTime"]) )
print( "\tEnd Time: "  + str(response["TranscriptionJob"]["CompletionTime"]) )
print( "\tTranscript URI: " + str(response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]) )

# Now get the transcript JSON from AWS Transcribe
transcript = getTranscript( str(response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]) ) 
print( "\n==> Transcript: \n" + transcript)