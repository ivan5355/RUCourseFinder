
import json

with open('data/rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)
    print(len( courses_data))