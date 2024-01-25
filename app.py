import json
from pprint import pprint

from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='templates')

with open('rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

@app.route('/')
def search_page():
    return render_template('main.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    search_term = data.get('searchTerm')

    matching_courses = []
    for course in courses_data:
        if search_term.lower() in course.get('title', '').lower():
            matching_courses.append(course)

    if not matching_courses:
        response_data = {'searchTerm': search_term, 'message': 'No search results found.'}
    else:
        results = []
        for course in matching_courses:
            course_title = course.get('title')
            sections = course.get('sections', [])

            instructors_for_course = []

            for section in sections:
                section_number = section.get('section_number')
                instructor_for_section = section.get('instructors', [])

                if instructor_for_section not in  instructors_for_course:
                    instructors_for_course.append(instructor_for_section)


            results.append({
                'instructors': instructors_for_course,
                'title': course_title,

            })

        response_data = {'searchTerm': search_term,
                         'courses': results
                         }

    pprint(response_data)
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)
