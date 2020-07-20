import boto3
import uuid
import requests
import json, codecs, re, pprint, datetime

def createSRT(transcript, name):

	def getTimeCode(seconds):
		t_hund = int(seconds % 1 * 1000)
		t_seconds = int( seconds )
		t_secs = ((float( t_seconds) / 60) % 1) * 60
		t_mins = int( t_seconds / 60 )
		return str( "%02d:%02d:%02d,%03d" % (00, t_mins, int(t_secs), t_hund ))

	start_time=end_time=sentence=mainText=""
	n=t = 1
	transcriptItems = json.loads(transcript)['results']['items']
	
	for item in transcriptItems:
		if item["type"] == "pronunciation":
			if start_time == "":
				start_time = item["start_time"]
			end_time = item["end_time"]
			sentence += item["alternatives"][0]["content"] + " "
			t += 1
		elif item["type"] == "punctuation" and item["alternatives"][0]["content"] == ".":
			mainText += f"{n}\n"
			mainText += f"{getTimeCode(float(start_time))} --> {getTimeCode(float(end_time))}\n{sentence}\n\n"
			start_time = ""
			sentence = ""
			t = 1
			n += 1

	e = codecs.open(f"{name}.srt", "w+", "utf-8")
	e.writelines(mainText)
	e.close()
	print(mainText)
	




client = boto3.client('transcribe')
main = client.list_transcription_jobs()

for jobs in main['TranscriptionJobSummaries']:
	jobName = jobs['TranscriptionJobName']
	trans = client.get_transcription_job(TranscriptionJobName=jobName)
	transUri = trans["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
	result = requests.get( transUri )
	#pprint.pprint(result.text)
	createSRT(result.text, jobName[44:])
