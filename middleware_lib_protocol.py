import random
import time
import threading
import certifi
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template
from pymongo import MongoClient
import secrets
import pytz
import logging
import networkx as nx
import matplotlib.pyplot as plt
import networkx as nx
from pyvis.network import Network
from locust import HttpUser, task, between
import psutil


app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = secrets.token_hex(16)  # Generate a random secret key

port = 27017
#uri = "mongodb+srv://laurence:kim@calendar-cluster.oppdc.mongodb.net/?retryWrites=true&w=majority&appName=calendar-cluster"
# uri = "mongodb+srv://Cluster94896:123@cluster94896.eyktwpb.mongodb.net/"
# client = MongoClient(uri, tlsCAFile=certifi.where())

client = MongoClient('localhost', 27017)
db = client.larger_calendar
# db = client.calendar


class Middleware:
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
    def __init__(self):
        self.events = set()
        self.user_db = client.larger_calendar

    def authenticate_user(self, username, password):
        logger.debug(f"Attempting to authenticate user: {username}")
        user = self.user_db.users.find_one({"username": username, "password": password})
        if user:
            logger.debug(f"Authentication successful for user: {username}")
            return True
        else:
            logger.debug(f"Authentication failed for user: {username}")
            return False

    # Middleware LIB functions
    def add_event(self, title, description, start_time, end_time, guests, creator):
        event_id = uuid.uuid4()
        self.events.add(str(event_id))
        dependencies = self.get_dependencies(creator)
        lower_bound, upper_bound = self.initialize_bounds()
        event = {
            "event_id": str(event_id),
            "membership_list": {element: 'alive' for element in self.events},
            "gossip_interval": 5,
            "heartbeat_interval": 1,
            "last_heartbeat": {str(event_id): time.time()},
            "event_reputations": {str(event_id): random.randint(0, 10)},
            "aggregation_interval": 1,
            "title": title,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "guests": guests,
            "comments": [],
            "creator": creator,
            "dependencies": dependencies,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "CommitBeforeQueue": [],
            "CommitAfterQueue": [],
            "timestamp": datetime.utcnow()
        }
        db.events.insert_one(event)
        start_background_thread(event)
        return event_id

    def update_event(self, event_id, title=None, description=None, start_time=None, end_time=None, guests=None, comments=None):
        event = db.events.find_one({"event_id": event_id})
        if not event:
            return None
        
        # Adjust bounds dynamically based on dependencies and current operations
        new_lower_bound, new_upper_bound = self.calculate_dynamic_bounds(event)

        new_values = {
            "$set": {
                "title": title or event['title'],
                "description": description or event['description'],
                "start_time": start_time or event['start_time'],
                "end_time": end_time or event['end_time'],
                "guests": guests or event['guests'],
                "comments": comments or event['comments'],
                "dependencies": self.update_dependencies(event),
                "lower_bound": new_lower_bound,
                "upper_bound": new_upper_bound,
                "timestamp": datetime.utcnow()
            }
        }
        db.events.update_one({"event_id": event_id}, new_values)
        return event_id

    def get_event(self, event_id):
        return db.events.find_one({"event_id": event_id})

    def get_dependencies(self, creator):
        dependencies = []

        # Find all recent events created by the user
        created_events = db.events.find({"creator": creator}).sort("timestamp", -1)

        # Find all recent events where the user is a guest
        guest_events = db.events.find({"guests": creator}).sort("timestamp", -1)

        for event in created_events:
            dependencies.append({
                "event_id": event["event_id"],
                "timestamp": event["timestamp"]
            })

        for event in guest_events:
            dependencies.append({
                "event_id": event["event_id"],
                "timestamp": event["timestamp"]
            })

        if dependencies:
            # Optionally sort and pick the most recent events if needed
            dependencies = sorted(dependencies, key=lambda x: x['timestamp'], reverse=True)

        return dependencies if dependencies else [{
            "event_id": None,
            "timestamp": datetime.utcnow().isoformat()
        }]

    def update_dependencies(self, event):
        dependencies = event['dependencies']
        dependencies['last_event_id'] = str(event['event_id'])
        dependencies['timestamp'] = datetime.utcnow().isoformat()
        return dependencies

    def resolve_dependencies(self, dependencies):
        last_event_id = dependencies.get('last_event_id')
        if last_event_id:
            last_event = db.events.find_one({"event_id": last_event_id})
            if last_event:
                # Check if the event is fully resolved
                if self.check_event_resolved(last_event):
                    return True
                else:
                    # Recursively resolve dependencies
                    return self.resolve_dependencies(last_event['dependencies'])
        return True

    def check_event_resolved(self, event):
        dependencies = event.get('dependencies', {})
        last_event_id = dependencies.get('last_event_id')
        if last_event_id:
            last_event = db.events.find_one({"event_id": last_event_id})
            if last_event:
                required_fields = ['title', 'description', 'timestamp']  # Example of necessary fields
                if all(field in last_event for field in required_fields):
                    # Recursively check if the last event's dependencies are resolved
                    return self.check_event_resolved(last_event)
                else:
                    return False
        return True

    # Middleware login functions
    def authenticate_user(self, username, password):
        user = db.users.find_one({"username": username, "password": password})
        return user is not None
    
    # Middleware gossip functions
    def update_gossip(self, event_id, membership_list, last_heartbeat, event_reputations):
        event = db.events.find_one({"event_id": event_id})
        if not event:
            return None
        new_values = {
            "$set": {
                "membership_list": membership_list,
                "gossip_interval": 5,
                "heartbeat_interval": 1,
                "last_heartbeat": last_heartbeat,
                "event_reputations": event_reputations,
                "aggregation_interval": 1,
            }
        }
        db.events.update_one({"event_id": event_id}, new_values)
        return event_id

    # Middleware dependency graph visualization functions
    # def build_dependency_graph(self):
    #     G = nx.DiGraph()

    #     # Traverse all events to build the graph
    #     for event in db.events.find():
    #         event_id = event["event_id"]
    #         G.add_node(event_id, label=event.get("title", "No Title"))

    #         dependencies = event.get("dependencies", [])
    #         for dep in dependencies:
    #             dep_event_id = dep.get("event_id")
    #             if dep_event_id:
    #                 G.add_node(dep_event_id)
    #                 G.add_edge(dep_event_id, event_id)  # Directed edge from dependency to event

    #     return G

    # def plot_dependency_graph(self):
    #     G = self.build_dependency_graph()

    #     pos = nx.spring_layout(G)  # Layout for visualization
    #     plt.figure(figsize=(12, 8))

    #     # Draw nodes with labels
    #     nx.draw(G, pos, with_labels=True, labels=nx.get_node_attributes(G, 'label'), node_size=3000, node_color="skyblue", font_size=10, font_weight="bold", arrowsize=20)
    #     nx.draw_networkx_edge_labels(G, pos, edge_labels={(u, v): "depends" for u, v in G.edges()}, font_color='red')

    #     plt.title("Event Dependency Graph")
    #     plt.show()

    def build_dependency_graph(self):
        G = nx.DiGraph()

        # Fetch all events from the database
        events = list(db.events.find({}, {"event_id": 1, "title": 1, "dependencies": 1}))

        # Traverse all events to build the graph
        for event in events:
            event_id = event["event_id"]
            G.add_node(event_id, label=event.get("title", "No Title"))

            dependencies = event.get("dependencies", [])
            for dep in dependencies:
                dep_event_id = dep.get("event_id")
                if dep_event_id:
                    G.add_node(dep_event_id)
                    G.add_edge(dep_event_id, event_id)  # Directed edge from dependency to event

        return G

    def visualize_graph(self):
        G = self.build_dependency_graph()

        # Use Pyvis for interactive visualization
        net = Network(notebook=True, directed=True)
        net.from_nx(G)

        # Save and display the graph
        net.show("event_dependency_graph.html")
# concurrency control dynamic timestamp protocol 
    def calculate_dynamic_bounds(self, event):
        lower_bound = event.get("lower_bound", datetime.utcnow())
        upper_bound = event.get("upper_bound", datetime.utcnow() + self.get_time_delta())
        
        # Adjust based on dependencies
        for dependency in event["dependencies"]:
            dep_event = self.get_event(dependency["event_id"])
            if dep_event:
                lower_bound = max(lower_bound, dep_event["upper_bound"])
                upper_bound = min(upper_bound, dep_event["lower_bound"])
        
        return lower_bound, upper_bound

    def initialize_bounds(self):
        # Initialize lower and upper bounds for new events
        lower_bound = datetime.utcnow()
        upper_bound = lower_bound + self.get_time_delta()
        return lower_bound, upper_bound

    def get_time_delta(self):
        # Monitor CPU load as a proxy for system load
        cpu_load = psutil.cpu_percent()
        
        # Adjust delta based on load (example logic)
        if cpu_load > 75:
            return self.base_delta * 0.5  # Reduce delta by half under high load
        elif cpu_load < 25:
            return self.base_delta * 1.5  # Increase delta by 50% under low load
        else:
            return self.base_delta  # Use base delta under normal load

middleware = Middleware()
middleware.visualize_graph()

# COMMUNICATION MIDDLEWARE ROUTE FUNCTIONS
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

@app.route('/api/my_events', methods=['GET'])
def get_my_events():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session['username']
    current_time = datetime.utcnow()
    print(f"Current UTC time: {current_time}")

    events = list(db.events.find({
        "$or": [
            {"creator": username},
            {"guests": username}
        ],
        "start_time": {"$gte": current_time}
    }).sort("start_time", 1))

    print(f"Number of events found: {len(events)}")
    for event in events:
        event["_id"] = str(event["_id"])
        print(f"Event: {event}")

    return jsonify(events)

@app.route('/api/my_week_events', methods=['GET'])
def get_my_week_events():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session['username']
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    
    # Get the start of the current week (Sunday)
    today = datetime.utcnow().replace(tzinfo=pytz.utc)
    start_of_week = today - timedelta(days=today.weekday() + 1)
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get the end of the current week (Saturday)
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
    print("start_of_week = ", start_of_week)
    print("end_of_week = ", end_of_week)
    # Find events where the user is the creator or a guest and the event is within the current week
    events = list(db.events.find({
        "$or": [
            {"creator": username},
            {"guests": username}
        ],
        "start_time": {"$gte": start_of_week.strftime("%Y-%m-%dT%H:%M:%SZ"), "$lte": end_of_week.strftime("%Y-%m-%dT%H:%M:%SZ")}
    }).sort("start_time", 1))

    # Send UTC times to the frontend
    for event in events:
        event["_id"] = str(event["_id"])
        #event["start_time"] = event["start_time"].isoformat()
        #event["end_time"] = event["end_time"].isoformat()
        event["membership_list"] = {element: 'alive' for element in middleware.events}
        if event["event_id"] not in middleware.events:
            middleware.events.add(event["event_id"])
            start_background_thread(event)
    return jsonify(events)

# Middleware to measure latency
@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def log_request(response):
    latency = time.time() - request.start_time
    app.logger.info(f"Request latency: {latency:.4f} seconds")
    return response

# Endpoint for generating load
@app.route('/api/generate_load', methods=['POST'])
def generate_load():
    data = request.json
    num_requests = data['num_requests']
    for _ in range(num_requests):
        create_random_event()
    return jsonify({"message": "Load generated"}), 200

# Function to create random event
def create_random_event():
    event_id = str(uuid.uuid4())
    title = f"Event {event_id[:8]}"
    description = f"Description for {title}"
    start_time = datetime.utcnow() + timedelta(days=random.randint(0, 30))
    end_time = start_time + timedelta(hours=random.randint(1, 4))
    guests = random.sample(users, random.randint(1, 5))
    creator = random.choice(users)
    dependencies = []

    event = {
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
    db.events.insert_one(event)


# LOGIN MIDDLEWARE ROUTE FUNCTIONS
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
    print("gossip used")
    while True:
        # Select a random subset of nodes to gossip with
        subset = random.sample(list(node["membership_list"].keys()), min(3, len(node["membership_list"])))
        middleware.update_gossip(node["event_id"], node["membership_list"], node["last_heartbeat"], node["event_reputations"])
        for peer in subset:
            send_gossip(node, peer)
            aggregate_reputation_scores(node) 
        time.sleep(node["gossip_interval"] * 2)

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

def aggregate_reputation_scores(node):
    print("aggregate_reputation_scores used")
    # Periodically aggregate reputation scores
    while True:
        for event_id in node["event_reputations"]:
            scores = get_all_reputation_scores(node, event_id)
            node["event_reputations"][event_id] = sum(scores)  
            time.sleep(node["aggregation_interval"])

def get_all_reputation_scores(node, event_id):
    print("get_all_reputation_scores used")
    # Retrieve reputation scores for a given event from all nodes
    all_scores = []
    for peer_id in node["membership_list"].keys():
        peer_node = get_node_by_id(peer_id)
        if peer_node and event_id in peer_node["event_reputations"]:
            all_scores.append(peer_node["event_reputations"][event_id])
    return all_scores


#@app.before_first_request
def start_background_thread(node):
    threading.Thread(target=gossip, args=(node,)).start()
    threading.Thread(target=monitor_heartbeats, args=(node,)).start()
    threading.Thread(target=send_heartbeat, args=(node,)).start()


if __name__ == '__main__':
    app.run(debug=True)
