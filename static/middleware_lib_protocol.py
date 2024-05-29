import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient

app = Flask(__name__, static_folder='static')

client = MongoClient('localhost', 27017)
db = client.calendar

class Middleware:
    def add_event(self, title, description, start_time, end_time, guests, creator):
        event_id = uuid.uuid4()
        dependencies = self.get_dependencies(creator)
        event = {
            "event_id": str(event_id),
            "title": title,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "guests": guests,
            "comments": [],
            "creator": creator,
            "dependencies": dependencies,
            "timestamp": datetime.utcnow()
        }
        db.events.insert_one(event)
        return event_id

    def update_event(self, event_id, title=None, description=None, start_time=None, end_time=None, guests=None, comments=None):
        event = db.events.find_one({"event_id": event_id})
        if not event:
            return None
        new_values = {
            "$set": {
                "title": title or event['title'],
                "description": description or event['description'],
                "start_time": start_time or event['start_time'],
                "end_time": end_time or event['end_time'],
                "guests": guests or event['guests'],
                "comments": comments or event['comments'],
                "dependencies": self.update_dependencies(event),
                "timestamp": datetime.utcnow()
            }
        }
        db.events.update_one({"event_id": event_id}, new_values)
        return event_id

    def get_event(self, event_id):
        return db.events.find_one({"event_id": event_id})

    def get_dependencies(self, creator):
        return {"last_event_id": str(uuid.uuid4()), "timestamp": datetime.utcnow().isoformat()}

    def update_dependencies(self, event):
        dependencies = event['dependencies']
        dependencies['last_event_id'] = str(event['event_id'])
        dependencies['timestamp'] = datetime.utcnow().isoformat()
        return dependencies

    def resolve_dependencies(self, dependencies):
        return True

middleware = Middleware()

@app.route('/api/events', methods=['POST'])
def add_event():
    data = request.json
    title = data['title']
    description = data['description']
    start_time = data['start_time']
    end_time = data['end_time']
    guests = data['guests']
    creator = data['creator']
    event_id = middleware.add_event(title, description, start_time, end_time, guests, creator)
    return jsonify({"event_id": str(event_id)})

@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    data = request.json
    title = data.get('title')
    description = data.get('description')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    guests = data.get('guests')
    comments = data.get('comments')
    try:
        updated_event_id = middleware.update_event(event_id, title, description, start_time, end_time, guests, comments)
        if updated_event_id:
            return jsonify({"event_id": str(updated_event_id)})
        else:
            return jsonify({"error": "Event not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/events/<event_id>', methods=['GET'])
def get_event(event_id):
    event = middleware.get_event(event_id)
    if (event):
        return jsonify(event)
    else:
        return jsonify({"error": "Event not found"}), 404

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True)
