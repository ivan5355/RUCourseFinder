import requests
import json
import os
from datetime import date
import sys

def get_current_semester():
    """Determine the current semester based on the current date.

    Check if next semester data is available early (in March or October). 
    If not, fall back to the current semester.
    """
    current_date = date.today()
    current_year = current_date.year
    current_month = current_date.month

    
    def term_exists(year, term):
        """Check if course data exists for a given year/term without downloading all data."""
        url = "https://classes.rutgers.edu/soc/api/courses.json"
        params = {'year': year, 'term': term, 'campus': 'NB'}
        
        try:
            # Make a HEAD request to check if data exists without downloading
            response = requests.head(url, params=params, timeout=10)
            if response.status_code == 200:

                # If HEAD works, make a quick GET to check if we get actual data
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                courses = response.json()
                return len(courses) > 0
            return False
        except Exception as e:
            print(f"Could not check availability for {year} Term {term}: {e}")
            return False

    # October → Try next year's Spring (term 1)
    if current_month == 10:
        next_spring_year = current_year + 1
        print(f"October detected - checking if Spring {next_spring_year} courses are available...")
        if term_exists(next_spring_year, 1):
            print(f"Spring {next_spring_year} courses found!")
            return next_spring_year, 1
        else:
            print(f"Spring {next_spring_year} courses not yet available, falling back to Fall {current_year}")
            return current_year, 9  # Fall fallback

    # March → Try current year's Fall (term 9)
    elif current_month == 3:
        print(f"March detected - checking if Fall {current_year} courses are available...")
        if term_exists(current_year, 9):
            print(f"Fall {current_year} courses found!")
            return current_year, 9
        else:
            print(f"Fall {current_year} courses not yet available, falling back to Spring {current_year}")
            return current_year, 1  # Spring fallback

    # Normal logic if not March or October
    elif 1 <= current_month <= 5:
        return current_year, 1  # Spring
    elif 5 < current_month <= 8:
        return current_year, 7  # Summer
    elif current_month >= 11:
        return current_year + 1, 1  # Next year Spring
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

    # check if the current semester is available
    year, term = get_current_semester()

    # fetch the course data
    courses = fetch_rutgers_courses(year, term)

    # save the course data
    save_course_data(courses)
    
    print("Course data update completed!")

if __name__ == "__main__":
    main() 