import json
import os
from pathlib import Path

import boto3
import faiss
import numpy as np


AWS_REGION = "us-east-1"
S3_BUCKET_NAME = "rustom-serverless-doc-processing-2026"

FAISS_FOLDER = Path("faiss")
FAISS_INDEX_PATH = FAISS_FOLDER / "index.faiss"
METADATA_PATH = FAISS_FOLDER / "metadata.json"

BEDROCK_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"


bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)


def chunk_text(text, chunk_size=500, chunk_overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start += chunk_size - chunk_overlap

    return chunks


def get_embedding(text):
    body = {
        "inputText": text
    }

    response = bedrock.invoke_model(
        modelId=BEDROCK_EMBEDDING_MODEL_ID,
        body=json.dumps(body)
    )

    response_body = json.loads(response["body"].read())
    return response_body["embedding"]


def build_faiss_index(chunks, document_id, object_key):
    embeddings = []
    metadata = []

    for i, chunk in enumerate(chunks):
        print(f"Generating embedding for chunk {i + 1}/{len(chunks)}")

        embedding = get_embedding(chunk)
        embeddings.append(embedding)

        metadata.append({
            "chunk_id": i,
            "document_id": document_id,
            "object_key": object_key,
            "chunk_text": chunk
        })

    embedding_matrix = np.array(embeddings).astype("float32")

    dimension = embedding_matrix.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embedding_matrix)

    return index, metadata


def save_and_upload(index, metadata):
    FAISS_FOLDER.mkdir(exist_ok=True)

    faiss.write_index(index, str(FAISS_INDEX_PATH))

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    s3.upload_file(str(FAISS_INDEX_PATH), S3_BUCKET_NAME, "faiss_index/index.faiss")
    s3.upload_file(str(METADATA_PATH), S3_BUCKET_NAME, "faiss_index/metadata.json")

    print("FAISS index and metadata uploaded to S3.")


def main():
    sample_text = """
    AWS Serverless Document Processing Project.

    This document explains a serverless, event-driven AWS architecture using
    Amazon S3, AWS Lambda, Amazon SQS, Amazon DynamoDB, Amazon SNS,
    Amazon Textract, Amazon Bedrock, and FAISS.

    The system extracts text from uploaded documents, generates summaries,
    classifies documents, creates vector embeddings, and supports retrieval
    augmented generation using a FAISS vector index.
    """

    document_id = "local-test-document"
    object_key = "sample-document.pdf"

    chunks = chunk_text(sample_text)

    print(f"Created {len(chunks)} chunks")

    index, metadata = build_faiss_index(chunks, document_id, object_key)

    save_and_upload(index, metadata)


if __name__ == "__main__":
    main()