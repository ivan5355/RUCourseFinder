import requests
import json
import os
from datetime import date
import sys

def get_current_semester():
    """Determine the current semester based on the current date."""
    
    current_date = date.today()
    current_year = current_date.year
    current_month = current_date.month
    
    if current_month >= 1 and current_month <= 5:
        return current_year, 1  # Spring
    elif current_month >= 5 and current_month <= 8:
        return current_year, 7  # Summer
    else:
        if current_month >= 11:
            return current_year + 1, 1  # Next spring
        else:
            return current_year, 9  # Fall

def fetch_rutgers_courses(year, term, campus="NB"):
    """Fetch course data from Rutgers API."""
    url = "https://classes.rutgers.edu/soc/api/courses.json"
    params = {'year': year, 'term': term, 'campus': campus}
    
    print(f"Fetching course data for {year} Term {term}...")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        courses = response.json()
        print(f"Successfully fetched {len(courses)} courses")
        return courses
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

def save_course_data(courses, output_path="data/rutgers_courses.json"):
    """Save course data to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(courses)} courses to {output_path}")
        
    except Exception as e:
        print(f"Error saving data: {e}")
        sys.exit(1)

def main():
    """Main function to fetch and save course data."""
    year, term = get_current_semester()
    courses = fetch_rutgers_courses(year, term)
    save_course_data(courses)
    print("Course data update completed!")

if __name__ == "__main__":
    main() 