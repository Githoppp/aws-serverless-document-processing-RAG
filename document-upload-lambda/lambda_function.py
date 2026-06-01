import json
import os
import boto3
from urllib.parse import unquote_plus

sqs = boto3.client("sqs")

QUEUE_URL = os.environ["QUEUE_URL"]

def lambda_handler(event, context):
    print("Received S3 event:", json.dumps(event))

    for record in event["Records"]:
        # Gets the name of the s3 bucket where the file was added
        bucket_name = record["s3"]["bucket"]["name"]

        # Gets the name of the file which was uploaded in the bucket
        object_key = unquote_plus(record["s3"]["object"]["key"])

        # Gets the size of the file uploaded in the s3 bucket, get("size", 0) means if size exists then get it or keep it 0
        object_size = record["s3"]["object"].get("size", 0)

        # Stores all the information received from the individual event into a dictionary called message which will be sent via sqs
        message = {
            "bucket_name": bucket_name,
            "object_key": object_key,
            "object_size": object_size,
            "event_time": record["eventTime"]
        }

        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message)
        )

        print("Message sent to SQS:", message)

    return {
        "statusCode": 200,
        "body": json.dumps("S3 event processed successfully")
    }