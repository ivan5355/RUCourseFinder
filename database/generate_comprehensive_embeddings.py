import os
import json
import numpy as np
from tqdm import tqdm
import dotenv
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai

# Load environment variables
dotenv.load_dotenv()

# Initialize Google Gemini client
google_api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=google_api_key)

# Initialize Pinecone client
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)

# Pinecone index details
index_name = "courses-comprehensive-gemini"
dimension = 768  # Dimension for text-embedding-004
metric = "cosine"

# Check if the index exists
existing_indexes = []
for index in pc.list_indexes():
    existing_indexes.append(index.name)

if index_name not in existing_indexes:
    print(f"Index '{index_name}' does not exist. Creating index...")
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(
            cloud='aws', 
            region='us-east-1'  
        )
    )
    print(f"Index '{index_name}' created successfully!")

# Access the index
index = pc.Index(index_name)

# Load the Rutgers courses data from JSON file
with open('../data/rutgers_courses.json', 'r') as json_file:
    courses_data = json.load(json_file)

def prepare_course_text(course):
    """Prepare a comprehensive text representation of a course including all available fields."""
    
    # Basic course information
    course_title = course.get('title', 'N/A')
    course_code = course.get('courseString', 'N/A')
    course_number = course.get('courseNumber', 'N/A')
    expanded_title = course.get('expandedTitle', '').strip()
    course_description = course.get('courseDescription', 'No description available')
    prereq_notes = course.get('preReqNotes', 'No prerequisites')
    
    # School and subject information
    school_info = course.get('school', {})
    school_name = school_info.get('description', 'N/A')
    subject_description = course.get('subjectDescription', 'N/A')
    subject_notes = course.get('subjectNotes', '')
    subject_group_notes = course.get('subjectGroupNotes', '')
    unit_notes = course.get('unitNotes', '')
    course_notes = course.get('courseNotes', '')
    
    # Credits and level information
    credits_obj = course.get('creditsObject', {})
    credits_description = credits_obj.get('description', 'N/A')
    level = course.get('level', 'N/A')  # U for undergraduate, G for graduate
    
    # Campus and location information
    main_campus = course.get('mainCampus', 'N/A')
    campus_locations = course.get('campusLocations', [])
    campus_info = []
    for loc in campus_locations:
        if loc.get('description'):
            campus_info.append(loc.get('description', ''))
    campus_info = ', '.join(campus_info)
    
    # Core codes (general education requirements)
    core_codes = course.get('coreCodes', [])
    core_info = []
    for core in core_codes:
        if core.get('coreCodeDescription'):
            core_info.append(core['coreCodeDescription'])
    core_info = ', '.join(core_info) if core_info else 'No core requirements'
    
    # Section information (instructors, meeting times, etc.)
    sections = course.get('sections', [])
    instructors_list = []
    meeting_info = []
    section_notes_list = []
    
    for section in sections:
        # Collect instructors
        section_instructors = section.get('instructors', [])
        for instructor in section_instructors:
            if instructor.get('name') and instructor['name'] not in instructors_list:
                instructors_list.append(instructor['name'])
        
        # Collect section notes
        section_notes = section.get('sectionNotes', '').strip()
        if section_notes and section_notes not in section_notes_list:
            section_notes_list.append(section_notes)
        
        # Collect meeting times and modes
        meeting_times = section.get('meetingTimes', [])
        for meeting in meeting_times:
            mode_desc = meeting.get('meetingModeDesc', '')
            meeting_day = meeting.get('meetingDay', '')
            start_time = meeting.get('startTime', '')
            end_time = meeting.get('endTime', '')
            campus_name = meeting.get('campusName', '')

            # Convert day code to full name
            day_map = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'Th': 'Thursday', 'F': 'Friday', 'S': 'Saturday', 'Su': 'Sunday'}
            # Handle Th (Thursday) and Su (Sunday) properly
            day_full = day_map.get(meeting_day, meeting_day)
           
            if meeting_day == 'Th':
                day_full = 'Thursday'
            elif meeting_day == 'Su':
                day_full = 'Sunday'
            elif meeting_day == 'T':
                day_full = 'Tuesday'
            elif meeting_day == 'S':
                day_full = 'Saturday'
            elif meeting_day == 'F':
                day_full = 'Friday'
            elif meeting_day == 'M':
                day_full = 'Monday'
            elif meeting_day == 'W':
                day_full = 'Wednesday'

            # Convert 24-hour time to 12-hour format
            def format_time(t):
                if not t or len(t) != 4 or not t.isdigit():
                    return t
                hour = int(t[:2])
                minute = int(t[2:])
                suffix = 'AM' if hour < 12 else 'PM'
                hour12 = hour if 1 <= hour <= 12 else (hour - 12 if hour > 12 else 12)
                return f"{hour12}:{minute:02d} {suffix}"
            start_time_fmt = format_time(start_time)
            end_time_fmt = format_time(end_time)

            # Use clear label for mode (e.g., Lecture, Lab, etc.)
            label = mode_desc if mode_desc else 'Meeting'

            # Compose the string
            if day_full and start_time_fmt and end_time_fmt and campus_name:
                meeting_detail = f"{label}: {day_full}, {start_time_fmt} – {end_time_fmt} at {campus_name}"
            else:
                meeting_detail = f"{label}: {meeting_day} {start_time}-{end_time} at {campus_name}".strip()
            if meeting_detail not in meeting_info:
                meeting_info.append(meeting_detail)
    
    instructors_text = ', '.join(instructors_list) if instructors_list else 'No instructors listed'
    section_notes_text = '. '.join(section_notes_list) if section_notes_list else ''
    meeting_info_text = '. '.join(meeting_info) if meeting_info else ''
    
    # Combine all information into comprehensive text
    text_parts = [
        f"Course Title: {course_title}",
        f"Course Code: {course_code}",
        f"Course Number: {course_number}",
    ]
    
    if expanded_title and expanded_title != course_title:
        text_parts.append(f"Extended Title: {expanded_title}")
    
    text_parts.extend([
        f"Description: {course_description}",
        f"Prerequisites: {prereq_notes}",
        f"School: {school_name}",
        f"Subject: {subject_description}",
        f"Credits: {credits_description}",
        f"Level: {'Undergraduate' if level == 'U' else 'Graduate' if level == 'G' else level}",
        f"Main Campus: {main_campus}",
        f"Campus Locations: {campus_info}",
        f"Core Requirements: {core_info}",
        f"Instructors: {instructors_text}",
    ])
    
    if subject_notes:
        text_parts.append(f"Subject Notes: {subject_notes}")
    if subject_group_notes:
        text_parts.append(f"Subject Group Notes: {subject_group_notes}")
    if unit_notes:
        text_parts.append(f"Unit Notes: {unit_notes}")
    if course_notes:
        text_parts.append(f"Course Notes: {course_notes}")
    if section_notes_text:
        text_parts.append(f"Section Notes: {section_notes_text}")
    if meeting_info_text:
        text_parts.append(f"Meeting Information: {meeting_info_text}")
    
    return '\n'.join(text_parts)

# Function to generate embeddings for a text
def generate_embedding(text):
    """Generate embeddings using Google's text-embedding-004."""
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"  # For documents being indexed
        )
        return result['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Fallback to zeros if embedding fails
        return np.zeros(768).tolist()  # text-embedding-004 has 768 dimensions

# Process each course individually (comprehensive texts are typically long)
print("Generating comprehensive course embeddings...")
vectors_to_upsert = []

for i, course in enumerate(tqdm(courses_data, desc="Processing courses")):
    # Prepare comprehensive course text
    course_text = prepare_course_text(course)
    
    # Generate embedding for the comprehensive text
    try:
        embedding = generate_embedding(course_text)
        
        # Prepare vector for upsert
        course_id = course.get('courseString')
        metadata = {
            'text': course_text,
            'title': course.get('title', ''),
            'code': course.get('courseString', ''),
            'description': course.get('courseDescription', '')[:500]  # Truncate for metadata limits
        }
        
        vectors_to_upsert.append({
            'id': course_id,
            'values': embedding,
            'metadata': metadata
        })
        
        # Upsert in batches of 100
        if len(vectors_to_upsert) >= 100:
            index.upsert(vectors_to_upsert)
            vectors_to_upsert = []
            
    except Exception as e:
        print(f"Error processing course {course.get('courseString', 'Unknown')}: {e}")

# Upsert any remaining vectors
if vectors_to_upsert:
    index.upsert(vectors_to_upsert)

print(f"Expected number of courses: {len(courses_data)}")
# Check index stats
index_stats = index.describe_index_stats()
print(f"Total vectors in index '{index_name}': {index_stats['total_vector_count']}")
print("Comprehensive course embeddings generation complete!") 