import os
import yaml
from flask import Flask, request, jsonify, render_template
from crewai import Agent, Task, Crew, Process
from crewai import LLM
import firebase_admin
from firebase_admin import credentials, firestore
from tools import check_database_for_duplicates, raise_ticket

def load_yaml(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

app = Flask(__name__)

import json

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
    import time
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


def get_crew(provider=None, api_key=None):
    agents_config = load_yaml('config/agents.yaml')
    tasks_config = load_yaml('config/tasks.yaml')

    settings = get_settings()
    
    active_llm = None
    if provider:
        if provider == 'gemini' and api_key:
            active_llm = LLM(model="gemini/gemini-1.5-flash", api_key=api_key)
        elif provider == 'groq' and api_key:
            active_llm = LLM(model="groq/llama-3.1-8b-instant", api_key=api_key)
        elif provider == 'openai' and api_key:
            active_llm = LLM(model="gpt-4o-mini", api_key=api_key)
        elif provider == 'ollama':
            active_llm = LLM(model="ollama/llama3.2", base_url="http://localhost:11434")

    if not active_llm:
        # Check settings
        if settings.get('gemini_api_key'):
            active_llm = LLM(model="gemini/gemini-1.5-flash", api_key=settings.get('gemini_api_key'))
        elif settings.get('openai_api_key'):
            active_llm = LLM(model="gpt-4o-mini", api_key=settings.get('openai_api_key'))

    # Detect which API key is available in the Render Environment
    if not active_llm:
        if not os.environ.get("RENDER"):
            active_llm = LLM(model="ollama/llama3.2", base_url="http://localhost:11434")
        elif os.environ.get("GEMINI_API_KEY"):
            active_llm = LLM(model="gemini/gemini-1.5-flash", api_key=os.environ.get("GEMINI_API_KEY"))
        elif os.environ.get("GROQ_API_KEY"):
            active_llm = LLM(model="groq/llama-3.1-8b-instant", api_key=os.environ.get("GROQ_API_KEY"))
        elif os.environ.get("OPENAI_API_KEY"):
            active_llm = LLM(model="gpt-4o-mini", api_key=os.environ.get("OPENAI_API_KEY"))
        else:
            return None, "No API Key found! Please add GEMINI_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY to Render Environment Variables, or provide one in the interface."

    triage_agent = Agent(
        config=agents_config['triage_agent'],
        llm=active_llm,
        verbose=True
    )
    validation_agent = Agent(
        config=agents_config['validation_agent'],
        llm=active_llm,
        tools=[check_database_for_duplicates],
        verbose=True
    )
    ticketing_agent = Agent(
        config=agents_config['ticketing_agent'],
        llm=active_llm,
        tools=[raise_ticket],
        verbose=True
    )
    
    task_triage = Task(
        config=tasks_config['task_triage'],
        agent=triage_agent
    )
    task_validation = Task(
        config=tasks_config['task_validation'],
        agent=validation_agent
    )
    task_create_ticket = Task(
        config=tasks_config['task_create_ticket'],
        agent=ticketing_agent
    )
    
    community_crew = Crew(
        agents=[triage_agent, validation_agent, ticketing_agent],
        tasks=[task_triage, task_validation, task_create_ticket],
        process=Process.sequential
    )
    return community_crew, None

@app.route("/", methods=["GET"])
def home():
    settings = get_settings()
    if settings.get('gemini_api_key'):
        llm_name = "Google Gemini 1.5 Flash (Settings)"
    elif settings.get('openai_api_key'):
        llm_name = "OpenAI GPT-4o-mini (Settings)"
    elif os.environ.get("GEMINI_API_KEY"):
        llm_name = "Google Gemini 1.5 Flash"
    elif os.environ.get("GROQ_API_KEY"):
        llm_name = "Meta Llama-3.1 (via Groq)"
    elif os.environ.get("OPENAI_API_KEY"):
        llm_name = "OpenAI GPT-4o-mini"
    elif not os.environ.get("RENDER"):
        llm_name = "Local Ollama Llama 3.2"
    else:
        llm_name = "No Cloud LLM Configured"
        
    return render_template("index.html", active_llm=llm_name)

@app.route("/residents")
def residents():
    mock_residents = [
        {"name": "Sarah Jenkins", "unit": "A-101", "status": "Active", "contact": "sarah.j@example.com"},
        {"name": "Michael Chen", "unit": "B-402", "status": "Active", "contact": "mchen@example.com"},
        {"name": "Amanda Smith", "unit": "A-105", "status": "Pending", "contact": "asmith@example.com"},
        {"name": "David Wallace", "unit": "C-202", "status": "Active", "contact": "davidw@example.com"}
    ]
    return render_template("residents.html", residents=mock_residents)

@app.route("/maintenance")
def maintenance():
    tickets = get_tickets().get("maintenance", [])
    return render_template("maintenance.html", tickets=tickets)

@app.route("/events")
def events():
    mock_events = [
        {"title": "Summer BBQ", "date": "Aug 15", "location": "Rec Center"},
        {"title": "HOA Meeting", "date": "Aug 20", "location": "Main Hall"},
        {"title": "Pool Maintenance", "date": "Aug 22", "location": "Community Pool"}
    ]
    return render_template("events.html", events=mock_events)

@app.route("/security")
def security():
    security_logs = get_tickets().get("security", [])
    return render_template("security.html", security_logs=security_logs)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    success_msg = None
    if request.method == "POST":
        gemini = request.form.get("gemini_api_key")
        openai = request.form.get("openai_api_key")
        save_settings({"gemini_api_key": gemini, "openai_api_key": openai})
        success_msg = "Settings saved successfully!"
        
    current_settings = get_settings()
    return render_template("settings.html", settings=current_settings, success_msg=success_msg)

@app.route("/report", methods=["POST"])

def process_report():
    data = request.json or {}
    issue_text = data.get("issue_text", "")
    provider = data.get("provider")
    api_key = data.get("api_key")
    if not issue_text:
        return jsonify({"error": "No issue_text provided in the request body"}), 400
        
    community_crew, error_msg = get_crew(provider, api_key)
    if error_msg:
        return jsonify({"error": error_msg}), 500

    print(f"\n[!] Instructing Crew to process issue: {issue_text}\n")
    result = community_crew.kickoff(inputs={'issue_text': issue_text})
    
    return jsonify({
        "status": "success", 
        "output": str(result)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
