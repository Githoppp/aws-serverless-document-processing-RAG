import json
from pathlib import Path

import boto3
import faiss
import numpy as np


AWS_REGION = "us-east-1"
S3_BUCKET_NAME = "rustom-serverless-doc-processing-2026"

FAISS_INDEX_S3_KEY = "faiss_index/index.faiss"
METADATA_S3_KEY = "faiss_index/metadata.json"

FAISS_FOLDER = Path("faiss")
FAISS_INDEX_PATH = FAISS_FOLDER / "index.faiss"
METADATA_PATH = FAISS_FOLDER / "metadata.json"

BEDROCK_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)


def download_faiss_files():
    FAISS_FOLDER.mkdir(exist_ok=True)

    s3.download_file(S3_BUCKET_NAME, FAISS_INDEX_S3_KEY, str(FAISS_INDEX_PATH))
    s3.download_file(S3_BUCKET_NAME, METADATA_S3_KEY, str(METADATA_PATH))

    print("Downloaded FAISS index and metadata from S3")


def get_embedding(text):
    body = {"inputText": text}

    response = bedrock.invoke_model(
        modelId=BEDROCK_EMBEDDING_MODEL_ID,
        body=json.dumps(body)
    )

    response_body = json.loads(response["body"].read())
    return response_body["embedding"]


def load_index_and_metadata():
    index = faiss.read_index(str(FAISS_INDEX_PATH))

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return index, metadata


def search_faiss(question, top_k=3):
    download_faiss_files()

    index, metadata = load_index_and_metadata()

    question_embedding = get_embedding(question)
    query_vector = np.array([question_embedding]).astype("float32")

    distances, indices = index.search(query_vector, top_k)

    results = []

    for rank, idx in enumerate(indices[0]):
        if idx == -1:
            continue

        result = metadata[idx]
        result["distance"] = float(distances[0][rank])
        results.append(result)

    return results

def generate_answer(question, retrieved_chunks):
    context = "\n\n".join(
        [chunk["chunk_text"] for chunk in retrieved_chunks]
    )

    prompt = f"""
    You are a helpful assistant answering questions from uploaded documents.

    Use ONLY the context below.

    Context:
    {context}

    Question:
    {question}

    If the answer is not present in the context, say:
    'I could not find the answer in the uploaded documents.'

    Answer:
    """

    response = bedrock.converse(
        modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    )

    answer = response["output"]["message"]["content"][0]["text"]

    return answer


# def main():
#     question = input("Ask a question about your documents: ")

#     results = search_faiss(question)

#     print("\nTop matching chunks:\n")

#     for i, result in enumerate(results, start=1):
#         print(f"Result {i}")
#         print(f"Source: {result['object_key']}")
#         print(f"Chunk number: {result['chunk_number']}")
#         print(f"Distance: {result['distance']}")
#         print("Chunk text:")
#         print(result["chunk_text"])
#         print("-" * 80)

def main():
    question = input(
        "Ask a question about your documents: "
    )

    results = search_faiss(
        question,
        top_k=3
    )

    print("\nRetrieved Chunks:\n")

    for i, result in enumerate(results, start=1):
        print(f"Result {i}")
        print(
            f"Source: {result['object_key']}"
        )
        print(
            f"Chunk number: {result['chunk_number']}"
        )
        print("-" * 80)

    print("\nGenerating Final Answer...\n")

    answer = generate_answer(
        question,
        results
    )

    print("ANSWER:\n")
    print(answer)


if __name__ == "__main__":
    main()