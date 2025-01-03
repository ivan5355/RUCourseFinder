import itertools
import re
import pandas as pd

df = pd.read_json('rutgers_courses.json')

# Extract major from courseString
df['major'] = df['courseString'].str.split(':').str[1]

# Function to find all combinations of courses
def find_combinations(nested_course_lists):

    result = []

    for course_lists in nested_course_lists:
        combinations = list(itertools.product(*course_lists))
        result.append(combinations)

    return result
   
# Extract prerequisite course codes
def parse_prerequisites(preReqNotes):

    # Remove HTML tags
    clean_notes = re.sub(r"<[^>]+>", "", preReqNotes)

    # Split by 'OR' to identify different main groups
    or_groups = []
    for group in clean_notes.split("OR"):
        or_groups.append(group.strip())

    prerequisites = []
    
    # Process each OR group
    for group in or_groups:
        and_courses = []
        
        # Split by 'and' to identify AND conditions within each group
        and_conditions = group.split("and")
        
        for condition in and_conditions:

            # Find all course numbers in the condition
            courses = re.findall(r'\b\d{2}:\d{3}:\d{3}\b', condition)
            
            if courses:  # Only add non-empty results
                and_courses.append(courses)
        
        # Append the AND conditions for each OR group
        if and_courses:
            prerequisites.append(and_courses)
    
    return prerequisites

# Flatten the prerequisite combinations into a single list
def flatten_combinations(nested_combinations):

    flattened_list = []

    for group in nested_combinations:
        for combo in group:
            flattened_list.append(combo)

    return flattened_list

# Apply the functions to the dataframe
df['prerequisite_codes'] = df['preReqNotes'].apply(parse_prerequisites)
df['prerequisite_codes'] = df['prerequisite_codes'].apply(find_combinations)
df['flattened_prerequisite_codes'] = df['prerequisite_codes'].apply(flatten_combinations)

def print_prereqs(major_number, df):
 
    # Filter the DataFrame for the specified major
    major_courses = df[df['major'] == major_number]
    major_courses = major_courses[
        ~major_courses['courseString'].str.split(':').str[2].str.startswith(('5', '6', '7', '8', '9'))
    ]
    
    # Print the courseString and flattened prerequisites
    for index, row in major_courses.iterrows():
        course_string = row['courseString']
        flattened_prereqs = row['flattened_prerequisite_codes']
        print(f"{course_string}: {flattened_prereqs}")
        print('\n')

def create_adjacency_list(major_number, df):
 
    major_courses = df[df['major'] == major_number]
    major_courses = major_courses[
        ~major_courses['courseString'].str.split(':').str[2].str.startswith(('5', '6', '7', '8', '9'))
    ]
    
    adjacency_list = {}
    
    for index, row in major_courses.iterrows():
        course = row['courseString']
        prerequisites = row['flattened_prerequisite_codes']
        
        # Initialize the course in the adjacency list
        if course not in adjacency_list:
            adjacency_list[course] = []
        
        # For each prerequisite combination
        for prereq_combo in prerequisites:
            for prereq in prereq_combo:
                adjacency_list[course].append(prereq) 

    return adjacency_list

if __name__ == "__main__":
    print_prereqs('198', df)
    adjacency_list = create_adjacency_list('198', df)
    print("Adjacency List:")
    for course, prereqs in adjacency_list.items():
        print(f"{course}: {prereqs}")


