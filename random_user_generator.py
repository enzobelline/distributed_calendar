import json
import random
import uuid

# Existing users
users = [
    {
        "_id": {"$oid": "6658e9f23cda412a98cdcdf6"},
        "username": "laurence",
        "password": "abc"
    },
    {
        "_id": {"$oid": "665e7b3fc9da1f34fc7a3b2d"},
        "username": "james",
        "password": "liang"
    }
]

# List of sample usernames for generation
sample_usernames = [
    "alex", "sam", "chris", "pat", "taylor", "jordan", "morgan", "casey", 
    "alexis", "blake", "ashley", "jordan", "charlie", "dana", "erin", "frank", 
    "george", "harry", "isabel", "jack", "kim", "lisa", "mike", "nina", "oliver", 
    "peter", "quincy", "rachel", "steve", "tina", "ursula", "victor", "wendy", 
    "xander", "yasmin", "zach", "bella", "claire", "david", "emma"
]
# print(len(sample_usernames))

# Generate 40 new users with the password "a"
for i in range(40):
    new_user = {
        "_id": {"$oid": str(uuid.uuid4().hex[:24])},
        "username": random.choice(sample_usernames),
        "password": "a"
    }
    users.append(new_user)

# Save the updated user list to a JSON file in the current directory
with open("users.json", "w") as file:
    json.dump(users, file, indent=2)

print("Users have been saved to users.json")
