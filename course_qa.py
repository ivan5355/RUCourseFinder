import json
import os
from pinecone import Pinecone
from dotenv import load_dotenv
import google.generativeai as genai
import numpy as np
from prompts import COURSE_ASSISTANT_PROMPT

class CourseQA:
    def __init__(self):
        load_dotenv()
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        
        # Initialize Google Gemini client
        genai.configure(api_key=self.google_api_key)
        
        # Connect to the comprehensive Google embeddings index (created with text-embedding-004)
        self.index = self.pc.Index("courses-comprehensive-gemini")
        
        # Load course data for local lookups if needed
        with open('data/rutgers_courses.json', 'r') as f:
            self.courses_data = json.load(f)
    
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
                
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(general_prompt)
                
                return {
                    'answer': response.text if response.text else "I'm sorry, I couldn't generate a response to your question.",
                }
            
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
            
            # Extract context from matches
            context_parts = []
            for match in search_results.matches:
                if 'text' in match.metadata:
                    context_parts.append(match.metadata['text'])
            
            if not context_parts:
                return {
                    'answer': "I found some course matches but couldn't retrieve the detailed information. Please try asking your question in a different way.",
                }
            
            context = "\n\n".join(context_parts)
            
            # Prepare conversation history for context
            conversation_context = ""
            if conversation_history:
                conversation_context = "\n\nPrevious Conversation:\n"
                for msg in conversation_history[-6:]:
                    role = "User" if msg['role'] == 'user' else "Assistant"
                    conversation_context += f"{role}: {msg['content']}\n"
                conversation_context += "\n"
            
            # Build the full prompt using the imported system prompt
            full_prompt = f"{COURSE_ASSISTANT_PROMPT}\n\nQuestion: {question}{conversation_context}\n\nRelevant Course Information:\n{context}"
            
            # Generate answer using Gemini 1.5 Flash
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(full_prompt)
            
            if not response.text:
                return {
                    'answer': "I apologize, but I couldn't generate a response for your question. Please try rephrasing it or ask a different course-related question.",
                }
            
            # relevant_courses_list = [match.metadata['code'] for match in search_results.matches] # Old version
            relevant_courses_list = []
            for match in search_results.matches:
                relevant_courses_list.append(match.metadata['code'])

            return {
                'answer': response.text,
            }
            
        except Exception as e:
            print(f"Error in answer_question: {str(e)}")
            return {
                'error': 'Failed to generate answer',
                'details': str(e)
            }
            
            