import os
import json
import numpy as np
from tqdm import tqdm
import dotenv
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

# Load environment variables
dotenv.load_dotenv()

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# Initialize Pinecone client
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)

# Pinecone index details
index_name = "courses"
dimension = 1536  
metric = "cosine"

# Check if the index exists
existing_indexes = []
for index in pc.list_indexes():
    existing_indexes.append(index.name)

if index_name not in existing_indexes:
    print(f"Index '{index_name}' does not exist. Creating index...")
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(
            cloud='aws', 
            region='us-east-1'  
        )
    )
    print(f"Index '{index_name}' created successfully!")

# Access the index
index = pc.Index(index_name)

# Load the Rutgers courses data from JSON file
with open('../data/rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

# Function to generate embeddings for a batch of texts
def generate_batch_embeddings(texts):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    embeddings = []
    for item in response.data:
        embeddings.append(np.array(item.embedding))
    return embeddings

titles = []
for course in courses_data:
    titles.append(course.get('title'))

batch_size = 100

# Process in batches
for i in tqdm(range(0, len(titles), batch_size), desc="Processing courses"):
    batch_titles = []
    for j in range(i, min(i + batch_size, len(titles))):
        batch_titles.append(titles[j])

    # Generate embeddings for the batch
    embeddings = generate_batch_embeddings(batch_titles)

    # Prepare vectors for upsert
    vectors_to_upsert = []
    for k in range(len(batch_titles)):
        title = batch_titles[k]
        embedding = embeddings[k].tolist()
        vectors_to_upsert.append((title, embedding))

    # Upsert batch into Pinecone
    index.upsert(vectors_to_upsert)

print(f"Expected number of titles: {len(titles)}")
# Check index stats
index_stats = index.describe_index_stats()
print(f"Total vectors in index '{index_name}': {index_stats['total_vector_count']}")




