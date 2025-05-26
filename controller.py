import json
import os
import numpy as np
import asyncio
import aiohttp
import pandas as pd
import openai
from pinecone import Pinecone
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict


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
        self.client = OpenAI(api_key=self.openai_api_key)
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self.index = self.pc.Index("courses")

         # Load courses data
        with open(courses_data_path, 'r') as json_file:
            self.courses_data = json.load(json_file)

        self.community_colleges = {
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
            
            # Map by full course code (removing colon and any whitespace)
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
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return np.array(response.data[0].embedding)

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

        # Get course titles from matches
        course_titles = []
        for match in result['matches']:
            course_titles.append(match['id'])

        # Get detailed course information
        courses = []
        for title in course_titles:
            if title in self.courses_by_title:
                courses.append(self.courses_by_title[title])

        return courses

    async def get_distance(self, your_location, college_data):
        """
        Calculate the driving distance between two locations using the Mapbox Directions API.

        Args:
            your_location (tuple): A tuple containing the latitude and longitude of the user's location.
            college_data (tuple): A tuple containing the latitude and longitude of the community college location.

        Returns:
            float: The driving distance between the two locations in miles.
        """
        
        if your_location is None or college_data is None:
            return float('inf')

        # college_data is already a tuple of (latitude, longitude)
        community_college_location = college_data
        
        # Mapbox API URL for Directions
        base_url = "https://api.mapbox.com/directions/v5/mapbox/driving"
        
        # Coordinates as Longitude, Latitude format
        start = f"{your_location[1]},{your_location[0]}"  
        end = f"{community_college_location[1]},{community_college_location[0]}"  
        
        access_token = self.mapbox_access_token

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


    async def search_by_title(self, title, location):
        """
        Search for courses by title.

        Args:
            title (str): Title of the course to search for
            location (tuple): User's location as (latitude, longitude) tuple

        Returns:
            list: List of course objects that match the title
        """
        try:
            close_matches = self.search_courses(title, top_k = 5)
            matching_courses = []
            course_titles = []

            for match in close_matches:
                # Remove colon from course code for lookup
                course_code = match.get('courseString', '').replace(':', '')
                matching_course = self.courses_by_code.get(course_code)
                if matching_course is None:
                    continue
                course_info = await self.extract_course_data(matching_course, location)
                matching_courses.append(course_info)
                course_titles.append(match.get('title', ''))
            
            return matching_courses
        except Exception as e:
            print(f"Error in search_by_title: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise

    async def search_by_code(self, course_code, location=None):
        """
        Search for courses by code.

        Args:
            code (str): Course code to search for
            location (tuple, optional): User's location as (latitude, longitude) tuple

        Returns:
            list: List of course objects that match the code
        """
        matching_courses = []

        for full_code, course in self.courses_by_code.items():
            if full_code.endswith(course_code):
                course_info = await self.extract_course_data(course, location)
                matching_courses.append(course_info)

        return matching_courses
                

    def search_by_professor(self, professor_name: str) -> List[Dict]:
        """Search for courses taught by a specific professor."""
        # Convert to lowercase for case-insensitive search
        professor_name = professor_name.lower()
        
        # Find matching professors
        matching_professors = []
        for instructor in self.instructors_courses.keys():
            if professor_name in instructor.lower():
                matching_professors.append(instructor)

        # Get courses for matching professors
        results = []
        for professor in matching_professors:
            courses = self.instructors_courses[professor]
            course_list = []
            for course in courses:
                course_list.append({
                    'courseString': course['courseString'],
                    'title': course['title']
                })
            results.append({
                'professor': professor,
                'courses': course_list
            })

        return results

    async def extract_course_data(self, course, your_location):
        """
        Extract course data from a course object.

        Args:
           matching_courses (list): List of course objects to extract data from

        Returns:
            dict: Extracted course data that contains the course number, title, prerequisites, and instructors
        """
        try:
            course_string = course.get('courseString')
            course_title = course.get('title')
            preq = course.get('preReqNotes') or "No prerequisites"

            sections = course.get('sections', [])
            instructors_for_course = []

            # Loops through each section to extract the instructors
            for section in sections:
                instructor_for_section = section.get('instructors', [])

                if not instructor_for_section:
                    instructor_for_section = [{'name': 'UNKNOWN'}]

                if instructor_for_section not in instructors_for_course:
                    instructors_for_course.append(instructor_for_section)

            course_code = course_string.replace(':', '')

            # Only calculate equivalencies if location is provided
            course_equivalencies = []
       
            if your_location:
                course_equivalencies = await self.get_top_5_course_equivalencies_by_distance(course_code, your_location)

            course_data = {
                'title': course_title,
                'course_number': course_string,
                'instructors': instructors_for_course,
                'prerequisites': preq,
                'equivalencies': course_equivalencies,
            }

            return course_data
        except Exception as e:
            print(f"Error in extract_course_data: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise

    def get_course_instructors(self, course_code: str) -> List[str]:
        """Get all instructors for a specific course."""
        if course_code not in self.courses_by_code:
            return []

        course = self.courses_by_code[course_code]
        sections = course.get('sections', [])
        instructors_for_course = []

        for section in sections:
            instructor_for_section = section.get('instructors', [])
            if instructor_for_section not in instructors_for_course:
                instructors_for_course.append(instructor_for_section)

        return instructors_for_course

# Main function to test searching by title, code, and professor. 
async def main():

    # Initialize the course_search controller with the path to your course data JSON
    # course_search_controller = course_search(courses_data_path='data/rutgers_courses.json')
    # location = (40.525635,-74.4629)
    
    #Test search courses by title
    # title = "Introduction to Computer Science"
    # print("Searching by Title:", title)
    # matching_courses = await course_search_controller.search_by_title(title,location)
    # print(matching_courses)
    
    # Test search courses by code
    # code = "112"
    # print("Searching by Code:", code)
    # matching_courses = await course_search_controller.search_by_code(code)
    # print(matching_courses)

    # Test search  courses by professor
    # professor = "Centeno"
    # print("Searching by Professor:", professor)
    # professor_courses = course_search_controller.search_by_professor(professor)
    # print(professor_courses)
    pass
