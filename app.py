import json
import difflib
import os
from pprint import pprint
from openai import OpenAI
from flask import Flask, render_template, request, jsonify
import asyncio
from pprint import pprint
import time
import aiohttp
import openai


app = Flask(__name__, template_folder='templates')

with open('rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

courses_by_title = {}

#maps the titles of courses to object
for course in courses_data:

    title = course.get('title').lower()
    courses_by_title[title] = course

os.environ["OPENAI_API_KEY"] = config.get("OPENAI_API_KEY")
openai_client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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


@app.route('/search', methods=['POST'])
def search():

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


        chatgpt_description = course_descriptions.get(course_title.lower())

        results.append({
            'gpt_description': chatgpt_description,
            'instructors': instructors_for_course,
            'title': course_title,
            'course_number': course_string,
        })

    response_data = {'searchTerm': search_term,
                     'courses': results
                     }
    pprint(response_data)



    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)
