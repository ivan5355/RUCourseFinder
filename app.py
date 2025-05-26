from quart import Quart, render_template, request, jsonify
from controller import course_search

app = Quart(__name__, template_folder='templates')
courses_controller = course_search(courses_data_path='data/rutgers_courses.json')

your_location = None

@app.route('/')
async def search_page():
    return await render_template('main.html')

@app.route('/save_location', methods=['POST'])
async def save_location():
    """
    Save user's current location.
    
    Expects JSON payload with latitude and longitude.
    Updates global your_location variable.
    
    Returns:
        JSON response with location status and coordinates
    """
    data = await request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    global your_location
    your_location = (latitude, longitude)
    return jsonify({
        'status': 'success', 
        'latitude': latitude, 
        'longitude': longitude
    })

@app.route('/search_by_title', methods=['POST'])
async def search_by_title():
    """
    Handles search requests for courses by title.

    This function processes a POST request containing a JSON payload with a 'searchTerm' field.
    It validates the request, checks if a location is set, and then calls the courses_controller
    to search for courses by title. The results are then returned as a JSON response.

    Returns:
        JSON response containing the search status, search term, and a list of course results.
    """
    try:
        data = await request.json
        search_term = data.get('searchTerm')
        
        # Input validation
        if not search_term:
            return jsonify({'status': 'error', 'message': 'Search term is required'})
        
        if not your_location:
            return jsonify({'status': 'error', 'message': 'Location not set'})

        # Gets the top courses, along with their course info(title, course_string, instructors, prerequisites, equivalencies)
        # that most closely macthes the title the user search
        results = await courses_controller.search_by_title(search_term, your_location)

        if not results:
            return jsonify({
                'status': 'success',
                'message': 'No results found',
                'results': []
            })
        
        return jsonify({
            'status': 'success',
            'searchTerm': search_term,
            'courses': results
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.route('/search_by_code', methods=['POST'])
async def search_by_code():
    """
    Handles search requests for courses by last 3 digits of course code.

    Expects a POST request with JSON payload containing last 3 digits of course code'.
    Uses the user's saved location to find nearby course equivalencies.

    Returns:
        JSON response with matching courses and their details
    """
    try:

        data = await request.json
        search_term = data.get('searchTerm', '')
        
        if not search_term:
            return jsonify({'status': 'error', 'message': 'Course code is required'})
        
        if not your_location:
            return jsonify({'status': 'error', 'message': 'Location not set'})

        # returns all courses and their course info that ends with the 3 digits the user specifies 
        results = await courses_controller.search_by_code(search_term, your_location)

        if not results:
            return jsonify({
                'status': 'success',
                'message': 'No results found',
                'courses': []
            })
        
        return jsonify({
            'status': 'success',
            'courseCode': search_term,
            'courses': results
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.route('/search_by_professor', methods=['POST'])
async def search_by_professor():
    """
    Handles search requests for courses by professor name.

    Expects a POST request with JSON payload containing 'searchTerm' for professor name.
    Returns a list of professors and their courses that match the search term.

    Returns:
        JSON response containing matching professors and their courses
    """
    try:
        
        data = await request.json
        search_term = data.get('searchTerm')
        
        if not search_term:
            return jsonify({'status': 'error', 'message': 'Professor name is required'})

        results = courses_controller.search_by_professor(search_term)

        if not results:
            return jsonify({
                'status': 'success',
                'message': 'No results found',
                'results': []
            })
        
        return jsonify({
            'searchTerm': search_term,
            'results': results
         })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
