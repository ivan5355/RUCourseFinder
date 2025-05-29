import json
import os
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

class CourseQA:
    def __init__(self):
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        
        # Initialize OpenAI client for OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.openrouter_api_key,
        )
        # Initialize Pinecone client (as before)
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self.index = None  # Initialize as None, will be set in initialize_vector_db
        
        # Load course data
        with open('data/rutgers_courses.json', 'r') as f:
            self.courses_data = json.load(f)
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # Load non-course system prompt
        self.non_course_system_prompt = self._load_system_prompt("data/non_course_system_prompt.txt")
        
        # Load classifier system prompt
        self.classifier_system_prompt = self._load_system_prompt("data/classifier_system_prompt.txt")
            
        # Initialize the vector database
        self.initialize_vector_db()
    
    def prepare_course_text(self, course):
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
    
    def generate_embedding(self, text):
        """Generate embeddings for a given text using OpenAI (for Pinecone)."""
        # Check cache first
        # if text in self.embedding_cache_qa:
        #     return self.embedding_cache_qa[text]

        # Use a separate OpenAI client instance for embeddings if you haven't modified it
        # or ensure your self.client for OpenRouter doesn't interfere if it's the same.
        # For simplicity, assuming a default OpenAI client or one specifically for embeddings.
        # If self.client was re-initialized for OpenRouter, embeddings need their own client.
        
        # Let's create a dedicated OpenAI client for embeddings to avoid confusion
        # if the main self.client is now for OpenRouter.
        openai_embed_client = OpenAI(api_key=self.openai_api_key)

        response = openai_embed_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        embedding = response.data[0].embedding
        # Store in cache
        # self.embedding_cache_qa[text] = embedding
        return embedding
    
    def _load_system_prompt(self, prompt_file_path="data/chatbot_system_prompt.txt"):
        """Load the system prompt from a text file."""
        try:
            with open(prompt_file_path, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"Error: Prompt file not found at {prompt_file_path}. Using default prompt.")
            # Fallback to a default prompt if file is not found
            return "You are a helpful Rutgers University course assistant." # A simple fallback

    def initialize_vector_db(self):
        """Initialize the vector database with course embeddings."""
        index_name = "course-qa"
        
        # Check if index exists by iterating through the list of index descriptions
        index_exists = False
        for index_info in self.pc.list_indexes(): 
            if index_info.name == index_name:
                index_exists = True
                break

        if not index_exists:
            print(f"Creating index: {index_name}...")
            self.pc.create_index(
                name=index_name,
                dimension=1536,  # Dimension for text-embedding-3-small
                metric='cosine',
                spec={"serverless": {"cloud": "aws", "region": "us-east-1"}} 
            )
            print(f"Index {index_name} created.")
            
            # Populate the newly created index
            print("Populating index with course data...")
            for course in self.courses_data:
                course_text = self.prepare_course_text(course)
                embedding = self.generate_embedding(course_text)
                self.index.upsert(
                    vectors=[{
                        'id': course['courseString'],
                        'values': embedding,
                        'metadata': {
                            'text': course_text,
                            'title': course.get('title', ''),
                            'code': course.get('courseString', '')
                        }
                    }]
                )
            print("Index populated.")
        else:
            print(f"Index {index_name} already exists.")
            self.index = self.pc.Index(index_name) # Set self.index if it already exists
    
    async def answer_question(self, question, conversation_history=None):
        """Answer a question about courses using vector search and GPT with conversation context."""
        if not self.index:
            print("Error: Pinecone index is not initialized.")
            return {
                'error': 'Failed to generate answer',
                'details': 'Pinecone index not available.'
            }
        try:
            # Check if the question is course-related before searching
            if not self._is_course_related_question(question):
                # Handle non-course questions directly
                response = self.client.chat.completions.create(
                    model="meta-llama/llama-3.3-8b-instruct:free",
                    messages=[
                        {"role": "system", "content": self.non_course_system_prompt},
                        {"role": "user", "content": question}
                    ]
                )
                
                return {
                    'answer': response.choices[0].message.content,
                    'relevant_courses': []
                }
            
            # Generate embedding for the question
            question_embedding = self.generate_embedding(question)
            
            # Find relevant courses
            search_results = self.index.query(
                vector=question_embedding,
                top_k=3,
                include_metadata=True
            )
            
            # Prepare context from relevant courses
            context_parts = []
            for match in search_results.matches:
                context_parts.append(match.metadata['text'])
            context = "\n\n".join(context_parts)
            
            # Prepare conversation history for context
            conversation_context = ""
            if conversation_history:
                conversation_context = "\n\nPrevious Conversation:\n"
                for msg in conversation_history[-6:]:  # Use last 6 messages for context
                    role = "User" if msg['role'] == 'user' else "Assistant"
                    conversation_context += f"{role}: {msg['content']}\n"
                conversation_context += "\n"
            
            # Generate answer using Llama 3 via OpenRouter
            response = self.client.chat.completions.create(
                model="meta-llama/llama-3.3-8b-instruct:free", # Changed model
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Question: {question}{conversation_context}\\n\\nRelevant Course Information:\\n{context}"}
                ]
            )
            
            # relevant_courses_list = [match.metadata['code'] for match in search_results.matches] # Old version
            relevant_courses_list = []
            for match in search_results.matches:
                relevant_courses_list.append(match.metadata['code'])

            return {
                'answer': response.choices[0].message.content,
                # 'relevant_courses': [match.metadata['code'] for match in search_results.matches]
                'relevant_courses': relevant_courses_list
            }
            
        except Exception as e:
            print(f"Error in answer_question: {str(e)}")
            return {
                'error': 'Failed to generate answer',
                'details': str(e)
            }

    def _is_course_related_question(self, question):
        """Determine if a question is related to courses using LLM."""
        try:
            response = self.client.chat.completions.create(
                model="meta-llama/llama-3.3-8b-instruct:free",
                messages=[
                    {"role": "system", "content": self.classifier_system_prompt},
                    {"role": "user", "content": f"Is this question related to university courses or academics?\n\nQuestion: {question}"}
                ]
            )
            
            answer = response.choices[0].message.content.strip().upper()
            return answer == "YES"
            
        except Exception as e:
            print(f"Error in course detection: {str(e)}")
            # If there's an error, default to assuming it's course-related to be safe
            return True 