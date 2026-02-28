import os
import boto3
import asyncio
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import PlainTextResponse
from contextlib import asynccontextmanager
import uvicorn

ASU_ID = "1234335377" 
AWS_REGION = "us-east-1"

S3_BUCKET_NAME = f"{ASU_ID}-in-bucket"
SQS_REQUEST_QUEUE = f"{ASU_ID}-req-queue"
SQS_RESPONSE_QUEUE = f"{ASU_ID}-resp-queue"

IAM_ACCESSKEY = ""
IAM_SECRETKEY = ""

iam_client = boto3.Session(aws_access_key_id=IAM_ACCESSKEY, aws_secret_access_key=IAM_SECRETKEY)
s3_client = iam_client.client("s3", region_name="us-east-1")
sdb_client = iam_client.client("sdb", region_name="us-east-1")
sqs_client = iam_client.client("sqs", region_name="us-east-1")

# Get SQS Queue URLs
sqs_request_url = sqs_client.get_queue_url(QueueName=SQS_REQUEST_QUEUE)["QueueUrl"]
sqs_response_url = sqs_client.get_queue_url(QueueName=SQS_RESPONSE_QUEUE)["QueueUrl"]

processed_results = dict()

async def upload_to_s3(file_obj, filename):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: s3_client.upload_fileobj(file_obj, S3_BUCKET_NAME, filename))

async def send_req_to_app_tier(filename):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: sqs_client.send_message(QueueUrl=sqs_request_url, MessageBody=filename))

async def retrieve_response(filename):
    print("Retreiving Response for:", filename)
    filename_without_ext = os.path.splitext(filename)[0]

    while True:

        if filename_without_ext in processed_results:
            return f"{filename}:{processed_results[filename_without_ext]}"
        
        response = sqs_client.receive_message(QueueUrl=sqs_response_url, MaxNumberOfMessages=10)
        messages = response.get("Messages", [])
        if messages:
            for msg in messages:
                body = msg["Body"]
                print(body,"Inside this message from response queue")
                processed_filename, result = body.split(":")
                processed_results[processed_filename] = result
                sqs_client.delete_message(QueueUrl=sqs_response_url, ReceiptHandle=msg["ReceiptHandle"])

                if processed_filename == filename_without_ext:
                    print("Matched with existing request so deleting message from response")
                    return f"{filename}:{result}"
        

async def listen_to_sqs():

    while True:
        response = sqs_client.receive_message(QueueUrl=sqs_response_url, MaxNumberOfMessages=10, WaitTimeSeconds=2)
        messages = response.get("Messages", [])

        if messages:
            for msg in messages:
                body = msg["Body"]
                print(f"Received SQS response: {body}")

                processed_filename, result = body.split(":")
                processed_results[processed_filename] = result

                sqs_client.delete_message(QueueUrl=sqs_response_url, ReceiptHandle=msg["ReceiptHandle"])
                print(f"Processed and deleted SQS message for: {processed_filename}")

        await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to start background SQS listener."""
    print("Starting SQS Listener in background")
    task = asyncio.create_task(listen_to_sqs())
    yield  
    task.cancel() 
    print("Stopped SQS Listener")

app = FastAPI(lifespan=lifespan)

@app.post("/")
async def handle_request(inputFile: UploadFile = File(...)):

    try:
        filename = inputFile.filename
        filename_without_ext = os.path.splitext(filename)[0]

        # if filename_without_ext in processed_results:
        #     return f"{filename}:{processed_results[filename_without_ext]}"

        print("\nProcessing: ", filename)

        await upload_to_s3(inputFile.file, filename)
        print(f"Image {filename} uploaded successfully!")

        await send_req_to_app_tier(filename)
        print(f"Image {filename} added to SQS request queue!")

        # result1 = await retrieve_response(filename)

        while filename_without_ext not in processed_results:
            await asyncio.sleep(1)

        result1 = f"{filename_without_ext}:{processed_results[filename_without_ext]}"
        processed_results.pop(filename_without_ext)

        return PlainTextResponse(f"{result1}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)