import threading
import requests
import random
import time
from pymongo import MongoClient
import certifi

# Connect to the MongoDB database
client = MongoClient('localhost', 27017)
user_db = client.larger_calendar

# Retrieve the usernames
def get_usernames():
    users = user_db.users.find({}, {"username": 1, "_id": 0})
    return [user["username"] for user in users]

# Simulate user activity
def simulate_user_activity(username):
    session = requests.Session()
    login_response = session.post('http://localhost:5000/login', json={'username': username, 'password': 'password'})
    login_data = login_response.json()
    
    if login_data.get("success"):
        for _ in range(10):
            response = session.post('http://localhost:5000/api/events', json={
                'title': f'Event by {username}',
                'description': 'Test event',
                'start_time': '2024-06-07T18:00',
                'end_time': '2024-06-07T19:00',
                'guests': ['guest1', 'guest2']
            })
            print(response.json())
            time.sleep(random.uniform(0.1, 0.5))
    else:
        print(f"Login failed for {username}: {login_data}")

if __name__ == "__main__":
    usernames = get_usernames()
    print(f"Retrieved usernames: {usernames}")
    threads = []

    for username in usernames:
        t = threading.Thread(target=simulate_user_activity, args=(username,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
