import json
import difflib
import os
from typing import OrderedDict
from flask import Flask, g, render_template, request, jsonify
import asyncio
from pprint import pprint
import time
import aiohttp
import openai
import pandas as pd
import requests
from datetime import datetime
import googlemaps as gmaps


app = Flask(__name__, template_folder='templates')

with open('rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

courses_by_title = {}

your_location = None

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

#maps the titles of courses to object
for course in courses_data:
    title = course.get('title').lower()
    courses_by_title[title] = course

#maps the course code to object
courses_by_code = {}
for course in courses_data:
    course_code = course.get('courseString').replace(':', '')
    courses_by_code[course_code] = course


os.environ["OPENAI_API_KEY"] = config.get("OPENAI_API_KEY")
openai_client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

os.environ["GOOGLE_MAPS_API_KEY"] = config.get("GOOGLE_MAPS_API_KEY")
gmaps = gmaps.Client(key=os.environ.get("GOOGLE_MAPS_API_KEY"))


@app.route('/')
def search_page():
    return render_template('main.html')

#generates course description by calling chat-gpt api
async def get_tasks(course_titles, session):
    tasks = []

    for title in course_titles:
        prompt = f"Tell me about the course {title} in 100 words. Make the description as descriptive as possible"

        async with session:
            task_coroutine = openai_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="gpt-3.5-turbo",
            )
            tasks.append(task_coroutine)
    return tasks


async def get_course_descriptions(course_titles):
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = await get_tasks(course_titles, session)
        responses = await asyncio.gather(*tasks)

        course_descriptions = {}  # Dictionary to store course descriptions

        for course_title, response in zip(course_titles, responses):
            result_text = response.choices[0].message.content
            course_descriptions[course_title] = result_text

    end = time.time()
    print(end - start)

    return course_descriptions


@app.route('/save_location', methods=['POST'])
def save_location():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    global your_location
    your_location = (latitude, longitude)

    if your_location is not None:
        print(f"Received location: Latitude={latitude}, Longitude={longitude}")
    else:
        print("Failed to receive location")

    return jsonify({'status': 'success', 'latitude': latitude, 'longitude': longitude})



def get_distance(your_location, community_college_location):

    if your_location is None or community_college_location is None:
        return float('inf')
    
    directions = gmaps.directions(your_location, community_college_location, mode="driving", departure_time=datetime.now())
    distance_in_meters = directions[0]['legs'][0]['distance']['value']
    distance_in_miles = distance_in_meters * 0.000621371
    return distance_in_miles


def get_top_5_course_equivalencies_by_distance(course_code):
    equivalencies = pd.read_csv('community_to_college.csv')
    equivalencies = equivalencies[equivalencies['equivalency'] == course_code]
    equivalencies['Distance'] = equivalencies['community_college'].apply(lambda x: get_distance(your_location, community_colleges.get(x)))
    equivalencies['Distance'] = equivalencies['Distance'].apply(lambda x: f'{x:.2f} miles')
    top_5 = equivalencies.sort_values('Distance').head(5)
    return top_5
 


@app.route('/search_by_title', methods=['POST'])
def search_by_title():

    data = request.json
    search_term = data.get('searchTerm')

    # finds the 5 closest matches based on the course_titles
    close_matches = difflib.get_close_matches(search_term.lower(), courses_by_title.keys(), n=10)

    matching_courses = []
    course_titles = []

    # loops through matches and adds object to matching_course that have a matching title
    for match in close_matches:

        matching_course = courses_by_title.get(match)
        matching_courses.append(matching_course)
        course_titles.append(match)

    if not matching_courses:
        return jsonify({'searchTerm': search_term, 'message': 'No search results found.'})

    results = []

    course_descriptions = asyncio.run(get_course_descriptions(course_titles))

    #loops through matching_courses to extract the coursecode, coursetitle, and instructors
    for course in matching_courses:

        course_string = course.get("courseString")
        course_title = course.get('title')

        sections = course.get('sections', [])

        instructors_for_course = []

        #loops through each section to extract the instructors
        for section in sections:

            instructor_for_section = section.get('instructors', [])

            if instructor_for_section not in instructors_for_course:
                instructors_for_course.append(instructor_for_section)


        chatgpt_description = get_course_descriptions(course_title)

        course_code = course_string.replace(':', '')
        course_equivalencies = get_top_5_course_equivalencies_by_distance(course_code)
        course_equivalencies = course_equivalencies.to_dict(orient='records')
        print(course_equivalencies)

        if not course_equivalencies:
            course_equivalencies = "No equivalencies found."
     

        results.append(OrderedDict([
            ('title', course_title),
            ('course_number', course_string),
            ('instructors', instructors_for_course),
            ('gpt_description', chatgpt_description),
            ('equivalencies', course_equivalencies),   
        ]))

    response_data = {'searchTerm': search_term,
                     'courses': results
                     }

    return jsonify(response_data)


def get_course_description(course_title):
    chat_completion = openai.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Tell me about the course " + course_title + " in 100 words. Make the description as descriptive as possible",
        }
    ],
    model="gpt-3.5-turbo",
    )
    return chat_completion.choices[0].message.content



@app.route('/search_by_code', methods=['POST'])
def get_course_by_code():
       
       data = request.json
       search_term = data.get('searchTerm')

       course = courses_by_code.get(search_term)
       if course is None:
            return jsonify({'error': 'Course not found'}), 404
       
       course_string = course.get("courseString")
       course_title = course.get('title')
       sections = course.get('sections', [])
       chatgpt_description = get_course_description(course_title)
       instructors_for_course = []

        #loops through each section to extract the instructors
       for section in sections:

          instructor_for_section = section.get('instructors', [])

          if instructor_for_section not in instructors_for_course:
             instructors_for_course.append(instructor_for_section)

       results = []


       course_code = course_string.replace(':', '')
       course_equivalencies = get_top_5_course_equivalencies_by_distance(course_code)
       course_equivalencies = course_equivalencies.to_dict(orient='records')
       
       results.append(OrderedDict([
            ('title', course_title),
            ('course_number', course_string),
            ('instructors', instructors_for_course),
            ('gpt_description', chatgpt_description),
            ('equivalencies', course_equivalencies),   
        ]))
       

       response_data = {'searchTerm': course_code,
                       'courses': results
                       }

       return jsonify(response_data)


#print(get_course_by_code('01640152'))
    
    

if __name__ == '__main__':
    app.run(debug=True)
