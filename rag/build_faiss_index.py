import json
from pathlib import Path

import boto3
import faiss
import numpy as np


AWS_REGION = "us-east-1"
S3_BUCKET_NAME = "rustom-serverless-doc-processing-2026"

PROCESSED_TEXT_PREFIX = "processed_text/"
FAISS_INDEX_S3_KEY = "faiss_index/index.faiss"
METADATA_S3_KEY = "faiss_index/metadata.json"

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
    body = {"inputText": text}

    response = bedrock.invoke_model(
        modelId=BEDROCK_EMBEDDING_MODEL_ID,
        body=json.dumps(body)
    )

    response_body = json.loads(response["body"].read())
    return response_body["embedding"]


def list_processed_text_files():
    response = s3.list_objects_v2(
        Bucket=S3_BUCKET_NAME,
        Prefix=PROCESSED_TEXT_PREFIX
    )

    files = []

    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".txt"):
            files.append(key)

    return files


def read_s3_text_file(key):
    response = s3.get_object(
        Bucket=S3_BUCKET_NAME,
        Key=key
    )

    return response["Body"].read().decode("utf-8")


def build_faiss_index():
    all_embeddings = []
    all_metadata = []

    text_files = list_processed_text_files()

    print(f"Found {len(text_files)} processed text files")

    for text_key in text_files:
        print(f"Reading {text_key}")

        text = read_s3_text_file(text_key)
        chunks = chunk_text(text)

        object_key = text_key.replace(PROCESSED_TEXT_PREFIX, "").replace(".txt", ".pdf")
        document_id = object_key

        for i, chunk in enumerate(chunks):
            print(f"Embedding {text_key} chunk {i + 1}/{len(chunks)}")

            embedding = get_embedding(chunk)
            all_embeddings.append(embedding)

            all_metadata.append({
                "chunk_id": len(all_metadata),
                "document_id": document_id,
                "object_key": object_key,
                "source_text_key": text_key,
                "chunk_number": i,
                "chunk_text": chunk
            })

    if not all_embeddings:
        raise ValueError("No processed text found. Upload/process a document first.")

    embedding_matrix = np.array(all_embeddings).astype("float32")

    dimension = embedding_matrix.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embedding_matrix)

    return index, all_metadata


def save_and_upload(index, metadata):
    FAISS_FOLDER.mkdir(exist_ok=True)

    faiss.write_index(index, str(FAISS_INDEX_PATH))

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    s3.upload_file(str(FAISS_INDEX_PATH), S3_BUCKET_NAME, FAISS_INDEX_S3_KEY)
    s3.upload_file(str(METADATA_PATH), S3_BUCKET_NAME, METADATA_S3_KEY)

    print("FAISS index uploaded to S3")
    print("Metadata uploaded to S3")


def main():
    index, metadata = build_faiss_index()
    save_and_upload(index, metadata)

    print(f"Indexed {len(metadata)} chunks successfully")


if __name__ == "__main__":
    main()