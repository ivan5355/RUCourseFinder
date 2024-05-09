import pprint
from bs4 import BeautifulSoup
import requests
import time
import pandas as pd
import json

with open('config.json', 'r') as f:
    config = json.load(f)
art_id = config['ArtId']

data = {'doSearch': "Search"}
cookies = {'ArtId': art_id}
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.1'
headers = {
    'User-Agent': user_agent,
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0'
}

community_colleges = {
    "AT": "Atlantic-Cape Community College",
    "BE": "Bergen Community College",
    "BR": "Brookdale Community College",
    "CA": "Camden County College",
    "MR": "County College of Morris",
    "EX": "Essex County College",
    "HD": "Hudson County Community College",
    "ME": "Mercer County Community College",
    "MI": "Middlesex College",
    "OC": "Ocean County College",
    "PA": "Passaic County Community College",
    "RV": "Raritan Valley Community College",
    "BU": "Rowan College at Burlington County",
    "CU": "Rowan College of South Jersey - Cumberland Campus",
    "GL": "Rowan College of South Jersey - Gloucester Campus",
    "SA": "Salem Community College",
    "SX": "Sussex County Community College",
    "UI": "UCNJ Union College of Union County, NJ",
    "WA": "Warren County Community College"
}

colleges = {
    "BB": "Rutgers Business School - New Brunswick",
    "BP": "Rutgers-Edward Bloustein Sch of Planning & Policy",
    "PH": "Rutgers-Ernest Mario School of Pharmacy",
    "MG": "Rutgers-Mason Gross School of Arts",
    "AS": "Rutgers-School of Arts and Sciences",
    "EN": "Rutgers-School of Engineering",
    "CK": "Rutgers-School of Env Biological Sciences",
    "ML": "Rutgers-School of Management and Labor Relations",
    "NR": "Rutgers-School of Nursing"
}

def get_classes(src, dest):
    unique_identifier = int(time.time())  # Unique timestamp
    query = f'{src}+{dest}&ts={unique_identifier}'  # Append to make request unique
    url = f'https://njtransfer.org/artweb/listeqs.cgi?{query}'
    r = requests.post(url, data=data, headers=headers, cookies=cookies)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, 'lxml')
    rows = soup.find_all('tr')[2:]
    courses = []
    for course in rows:
        tds = course.find_all('td')
        courses.append({
            'code': tds[0].a.text,
            'name': tds[2].text,
            'credits': tds[3].text,
            'equivalency': tds[5].text,
            'transfer_credit': tds[7].text
        })
    return courses

for cc_code, cc_name in community_colleges.items():
    for c_code, c_name in colleges.items():
        courses = get_classes(cc_code, c_code)
        if courses:
            df = pd.DataFrame(courses)
            filename = f"{cc_name}_{c_name}.csv"
            df.to_csv(filename, index=False)
            print(f"Data saved to {filename}")
        else:
            print(f"No data found for {cc_name} and {c_name}")