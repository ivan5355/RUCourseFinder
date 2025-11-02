<img width="1489" alt="Screenshot 2025-06-03 at 7 50 11 PM" src="https://github.com/user-attachments/assets/b4e4c4b4-99d2-49c0-9a07-edee9baa46ac" />
<img width="1468" alt="Screenshot 2025-06-03 at 7 49 32 PM" src="https://github.com/user-attachments/assets/b3312975-5ae1-4fc0-86eb-a48cabaf37f0" />

## ruequialent
- The RUequivalent application enhances the existing course search functionality at Rutgers University by allowing users to search for courses based on course title, professor, or course code.

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

5. Get the most updated course data:
   ```bash
   python scripts/get_course_data.py
   ```
   This will fetch the latest course data from Rutgers and save it to the `data/` directory. Run this script periodically to keep your course data up to date.

## Dependencies

The application requires the following main dependencies:
- FastAPI: Modern, fast web framework for building APIs
- Uvicorn: ASGI server for running FastAPI applications
- Jinja2: Template engine for rendering HTML
- Google Generative AI: For embeddings using text-embedding-004 model
- Pinecone: Vector database for semantic search
- Pandas: Data manipulation and analysis
- Selenium: Web scraping course equivalencies
- BeautifulSoup4: HTML parsing
- NumPy: Numerical computing
- python-dotenv: Environment variable management
- aiohttp: Asynchronous HTTP client/server
- python-multipart: For handling multipart/form-data

All dependencies are listed in `requirements.txt` and will be installed automatically during setup.

## Running the Application

1. Make sure you're in the project directory and your virtual environment is activated

2. Update course data to the latest semester if you haven't done so already:
   ```bash
   python scripts/get_course_data.py
   ```
   Run this whenever you want to fetch the most recent course offerings.

3. Start the application:
   ```bash
   python app.py
   ```

4. Open the app in web browser at:
   ```
   http://localhost:5005
   ```

5. (Optional) Allow location access when prompted to enable distance-based sorting for community college equivalencies. The app works without location access, but distances won't be shown.

## Key Features:

**Course Search**: Search Rutgers University courses by title, professor, or course code with ease.

**Semantic Search**: By utilizing vector embeddings powered by Google's text-embedding-004 model, the application ensures more accurate and flexible search results, even when the exact course title doesn't match the user's query. This is particularly useful for title-based searches, accommodating variations in phrasing.

**Course Equivalency**: For each Rutgers course, the application displays a list of equivalent courses at community colleges across New Jersey.

**Distance Calculation**: When location access is granted, displays the distance from the user's location to community colleges offering equivalent courses, sorted by proximity. Community colleges are still shown even without location access.

## Technical Architecture

- **Backend**: Python with FastAPI framework and Uvicorn ASGI server
- **AI Models**: Google text-embedding-004 for semantic search
- **Vector Database**: Pinecone for storing and retrieving course embeddings
- **Data Processing**: Custom embedding generation and course data management
- **Frontend**: HTML/CSS/JavaScript with modern responsive design
- **Asynchronous Processing**: FastAPI's async/await support for improved performance

  

