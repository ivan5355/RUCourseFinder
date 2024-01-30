import json
import difflib
import os
from pprint import pprint
from openai import OpenAI
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='templates')

with open('rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

courses_by_title = {}
for course in courses_data:
    title = course.get('title').lower()
    courses_by_title[title] = course



os.environ["OPENAI_API_KEY"] = config.get("OPENAI_API_KEY")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


@app.route('/')
def search_page():
    return render_template('main.html')


@app.route('/search', methods=['POST'])
def search():
    data = request.json
    search_term = data.get('searchTerm')

    close_matches = difflib.get_close_matches(search_term.lower(),
                                              courses_by_title.keys(), n=5) #finds closest matches in coursetitle:courseobject dictionart

    matching_courses = []

    #loops through mactches  and check if the courses by_tit
    for match in close_matches:
        matching_course = courses_by_title.get(match)
        if matching_course:
            matching_courses.append(matching_course) #adds object to list that have a matching title

    if not matching_courses:
        return jsonify({'searchTerm': search_term, 'message': 'No search results found.'})

    results = []
    for course in matching_courses:
        course_title = course.get('title')
        sections = course.get('sections', [])

        instructors_for_course = []

        for section in sections:
            instructor_for_section = section.get('instructors', [])

            if instructor_for_section not in instructors_for_course:
                instructors_for_course.append(instructor_for_section)

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Tell me about the course {course_title} in 100 words. Make the description as descriptive as possible",
                }
            ],
            model="gpt-3.5-turbo",
        )

        chatgptdescription = chat_completion.choices[0].message.content

        results.append({
            'gptgenerated': chatgptdescription,
            'instructors': instructors_for_course,
            'title': course_title,
        })

    response_data = {'searchTerm': search_term,
                     'courses': results
                     }

    pprint(response_data)
    print(response_data['courses'][0]['gptgenerated'])
    return jsonify(response_data)


if __name__ == '__main__':
    app.run(debug=True)
