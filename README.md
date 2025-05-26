## RU Course Finder

The RU Course Finder application enhances the existing course search functionality at Rutgers University by allowing users to search for courses based on course title, professor, or course code. Unlike the current search, which relies on exact keyword matches, my application incorporates semantic search. This feature compares vector embeddings of the user's search query with embeddings of actual course titles, improving the accuracy and relevance of search results—especially when searching by course title. This makes it easier for users to find courses even when their search terms don't exactly match the course title.
Additionally, the application provides a unique feature where students can view equivalent courses at local community colleges, along with the distance to these colleges and the name of the equivalent course.

## Installation and Setup

1. Clone the repository:
   ```bash
   git clone [repository-url]
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
   Create a `.env` file in the root directory with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=your_pinecone_environment
   ```

5. Initialize the database:
   - Make sure you have the `data/rutgers_courses.json` file in place
   - The application uses Pinecone for vector embeddings and OpenAI for generating embeddings
   - Ensure your Pinecone and OpenAI accounts are properly set up with valid API keys

## Dependencies

The application requires the following main dependencies:
- Quart: Web framework for the application
- OpenAI: For generating course embeddings
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
   http://localhost:5000
   ```

4. Allow location access when prompted to enable distance calculation features

## Key Features:

Course Search: Search Rutgers University courses by title, professor, or course code with ease.

Semantic Search: By utilizing vector embeddings, the application ensures more accurate and flexible search results, even when the exact course title doesn't match the user's query. This is particularly useful for title-based searches, accommodating variations in phrasing.

Course Equivalency: For each Rutgers course, the application offers a list of equivalent courses at nearby community colleges.

Distance Calculation: Displays the distance from the user's location to community colleges offering equivalent courses, making it easier to evaluate nearby options.

# Future Features:

- Provide how much the course costs to take at a communuity college compared to Rutgers
- Fine tune a model where a student can ask questions about Rutgers courses
  
<img width="1497" alt="Screenshot 2025-01-01 at 3 04 50 PM" src="https://github.com/user-attachments/assets/974b5885-7458-45e5-9f50-d59e905f4f79" />
<img width="1473" alt="Screenshot 2025-01-01 at 3 05 56 PM" src="https://github.com/user-attachments/assets/397f482e-9dd7-4773-a901-43827999466a" />
<img width="1505" alt="Screenshot 2025-01-01 at 3 08 04 PM" src="https://github.com/user-attachments/assets/6c8a2c95-ce1b-4a15-9c25-4cf3a74f887b" />
<img width="1507" alt="Screenshot 2025-01-01 at 3 15 36 PM" src="https://github.com/user-attachments/assets/38ca8c92-0b18-4f19-9c1c-dd914b4112f3" />

## Troubleshooting

### Pinecone Package Error
If you see an error about `pinecone-client` being renamed to `pinecone`, follow these steps:

1. Deactivate your virtual environment:
   ```bash
   deactivate
   ```

2. Remove the old virtual environment:
   ```bash
   rm -rf venv
   ```

3. Create a new virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

4. Install the requirements fresh:
   ```bash
   pip install -r requirements.txt
   ```

If you still encounter issues, try manually removing the old package and installing the new one:
```bash
pip uninstall pinecone-client
pip install pinecone
```

