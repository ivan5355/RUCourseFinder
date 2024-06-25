import json
import difflib
import os
from pprint import pprint
from typing import OrderedDict
from dotenv import load_dotenv
from quart import Quart, render_template, request, jsonify
import asyncio
import time
import aiohttp
import pandas as pd
import googlemaps as gmaps
from datetime import datetime
from openai import AsyncOpenAI
from async_googlemaps import AsyncClient
from hypercorn.config import Config
from hypercorn.asyncio import serve

app = Quart(__name__, template_folder='templates')

with open('rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)


courses_by_title = {}

course_cache = {}

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

# Maps the titles of courses to objects
for course in courses_data:
    title = course.get('title').lower()
    courses_by_title[title] = course

# Maps the course code to objects
courses_by_code = {}
for course in courses_data:
    course_code = course.get('courseString').replace(':', '')
    courses_by_code[course_code] = course

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


os.environ["GOOGLE_MAPS_API_KEY"] = config.get("GOOGLE_MAPS_API_KEY")

your_location = None

@app.route('/')
async def search_page():
    return await render_template('main.html')

#gets the course descriptions for the courses 
async def get_tasks(course_titles, session):
    tasks = []
    for title in course_titles:
        if title.lower() in course_cache:
            continue  
        prompt = f"Tell me about the course {title} in 100 words. Make the description as descriptive as possible"
        task_coroutine = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        tasks.append((title, task_coroutine))
        print(f"Added task for {title}")
    return tasks

#Waits until the course descriptions are received and then returns the course descriptions at the same time
async def get_course_descriptions(course_titles):
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = await get_tasks(course_titles, session)
        
        course_descriptions = {}  # Dictionary to store course descriptions

        # First, add all cached descriptions
        for course_title in course_titles:
            if course_title.lower() in course_cache:
                course_descriptions[course_title] = course_cache[course_title.lower()]

        # Gather all non-cached tasks
        non_cached_tasks = [task for title, task in tasks if title.lower() not in course_cache]
        responses = await asyncio.gather(*non_cached_tasks)

        # Process responses and update cache
        for (title, _), response in zip(tasks, responses):
            if title.lower() not in course_cache:
                result_text = response.choices[0].message.content
                course_descriptions[title] = result_text
                course_cache[title.lower()] = result_text
                print(f"Finished task for course: {title}")

    write_cache_to_file(course_cache, 'course_cache.json')
    end = time.time()
    print(end - start)
    return course_descriptions

#Writes the cache to a file
def write_cache_to_file(cache, filename):
    with open(filename, 'w') as json_file:
        json.dump(cache, json_file, indent=4)

#Reads the cache from a file
@app.route('/save_location', methods=['POST'])
async def save_location():
    data = await request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    global your_location
    your_location = (latitude, longitude)

    if your_location is not None:
        print(f"Received location: Latitude={latitude}, Longitude={longitude}")
    else:
        print("Failed to receive location")

    return jsonify({'status': 'success', 'latitude': latitude, 'longitude': longitude})

#Gets the distance between the user's location and the community college
async def get_distance(your_location, community_college_location):

    if your_location is None or community_college_location is None:
        return float('inf')
    async with aiohttp.ClientSession() as session:
        gmaps_client = AsyncClient(key=os.environ.get("GOOGLE_MAPS_API_KEY"), aiohttp_session=session)
        directions = await gmaps_client.directions(your_location, community_college_location, mode="driving", departure_time=datetime.now())
    
    distance_in_meters = directions[0]['legs'][0]['distance']['value']
    distance_in_miles = distance_in_meters * 0.000621371
    return distance_in_miles

#Gets the top 5 course equivalencies by distance
async def get_top_5_course_equivalencies_by_distance(course_code):
    equivalencies = pd.read_csv('community_to_college.csv')
    equivalencies = equivalencies[equivalencies['equivalency'] == course_code]
    
    if equivalencies.empty:
        return []
    
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

    return top_5

#searches for the course by title
@app.route('/search_by_title', methods=['POST'])
async def search():
    data = await request.json
    search_term = data.get('searchTerm')

    # Finds the 5 closest matches based on the course_titles
    close_matches = difflib.get_close_matches(search_term.lower(), courses_by_title.keys(), n=10)
    matching_courses = []
    course_titles = []

    # Loops through matches and adds objects to matching_course that have a matching title
    for match in close_matches:
        matching_course = courses_by_title.get(match)
        matching_courses.append(matching_course)
        course_titles.append(match)
    if not matching_courses:
        return jsonify({'searchTerm': search_term, 'message': 'No search results found.'})
    
    results = []
    course_descriptions = await get_course_descriptions(course_titles)

    # Loops through matching_courses to extract the course code, course title, and instructors
    for course in matching_courses:
        course_string = course.get("courseString")
        course_title = course.get('title')
        sections = course.get('sections', [])
        instructors_for_course = []

        # Loops through each section to extract the instructors
        for section in sections:
            instructor_for_section = section.get('instructors', [])
            if instructor_for_section not in instructors_for_course:
                instructors_for_course.append(instructor_for_section)

        chatgpt_description = course_descriptions.get(course_title.lower())
        print(course['title'], instructors_for_course)

        course_code = course_string.replace(':', '')
        course_equivalencies = await get_top_5_course_equivalencies_by_distance(course_code) 
        pprint(course_equivalencies)

    
        results.append({
            'gpt_description': chatgpt_description,
            'instructors': instructors_for_course,
            'title': course_title,
            'equivalencies': course_equivalencies,
            'course_number': course_string
        })

    response_data = {
        'searchTerm': search_term,
        'courses': results
    }
    return jsonify(response_data)

#Gets the course description
async def get_course_description(course_title):
        prompt = f"Tell me about the course {title} in 100 words. Make the description as descriptive as possible"
        description = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        return description.choices[0].message.content

#searches for the course by code
@app.route('/search_by_code', methods=['POST'])
async def get_course_by_code():
    data = await request.json
    search_term = data.get('searchTerm')

    course = courses_by_code.get(search_term)
    if course is None:
        return jsonify({'error': 'Course not found'}), 404
    
    course_string = course.get("courseString")
    course_title = course.get('title')
    sections = course.get('sections', [])
    chatgpt_description = await get_course_description(course_title)
    instructors_for_course = []

    # Loops through each section to extract the instructors
    for section in sections:
        instructor_for_section = section.get('instructors', [])
        if instructor_for_section not in instructors_for_course:
            instructors_for_course.append(instructor_for_section)
    
    print(instructors_for_course)

    results = []

    course_code = course_string.replace(':', '')
    # course_equivalencies = get_top_5_course_equivalencies_by_distance(course_code)
    # course_equivalencies = course_equivalencies.to_dict(orient='records')
    # print(course_equivalencies)
    
    results.append(OrderedDict([
        ('title', course_title),
        ('course_number', course_string),
        ('instructors', instructors_for_course),
        ('gpt_description', chatgpt_description)  
    ]))
    
    response_data = {
        'searchTerm': course_code,
        'courses': results
    }

    return jsonify(response_data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    asyncio.run(serve(app, config))

# if __name__ == "__main__":
#     app.run(port=5000)
