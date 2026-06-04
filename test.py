import requests

try:
    response = requests.post(
        'http://127.0.0.1:5001/chat',
        json={'message': 'hi'},
        headers={'Content-Type': 'application/json'}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
