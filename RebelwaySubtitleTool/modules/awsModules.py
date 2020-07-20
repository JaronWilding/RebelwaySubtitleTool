
import boto3
import uuid
import requests
import json, codecs, re
	
# ==================================================================================
# The majority of this function was taken from the example files on the AWS website.
# The code has been changed, as some functions kept throwing errors.
# https://aws.amazon.com/blogs/machine-learning/create-video-subtitles-with-translation-using-machine-learning/
# ==================================================================================

class Transcribe:

	def __init__(self, region, bucket, mediaFile):
		self.region = region
		self.bucket = bucket
		self.mediaFile = mediaFile

	def createJob(self):
		transcribe = boto3.client("transcribe", region_name=self.region)
		mediaUri = f"https://s3-{self.region}.amazonaws.com/{self.bucket}/{self.mediaFile}"
		print(f"Creating Job: Transcribe {self.mediaFile} for {mediaUri}")

		response = transcribe.start_transcription_job( TranscriptionJobName="transcribe_" + uuid.uuid4().hex + "_" + self.mediaFile , \
			LanguageCode = "en-US", \
			MediaFormat = "mp4", \
			Media = { "MediaFileUri" : mediaUri }, \
			#Settings = { "VocabularyName" : "MyVocabulary" } \
			)
		return response

	def getJobStatus(self, jobName):
		transcribe = boto3.client('transcribe')
		response = transcribe.get_transcription_job( TranscriptionJobName=jobName )
		return response
	
	def getTranscript(self, transcriptURI):
		result = requests.get( transcriptURI )
		return result.text


class SRTModule:

	def __init__(self, transcript, sourceLangCode, srtFileName):
		self.writeTranscriptToSRT(transcript, sourceLangCode, srtFileName)

	def newPhrase(self):
		return { 'start_time': '', 'end_time': '', 'words' : [] }

	def getTimeCode(self,  seconds):
		t_hund = int(seconds % 1 * 1000)
		t_seconds = int( seconds )
		t_secs = ((float( t_seconds) / 60) % 1) * 60
		t_mins = int( t_seconds / 60 )
		return str( "%02d:%02d:%02d,%03d" % (00, t_mins, int(t_secs), t_hund ))
	
	
	def writeTranscriptToSRT(self, transcript, sourceLangCode, srtFileName):
		phrases = self.getPhrasesFromTranscript( transcript )

		e = codecs.open(srtFileName, "w+", "utf-8")
		x = 1

		for phrase in phrases:
			length = len(phrase["words"])
			e.write("{0}\n.".format(str(x)))
			x += 1
			e.write( "{start_time} --> {end_time}\n".format(start_time = phrase["start_time"], end_time=phrase["end_time"]))
			e.write("{0}\n\n".format(self.getPhraseText(phrase)))

		e.close()

	def getPhrasesFromTranscript(self, transcript):

		ts = json.loads( transcript )
		items = ts['results']['items']

		phrase =  self.newPhrase()
		phrases = []
		nPhrase = True
		x = 0
		c = 0

		print("==> Creating phrases from transcript...")

		for item in items:

			if nPhrase == True:
				if item["type"] == "pronunciation":
					phrase["start_time"] = self.getTimeCode( float(item["start_time"]) )
					nPhrase = False
				c+= 1
			else:	
				if item["type"] == "pronunciation":
					phrase["end_time"] = self.getTimeCode( float(item["end_time"]) )
				
			phrase["words"].append(item['alternatives'][0]["content"])
			x += 1
		
			if x == 10:
				phrases.append(phrase)
				phrase = self.newPhrase()
				nPhrase = True
				x = 0
			
		return phrases

	def getPhraseText(self, phrase):
		length = len(phrase["words"])
		out = ""
		for i in range( 0, length ):
			if re.match( '[a-zA-Z0-9]', phrase["words"][i]):
				if i > 0:
					out += " " + phrase["words"][i]
				else:
					out += phrase["words"][i]
			else:
				out += phrase["words"][i]
		return out
	
