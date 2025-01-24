import os
import json
import openai
import numpy as np
from tqdm import tqdm
import dotenv
from pinecone import Pinecone

dotenv.load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY") 

# Initialize Pinecone using the correct API key
pc = Pinecone(api_key=pinecone_api_key)

# Name of the index
index_name = "courses"  

# The embedding dimension for text-embedding-ada-002
dimension = 1536  

# Access the Pinecone index
index = pc.Index(index_name)

# Load the Rutgers courses data from a JSON file
with open('data/rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

# Function to generate embeddings using OpenAI API
def generate_embeddings(text):
    response = openai.Embedding.create(
        model="text-embedding-ada-002",  
        input=text
    )
    return np.array(response['data'][0]['embedding'])

# Process the courses and store embeddings in Pinecone
print("Processing courses...")

for course in tqdm(courses_data, total=len(courses_data), desc="Processing courses"):
    course_title = course.get('title')

    if course_title:

        # Generate embeddings for the course title
        embedding = generate_embeddings(course_title)
        vector = embedding.tolist()  

        # Upsert the vector into Pinecone (insert or update)
        index.upsert([(course_title, vector)])
    else:
        print(f"Warning: Course without title found: {course}")

