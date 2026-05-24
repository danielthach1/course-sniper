import requests
import json

r = requests.get(
    "https://sis.rutgers.edu/soc/api/courses.json",
    params={"year": "2026", "term": "1", "campus": "NB", "subject": "198"}
)

data = r.json()
print(json.dumps(data[0], indent=2))