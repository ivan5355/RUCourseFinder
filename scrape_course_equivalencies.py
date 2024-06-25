import os
import time
from bs4 import BeautifulSoup
import pandas as pd
from selenium.webdriver.support.ui import Select
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Initialize the browser
driver = webdriver.Chrome()

community_colleges = ["Atlantic-Cape Community College", 'Bergen Community College', 'Brookdale Community College', 'Camden County College', 'County College of Morris', 'Essex County College', 'Hudson County Community College', 'Mercer County Community College', 'Middlesex College', 'Ocean County College', 'Passaic County Community College', 'Raritan Valley Community College', 'Rowan College at Burlington County', 'Rowan College of South Jersey - Cumberland Campus', 'Rowan College of South Jersey - Gloucester Campus', 'Salem Community College', 'Sussex County Community College', 'UCNJ Union College of Union County, NJ', 'Warren County Community College']
                      
colleges = ["Rutgers Business School - New Brunswick", "Rutgers-Edward Bloustein Sch of Planning & Policy", "Rutgers-Ernest Mario School of Pharmacy", "Rutgers-Mason Gross School of Arts", "Rutgers-School of Arts and Sciences", "Rutgers-School of Engineering", "Rutgers-School of Env Biological Sciences", "Rutgers-School of Management and Labor Relations", "Rutgers-School of Nursing"]

# Initialize the browser
driver = webdriver.Chrome()

def get_classes(community_college, college):
    
    driver.get('https://njtransfer.org/artweb/chgri.cgi')

    # Select the community college and college
    community_colleges = Select(driver.find_element(By.NAME, "SIInst"))
    community_colleges.select_by_visible_text(community_college)

    colleges = Select(driver.find_element(By.NAME, "RIInst"))
    colleges.select_by_visible_text(college)

    # Click the submit button
    try:
      cookies_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "acceptcookies")))
      cookies_button.click()
    except:
      pass


    submit_button = driver.find_element(By.NAME, "SubChgRI")
    submit_button.click()

    list_all = driver.find_element(By.CLASS_NAME, "btn.btn-round.btn-warning.btn-sm.shadow-none")
    list_all.click()

    search_button = driver.find_element(By.NAME, "doSearch")
    search_button.click()

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    rows = soup.find_all('tr')[2:]

    courses = []
    for course in rows:
        tds = course.find_all('td')
        courses.append({
            'community_college': community_college,
            'college': college,
            'code': tds[0].a.text,
            'name': tds[2].text,
            'credits': tds[3].text,
            'equivalency': tds[5].text,
            'transfer_credit': tds[7].text
        })

    return courses


all_courses = []

# Loop through all the community colleges and colleges
for community_college in community_colleges:
    for college in colleges:
        courses = get_classes(community_college, college)
        if courses:
            all_courses.extend(courses)
            print(f"Got {len(courses)} courses for {community_college} and {college}")
        else:
            print(f"Error getting courses for {community_college} and {college}")

# Save the data to a CSV file
df = pd.DataFrame(all_courses)
df.to_csv('community_to_college.csv', index=False)

driver.quit()


