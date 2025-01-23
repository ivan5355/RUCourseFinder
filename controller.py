import json
import os
import numpy as np
import asyncio
import aiohttp
import pandas as pd
import openai
from pinecone import Pinecone
import re
import dotenv 
from dotenv import load_dotenv


class course_search:
    """
    Controller for managing Rutgers course data and search functionality.

    Handles course data processing, mapping, and advanced search capabilities 
    including vector search, course equivalencies, and distance calculations.

    Attributes:
        courses_data (list): Loaded course data from JSON file
        courses_by_title (dict): Mapping of course titles to course details
        courses_by_code (dict): Mapping of course codes to course details
        instructors_courses (dict): Mapping of instructors to their courses
    """

    def __init__(self, courses_data_path = 'data/rutgers_courses.json'):
        """
        Initialize the course_search controller with course data.

        Args:
            courses_data_path (str, optional): Path to courses JSON file. 
                Defaults to 'data/rutgers_courses.json'.
        """

        load_dotenv()

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.mapbox_access_token = os.getenv("MAPBOX_ACCESS_TOKEN")

         # Initialize OpenAI and Pinecone clients
        openai.api_key = self.openai_api_key
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self.index = self.pc.Index("courses")

         # Load courses data
        with open(courses_data_path, 'r') as json_file:
            self.courses_data = json.load(json_file)

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
            "Rowan College of South Jersey - Gloucester Campus": (39.7394, -75.0089),
            "Salem Community College": (39.6794, -75.4489),
            "Sussex County Community College": (41.0594, -74.7589),
            "UCNJ Union College of Union County, NJ": (40.6494, -74.3089),
            "Warren County Community College": (40.7594, -75.0089)
        }

         # Initialize course mappings
        self.courses_by_title = {}
        self.courses_by_code = {}
        self.courses_by_code_title = {}
        self.instructors_courses = {}

        self.build_course_mappings()

    def build_course_mappings(self):
        """
        Build internal mappings for courses, titles, and instructors.

        Creates efficient lookup dictionaries for:
        - Courses by title
        - Courses by code
        - Instructors and their courses
        """
        for course in self.courses_data:
            title = course.get('title', '').lower()
            course_string = course.get('courseString', '')
            # Map by title
            self.courses_by_title[title] = course
            
            # Map by full course code (removing colon)
            full_code = course_string.replace(':', '').strip()
            self.courses_by_code[full_code] = course
            
            # Map course code to title
            self.courses_by_code_title[full_code] = title

            sections = course.get('sections', [])
        
            for section in sections:
                instructors = section.get('instructors', [])
                
                # Handle multiple instructors per section
                for instructor in instructors:
                    instructor_name = instructor.get('name', '')  
                    if instructor_name not in self.instructors_courses:
                        self.instructors_courses[instructor_name] = []

                    # Store both title and course string
                    course_info = {'title': title, 'courseString': course_string}
                    if course_info not in self.instructors_courses[instructor_name]:
                        self.instructors_courses[instructor_name].append(course_info)


    def generate_embeddings(self, text):
        """
        Generate embeddings for a given text.

        Args:
            text (str): The text to generate embeddings for.

        Returns:
            numpy.ndarray: The generated embeddings.
        """
        response = openai.Embedding.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return np.array(response['data'][0]['embedding'])

    def search_courses(self, query, top_k):
        """
        Search for courses based on a given text user inputs

        Args:
            text (str): The text to search for.

        Returns:
            list: top 10 courses matching the search query.
        """
        # Generate the embedding for the search query
        query_embedding = self.generate_embeddings(query)

        # Perform the search in Pinecone
        result = self.index.query(
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

    your_location = None

    # Gets the distance between the user's location and the community college
    async def get_distance(your_location, community_college_location):
        """
        Calculate the driving distance between two locations using the Mapbox Directions API.

        Args:
            your_location (tuple): A tuple containing the latitude and longitude of the user's location.
            community_college_location (tuple): A tuple containing the latitude and longitude of the community college location.

        Returns:
            float: The driving distance between the two locations in miles.
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

    your_location = None

    async def get_top_5_course_equivalencies_by_distance(self, course_code, your_location):
        """
        Find top 5 course equivalencies sorted by distance from user's location.

        Args:
            course_code (str): Course code to find equivalencies for
            your_location (tuple): User's current location (latitude, longitude)

        Returns:
            list: Top 5 course equivalencies with distance information
        """
        equivalencies = pd.read_csv('data/community_to_college.csv')
        equivalencies = equivalencies[equivalencies['equivalency'] == course_code]

        if equivalencies.empty:
            return []

        distance_tasks = []
        for college in equivalencies['community_college']:
            distance_tasks.append(
                self.get_distance(your_location, self.community_colleges.get(college))
            )
        
        distances = await asyncio.gather(*distance_tasks)
        equivalencies['Distance'] = distances
        
        unique_colleges = set()
        top_5 = []
        
        for _, row in equivalencies.sort_values('Distance').iterrows():
            college = row['community_college']
            if college not in unique_colleges:
                unique_colleges.add(college)
                top_5.append(row.to_dict())
            
                if len(top_5) == 5:
                    break

        return top_5


    async def search_by_title(self, title):
        """
        Search for courses by title.

        Args:
            title (str): Title of the course to search for

        Returns:
            list: List of course objects that match the title
        """
        
        # Finds the top 10 closest matches based on the course_titles. Stored as list of strings
        close_matches = self.search_courses(title, top_k = 5)
        print(f"Close matches: {close_matches}")
        
        matching_courses = []
        course_titles = []

        # Loops through matches and adds course objects to matching_course that have a matching title
        for match in close_matches:

            matching_course = self.courses_by_title.get(match.lower())
            course_info = await self.extract_course_data(matching_course)
            matching_courses.append(course_info)
            course_titles.append(match)
          
           
        return matching_courses

    async def search_by_code(self, course_code):
        """
        Search for courses by code.

        Args:
            code (str): Course code to search for

        Returns:
            list: List of course objects that match the code
        """
        matching_courses = []

        # Search through the course:sections dictionary to get the sections for a course
        for full_code, course in self.courses_by_code.items():
            if full_code.endswith(course_code):
                course_info = await self.extract_course_data(course)
                matching_courses.append(course_info)

        return matching_courses
                
                

    def search_by_professor(self, professor):
        """
        Search for courses by professor.

        Args:
            professor (str): Name of the professor to search for

        Returns:
            list: List of course objects that match the professor
        """
        matching_professors = []

        # Search through the instructor:courses dictionary to get the courses taught by a professor
        for professor in self.instructors_courses.keys():
            if professor.lower() in professor.lower():
                matching_professors.append(professor)
        
        results = []

        # Store the professor and their course titles in a list of dictionaries 
        for professor in matching_professors:
            courses = self.instructors_courses[professor]
            results.append({
                'professor': professor,
                'courses': courses
            })
        
        return results

    async def extract_course_data(self, course):
        """
        Extract course data from a course object.

        Args:
           matching_courses (list): List of course objects to extract data from

        Returns:
            dict: Extracted course data that contains the course number, title, prerequisites, and instructors
        """

        course_string = course.get('courseString')
        course_title = course.get('title')
        preq = course.get('preReqNotes') or "No prerequisites"

        sections = course.get('sections', [])
        instructors_for_course = []
        print(course_title)
        print(course_string)

        # Loops through each section to extract the instructors
        for section in sections:
            print(section.get('instructors', []))
            instructor_for_section = section.get('instructors', [])

            if not instructor_for_section:
                instructor_for_section = [{'name': 'UNKNOWN'}]

            if instructor_for_section not in instructors_for_course:
                instructors_for_course.append(instructor_for_section)

        course_code = course_string.replace(':', '')

         # Only calculate equivalencies if location is provided
        course_equivalencies = []
        your_location = None
        if your_location:
            course_equivalencies = await self.get_top_5_course_equivalencies_by_distance(course_code, your_location)
        else:
            print("No location provided. Skipping course equivalencies.")

        course_data = {
            'title': course_title,
            'course_number': course_string,
            'instructors': instructors_for_course,
            'prerequisites': preq,
            'equivalencies': course_equivalencies,
        }

        return course_data

# Main function to test searching by title, code, and professor. 
async def main():

    # Initialize the course_search controller with the path to your course data JSON
    course_search_controller = course_search(courses_data_path='data/rutgers_courses.json')

    # Test search by title
    title = "Introduction to Computer Science"
    print("Searching by Title:", title)
    matching_courses = await course_search_controller.search_by_title(title)
    print(matching_courses)
    
    # Test search by code
    # code = "112"
    # print("Searching by Code:", code)
    # matching_courses = await course_search_controller.search_by_code(code)
    # print(matching_courses)

    # Test search by professor
    # professor = "Centeno"
    # print("Searching by Professor:", professor)
    # courses = course_search_controller.search_by_professor(professor)
    # for course in courses:
    #     print(f"Course Code: {course.get('courseString', '')}")
    #     print(f"Title: {course.get('title', '')}\n")

    
# Run the async main function
asyncio.run(main())

   