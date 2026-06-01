Project Overview:
This project implements a serverless, event-driven document processing pipeline on AWS. When a document is uploaded to Amazon S3, an AWS Lambda function is triggered, metadata is sent to Amazon SQS, processed by a second Lambda function, stored in Amazon DynamoDB, and a notification is sent using Amazon SNS.

The project is designed as the foundation for a future AI-powered document processing and RAG system.

Project Overview:


Architecture:


Current Implementation:
- S3 bucket for document uploads
- Lambda function triggered by S3 events
- SQS queue for decoupled processing
- Lambda function for metadata processing
- DynamoDB table for storing document metadata
- SNS email notification after successful processing
- CloudWatch Logs for monitoring and debugging


AWS Services Used:


Event Flow:
1. User uploads a document to S3.
2. S3 triggers the upload Lambda function.
3. Upload Lambda extracts document metadata.
4. Upload Lambda sends metadata message to SQS.
5. SQS triggers the metadata processing Lambda function.
6. Metadata processing Lambda stores metadata in DynamoDB.
7. Metadata processing Lambda publishes a success notification to SNS.
8. User receives an email notification.


Monitoring and Logging:
Amazon CloudWatch Logs is used to monitor Lambda execution, debug failures, and trace the event-driven workflow throughout the pipeline.


Failure Handling:
The architecture includes a Dead Letter Queue (DLQ) for failed SQS messages. If a document metadata message cannot be processed after multiple attempts (set to 3), it is moved to the DLQ for later inspection and troubleshooting.


Cost Optimizations:
This project was designed to minimize AWS costs by using serverless and pay-per-use services.

Cost-control measures:
- S3 is used only for small test documents.
- Lambda functions run only when triggered.
- SQS is used with small test messages.
- DynamoDB uses on-demand capacity.
- SNS uses email notifications only.
- CloudWatch Logs are used for debugging and can be configured with short retention.
- Resources can be deleted after testing while preserving code, diagrams, and screenshots in GitHub.

Setup Instructions:


Features:


Future Improvements:


Lessons Learned:
