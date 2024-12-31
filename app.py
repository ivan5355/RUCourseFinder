import json
import difflib
import os
import numpy as np
from quart import Quart, render_template, request, jsonify
import asyncio
import aiohttp
import pandas as pd
import openai
from pinecone import Pinecone

app = Quart(__name__, template_folder='templates')

# Loads the Rutgers courses from the JSON file
with open('rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

openai.api_key = os.getenv("OPENAI_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")

# Initialize Pinecone client
pc = Pinecone(api_key=pinecone_api_key)

index_name = "courses"

# Connect to the Pinecone index
index = pc.Index(index_name)

community_colleges = {
    "Rowan College of South Jersey - Cumberland Campus": (39.4794, -75.0289),
    "Atlantic Cape Community College": (39.4572, -74.7229),
    "Bergen Community College": (40.9367, -74.0739),
    "Brookdale Community College": (40.3294, -74.1089),
    "Camden County College": (39.8008, -75.0475),
    "County College of Morris": (40.8484, -74.5898),
    "Essex County College": (40.7484, -74.1724),
    "Hudson County Community College": (40.7228, -74.0543),
    "Mercer County Community College": (40.3094, -74.6689),
    "Middlesex College": (40.5194, -74.3889),
    "Ocean County College": (39.9794, -74.1789),
    "Passaic County Community College": (40.9167, -74.1667),
    "Raritan Valley Community College": (40.5794, -74.6889),
    "Rowan College at Burlington County": (39.9594, -74.9189),
    "Rowan College of South Jersey - Cumberland Campus": (39.4794, -75.0289),
    "Rowan College of South Jersey - Gloucester Campus": (39.7394, -75.0089),
    "Salem Community College": (39.6794, -75.4489),
    "Sussex County Community College": (41.0594, -74.7589),
    "UCNJ Union College of Union County, NJ": (40.6494, -74.3089),
    "Warren County Community College": (40.7594, -75.0089)
}

courses_by_title = {}
courses_by_code = {} 

# Maps the titles and codes of courses to course objects
for course in courses_data:
    title = course.get('title').lower()
    course_string = course.get('courseString', '')
    
    # Map by title
    courses_by_title[title] = course
    
    # Map by full course code (removing colon)
    full_code = course_string.replace(':', '').strip()
    courses_by_code[full_code] = course

instructors_courses = {}

#Maps the instructor to their courses
for course in courses_data:

    title = course.get('title')
    course_string = course.get('courseString')
    
    sections = course.get('sections', [])

    for section in sections:
        instructors = section.get('instructors', [])
        
        # Handle multiple instructors per section
        for instructor in instructors:

            instructor_name = instructor.get('name', '')  
            if instructor_name not in instructors_courses:
                instructors_courses[instructor_name] = []

            # Store both title and course string
            course_info = {'title': title, 'courseString': course_string}
            if course_info not in instructors_courses[instructor_name]:
                instructors_courses[instructor_name].append(course_info)

your_location = None

@app.route('/')
async def search_page():
    return await render_template('main.html')

def generate_embeddings(text):
    response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=text
    )
    return np.array(response['data'][0]['embedding'])


# Gets the course descriptions for the courses
@app.route('/save_location', methods=['POST'])
async def save_location():
    data = await request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    global your_location
    your_location = (latitude, longitude)
    print(f"Received location: Latitude={latitude}, Longitude={longitude}")

    if your_location is not None:
        print(f"Received location: Latitude={latitude}, Longitude={longitude}")
    else:
        print("Failed to receive location")

    return jsonify({'status': 'success', 'latitude': latitude, 'longitude': longitude})

# Gets the distance between the user's location and the community college
async def get_distance(your_location, community_college_location):
    """
    Calculate the driving distance between two locations using the Mapbox Directions API.
    """
    if your_location is None or community_college_location is None:
        return float('inf')

    # Mapbox API URL for Directions
    base_url = "https://api.mapbox.com/directions/v5/mapbox/driving"
    
    # Coordinates as Longitude, Latitude format
    start = f"{your_location[1]},{your_location[0]}"  
    end = f"{community_college_location[1]},{community_college_location[0]}"  
    
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")

    url = f"{base_url}/{start};{end}?access_token={access_token}&geometries=geojson&overview=simplified&annotations=distance"
    
    # Asynchronously make the request
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:

                data = await response.json()

                # Get the distance in meters
                distance_in_meters = data['routes'][0]['legs'][0]['distance']

                # Convert meters to miles (1 mile = 1609.34 meters)
                distance_in_miles = round((distance_in_meters / 1609.34), 2)

                return distance_in_miles
            
        
# Gets the top 5 course equivalencies by distance
async def get_top_5_course_equivalencies_by_distance(course_code):

    equivalencies = pd.read_csv('community_to_college.csv')

    # Filters the equivalencies by the course code
    equivalencies = equivalencies[equivalencies['equivalency'] == course_code]

    if equivalencies.empty:
        print(f"No course equivalencies found for {course_code}")
        return []
    else:
        print(f"Found course equivalencies for {course_code}")

    # Gets the distance between the user's location and the community college and awaits the results
    distance_tasks = [get_distance(your_location, community_colleges.get(college)) 
                      for college in equivalencies['community_college']]
    distances = await asyncio.gather(*distance_tasks)
    
    equivalencies['Distance'] = distances
    unique_colleges = set()
    top_5 = []
    
    # adds only the unique top 5 colleges to the top_5 list
    for _, row in equivalencies.sort_values('Distance').iterrows():
        college = row['community_college']
        if college not in unique_colleges:
            unique_colleges.add(college)
            top_5.append(row.to_dict())
        
            if len(top_5) == 5:
                break

    if not top_5:
        print("No course equivalencies found.")

    return top_5


# Function to search for the most similar courses to a given query
def search_courses(query, top_k):

    # Generate the embedding for the search query
    query_embedding = generate_embeddings(query)

    # Perform the search in Pinecone
    result = index.query(
        vector=query_embedding.tolist(),  
        top_k=top_k,
        include_metadata=True
    )

    if not result['matches']:
        print(f"No matches found for query: {query}")
    else:
        print(f"Found {len(result['matches'])} matches for query: {query}")
        for match in result['matches']:
            print(f"Course ID: {match['id']}, Score: {match['score']}")

    # Extract the course titles from the search results
    course_titles = [match['id'] for match in result['matches']]

    return course_titles

# Searches for the course by title
@app.route('/search_by_title', methods=['POST'])
async def search():
    data = await request.json
    search_term = data.get('searchTerm')

    # Finds the top 10 closest matches based on the course_titles. Stored as list of strings
    close_matches = search_courses(search_term, top_k=10)
    print(f"Close matches: {close_matches}")
       
    matching_courses = []
    course_titles = []

    # Loops through matches and adds course objects to matching_course that have a matching title
    for match in close_matches:

        matching_course = courses_by_title.get(match.lower())
      
        matching_courses.append(matching_course)
        course_titles.append(match)

    if not matching_courses:
        return jsonify({'searchTerm': search_term, 'message': 'No search results found.'})
    
    results = []

    # Loops through matching_courses to extract the course code, course title, and instructors
    for course in matching_courses:
        course_string = course.get("courseString")
        course_title = course.get('title')
        preq = course.get('preReqNotes')

        if preq is None:
            preq = "No prerequisites"

        sections = course.get('sections', [])
        instructors_for_course = []

        # Loops through each section to extract the instructors
        for section in sections:
            instructor_for_section = section.get('instructors', [])
            if instructor_for_section not in instructors_for_course:
                instructors_for_course.append(instructor_for_section)

        print(course['title'], instructors_for_course)

        course_code = course_string.replace(':', '')

        # Gets the top 5 course equivalencies by distance
        course_equivalencies = await get_top_5_course_equivalencies_by_distance(course_code) 

        results.append({
            'instructors': instructors_for_course,
            'title': course_title,
            'prerequisites': preq,
            'equivalencies': course_equivalencies,
            'course_number': course_string
        })

    response_data = {
        'searchTerm': search_term,
        'courses': results
    }
    return jsonify(response_data)

#Search by professor
@app.route('/search_by_professor', methods=['POST'])
async def search_by_professor():

    data = await request.json
    search_term = data.get('searchTerm', '').lower()
    
    matching_professors = []

    # Search through the instructor:courses dictionary to get the courses taught by a professor
    for professor in instructors_courses.keys():
        if search_term in professor.lower():
            matching_professors.append(professor)
    
    results = []

    # Store the professor and their courses in a list of dictionaries 
    for professor in matching_professors:
        courses = instructors_courses[professor]
        results.append({
            'professor': professor,
            'courses': courses
        })
    
    if not results:
        return jsonify({'searchTerm': search_term, 'message': 'No professors found.'})
    
    return jsonify({
        'searchTerm': search_term,
        'results': results
    })

@app.route('/search_by_code', methods=['POST'])
async def search_by_code():
    data = await request.json
    search_term = data.get('searchTerm', '')
    
    # Ensure search term is numeric
    if not search_term.isdigit():
        return jsonify({'searchTerm': search_term, 'message': 'Please enter only digits.'})
    
    matching_courses = []
    
    # Search for courses where the code ends with the search term
    for full_code, course in courses_by_code.items():

        if full_code.endswith(search_term):

            course_string = course.get('courseString')
            course_code = course_string.replace(':', '')
            preq = course.get('preReqNotes') or "No prerequisites"
            
            sections = course.get('sections', [])
            instructors_for_course = []
            
            # Get instructors for the course
            for section in sections:
                instructor_for_section = section.get('instructors', [])
                if instructor_for_section not in instructors_for_course:
                    instructors_for_course.append(instructor_for_section)
            
            # Get course equivalencies
            course_equivalencies = await get_top_5_course_equivalencies_by_distance(course_code)
            
            matching_courses.append({
                'instructors': instructors_for_course,
                'title': course.get('title'),
                'prerequisites': preq,
                'equivalencies': course_equivalencies,
                'course_number': course_string
            })
    
    if not matching_courses:
        return jsonify({'searchTerm': search_term, 'message': 'No courses found with that code.'})
    
    return jsonify({
        'searchTerm': search_term,
        'courses': matching_courses
    })

if __name__ == '__main__':
    app.run(debug=True)
