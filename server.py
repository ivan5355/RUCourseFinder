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
            'results': results
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(debug=True)
