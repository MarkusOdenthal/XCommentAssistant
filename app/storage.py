import json
from flask import current_app as app

def read_data():
    try:
        with open(app.config['DATA_FILE'], 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print("Data file not found.")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON.")
        return None

def write_data(data):
    try:
        with open(app.config['DATA_FILE'], 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
    except IOError as e:
        print(f"Failed to write data: {e}")