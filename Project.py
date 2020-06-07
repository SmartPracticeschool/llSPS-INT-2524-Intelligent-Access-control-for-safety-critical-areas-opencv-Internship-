#for creating  a bucket
import ibm_boto3
from ibm_botocore.client import Config, ClientError

import cv2
import numpy as np
import datetime

#CloudantDB
from cloudant.client import Cloudant
from cloudant.error import CloudantException
from cloudant.result import Result, ResultByKey
import requests

import json
from ibm_watson import VisualRecognitionV4
from ibm_watson.visual_recognition_v4 import AnalyzeEnums, FileWithMetadata
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

from ibm_watson import TextToSpeechV1
from playsound import playsound


# Constants for IBM COS values
COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud" # Current list avaiable at https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints
COS_API_KEY_ID = "x7BxfdQP_nAFNEMg3MSHvD7YC59zZ1gqs6BvKmB7tbEH" # eg "W00YiRnLW4a3fTjMB-odB-2ySfTrFBIQQWanc--P3byk"
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_RESOURCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/b1ac3f2736814de592bb16211ba2acea:4ae0113a-daec-4b75-ab73-375d8e6403f3::" # eg "crn:v1:bluemix:public:cloud-object-storage:global:a/3bf0d9003abfb5d29761c3e97696b71c:d6f04d83-6c4f-4a62-a165-696756d63903::"

# Create resource
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_RESOURCE_CRN,
    ibm_auth_endpoint=COS_AUTH_ENDPOINT,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)

def create_bucket(bucket_name):
    print("Creating new bucket: {0}".format(bucket_name))
    try:
        cos.Bucket(bucket_name).create(
            CreateBucketConfiguration={
                "LocationConstraint":"jp-tok-standard"
            }
        )
        print("Bucket: {0} created!".format(bucket_name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to create bucket: {0}".format(e))


authenticator = IAMAuthenticator('ZCRzhwLwrlj2QeDdXs9UtfUQYt3Cn9IlLSgXhy5nTxgU')
visual_recognition = VisualRecognitionV4(
    version='2019-02-11',
    authenticator=authenticator
)

visual_recognition.set_service_url('https://api.us-south.visual-recognition.watson.cloud.ibm.com/instances/768a1911-c2ab-4515-9c43-ee7ee4e9bb70')

authenticator = IAMAuthenticator('Z1AlvgOrZM2OAav9mTXekzUNu1YyyeSnKEcAGysXTqu_')
text_to_speech = TextToSpeechV1(
    authenticator=authenticator
)

text_to_speech.set_service_url('https://api.eu-gb.text-to-speech.watson.cloud.ibm.com/instances/775bf7e6-4cec-4579-830d-c63f75490691')
#sending a image to object/////////////////////////////////////////////////////////////////////////////////////////////////////
#pic name is worker.jpg , bucket name is projectiot#########################
###########cloundantdb side//////////////////////////////////////////////////////////////////////


face_classifier=cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
eye_classifier=cv2.CascadeClassifier("haarcascade_eye.xml")


#Provide CloudantDB credentials such as username,password and url

client = Cloudant("cff8f8d1-8e77-4ae2-930b-169c5de7ef5b-bluemix", "4b14b230343619d8341bc7c596f6d44530526d5d6397160756604a520fa58a7c", url="https://cff8f8d1-8e77-4ae2-930b-169c5de7ef5b-bluemix:4b14b230343619d8341bc7c596f6d44530526d5d6397160756604a520fa58a7c@cff8f8d1-8e77-4ae2-930b-169c5de7ef5b-bluemix.cloudantnosqldb.appdomain.cloud")
client.connect()

#Provide your database name

database_name = "project-iot"

my_database = client.create_database(database_name)

if my_database.exists():
   print(f"'{database_name}' successfully created.")



def multi_part_upload(bucket_name, item_name, file_path):
    try:
        print("Starting file transfer for {0} to bucket: {1}\n".format(item_name, bucket_name))
        # set 5 MB chunks
        part_size = 1024 * 1024 * 5

        # set threadhold to 15 MB
        file_threshold = 1024 * 1024 * 15

        # set the transfer threshold and chunk size
        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold,
            multipart_chunksize=part_size
        )

        # the upload_fileobj method will automatically execute a multi-part upload
        # in 5 MB chunks for all files over 15 MB
        with open(file_path, "rb") as file_data:
            cos.Object(bucket_name, item_name).upload_fileobj(
                Fileobj=file_data,
                Config=transfer_config
            )

        print("Transfer for {0} Complete!\n".format(item_name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to complete multi-part upload: {0}".format(e))


#It will read the first frame/image of the video
video=cv2.VideoCapture(0)

while True:
    #capture the first frame
    check,frame=video.read()
    gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    

    #detect the faces from the video using detectMultiScale function
    faces=face_classifier.detectMultiScale(gray,1.3,5)
    eyes=eye_classifier.detectMultiScale(gray,1.3,5)

    print(faces)
    
    #drawing rectangle boundries for the detected face
    for(x,y,w,h) in faces:
        cv2.rectangle(frame, (x,y), (x+w,y+h), (127,0,255), 2)
        cv2.imshow('Face detection', frame)
        picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
        cv2.imwrite(picname+".jpg",frame)
        multi_part_upload("project-iot", picname+".jpg", picname+".jpg")
        json_document={"link":COS_ENDPOINT+"/"+"project-iot"+"/"+picname+".jpg"}
        new_document = my_database.create_document(json_document)
        # Check that the document exists in the database.
        if new_document.exists():
            print(f"Document successfully created.")

        url = "https://www.fast2sms.com/dev/bulk"
        querystring = {"authorization":"VunYHRXBhEbfL1vleDJQI0ySWo4M2NAm6Oxq5gipadwt3crZFCj3Mtxd1nUW2K0Pc5zFJHhmwOI9TgBo","sender_id":"FSTSMS","message":"A worker is at the gates.","language":"english","route":"p","numbers":"8300448682, 9025592443"}
        headers = {
           'cache-control': "no-cache"
           }
        response = requests.request("GET", url, headers=headers, params=querystring)
        print(response.text)
        
        with open(picname + '.jpg', 'rb') as img:
            result = visual_recognition.analyze(
                collection_ids=["2db6113b-aaae-4924-b424-a1103669251f"],
                features=[AnalyzeEnums.Features.OBJECTS.value],
                images_file=[FileWithMetadata(img)],
                threshold = '0.6').get_result()

        if (result['images'][0]['objects'] != {}):
            with open('Can_Enter.mp3', 'wb') as audio_file: #wb means write bytes
                audio_file.write(
                    text_to_speech.synthesize(
                        'The Gate will open. You can enter now.',
                        voice='en-US_AllisonVoice',
                        accept='audio/mp3').get_result().content)
            playsound('Can_Enter.mp3')

        else:
            with open('Cannot_Enter.mp3', 'wb') as audio_file: #wb means write bytes
                audio_file.write(
                    text_to_speech.synthesize(
                        'As you are not wearing the appropriate personal protection equipment (helmet), you cannot enter. Please wear a helmet.',
                        voice='en-US_AllisonVoice',
                        accept='audio/mp3').get_result().content)
            playsound('Cannot_Enter.mp3')
        
        
    #drawing rectangle boundries for the detected eyes
    for(ex,ey,ew,eh) in eyes:
        cv2.rectangle(frame, (ex,ey), (ex+ew,ey+eh), (127,0,255), 2)
        cv2.imshow('Face detection', frame)

    #waitKey(1)- for every 1 millisecond new frame will be captured
    Key=cv2.waitKey(1)
    if Key==ord('q'):
        #release the camera
        video.release()
        #destroy all windows
        cv2.destroyAllWindows()
        break
