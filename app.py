import json
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
        titles = [course.get('title') for course in matching_courses]
        instructors = [course.get('instructors', []) for course in matching_courses]
        response_data = {'searchTerm': search_term,
                         'results': matching_courses,
                         'titles': titles,
                         'insturctors' : instructors
                         }

    print("Response Data:", response_data)

    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)
