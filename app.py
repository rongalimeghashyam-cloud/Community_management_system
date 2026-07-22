import os
import yaml
from flask import Flask, request, jsonify
from crewai import Agent, Task, Crew, Process
from crewai import LLM
from tools import check_database_for_duplicates

def load_yaml(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

app = Flask(__name__)

def get_crew():
    agents_config = load_yaml('config/agents.yaml')
    tasks_config = load_yaml('config/tasks.yaml')

    # Detect which API key is available in the Render Environment
    if not os.environ.get("RENDER"):
        active_llm = LLM(model="ollama/llama3.2", base_url="http://localhost:11434")
    elif os.environ.get("GEMINI_API_KEY"):
        active_llm = LLM(model="gemini/gemini-1.5-flash", api_key=os.environ.get("GEMINI_API_KEY"))
    elif os.environ.get("GROQ_API_KEY"):
        active_llm = LLM(model="groq/llama-3.1-8b-instant", api_key=os.environ.get("GROQ_API_KEY"))
    elif os.environ.get("OPENAI_API_KEY"):
        active_llm = LLM(model="gpt-4o-mini", api_key=os.environ.get("OPENAI_API_KEY"))
    else:
        return None, "No API Key found! Please add GEMINI_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY to Render Environment Variables."

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
    return jsonify({"status": "running", "message": "CrewAI Community System is active. Send POST to /report"})

@app.route("/report", methods=["POST"])
def process_report():
    data = request.json or {}
    issue_text = data.get("issue_text", "")
    if not issue_text:
        return jsonify({"error": "No issue_text provided in the request body"}), 400
        
    community_crew, error_msg = get_crew()
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
