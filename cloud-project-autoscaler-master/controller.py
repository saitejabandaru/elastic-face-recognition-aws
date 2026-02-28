import boto3
import time

# AWS Configuration
AWS_REGION = "us-east-1"
ASU_ID = "1232625370"

SQS_REQUEST_QUEUE = f"{ASU_ID}-req-queue"

INSTANCE_NAME_PREFIX = "app-tier-instance-"

IAM_ACCESSKEY = ""
IAM_SECRETKEY = ""

iam_session = boto3.Session(aws_access_key_id=IAM_ACCESSKEY, aws_secret_access_key=IAM_SECRETKEY)

sqs_client = iam_session.client("sqs", region_name=AWS_REGION)
ec2_client = iam_session.client("ec2", region_name=AWS_REGION)

sqs_request_url = sqs_client.get_queue_url(QueueName=SQS_REQUEST_QUEUE)["QueueUrl"]

def get_sqs_queue_size():
    response = sqs_client.get_queue_attributes(
        QueueUrl=sqs_request_url,
        AttributeNames=["ApproximateNumberOfMessages"]
    )
    return int(response["Attributes"]["ApproximateNumberOfMessages"])

def get_instances_by_state(state):
    response = ec2_client.describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [f"{INSTANCE_NAME_PREFIX}*"]},
            {"Name": "instance-state-name", "Values": [state]}
        ]
    )
    return [instance["InstanceId"] for res in response["Reservations"] for instance in res["Instances"]]

def start_instances(instance_ids):
    if instance_ids:
        ec2_client.start_instances(InstanceIds=instance_ids)
        print(f"Started instances: {instance_ids}")

def stop_instances(instance_ids):
    if instance_ids:
        ec2_client.stop_instances(InstanceIds=instance_ids)
        print(f"Stopping instances: {instance_ids}")

stop_all_count = 0

def autoscale():
    global stop_all_count
    while True:
        queue_size = get_sqs_queue_size()
        running_instances = get_instances_by_state("running")
        stopped_instances = get_instances_by_state("stopped")

        print(f"Queue Size: {queue_size} | Running: {len(running_instances)} | Stopped: {len(stopped_instances)}")

        if queue_size > len(running_instances):
            instances_needed = min(queue_size - len(running_instances), len(stopped_instances))
            if instances_needed > 0:
                instances_to_start = stopped_instances[:instances_needed]
                start_instances(instances_to_start)

            stop_all_count = 0

        elif queue_size == 0 and len(running_instances) > 0:

            stop_all_count +=1 
            if(stop_all_count > 1):
                stop_instances(running_instances)
                stop_all_count = 0

        time.sleep(2.5)

if __name__ == "__main__":
    print("Controller started and Monitoring SQS and managing EC2 instances")
    autoscale()