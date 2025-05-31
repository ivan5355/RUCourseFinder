## RU Course Finder

The RU Course Finder application enhances the existing course search functionality at Rutgers University by allowing users to search for courses based on course title, professor, or course code. Unlike the current search, which relies on exact keyword matches, my application incorporates semantic search. This feature compares vector embeddings of the user's search query with embeddings of actual course titles, improving the accuracy and relevance of search results—especially when searching by course title. This makes it easier for users to find courses even when their search terms don't exactly match the course title.

Additionally, the application provides a unique feature where students can view equivalent courses at local community colleges, along with the distance to these colleges and the name of the equivalent course.


## Installation and Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ivan5355/RUCourseFinder
   cd RUCourseFinder
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create accounts from Google AI Studio, Pinecone, and Mapbox and get their API keys. Create a `.env` file in the root directory with the following variables:
   ```
   GOOGLE_API_KEY=your_google_ai_studio_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   MAPBOX_ACCESS_TOKEN=your_mapbox_token
   ```

## Dependencies

The application requires the following main dependencies:
- Quart: Web framework for the application
- Google Generative AI: For embeddings and chat functionality using Gemini models
- Pinecone: Vector database for semantic search
- Pandas: Data manipulation and analysis
- Selenium: Web scraping course equivalencies
- BeautifulSoup4: HTML parsing
- NumPy: Numerical computing
- python-dotenv: Environment variable management

All dependencies are listed in `requirements.txt` and will be installed automatically during setup.

## Running the Application

1. Make sure you're in the project directory and your virtual environment is activated

2. Start the application:
   ```bash
   python app.py
   ```

3. Open your web browser and navigate to:
   ```
   http://localhost:5002
   ```

4. Allow location access when prompted to enable distance calculation features

## Key Features:

**Course Search**: Search Rutgers University courses by title, professor, or course code with ease.

**Semantic Search**: By utilizing vector embeddings powered by Google's text-embedding-004 model, the application ensures more accurate and flexible search results, even when the exact course title doesn't match the user's query. This is particularly useful for title-based searches, accommodating variations in phrasing.

**Course Equivalency**: For each Rutgers course, the application offers a list of equivalent courses at nearby community colleges.

**Distance Calculation**: Displays the distance from the user's location to community colleges offering equivalent courses, making it easier to evaluate nearby options.

**AI Chatbot**: An intelligent chatbot powered by Google's Gemini 1.5 Flash model that can answer questions about Rutgers courses, helping students make informed decisions about their course selections. The chatbot features:
- Course-related question detection to provide relevant RAG (Retrieval-Augmented Generation) responses
- Conversation history awareness for follow-up questions
- Support for general conversation when questions aren't course-related
- Information about course content, prerequisites, instructors, schedules, and general course-related queries

**Smart Context Handling**: The system intelligently determines whether user questions are course-related and activates the appropriate response mechanism, providing either detailed course information through RAG or general conversation capabilities.

## Technical Architecture

- **Backend**: Python with Quart framework
- **AI Models**: Google Gemini 1.5 Flash for chat, Google text-embedding-004 for semantic search
- **Vector Database**: Pinecone for storing and retrieving course embeddings
- **Data Processing**: Custom embedding generation and course data management
- **Frontend**: HTML/CSS/JavaScript with modern responsive design

  
<img width="1497" alt="Screenshot 2025-01-01 at 3 04 50 PM" src="https://github.com/user-attachments/assets/974b5885-7458-45e5-9f50-d59e905f4f79" />
<img width="1473" alt="Screenshot 2025-01-01 at 3 05 56 PM" src="https://github.com/user-attachments/assets/397f482e-9dd7-4773-a901-43827999466a" />
<img width="1505" alt="Screenshot 2025-01-01 at 3 08 04 PM" src="https://github.com/user-attachments/assets/6c8a2c95-ce1b-4a15-9c25-4cf3a74f887b" />
<img width="1507" alt="Screenshot 2025-01-01 at 3 15 36 PM" src="https://github.com/user-attachments/assets/38ca8c92-0b18-4f19-9c1c-dd914b4112f3" />

