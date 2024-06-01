import random
import time
import threading
import certifi
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template
from pymongo import MongoClient
import secrets

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = secrets.token_hex(16)  # Generate a random secret key

port = 27017
uri = "mongodb+srv://Cluster94896:123@cluster94896.eyktwpb.mongodb.net/"
client = MongoClient(uri, tlsCAFile=certifi.where())

#client = MongoClient('localhost', 27017)
db = client.calendar

class Middleware:
    def add_event(self, title, description, start_time, end_time, guests, creator):
        event_id = uuid.uuid4()
        dependencies = self.get_dependencies(creator)
        event = {
            "event_id": str(event_id),
	        "membership_list": {str(event_id): 'alive'},
	        "gossip_interval": 5,
	        "heartbeat_interval": 1,
	        "last_heartbeat": {str(event_id): time.time()},
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
        start_background_thread(event)
        #print(event)
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

    def authenticate_user(self, username, password):
        user = db.users.find_one({"username": username, "password": password})
        return user is not None

middleware = Middleware()

@app.route('/api/events', methods=['POST'])
def add_event():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    title = data['title']
    description = data['description']
    start_time = data['start_time']
    end_time = data['end_time']
    guests = data['guests']
    creator = session['username']
    event_id = middleware.add_event(title, description, start_time, end_time, guests, creator)
    return jsonify({"event_id": str(event_id)})

@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

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
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    event = middleware.get_event(event_id)
    if event:
        return jsonify(event)
    else:
        return jsonify({"error": "Event not found"}), 404

@app.route('/')
def index():
    if 'username' not in session:
        print("No username in session. Redirecting to login.")
        return redirect(url_for('login'))
    print("Username in session. Rendering index.")
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        data = request.json
        username = data['username']
        password = data['password']
        if middleware.authenticate_user(username, password):
            session['username'] = username
            print("Login successful. Redirecting to index.")
            return jsonify({"success": True, "username": username})
        else:
            error = "Invalid credentials"
            print("Invalid credentials. Showing error.")
            return jsonify({"success": False, "error": error})
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


def gossip(node):
    while True:
        # Select a random subset of nodes to gossip with
        subset = random.sample(list(node["membership_list"].keys()), min(3, len(node["membership_list"])))
        for peer in subset:
            send_gossip(node, peer)
        time.sleep(node["gossip_interval"])

def send_gossip(node, peer):
    # Simulate sending gossip to a peer
    peer_node = get_node_by_id(peer)
    if peer_node:
        merge_membership_lists(node, peer_node)

def merge_membership_lists(node, peer_node):
    # Merge membership lists
    for peer_id, status in peer_node["membership_list"].items():
        if peer_id not in node["membership_list"]:
            node["membership_list"][peer_id] = status
        elif node["membership_list"][peer_id] == 'alive' and status == 'dead':
            node["membership_list"][peer_id] = 'dead'
        elif node["membership_list"][peer_id] == 'suspected' and status == 'alive':
            node["membership_list"][peer_id] = 'alive'
    # Update heartbeat timestamps
    for peer_id in peer_node["last_heartbeat"]:
        if peer_id not in node["last_heartbeat"] or peer_node["last_heartbeat"][peer_id] > node["last_heartbeat"][peer_id]:
            node["last_heartbeat"][peer_id] = peer_node["last_heartbeat"][peer_id]

def get_node_by_id(event_id):
    # Function to retrieve a node object by its ID
    return middleware.get_event(event_id)

def monitor_heartbeats(node):
    while True:
        current_time = time.time()
        for peer_id in list(node["last_heartbeat"].keys()):
            if current_time - node["last_heartbeat"][peer_id] > node["gossip_interval"] * 2:
                node["membership_list"][peer_id] = 'suspected'
            if current_time - node["last_heartbeat"][peer_id] > node["gossip_interval"] * 4:
                node["membership_list"][peer_id] = 'dead'
        time.sleep(node["heartbeat_interval"])

def send_heartbeat(node):
    while True:
        node["last_heartbeat"][node["event_id"]] = time.time()
        for peer_id in node["membership_list"].keys():
            if peer_id != node["event_id"]:
                peer_node = get_node_by_id(peer_id)
                if peer_node:
                    peer_node["last_heartbeat"][node["event_id"]] = time.time()
        time.sleep(node["heartbeat_interval"])

#@app.before_first_request
def start_background_thread(node):
    threading.Thread(target=gossip, args=(node,)).start()
    threading.Thread(target=monitor_heartbeats, args=(node,)).start()
    threading.Thread(target=send_heartbeat, args=(node,)).start()



if __name__ == '__main__':
    app.run(debug=True)




