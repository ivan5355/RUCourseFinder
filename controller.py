import json
import os
import numpy as np
import asyncio
import aiohttp
import pandas as pd
import re
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import google.generativeai as genai
from typing import List, Dict
import difflib
import math

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

        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.mapbox_access_token = os.getenv("MAPBOX_ACCESS_TOKEN")

        # Initialize Google Gemini client for embeddings
        genai.configure(api_key=self.google_api_key)
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self.index = self.pc.Index("courses-gemini")  # Changed to use Gemini embeddings index
        self.distances_cache = {}

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

    # remove em tags from text
    def remove_em_tags(self, text):
        """Remove <em> and </em> tags from text.
        
        Args:
            text (str): The text to be cleaned.
            
        Returns:
            str: The text with HTML em tags removed.
        """
        if not text:
            return text
        return re.sub(r'</?em>', '', text)

    # build course mappings
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

    # format instructor name
    def _format_instructor_name(self, name) -> str:
        """Formats instructor names into a more readable 'Firstname Lastname' format.
        
        Handles 'LASTNAME, FIRSTNAME' and 'LASTNAME' formats, and returns 'TBA' for unknown instructors.

        Args:
            name (str): The instructor's name as a string.

        Returns:
            str: The formatted name.
        """
        if not name or name == 'UNKNOWN':
            return 'TBA'
        
        # Handle "LASTNAME, FIRSTNAME" format
        if ',' in name:
            parts = []
            for p in name.split(','):
                parts.append(p.strip())

            if len(parts) == 2:
                # Title-case both parts and join as "Firstname Lastname"
                return f"{parts[1].title()} {parts[0].title()}"
        
        # Handle "LASTNAME" format (or any other format) by just title-casing it
        return name.title()

    def generate_embeddings(self, text):
        """
        Generate embeddings for a given text using Google's text-embedding-004.

        Args:
            text (str): The text to generate embeddings for.

        Returns:
            numpy.ndarray: The generated embeddings.
        """
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_query"  # For search queries
            )
            return np.array(result['embedding'])
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Fallback to zeros if embedding fails
            return np.zeros(768)  # text-embedding-004 has 768 dimensions

    # search courses by title
    def search_courses(self, query, top_k):
        """
        Search for courses based on a given text user inputs

        Args:
            query (str): The text to search for.
            top_k (int): The number of top results to return.

        Returns:
            list: A list of course objects matching the search query.
        """
        try:

            # Generate the embedding for the search query
            query_embedding = self.generate_embeddings(query)

            # Perform the search in Pinecone
            result = self.index.query(
                vector=query_embedding.tolist(),  
                top_k=top_k,
                include_metadata=True
            )

            if not result['matches']:
                return []

            # Get course codes from matches (Pinecone returns course codes as IDs)
            course_codes = []

            for match in result['matches']:
                course_code = match['id']  # This is actually a course code like "01:198:111"

                # Remove colon for lookup in courses_by_code
                clean_code = course_code.replace(':', '')
                course_codes.append(clean_code)

            # Get detailed course information using course codes
            courses = []
            for code in course_codes:
                if code in self.courses_by_code:
                    courses.append(self.courses_by_code[code])

            return courses
        
        except Exception as e:
            print(f"Error in search_courses: {str(e)}")
            return []

    # get distance between two locations
    async def get_distance(self, your_location, college_data):
        """
        Calculate the driving distance between two locations using the Mapbox Directions API.

        Args:
            your_location (tuple): A tuple containing the latitude and longitude of the user's location.
            college_data (tuple): A tuple containing the latitude and longitude of the community college location.

        Returns:
            float: The driving distance between the two locations in miles.
        """
        
        # If we are missing coordinates, return None so it can be serialized safely
        if your_location is None or college_data is None:
            return None

        community_college_location = college_data
        
        # Mapbox API URL for Directions
        base_url = "https://api.mapbox.com/directions/v5/mapbox/driving"
        
        # Coordinates as Longitude, Latitude format
        start = f"{your_location[1]},{your_location[0]}"  
        end = f"{community_college_location[1]},{community_college_location[0]}"  
        
        access_token = self.mapbox_access_token

        # Mapbox API URL for Directions
        url = f"{base_url}/{start};{end}?access_token={access_token}&geometries=geojson&overview=simplified&annotations=distance"
        
        # Asynchronously make the request
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:

                # Get the data from the response
                data = await response.json()

                # Get the distance in meters
                distance_in_meters = data['routes'][0]['legs'][0]['distance']

                # Convert meters to miles (1 mile = 1609.34 meters)
                distance_in_miles = round((distance_in_meters / 1609.34), 2)

                return distance_in_miles

     #precompute distances to all community colleges
    async def get_all_college_distances(self, your_location):
        """
        Asynchronously calculates the driving distance from a given location to all community colleges.

        This method leverages asyncio to perform multiple distance calculations concurrently,
        improving performance by reducing total wait time for API responses.

        Args:
            your_location (tuple): A tuple containing the latitude and longitude of the user's location.

        Returns:
            dict: A dictionary mapping community college names to their calculated driving distances in miles.
                  Returns an empty dictionary if the user's location is not provided.
        """
        if not your_location:
            return {}

        # Check cache for pre-computed distances
        if your_location in self.distances_cache:
            return self.distances_cache[your_location]

        colleges = self.community_colleges.keys()
        
        # Create a list of tasks for getting distances
        tasks = [self.get_distance(your_location, self.community_colleges[college]) for college in colleges]
        
        # Run all tasks concurrently
        distances = await asyncio.gather(*tasks)
        
        # Create a dictionary mapping college names to distances
        college_distances = dict(zip(colleges, distances))
        
        # Cache the results for future requests
        self.distances_cache[your_location] = college_distances

        return college_distances

    # get top 5 course equivalencies by distance
    async def get_top_5_course_equivalencies_by_distance(self, course_code, college_distances):
        """
        Find course equivalencies sorted by distance when available.
        If no location is available, surface all unique equivalencies without distance sorting.

        Args:
            course_code (str): Course code to find equivalencies for
            college_distances (dict): Precomputed distances to community colleges. Can be None/empty if no location.

        Returns:
            list: Course equivalencies with distance information (or without if location unavailable)
        """
        equivalencies = pd.read_csv('data/community_to_college.csv')
        equivalencies = equivalencies[equivalencies['equivalency'] == course_code]

        if equivalencies.empty:
            return []

        # If we have distance information, use it for sorting
        if college_distances:
            # Use precomputed distances to save computation time
            distances = []
            for college in equivalencies['community_college']:
                dist = college_distances.get(college)
                # Replace infinite or missing distances with None so they serialize to null in JSON
                if dist is None or (isinstance(dist, (int, float)) and math.isinf(dist)):
                    distances.append(None)
                else:
                    distances.append(dist)
    
            equivalencies['Distance'] = distances
            
            unique_colleges = set()
            top_5 = []
            
            #Get top 5 unique colleges by distance
            for _, row in equivalencies.sort_values('Distance').iterrows():
                college = row['community_college']
                if college not in unique_colleges:
                    unique_colleges.add(college)

                    row_data = row.to_dict()
                    # Convert pandas NaN to None for JSON safety
                    if pd.isna(row_data.get('Distance')):
                        row_data['Distance'] = None

                    top_5.append(row_data)
                    if len(top_5) == 5:
                        break
        else:
            # No location available - return all unique equivalencies without distance sorting
            equivalencies['Distance'] = None
            unique_colleges = set()
            all_equivalencies = []

            for _, row in equivalencies.sort_values('community_college').iterrows():
                college = row['community_college']
                if college not in unique_colleges:
                    unique_colleges.add(college)
                    row_data = row.to_dict()
                    row_data['Distance'] = None
                    all_equivalencies.append(row_data)

            return all_equivalencies

        return top_5

    async def search_by_title(self, title, college_distances):
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

                print(matching_course)
                if matching_course is None:
                    continue
              
                course_info = await self.extract_course_data(matching_course, college_distances)
                matching_courses.append(course_info)
                course_titles.append(match.get('title', ''))
            
            return matching_courses
            
        except Exception as e:
            print(f"Error in search_by_title: {str(e)}")
            raise

    # search by course code
    async def search_by_code(self, course_code, college_distances):
        """
        Search for courses by code.

        Args:
            course_code (str): Course code to search for.
            location (tuple, optional): User's location as (latitude, longitude) tuple.

        Returns:
            list: List of course objects that match the code.
        """
        matching_courses = []

        for full_code, course in self.courses_by_code.items():
            if full_code.endswith(course_code):
                course_info = await self.extract_course_data(course, college_distances)
                matching_courses.append(course_info)
        return matching_courses

    async def search_by_professor(self, professor_name):
        """Search for courses taught by a specific professor with suggestions.
        
        If an exact match is found, it returns the professor's courses. 
        Otherwise, it provides a list of suggestions for similar names.
        
        Args:
            professor_name (str): The name of the professor to search for.
            
        Returns:
            list: A list of dictionaries, either containing professor data or suggestions.
        """
        search_term = professor_name.lower().strip()
        
        if not search_term:
            return []

        # Find professors where the search term is part of their name
        exact_matches = []
        for prof in self.instructors_courses.keys():
            if search_term in prof.lower():
                exact_matches.append(prof)

        # If we found direct matches, return their data
        if exact_matches:
            results = []
            for prof_name in exact_matches:
                results.append({
                    'professor': self._format_instructor_name(prof_name),
                    'courses': self.instructors_courses.get(prof_name, [])
                })
            return results

        # If no direct matches, find suggestions
        suggestions = self._find_similar_professors(search_term)
        if suggestions:
            formatted_suggestions = []
            for s in suggestions:
                formatted_suggestions.append(self._format_instructor_name(s))
            return [{
                'professor': 'No exact match found',
                'suggestions': formatted_suggestions,
                'message': f'No professor found with name "{professor_name}". Did you mean one of these?'
            }]
            
        return []

    def _find_similar_professors(self, name: str, threshold=0.7):
        """Finds professors with names similar to the search term using difflib.
        
        Args:
            name (str): The name to find similarities for.
            threshold (float): The cutoff for similarity score (0.0 to 1.0).
            
        Returns:
            list: A list of names deemed similar to the input name.
        """
   
        all_professors = list(self.instructors_courses.keys())
        
        # Get close matches using difflib
        similar_matches = difflib.get_close_matches(name, all_professors, n=5, cutoff=threshold)
        
        return similar_matches

    async def extract_course_data(self, course, college_distances=None):
        """
        Extract course data from a course object.

        Args:
           course (dict): A course object to extract data from.
           college_distances (dict, optional): Precomputed distances to community colleges.

        Returns:
            dict: Extracted course data that contains the course number, title, prerequisites, and instructors.
        """
        try:
       
            course_string = course.get('courseString')
            course_title = course.get('title')
            preq = course.get('preReqNotes') or "No prerequisites"

            # Clean em tags from prerequisites
            preq = self.remove_em_tags(preq)
            synopsis_url = course.get('synopsisUrl', '')

            sections = course.get('sections', [])
            instructors_for_course = []

            # Loops through each section to extract the instructors
            for section in sections:
                instructor_for_section = section.get('instructors', [])

                if not instructor_for_section:
                    instructors_for_course.append([{'name': 'TBA'}])
                else:
                    formatted_instructors = []
                    for i in instructor_for_section:
                        formatted_instructors.append({'name': self._format_instructor_name(i['name'])})
                    
                    if formatted_instructors not in instructors_for_course:
                        instructors_for_course.append(formatted_instructors)

            course_code = course_string.replace(':', '')

            # Get equivalencies (with or without distance info)
            course_equivalencies = await self.get_top_5_course_equivalencies_by_distance(course_code, college_distances)

            course_data = {
                'title': course_title,
                'course_number': course_string,
                'instructors': instructors_for_course,
                'prerequisites': preq,
                'equivalencies': course_equivalencies,
                'synopsisUrl': synopsis_url,
            }

            return course_data
        except Exception as e:
            print(f"Error in extract_course_data: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise

    def get_course_instructors(self, course_code):
        """Get all instructors for a specific course.
        
        Args:
            course_code (str): The course code (e.g., '01198111') to look up.
            
        Returns:
            list: A list of instructor names for the given course.
        """
        if course_code not in self.courses_by_code:
            return []

        course = self.courses_by_code[course_code]
        sections = course.get('sections', [])
        instructors_for_course = []

        # Loops through each section to extract the instructors
        for section in sections:

            instructor_for_section = section.get('instructors', [])
            if instructor_for_section not in instructors_for_course:
                instructors_for_course.append(instructor_for_section)

        return instructors_for_course

# Main function to test searching by title, code, and professor. 
async def main():
    """A main function for testing the search functionalities of the controller."""

    pass
