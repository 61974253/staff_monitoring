import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE, override=True)

api_key = os.getenv("CHROMA_API_KEY")
tenant = os.getenv("CHROMA_TENANT")
database = os.getenv("CHROMA_DATABASE")
collection_name = os.getenv("CHROMA_COLLECTION_NAME")

if not all([api_key, tenant, database, collection_name]):
    raise ValueError(
        "Missing settings. Check your .env file."
    )

print("STEP 1: Environment settings loaded.")

try:
    print("STEP 2: Connecting to Chroma Cloud...")

    client = chromadb.CloudClient(
        api_key=api_key,
        tenant=tenant,
        database=database,
    )

    print("STEP 3: Client created successfully.")

    print("STEP 4: Checking database access...")

    collections = client.list_collections()

    print("STEP 5: Database access successful.")
    print("Available collections:")

    for item in collections:
        print("-", item.name)

    print("STEP 6: Checking selected collection...")

    collection = client.get_collection(
        name=collection_name
    )

    print("Collection:", collection.name)
    print("Total records:", collection.count())

except Exception as error:
    print("\nFAILED!")
    print("Error type:", type(error).__name__)
    print("Error details:", str(error))