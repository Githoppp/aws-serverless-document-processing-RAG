import json
import os
import uuid
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

# For phase-2
textract = boto3.client("textract")
bedrock = boto3.client("bedrock-runtime")

# For phase-3
s3 = boto3.client("s3")

TABLE_NAME = os.environ["TABLE_NAME"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print("Received SQS event:", json.dumps(event))

    for record in event["Records"]:
        message = json.loads(record["body"])

        document_id = str(uuid.uuid4())
     
        print("Bucket:", message["bucket_name"])
        print("Object:", message["object_key"])

        # Call Textract
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

        # For phase-3
        processed_text_key = f"processed_text/{message['object_key'].rsplit('.', 1)[0]}.txt"

        s3.put_object(
            Bucket=message["bucket_name"],
            Key=processed_text_key,
            Body=extracted_text.encode("utf-8"),
            ContentType="text/plain"
        )

        print("Extracted text saved to S3:")
        print(processed_text_key)
        

        prompt = f"""
        Analyze the following document.
        Tasks:

        1. Provide a summary in 3-5 sentences.

        2. Classify the document into ONE of the following categories:

        - Resume
        - Invoice
        - Contract
        - Research Paper
        - Technical Document
        - Medical Report
        - Other

        Return your response in the following format:

        SUMMARY:
        <summary>

        CLASSIFICATION:
        <classification>

        Document:

        {extracted_text}
        """

        # Send prompt to Bedrock
        try:
            print("Calling Bedrock...")

            response = bedrock.converse(
                modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ]
            )

            response_text = response["output"]["message"]["content"][0]["text"]

            print("Bedrock call successful")
            print("Generated Summary:")
            print(response_text)

            summary = ""
            document_type = ""

            if "CLASSIFICATION:" in response_text:
                parts = response_text.split("CLASSIFICATION:")

                summary = parts[0].replace("SUMMARY:", "").strip()
                document_type = parts[1].strip()

            print("Summary:")
            print(summary)

            print("Document Type:")
            print(document_type)

        except Exception as e:
            print("Bedrock error:", str(e))
            raise

        # Store metadata in DynamoDB
        item = {
            "document_id": document_id,
            "bucket_name": message["bucket_name"],
            "object_key": message["object_key"],
            "object_size": message["object_size"],
            "upload_event_time": message["event_time"],
            "processing_status": "PROCESSED",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "document_type": document_type
        }

        
        table.put_item(Item=item)


        # Send SNS notification
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Document Processed Successfully",
            Message=f"Document processed successfully:\n\nFile: {message['object_key']}\nBucket: {message['bucket_name']}\nStatus: PROCESSED\nSummary:\n{summary}\nClassification:{document_type}"
        )

        print("Metadata stored and SNS notification sent:", item)

    return {
        "statusCode": 200,
        "body": json.dumps("Metadata processed successfully")
    }