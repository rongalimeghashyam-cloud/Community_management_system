import os
import json

with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

# We want to replace the `get_crew` and routes
# We'll split before `@app.route("/", methods=["GET"])`

split_marker = '@app.route("/", methods=["GET"])'
if split_marker not in app_content:
    print("Could not find split marker in app.py")
    exit(1)

top_part, bottom_part = app_content.split(split_marker)

# Let's write the new routes and get_crew logic

new_routes = """import json

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

def get_crew(provider=None, api_key=None):
    agents_config = load_yaml('config/agents.yaml')
    tasks_config = load_yaml('config/tasks.yaml')

    settings = get_settings()
    
    active_llm = None
    if provider and api_key:
        if provider == 'gemini':
            active_llm = LLM(model="gemini/gemini-1.5-flash", api_key=api_key)
        elif provider == 'groq':
            active_llm = LLM(model="groq/llama-3.1-8b-instant", api_key=api_key)
        elif provider == 'openai':
            active_llm = LLM(model="gpt-4o-mini", api_key=api_key)

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
    task_triage = Task(
        config=tasks_config['task_triage'],
        agent=triage_agent
    )
    task_validation = Task(
        config=tasks_config['task_validation'],
        agent=validation_agent
    )
    
    community_crew = Crew(
        agents=[triage_agent, validation_agent],
        tasks=[task_triage, task_validation],
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
    mock_tickets = [
        {"id": "1024", "title": "Massive pothole on Main Street", "location": "Main Street", "date": "Today, 08:30 AM", "priority": "High", "status": "Open"},
        {"id": "0988", "title": "Trash missed collection", "location": "Elm St", "date": "Yesterday", "priority": "Low", "status": "Resolved"},
        {"id": "1025", "title": "Leaking pipe in basement", "location": "Bldg B", "date": "Today, 10:15 AM", "priority": "High", "status": "Open"}
    ]
    return render_template("maintenance.html", tickets=mock_tickets)

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
    mock_logs = [
        {"event": "Unauthorized vehicle at Gate B", "time": "10 mins ago", "location": "Gate B", "level": "Warning"},
        {"event": "Camera offline in Parking C", "time": "1 hour ago", "location": "Parking C", "level": "Critical"},
        {"event": "Routine patrol completed", "time": "2 hours ago", "location": "All areas", "level": "Info"}
    ]
    return render_template("security.html", security_logs=mock_logs)

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
"""

# Now we need to reconstruct app.py by replacing the get_crew and anything after it up to /report
# Find get_crew definition in top_part
get_crew_idx = top_part.find('def get_crew(')
top_imports = top_part[:get_crew_idx]

# Find /report in bottom_part
report_idx = bottom_part.find('@app.route("/report"')
bottom_report = bottom_part[report_idx + len('@app.route("/report", methods=["POST"])'):]

new_app_content = top_imports + new_routes + bottom_report

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_app_content)

print("Updated app.py with new routes and settings logic.")
