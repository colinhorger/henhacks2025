import os
import json
import random
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from google import genai  # Import the Google genai package

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize the Gemini client correctly
# The 'configure' method doesn't exist, so we create the client directly
genai_client = genai.Client(api_key=GEMINI_API_KEY)

# In-memory data store (replace with a database in production)
users = {}
tasks = {}
hobby_categories = [
    "art", "music", "writing", "cooking", "gardening", "fitness", 
    "photography", "learning", "meditation", "reading"
]

# Egg states
EGG_STATES = {
    0: "intact",    # New egg
    1: "crack_1",   # One task completed
    2: "crack_2",   # Two tasks completed
    3: "hatched"    # All tasks completed
}

# User model
class User:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.completed_eggs = 0
        self.current_tasks = []
        self.current_egg_state = 0
        self.completed_tasks = 0

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "completed_eggs": self.completed_eggs,
            "current_tasks": self.current_tasks,
            "current_egg_state": self.current_egg_state,
            "completed_tasks": self.completed_tasks,
            "egg_state_name": EGG_STATES[self.current_egg_state]
        }
    
    def complete_task(self, task_id):
        if task_id in self.current_tasks:
            self.current_tasks.remove(task_id)
            self.completed_tasks += 1
            
            # Update egg state
            if self.completed_tasks % 3 == 0:
                # Egg has hatched
                self.completed_eggs += 1
                self.current_egg_state = 0  # Reset to new egg
            else:
                # Update crack level
                self.current_egg_state = self.completed_tasks % 3
            
            return True
        return False
    def remove_task(self, task_id):
        if task_id in self.current_tasks:
            self.current_tasks.remove(task_id)
            return True
        else:
            return False
        


# Generate a task using Gemini API
def generate_task(hobby_category):
    prompt = f"Generate a single engaging task related to {hobby_category} that can be completed in 15-30 minutes. The task should be specific, actionable, and beginner-friendly. Only return the task description without any additional text."
    
    try:
        # Use the client directly to generate content, matching quick_test.py
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error generating task: {e}")
        # Fallback for when API calls fail
        fallback_tasks = {
            "art": "Sketch an object in your room using only one continuous line.",
            "music": "Find a song you like and try to hum or whistle along with the melody.",
            "writing": "Write a 6-word story about your day.",
            "cooking": "Create a new spice blend with what you have in your kitchen.",
            "gardening": "Identify three plants in your neighborhood and learn their names.",
            "fitness": "Do a 7-minute workout of jumping jacks, push-ups, and sit-ups.",
            "photography": "Take 5 photos of the same object from different angles.",
            "learning": "Learn and practice 5 new words in a language you're interested in.",
            "meditation": "Do a 5-minute mindfulness exercise focusing on your breathing.",
            "reading": "Read one short article on a topic you know little about."
        }
        return fallback_tasks.get(hobby_category, "Try something new for 15 minutes today.")


# API Routes
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    user_id = str(len(users) + 1)  # Simple ID generation
    new_user = User(user_id, data['username'])
    users[user_id] = new_user
    
    # Generate initial tasks
    generate_new_tasks_for_user(user_id)
    
    return jsonify(new_user.to_dict()), 201

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    if user_id in users:
        return jsonify(users[user_id].to_dict())
    return jsonify({"error": "User not found"}), 404

@app.route('/api/tasks/<user_id>', methods=['GET'])
def get_tasks(user_id):
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    
    user = users[user_id]
    user_tasks = []
    
    for task_id in user.current_tasks:
        if task_id in tasks:
            user_tasks.append({
                "task_id": task_id,
                "description": tasks[task_id]["description"],
                "category": tasks[task_id]["category"]
            })
    
    return jsonify(user_tasks)

def generate_new_tasks_for_user(user_id):
    if user_id not in users:
        return False
    
    user = users[user_id]
    
    # Clear current tasks if any
    user.current_tasks = []
    
    # Generate 3 new tasks from different categories
    selected_categories = random.sample(hobby_categories, 3)
    
    for category in selected_categories:
        task_description = generate_task(category)
        task_id = str(len(tasks) + 1)  # Simple ID generation
        
        tasks[task_id] = {
            "task_id": task_id,
            "description": task_description,
            "category": category
        }
        
        user.current_tasks.append(task_id)
    
    return True

@app.route('/api/tasks/<user_id>/complete/<task_id>', methods=['POST'])
def complete_task(user_id, task_id):
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    
    user = users[user_id]
    if user.complete_task(task_id):
        response = {
            "success": True,
            "egg_state": user.current_egg_state,
            "egg_state_name": EGG_STATES[user.current_egg_state],
            "completed_eggs": user.completed_eggs,
            "completed_tasks": user.completed_tasks
        }
        
        # If all tasks are completed, generate new ones
        if not user.current_tasks:
            generate_new_tasks_for_user(user_id)
            response["new_tasks_generated"] = True
        
        return jsonify(response)
    
    return jsonify({"error": "Task not found or already completed"}), 400

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    leaderboard = sorted(
        [user.to_dict() for user in users.values()],
        key=lambda x: x["completed_eggs"],
        reverse=True
    )
    return jsonify(leaderboard)

@app.route('/')
def index():
    return render_template('index.html')

# Main entry point
if __name__ == '__main__':
    app.run(debug=True)