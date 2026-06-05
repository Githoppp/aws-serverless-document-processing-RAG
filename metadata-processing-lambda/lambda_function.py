import json
import os
import uuid
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

# For phase-2
textract = boto3.client("textract")

TABLE_NAME = os.environ["TABLE_NAME"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print("Received SQS event:", json.dumps(event))

    for record in event["Records"]:
        message = json.loads(record["body"])

        document_id = str(uuid.uuid4())

        item = {
            "document_id": document_id,
            "bucket_name": message["bucket_name"],
            "object_key": message["object_key"],
            "object_size": message["object_size"],
            "upload_event_time": message["event_time"],
            "processing_status": "PROCESSED",
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

        table.put_item(Item=item)

        print("Bucket:", message["bucket_name"])
        print("Object:", message["object_key"])

        textract_response = textract.detect_document_text(
            Document={
                "S3Object": {
                    "Bucket": message["bucket_name"],
                    "Name": message["object_key"]
                }
            }
        )

        extracted_text = ""

        for block in textract_response["Blocks"]:
            if block["BlockType"] == "LINE":
                extracted_text += block["Text"] + "\n"

        print("Extracted text from Textract:")
        print(extracted_text)

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Document Processed Successfully",
            Message=f"Document processed successfully:\n\nFile: {message['object_key']}\nBucket: {message['bucket_name']}\nStatus: PROCESSED"
        )

        print("Metadata stored and SNS notification sent:", item)

    return {
        "statusCode": 200,
        "body": json.dumps("Metadata processed successfully")
    }