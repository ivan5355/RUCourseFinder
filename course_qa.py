import json
import os
from pinecone import Pinecone
from dotenv import load_dotenv
import google.generativeai as genai
<<<<<<< HEAD
import numpy as np
from prompts import COURSE_ASSISTANT_PROMPT
=======
import re
>>>>>>> refs/remotes/origin/main

class CourseQA:
    def __init__(self):
        load_dotenv()
<<<<<<< HEAD
=======
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
>>>>>>> refs/remotes/origin/main
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        
<<<<<<< HEAD
        # Initialize Pinecone client
=======
        # Initialize Google Gemini client
        genai.configure(api_key=self.google_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Initialize Pinecone client (as before)
>>>>>>> refs/remotes/origin/main
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        
<<<<<<< HEAD
        # Initialize Google Gemini client
        genai.configure(api_key=self.google_api_key)
        
        # Connect to the comprehensive Google embeddings index (created with text-embedding-004)
        self.index = self.pc.Index("courses-comprehensive-gemini")
        
        # Load course data for local lookups if needed
        with open('data/rutgers_courses.json', 'r') as f:
            self.courses_data = json.load(f)
=======
        # Initialize course search controller for professor queries
        from controller import course_search
        self.course_controller = course_search()
        
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
>>>>>>> refs/remotes/origin/main
    
    def is_course_related_question(self, question):
        """Check if the question is course-related before activating RAG."""
        try:
            screening_prompt = f"""Determine if this question is related to college/university courses, classes, academics, or education.

Question: "{question}"

Respond with only "YES" if the question is about:
- Course information (descriptions, prerequisites, credits, schedules)
- Instructors or professors
- Academic subjects or majors
- Class schedules or meeting times
- Course requirements or equivalencies
- Academic planning or course selection

Respond with only "NO" if the question is about:
- General conversation or greetings
- Weather, sports, entertainment, politics
- Technical support or non-academic topics
- Personal matters unrelated to courses

Response:"""

            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(screening_prompt)
            
            return response.text.strip().upper() == "YES"
            
        except Exception as e:
            print(f"Error in course screening: {e}")
            # If screening fails, assume it's course-related to be safe
            return True
    
    def generate_embedding(self, text):
<<<<<<< HEAD
        """Generate embeddings using Google's text-embedding-004."""
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_query"  # For search queries
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Fallback to zeros if embedding fails
            return np.zeros(768).tolist()  # text-embedding-004 has 768 dimensions

    async def answer_question(self, question, conversation_history=None):
        """Answer a question about courses using vector search and Gemini 1.5 Flash with conversation context."""
        try:
            # First, check if this is a course-related question
            if not self.is_course_related_question(question):
                # For non-course questions, act as a normal chatbot without RAG
                conversation_context = ""
                if conversation_history:
                    conversation_context = "\n\nPrevious Conversation:\n"
                    for msg in conversation_history[-6:]:
                        role = "User" if msg['role'] == 'user' else "Assistant"
                        conversation_context += f"{role}: {msg['content']}\n"
                    conversation_context += "\n"
                
                # Simple prompt for general conversation
                general_prompt = f"You are a helpful AI assistant. Respond naturally and helpfully to the user's question.\n\nQuestion: {question}{conversation_context}"
                
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(general_prompt)
                
                return {
                    'answer': response.text if response.text else "I'm sorry, I couldn't generate a response to your question.",
                }
            
=======
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
                response = self.model.generate_content(self.non_course_system_prompt + "\n\n" + question)
                
                return {
                    'answer': response.text,
                    'relevant_courses': []
                }
            
            # Check if this is a professor-related question
            if self._is_professor_question(question):
                return await self._handle_professor_question(question, conversation_history)
            
>>>>>>> refs/remotes/origin/main
            # Generate embedding for the question
            question_embedding = self.generate_embedding(question)
            
            # Find relevant courses using RAG
            search_results = self.index.query(
                vector=question_embedding,
                top_k=3,
                include_metadata=True
            )
            
            # Check if we got any results
            if not search_results.matches:
                return {
                    'answer': "I couldn't find any relevant course information for your question. Please try rephrasing your question or ask about specific courses, instructors, or academic topics at Rutgers.",
                }
            
            # Prepare context from relevant courses
            context_parts = []
<<<<<<< HEAD
            
            for match in search_results.matches:
                if 'text' in match.metadata:
                    context_parts.append(match.metadata['text'])
            
            if not context_parts:
                return {
                    'answer': "I found some course matches but couldn't retrieve the detailed information. Please try asking your question in a different way.",
                }
            
=======
            for match in search_results.matches:
                context_parts.append(match.metadata['text'])
>>>>>>> refs/remotes/origin/main
            context = "\n\n".join(context_parts)
            
            # Prepare conversation history for context
            conversation_context = ""
            if conversation_history:
                conversation_context = "\n\nPrevious Conversation:\n"
                for msg in conversation_history[-6:]:
                    role = "User" if msg['role'] == 'user' else "Assistant"
                    conversation_context += f"{role}: {msg['content']}\n"
                conversation_context += "\n"
            
<<<<<<< HEAD
            # Create the full prompt using the imported system prompt
            full_prompt = f"{COURSE_ASSISTANT_PROMPT}\n\nQuestion: {question}{conversation_context}\n\nRelevant Course Information:\n{context}"
            
            # Generate answer using Gemini 1.5 Flash
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(full_prompt)
            
            if not response.text:
                return {
                    'answer': "I apologize, but I couldn't generate a response for your question. Please try rephrasing it or ask a different course-related question.",
                }
=======
            # Generate answer using Google Gemini
            prompt = f"{self.system_prompt}\n\nQuestion: {question}{conversation_context}\n\nRelevant Course Information:\n{context}"
            response = self.model.generate_content(prompt)
>>>>>>> refs/remotes/origin/main
            
            # relevant_courses_list = [match.metadata['code'] for match in search_results.matches] # Old version
            relevant_courses_list = []
            for match in search_results.matches:
                relevant_courses_list.append(match.metadata['code'])

            return {
                'answer': response.text,
<<<<<<< HEAD
=======
                # 'relevant_courses': [match.metadata['code'] for match in search_results.matches]
                'relevant_courses': relevant_courses_list
>>>>>>> refs/remotes/origin/main
            }
            
        except Exception as e:
            print(f"Error in answer_question: {str(e)}")
            return {
                'error': 'Failed to generate answer',
                'details': str(e)
            }
<<<<<<< HEAD
=======

    def _is_course_related_question(self, question):
        """Determine if a question is related to courses using LLM."""
        try:
            response = self.model.generate_content(self.classifier_system_prompt + "\n\n" + f"Is this question related to university courses or academics?\n\nQuestion: {question}")
            
            answer = response.text.strip().upper()
            return answer == "YES"
            
        except Exception as e:
            print(f"Error in course detection: {str(e)}")

            # If there's an error, default to assuming it's course-related to be safe
            return True 

    def _is_professor_question(self, question):
        """Determine if a question is asking about what courses a professor teaches."""
        question_lower = question.lower()
        
        # Keywords that suggest professor-related queries
        professor_indicators = [
            'professor', 'prof', 'instructor', 'teacher', 'teaches', 'taught by',
            'what courses does', 'what classes does', 'courses taught by',
            'classes taught by', 'who teaches', 'taught by'
        ]
        
        # return any(indicator in question_lower for indicator in professor_indicators) # Old one-liner
        for indicator in professor_indicators:
            if indicator in question_lower:
                return True
        return False
    
    async def _handle_professor_question(self, question, conversation_history=None):
        """Handle professor-related questions using the controller's professor search."""
        try:
            # Extract professor name from the question
            professor_name = self._extract_professor_name(question)
            
            if not professor_name:
                return {
                    'answer': 'I couldn\'t identify the professor name in your question. Could you please specify which professor you\'re asking about?',
                    'relevant_courses': []
                }
            
            # Search for the professor using the controller
            professor_results = self.course_controller.search_by_professor(professor_name)
            
            if not professor_results:
                return {
                    'answer': f'I couldn\'t find any courses taught by professor "{professor_name}". Please check the spelling or try searching with just the last name.',
                    'relevant_courses': []
                }
            
            # Check if we got suggestions instead of actual results
            if len(professor_results) == 1 and 'suggestions' in professor_results[0]:
                suggestions = professor_results[0]['suggestions']
  
                suggestions_text = ""
                for prof in suggestions:
                    suggestions_text += f"• {prof}\n"
                
                return {
                    'answer': f'I couldn\'t find an exact match for professor "{professor_name}". Did you mean one of these professors?\n\n{suggestions_text.strip()}\n\nPlease ask again with the correct professor name.',
                    'relevant_courses': []
                }
            
            # Format the professor results into a readable response
            response_parts = []
            relevant_courses = []
            
            for result in professor_results:
                professor = result['professor']
                courses = result['courses']
                
                response_parts.append(f"Professor: {professor}")
                response_parts.append(f"Courses taught:")
                
                for course in courses:
                    course_line = f"• {course['courseString']} - {course['title']}"
                    response_parts.append(course_line)
                    relevant_courses.append(course['courseString'])
                
                response_parts.append("")  # Add blank line between professors
            
            formatted_response = '\n'.join(response_parts).strip()
            
            return {
                'answer': formatted_response,
                'relevant_courses': relevant_courses
            }
            
        except Exception as e:
            print(f"Error in _handle_professor_question: {str(e)}")
            return {
                'error': 'Failed to process professor question',
                'details': str(e)
            }
    
    def _extract_professor_name(self, question):
        """Extract professor name from the question."""
        # Remove common words
        skip_words = ['professor', 'prof', 'instructor', 'dr', 'doctor', 'what', 'courses', 'does', 'teach', 'teaches', 'taught', 'by', 'classes']
        
        # Find potential name words
        name_words = []
        for word in question.split():
            clean_word = word.strip('.,?!:;')
            if clean_word.lower() not in skip_words and clean_word:
                if clean_word[0].isupper() or len(clean_word) > 3:
                    name_words.append(clean_word)
        
        if name_words:
            name = ' '.join(name_words[:2])  # Take first 2 words max
            if len(name) > 1 and name.replace(' ', '').isalpha():
                return name
        
        return None
    
  
>>>>>>> refs/remotes/origin/main
