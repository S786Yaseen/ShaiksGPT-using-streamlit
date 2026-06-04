import requests
import json

api_key = "740311d2537c68d3d76de33de8c68a5e0a64108176c0c5742107c17bfaf697a3"
url = "https://serpapi.com/search"
params = {
    "engine": "google",
    "q": "current year",
    "api_key": api_key
}

try:
    response = requests.get(url, params=params)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    if 'organic_results' in data:
        print("Success! SerpAPI organic results found.")
    else:
        print("Response:", json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")
