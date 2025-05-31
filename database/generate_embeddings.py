import os
import json
import numpy as np
from tqdm import tqdm
import dotenv
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai

# Load environment variables
dotenv.load_dotenv()

# Initialize Google Gemini client
google_api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=google_api_key)

# Initialize Pinecone client
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)

# Pinecone index details
index_name = "courses-gemini"
dimension = 768  # text-embedding-004 uses 768 dimensions
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

# Function to generate embeddings for a batch of texts using Google's text-embedding-004
def generate_batch_embeddings(texts):
    embeddings = []
    for text in texts:
        try:
            # Use Google's text-embedding-004 model
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"  # For storing documents
            )
            embeddings.append(np.array(result['embedding']))
        except Exception as e:
            print(f"Error generating embedding for text: {text[:50]}... Error: {e}")
            # Create a zero vector as fallback
            embeddings.append(np.zeros(dimension))
    return embeddings

# Prepare a list of course titles and their corresponding course objects
course_titles = [course.get('title', '') for course in courses_data]

batch_size = 50  # Smaller batch size for Google API rate limits

# Process in batches
for i in tqdm(range(0, len(course_titles), batch_size), desc="Processing courses"):
    batch_titles = course_titles[i:i+batch_size]
    batch_courses = courses_data[i:i+batch_size]

    # Generate embeddings for the batch (only the title)
    embeddings = generate_batch_embeddings(batch_titles)

    # Prepare vectors for upsert
    vectors_to_upsert = []
    for k in range(len(batch_titles)):
        course = batch_courses[k]
        course_id = course.get('courseString')
        embedding = embeddings[k].tolist()
        metadata = {
            'title': course.get('title', ''),
            'code': course.get('courseString', '')
        }
        vectors_to_upsert.append({
            'id': course_id,
            'values': embedding,
            'metadata': metadata
        })

    # Upsert batch into Pinecone
    index.upsert(vectors_to_upsert)

print(f"Expected number of titles: {len(course_titles)}")
# Check index stats
index_stats = index.describe_index_stats()
print(f"Total vectors in index '{index_name}': {index_stats['total_vector_count']}") 