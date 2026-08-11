import os
import json
import time

HAS_FIREBASE = False
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    HAS_FIREBASE = True
except ImportError:
    print("firebase_admin not installed. System will use local JSON database.")


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

def get_api_keys():
    settings = get_settings()
    keys = settings.get("api_keys", {})
    # Combine with env vars if not set in settings
    combined_keys = {
        "openai": keys.get("openai") or os.environ.get("OPENAI_API_KEY", ""),
        "gemini": keys.get("gemini") or os.environ.get("GEMINI_API_KEY", ""),
        "groq": keys.get("groq") or os.environ.get("GROQ_API_KEY", ""),
        "qwen": keys.get("qwen") or os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY", ""),
        "anthropic": keys.get("anthropic") or os.environ.get("ANTHROPIC_API_KEY", ""),
        "deepseek": keys.get("deepseek") or os.environ.get("DEEPSEEK_API_KEY", ""),
        "ollama_url": keys.get("ollama_url") or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    }
    return combined_keys

def mask_key(key):
    if not key:
        return ""
    if len(key) <= 8:
        return "********"
    return key[:4] + "..." + key[-4:]

def get_masked_api_keys():
    keys = get_api_keys()
    masked = {}
    for provider, val in keys.items():
        if provider == "ollama_url":
            masked[provider] = val
        else:
            masked[provider] = mask_key(val)
    return masked

def save_api_keys(new_keys):
    settings = get_settings()
    current_keys = settings.get("api_keys", {})
    for provider, val in new_keys.items():
        if val is not None:
            # If user sent masked key string (e.g. sk-p...1234), keep existing key if unmodified
            if "..." in val and provider in current_keys and mask_key(current_keys[provider]) == val:
                continue
            current_keys[provider] = val.strip()
    settings["api_keys"] = current_keys
    save_settings(settings)
    return get_masked_api_keys()

db = None
if HAS_FIREBASE:
    try:
        if os.environ.get("FIREBASE_CREDENTIALS"):
            cred_dict = json.loads(os.environ.get("FIREBASE_CREDENTIALS"))
            cred = credentials.Certificate(cred_dict)
        else:
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
            m_docs = db.collection('tickets_maintenance').limit(50).stream()
            for doc in m_docs:
                tickets["maintenance"].append(doc.to_dict())
            # Fetch security
            s_docs = db.collection('tickets_security').limit(50).stream()
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
            db.collection(collection_name).document(str(ticket_data['id'])).set(ticket_data)
        except Exception as e:
            print("Error saving to Firebase:", e)
            
    # Save locally as fallback
    tickets = get_tickets()
    if department not in tickets:
        tickets[department] = []
        
    existing_ids = [str(t.get('id')) for t in tickets[department]]
    if str(ticket_data['id']) not in existing_ids:
        tickets[department].insert(0, ticket_data)
        os.makedirs('config', exist_ok=True)
        with open('config/tickets.json', 'w') as f:
            json.dump(tickets, f, indent=4)

def update_ticket_status(ticket_id, department, new_status):
    if db:
        try:
            collection_name = f'tickets_{department}'
            db.collection(collection_name).document(str(ticket_id)).update({"status": new_status})
        except Exception as e:
            print("Error updating Firebase ticket:", e)

    # Local fallback
    tickets = get_tickets()
    dept_tickets = tickets.get(department, [])
    updated = False
    for t in dept_tickets:
        if str(t.get('id')) == str(ticket_id):
            t['status'] = new_status
            updated = True
            break
    if updated:
        os.makedirs('config', exist_ok=True)
        with open('config/tickets.json', 'w') as f:
            json.dump(tickets, f, indent=4)
    return updated

def log_agent_query(query, model_used, response, status="success", duration_sec=0.0):
    log_entry = {
        "id": f"LOG-{int(time.time()*1000)}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "query": query,
        "model": model_used,
        "response": response[:300] + "..." if len(response) > 300 else response,
        "status": status,
        "duration": round(duration_sec, 2)
    }
    
    logs = get_query_logs()
    logs.insert(0, log_entry)
    logs = logs[:100]  # keep latest 100 logs
    
    os.makedirs('config', exist_ok=True)
    with open('config/query_logs.json', 'w') as f:
        json.dump(logs, f, indent=4)

def get_query_logs():
    try:
        with open('config/query_logs.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

