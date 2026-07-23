import os
import yaml
from flask import Flask, request, jsonify, render_template
from crewai import Agent, Task, Crew, Process
from crewai import LLM
from tools import check_database_for_duplicates, raise_ticket
from database import get_tickets

def load_yaml(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

app = Flask(__name__)


# --- HARDCODED API KEYS ---
# Place your API keys here so users don't need to enter them in the UI.
HARDCODED_OPENAI_API_KEY = "sk-proj-y1Mk8zvgSR862uxg1ZtLOyR4wCZIThckAZ7emL" + "wW4ekY7GxkmzhZWH4IJCiz5WPrnDJ9uhN3ejT3BlbkFJWRVf_JFFgU5wZl_18_xji9oMYJkhNNxLNrbh19DpzEo5Cl0pl6aE1m8teCwPGkvgKGkcUAoqgA"
HARDCODED_GEMINI_API_KEY = "AQ.Ab8RN6I9A-adh" + "UcEuC99DPXXof0VbGZpBJzqOL4-t4tz1e0KrA"
# --------------------------

def get_crew(selected_model="gemini"):
    agents_config = load_yaml('config/agents.yaml')
    tasks_config = load_yaml('config/tasks.yaml')

    active_llm = None
    
    if selected_model == "gemini":
        if HARDCODED_GEMINI_API_KEY and HARDCODED_GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
            active_llm = LLM(model="gemini/gemini-2.5-pro", api_key=HARDCODED_GEMINI_API_KEY)
        else:
            return None, "Gemini API Key not configured."
    elif selected_model == "openai":
        if HARDCODED_OPENAI_API_KEY and HARDCODED_OPENAI_API_KEY != "YOUR_OPENAI_API_KEY":
            active_llm = LLM(model="gpt-4o-mini", api_key=HARDCODED_OPENAI_API_KEY)
        else:
            return None, "OpenAI API Key not configured."
    elif selected_model == "llama":
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            active_llm = LLM(model="groq/llama-3.1-8b-instant", api_key=groq_key)
        else:
            active_llm = LLM(model="ollama/llama3.2", base_url="http://localhost:11434")

    if active_llm is None:
        return None, f"Failed to initialize the {selected_model} model. Please check the backend configuration."

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
    if HARDCODED_GEMINI_API_KEY and HARDCODED_GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
        llm_name = "Google Gemini 2.5 Pro (Hardcoded)"
    elif HARDCODED_OPENAI_API_KEY and HARDCODED_OPENAI_API_KEY != "YOUR_OPENAI_API_KEY":
        llm_name = "OpenAI GPT-4o-mini (Hardcoded)"
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



@app.route("/report", methods=["POST"])
def process_report():
    data = request.json or {}
    issue_text = data.get("issue_text", "")
    selected_model = data.get("model", "gemini")
    
    if not issue_text:
        return jsonify({"error": "No issue_text provided in the request body"}), 400
        
    community_crew, error_msg = get_crew(selected_model)
    if error_msg:
        return jsonify({"error": error_msg}), 500

    try:
        print(f"\n[!] Instructing Crew to process issue with model {selected_model}: {issue_text}\n")
        result = community_crew.kickoff(inputs={'issue_text': issue_text})
        
        # Build tracking progress for the UI
        progress_text = "### Agent Tracking Progress ###\n\n"
        if hasattr(result, 'tasks_output'):
            for task_output in result.tasks_output:
                progress_text += f"[\u2714] Agent Task Completed: {task_output.description}\n"
                progress_text += f"{task_output.raw}\n\n"
        
        final_output = f"{progress_text}---\n### Final Result ###\n{str(result)}"
        
        return jsonify({
            "status": "success", 
            "output": final_output
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": f"AI Processing Error: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
