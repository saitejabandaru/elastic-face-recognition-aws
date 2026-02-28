import os
import boto3
import torch
import time
import asyncio
# from model.face_recognition import face_match
from face_recognition import face_match

S3_INPUT_BUCKET = f"1232625370-in-bucket"
S3_OUTPUT_BUCKET = f"1232625370-out-bucket"
SQS_REQUEST_QUEUE = f"1232625370-req-queue"
SQS_RESPONSE_QUEUE = f"1232625370-resp-queue"

IAM_ACCESSKEY = ""
IAM_SECRETKEY = ""

iam_client = boto3.Session(aws_access_key_id=IAM_ACCESSKEY, aws_secret_access_key=IAM_SECRETKEY)

s3_client = iam_client.client("s3", region_name="us-east-1")
sdb_client = iam_client.client("sdb", region_name="us-east-1")
sqs_client = iam_client.client("sqs", region_name="us-east-1")

sqs_request_url = sqs_client.get_queue_url(QueueName=SQS_REQUEST_QUEUE)["QueueUrl"]
sqs_response_url = sqs_client.get_queue_url(QueueName=SQS_RESPONSE_QUEUE)["QueueUrl"]

def download_image_from_s3(filename):
    local_path = f"/tmp/{filename}"
    s3_client.download_file(S3_INPUT_BUCKET, filename, local_path)
    return local_path

def recognize_face_from_s3(filename):
    image_path = download_image_from_s3(filename)
    return face_match(image_path, 'data.pt')[0]

async def upload_to_s3(key, body):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: s3_client.put_object(Bucket=S3_OUTPUT_BUCKET, Key=key, Body=body))

async def send_req_to_app_tier(filename, prediction):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: sqs_client.send_message(QueueUrl=sqs_response_url, MessageBody=f"{filename}:{prediction}"))

def processImage(msg):
    filename = msg["Body"]
    filename_without_ext = os.path.splitext(filename)[0]
    print(filename, "We got this from request queue")

    prediction = recognize_face_from_s3(filename)

    s3_client.put_object(Bucket=S3_OUTPUT_BUCKET, Key=filename_without_ext, Body=prediction)

    sqs_client.send_message(QueueUrl=sqs_response_url, MessageBody=f"{filename_without_ext}:{prediction}")
    # await send_req_to_app_tier(filename_without_ext, prediction)

    sqs_client.delete_message(QueueUrl=sqs_request_url, ReceiptHandle=msg["ReceiptHandle"])

def process_request():
    while True:
        response = sqs_client.receive_message(QueueUrl=sqs_request_url, MaxNumberOfMessages=1, WaitTimeSeconds=1)
        messages = response.get("Messages", [])

        print(len(messages), "Queue Length of Request")

        if messages:
            for msg in messages:
                processImage(msg)
        else:
            time.sleep(0.5)

if __name__ == "__main__":
    print("Backend server started. Waiting for requests...")
    process_request()