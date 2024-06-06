import random
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('localhost', 27017)
db = client.larger_calendar

# Fetch all users from the database
users = list(db.users.find({}, {"username": 1}))

# Function to generate a random event
def generate_random_event(usernames):
    event_id = str(uuid.uuid4())
    title = f"Event {event_id[:8]}"
    description = f"Description for {title}"
    start_time = datetime.utcnow() + timedelta(days=random.randint(0, 30))
    end_time = start_time + timedelta(hours=random.randint(1, 4))
    guests = random.sample(usernames, random.randint(1, 5))
    creator = random.choice(usernames)
    dependencies = []

    # Optionally, add some dependencies from existing events
    existing_events = list(db.events.find().limit(10))
    if existing_events:
        for _ in range(random.randint(0, 3)):
            dep_event = random.choice(existing_events)
            dependencies.append({
                "event_id": dep_event["event_id"],
                "timestamp": dep_event["timestamp"]
            })

    return {
        "event_id": event_id,
        "title": title,
        "description": description,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "guests": guests,
        "creator": creator,
        "dependencies": dependencies,
        "timestamp": datetime.utcnow().isoformat()
    }

# Generate and insert 200 random events
usernames = [user["username"] for user in users]
for _ in range(200):
    event = generate_random_event(usernames)
    db.events.insert_one(event)

print("Inserted 200 random events.")
