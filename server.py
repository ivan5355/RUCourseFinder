from quart import Quart, render_template, request, jsonify
from controller import course_search

app = Quart(__name__)
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
   
    data = await request.json
    search_term = data.get('searchTerm')

    results = await courses_controller.search_by_title(search_term)

    if not results:
        return jsonify({'searchTerm': search_term, 'message': 'No search results found.'})

    return jsonify({
        'searchTerm': search_term,
        'results': results
    })

if __name__ == '__main__':
    app.run(debug=True)
