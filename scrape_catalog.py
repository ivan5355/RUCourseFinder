import requests
from bs4 import BeautifulSoup

with open("catalog.txt", "w", encoding="utf-8") as f:
    for i in range(1, 1540):  # inclusive up to page 1539
        url = f"https://catalogs.rutgers.edu/generated/nb-ug_current/pg{i}.html"
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            #store text in a file called catalog.txt
            with open("catalog.txt", "a", encoding="utf-8") as f:
                f.write(f"\n--- Page {i} ---\n")
                f.write(text + "\n")
            print(f"Saved page {i}")
        else:
            print(f"Failed to fetch page {i}: status code {response.status_code}")
