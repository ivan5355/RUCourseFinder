from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from controller import course_search
import os

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

courses_controller = course_search(courses_data_path='data/rutgers_courses.json')

your_location = None
college_distances = None

@app.get("/", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

@app.post("/save_location")
async def save_location(request: Request):
    """
    Save user's current location.
    
    Expects JSON payload with latitude and longitude.
    Updates global your_location variable.
    
    Returns:
        JSON response with location status and coordinates
    """
    data = await request.json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    global your_location
    your_location = (latitude, longitude)

    global college_distances
    college_distances = await courses_controller.get_all_college_distances(your_location)

    return {
        'status': 'success', 
        'latitude': latitude, 
        'longitude': longitude
    }

@app.post("/search_by_title")
async def search_by_title(request: Request):
    """
    Handles search requests for courses by title.

    This function processes a POST request containing a JSON payload with a 'searchTerm' field.
    It validates the request, checks if a location is set, and then calls the courses_controller
    to search for courses by title. The results are then returned as a JSON response.

    Returns:
        JSON response containing the search status, search term, and a list of course results.
    """
    if not courses_controller:
        return {
            'status': 'error',
            'message': 'Search functionality is disabled. Please check API keys in .env file.'
        }
    
    try:
        data = await request.json()
        search_term = data.get('searchTerm')
        
        # Input validation
        if not search_term:
            return {'status': 'error', 'message': 'Search term is required'}
        
        if not your_location:
            return {'status': 'error', 'message': 'Location not set'}

        # Gets the top courses, along with their course info(title, course_string, instructors, prerequisites, equivalencies)
        # that most closely macthes the title the user search
        results = await courses_controller.search_by_title(search_term, college_distances)

        if not results:
            return {
                'status': 'success',
                'message': 'No results found',
                'results': []
            }
        
        return {
            'status': 'success',
            'searchTerm': search_term,
            'courses': results
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }

@app.post("/search_by_code")
async def search_by_code(request: Request):
    """
    Handles search requests for courses by last 3 digits of course code.

    Expects a POST request with JSON payload containing last 3 digits of course code'.
    Uses the user's saved location to find nearby course equivalencies.

    Returns:
        JSON response with matching courses and their details
    """
    try:

        data = await request.json()
        search_term = data.get('searchTerm', '')
        
        if not search_term:
            return {'status': 'error', 'message': 'Course code is required'}
        
        if not your_location:
            return {'status': 'error', 'message': 'Location not set'}

        # returns all courses and their course info that ends with the 3 digits the user specifies 
        results = await courses_controller.search_by_code(search_term, college_distances)

        if not results:
            return {
                'status': 'success',
                'message': 'No results found',
                'courses': []
            }
        
        return {
            'status': 'success',
            'courseCode': search_term,
            'courses': results
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }

@app.post("/search_by_professor")
async def search_by_professor(request: Request):
    """
    Handles search requests for courses by professor's last name.

    Expects a POST request with JSON payload containing 'searchTerm'.
    Returns a list of professors and their courses, or suggestions.
    """

    try:
        data = await request.json()
        search_term = data.get('searchTerm')
        
        if not search_term:
            return {'status': 'error', 'message': 'Search term is required'}
        
        results = courses_controller.search_by_professor(search_term)
        
        return {
            'status': 'success',
            'searchTerm': search_term,
            'results': results
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5005)  