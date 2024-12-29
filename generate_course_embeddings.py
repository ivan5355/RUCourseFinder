import json
import os
import openai
import numpy as np  # Import numpy to handle the embedding response
import csv
from tqdm import tqdm  # Optional: For progress bar visualization
import dotenv

dotenv.load_dotenv()

# Load environment variables from .env file
openai.api_key = os.getenv("OPENAI_API_KEY")

# Loads the Rutgers courses from the JSON file
with open('rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

def generate_embeddings(text):
    response = openai.Embedding.create(
        model="text-embedding-ada-002",  # You can choose another model here
        input=text
    )
    return np.array(response['data'][0]['embedding'])

# Create a dictionary to store course embeddings
course_embeddings = {}

# Track progress using tqdm (progress bar)
with open('course_embeddings.csv', mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['course_title', 'embedding'])
    
    # Loop through courses with progress tracking
    for i, course in tqdm(enumerate(courses_data), total=len(courses_data), desc="Processing courses"):
        course_title = course.get('title')
        
        if course_title:  # Ensure the course has a title
            embedding = generate_embeddings(course_title)
            course_embeddings[course_title.lower()] = embedding
            writer.writerow([course_title, embedding.tolist()])
        else:
            print(f"Warning: Course without title found: {course}")
