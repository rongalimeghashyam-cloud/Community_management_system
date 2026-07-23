import os
import json
import time
import firebase_admin
from firebase_admin import credentials, firestore

def get_settings():
    try:
        with open('config/settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_settings(new_settings):
    settings = get_settings()
    settings.update(new_settings)
    os.makedirs('config', exist_ok=True)
    with open('config/settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

db = None
try:
    cred = credentials.Certificate('config/firebase-credentials.json')
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print("Firebase initialization skipped or failed:", e)

def get_tickets():
    if db:
        try:
            tickets = {"maintenance": [], "security": []}
            # Fetch maintenance
            m_docs = db.collection('tickets_maintenance').limit(20).stream()
            for doc in m_docs:
                tickets["maintenance"].append(doc.to_dict())
            # Fetch security
            s_docs = db.collection('tickets_security').limit(20).stream()
            for doc in s_docs:
                tickets["security"].append(doc.to_dict())
            return tickets
        except Exception as e:
            print("Error fetching from Firebase:", e)
            
    # Fallback to local
    try:
        with open('config/tickets.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"maintenance": [], "security": []}

def save_ticket(department, ticket_data):
    if department == 'security':
        if 'id' not in ticket_data:
            ticket_data['id'] = f"S{int(time.time())}"
    else:
        if 'id' not in ticket_data:
            ticket_data['id'] = f"{int(time.time())}"
            
    if db:
        try:
            collection_name = f'tickets_{department}'
            db.collection(collection_name).document(ticket_data['id']).set(ticket_data)
        except Exception as e:
            print("Error saving to Firebase:", e)
            
    # Save locally as fallback
    tickets = get_tickets()
    if department not in tickets:
        tickets[department] = []
        
    existing_ids = [t.get('id') for t in tickets[department]]
    if ticket_data['id'] not in existing_ids:
        tickets[department].insert(0, ticket_data)
        os.makedirs('config', exist_ok=True)
        with open('config/tickets.json', 'w') as f:
            json.dump(tickets, f, indent=4)
