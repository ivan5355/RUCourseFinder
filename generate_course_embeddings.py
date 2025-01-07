import os
import json
import openai
import numpy as np
from tqdm import tqdm
import dotenv
from pinecone import Pinecone

# Load environment variables (API keys, etc.)
dotenv.load_dotenv()

# Set your OpenAI API key and Pinecone API key
openai.api_key = os.getenv("OPENAI_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")  # Load Pinecone API key

# Initialize Pinecone using the correct API key
pc = Pinecone(api_key=pinecone_api_key)

# Define index name and dimension
index_name = "courses"  # The name of your index in Pinecone
dimension = 1536  # The embedding dimension for text-embedding-ada-002


# Access the Pinecone index
index = pc.Index(index_name)

# Load the Rutgers courses data from a JSON file
with open('rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

# Function to generate embeddings using OpenAI API
def generate_embeddings(text):
    response = openai.Embedding.create(
        model="text-embedding-ada-002",  # Choose your embedding model
        input=text
    )
    return np.array(response['data'][0]['embedding'])

# Process the courses and store embeddings in Pinecone
print("Processing courses...")

for course in tqdm(courses_data, total=len(courses_data), desc="Processing courses"):
    course_title = course.get('title')
    course_description = course.get('description', '')  # Optional description

    if course_title:
        # Generate embeddings for the course title
        embedding = generate_embeddings(course_title)
        vector = embedding.tolist()  # Convert the numpy array to list for Pinecone\

        # Upsert the vector into Pinecone (insert or update)
        index.upsert([(course_title, vector)])
    else:
        print(f"Warning: Course without title found: {course}")

