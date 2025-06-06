from quart import Quart, render_template, request, jsonify, send_from_directory
from controller import course_search
from course_qa import CourseQA
from content_based_recommender import ContentBasedCourseRecommender
import os

app = Quart(__name__)
# Ensure static files are properly configured
app.static_folder = 'static'
app.template_folder = 'templates'

courses_controller = course_search(courses_data_path='data/rutgers_courses.json')
course_qa = CourseQA()
# Initialize content-based recommender
content_recommender = ContentBasedCourseRecommender('data/rutgers_courses.json')

your_location = None

@app.route('/')
async def search_page():
    return await render_template('main.html')

@app.route('/chatbot')
async def chatbot_page():
    return await render_template('chatbot.html')

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

@app.route('/get_recommendations', methods=['POST'])
async def get_recommendations():
    """
    Get course recommendations based on user preferences.
    
    Expects JSON payload with user preferences:
    {
        'interests': ['computer science', 'data science'],
        'preferred_subjects': ['Computer Science', 'Statistics'],
        'preferred_schools': ['School of Engineering'],
        'preferred_level': 'U',
        'preferred_credits': 3,
        'difficulty_preference': 'Intermediate',
        'core_requirements': ['QR', 'WCD'],
        'completed_courses': ['01:198:111', '01:198:112'],
        'career_goals': 'software engineering',
        'num_recommendations': 10
    }
    
    Returns:
        JSON response with recommended courses
    """
    try:
        data = await request.json
        
        # Extract user preferences
        user_preferences = {
            'interests': data.get('interests', []),
            'preferred_subjects': data.get('preferred_subjects', []),
            'preferred_schools': data.get('preferred_schools', []),
            'preferred_level': data.get('preferred_level', 'U'),
            'preferred_credits': data.get('preferred_credits'),
            'difficulty_preference': data.get('difficulty_preference'),
            'core_requirements': data.get('core_requirements', []),
            'completed_courses': data.get('completed_courses', []),
            'career_goals': data.get('career_goals', '')
        }
        
        num_recommendations = data.get('num_recommendations', 10)
        
        # Get recommendations
        recommendations = content_recommender.recommend_courses(
            user_preferences, 
            num_recommendations=num_recommendations
        )
        
        return jsonify({
            'status': 'success',
            'recommendations': recommendations,
            'total_found': len(recommendations)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.route('/get_similar_courses', methods=['POST'])
async def get_similar_courses():
    """
    Find courses similar to a given course.
    
    Expects JSON payload with:
    {
        'course_id': '01:198:111',
        'num_similar': 5
    }
    
    Returns:
        JSON response with similar courses
    """
    try:
        data = await request.json
        course_id = data.get('course_id')
        num_similar = data.get('num_similar', 5)
        
        if not course_id:
            return jsonify({'status': 'error', 'message': 'Course ID is required'})
        
        similar_courses = content_recommender.find_similar_courses(
            course_id, num_similar=num_similar
        )
        
        return jsonify({
            'status': 'success',
            'course_id': course_id,
            'similar_courses': similar_courses
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.route('/filter_courses', methods=['POST'])
async def filter_courses():
    """
    Filter courses by specific criteria.
    
    Expects JSON payload with filtering criteria:
    {
        'subject_description': 'Computer Science',
        'level': 'U',
        'credits': 3,
        'school_description': 'School of Engineering'
    }
    
    Returns:
        JSON response with filtered courses
    """
    try:
        data = await request.json
        
        # Get filtering criteria
        criteria = {k: v for k, v in data.items() if v is not None and v != ''}
        
        filtered_courses = content_recommender.get_courses_by_criteria(**criteria)
        
        return jsonify({
            'status': 'success',
            'criteria': criteria,
            'courses': filtered_courses[:50],  # Limit to 50 courses
            'total_found': len(filtered_courses)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500

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

@app.route('/ask_question', methods=['POST'])
async def ask_question():
    """
    Handles questions about courses.

    Expects a POST request with JSON payload containing 'question' and optional 'conversation_history'.
    Returns an answer and relevant course codes.

    Returns:
        JSON response containing the answer and relevant courses
    """
    try:
        data = await request.json
        question = data.get('question')
        conversation_history = data.get('conversation_history', [])
        
        if not question:
            return jsonify({'status': 'error', 'message': 'Question is required'})

        result = await course_qa.answer_question(question, conversation_history)
        
        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error'],
                'details': result.get('details')
            }), 500
        
        return jsonify({
            'status': 'success',
            'answer': result['answer'],
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.route('/static/<path:filename>')
async def static_files(filename):
    """Serve static files"""
    return await send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5002)
