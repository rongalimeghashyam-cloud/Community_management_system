import os
import yaml
import time
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for
from crewai import Agent, Task, Crew, Process
from crewai import LLM
from tools import check_database_for_duplicates, raise_ticket, query_community_info
from database import (
    get_tickets, 
    get_api_keys, 
    get_masked_api_keys, 
    save_api_keys, 
    log_agent_query, 
    get_query_logs,
    update_ticket_status,
    get_settings,
    save_settings
)

def load_yaml(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

app = Flask(__name__)

def get_local_ollama_llm(custom_url=None):
    """Returns an LLM instance pointing to local Ollama if available."""
    base_url = custom_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=2)
        if resp.status_code == 200:
            models_data = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models_data]
            for pref in ["llama3.2:3b", "llama3.2:1b", "llama3.2", "llama3", "llama", "qwen2.5"]:
                for m in model_names:
                    if pref in m:
                        return LLM(model=f"ollama/{m}", base_url=base_url), f"Ollama ({m})"
            if model_names:
                return LLM(model=f"ollama/{model_names[0]}", base_url=base_url), f"Ollama ({model_names[0]})"
    except Exception as e:
        print(f"Ollama connection check to {base_url}: {e}")
    return None, None

def safe_create_llm(model_name, api_key=None, base_url=None):
    try:
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        return LLM(model=model_name, **kwargs)
    except Exception as e:
        print(f"Notice: LLM initialization for {model_name} skipped ({e})")
        return None

def resolve_active_llm(selected_model=None):
    """
    Resolves the active LLM instance matching the requested provider or default setting.
    Seamlessly falls back across Gemini, OpenAI, DeepSeek, Anthropic, and Llama.
    """
    keys = get_api_keys()
    settings = get_settings()
    
    # Normalize selected model parameter
    if not selected_model or selected_model in ["default", "auto"]:
        selected_model = settings.get("default_model", "auto")

    selected_model = selected_model.lower().strip()

    # 1. Google Gemini Selection
    if selected_model == "gemini":
        if keys.get("gemini"):
            llm = safe_create_llm("gemini/gemini-2.0-flash", api_key=keys["gemini"])
            if llm:
                return llm, "Google Gemini 2.0 Flash", None
        return None, None, "Google Gemini API key missing or invalid."

    # 2. OpenAI Selection
    elif selected_model == "openai":
        if keys.get("openai"):
            llm = safe_create_llm("gpt-4o-mini", api_key=keys["openai"])
            if llm:
                return llm, "OpenAI GPT-4o-mini", None
        return None, None, "OpenAI API key missing or invalid."

    # 3. DeepSeek Selection
    elif selected_model == "deepseek":
        if keys.get("deepseek"):
            llm = safe_create_llm("deepseek/deepseek-chat", api_key=keys["deepseek"], base_url="https://api.deepseek.com")
            if llm:
                return llm, "DeepSeek V3", None
        return None, None, "DeepSeek API key missing or invalid."

    # 4. Anthropic Claude Selection
    elif selected_model == "anthropic":
        if keys.get("anthropic"):
            llm = safe_create_llm("anthropic/claude-3-5-sonnet-20241022", api_key=keys["anthropic"])
            if llm:
                return llm, "Claude 3.5 Sonnet", None
        return None, None, "Anthropic API key missing or invalid."

    # 5. Alibaba Qwen Selection
    elif selected_model == "qwen":
        if keys.get("qwen"):
            llm = safe_create_llm("qwen/qwen-2.5-72b-instruct", api_key=keys["qwen"])
            if llm:
                return llm, "Alibaba Qwen 2.5 72B", None
        return None, None, "Qwen API key missing or invalid."

    # 6. Llama / Groq Selection
    elif selected_model in ["local_llama", "ollama", "llama", "groq", "groq_llama"]:
        llm, name = get_local_ollama_llm(keys.get("ollama_url"))
        if llm:
            return llm, name, None
        if keys.get("groq"):
            llm = safe_create_llm("groq/llama-3.1-8b-instant", api_key=keys["groq"])
            if llm:
                return llm, "Groq Llama 3.1 8B", None

    # AUTO / DEFAULT Fallback Chain (Ideal for Render cloud & local offline fallbacks):
    # Try local Ollama if online
    ollama_llm, ollama_name = get_local_ollama_llm(keys.get("ollama_url"))
    if ollama_llm:
        return ollama_llm, ollama_name, None

    # Try Gemini
    if keys.get("gemini"):
        llm = safe_create_llm("gemini/gemini-2.0-flash", api_key=keys["gemini"])
        if llm:
            return llm, "Google Gemini 2.0 Flash", None

    # Try OpenAI
    if keys.get("openai"):
        llm = safe_create_llm("gpt-4o-mini", api_key=keys["openai"])
        if llm:
            return llm, "OpenAI GPT-4o-mini", None

    # Try DeepSeek
    if keys.get("deepseek"):
        llm = safe_create_llm("deepseek/deepseek-chat", api_key=keys["deepseek"], base_url="https://api.deepseek.com")
        if llm:
            return llm, "DeepSeek V3", None

    # Try Anthropic
    if keys.get("anthropic"):
        llm = safe_create_llm("anthropic/claude-3-5-sonnet-20241022", api_key=keys["anthropic"])
        if llm:
            return llm, "Claude 3.5 Sonnet", None

    # Try Groq
    if keys.get("groq"):
        llm = safe_create_llm("groq/llama-3.1-8b-instant", api_key=keys["groq"])
        if llm:
            return llm, "Groq Llama 3.1", None

    return None, None, "No active API key found!"



def get_crew(selected_model="local_llama"):
    agents_config = load_yaml('config/agents.yaml')
    tasks_config = load_yaml('config/tasks.yaml')

    active_llm, model_name, error_msg = resolve_active_llm(selected_model)
    if error_msg:
        return None, None, error_msg

    triage_agent = Agent(
        config=agents_config['triage_agent'],
        llm=active_llm,
        tools=[query_community_info],
        max_iter=3,
        max_execution_time=60,
        verbose=False
    )
    validation_agent = Agent(
        config=agents_config['validation_agent'],
        llm=active_llm,
        tools=[check_database_for_duplicates],
        max_iter=3,
        max_execution_time=60,
        verbose=False
    )
    ticketing_agent = Agent(
        config=agents_config['ticketing_agent'],
        llm=active_llm,
        tools=[raise_ticket],
        max_iter=3,
        max_execution_time=60,
        verbose=False
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
        process=Process.sequential,
        max_rpm=10
    )
    return community_crew, model_name, None

# --- USER PORTAL ROUTES ---

@app.route("/", methods=["GET"])
def home():
    _, active_name, _ = resolve_active_llm()
    llm_name = active_name or "No API Key Configured"
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

@app.route("/query", methods=["POST"])
def user_agent_query():
    """
    Direct endpoint connecting user queries directly to the active AI Agent.
    Handles interactive user questions, complaints, and general assistance.
    """
    start_time = time.time()
    data = request.json or {}
    user_query = data.get("query", "").strip()
    selected_model = data.get("model", "default")
    
    if not user_query:
        return jsonify({"status": "error", "error": "Query text cannot be empty."}), 400

    community_crew, model_used, error_msg = get_crew(selected_model)
    if error_msg:
        log_agent_query(user_query, selected_model, error_msg, status="error", duration_sec=0.0)
        return jsonify({"status": "error", "error": error_msg}), 500

    try:
        result = community_crew.kickoff(inputs={'issue_text': user_query})
        duration = time.time() - start_time
        
        output_str = str(result)
        logs = []
        if hasattr(result, 'tasks_output'):
            for task_out in result.tasks_output:
                logs.append({
                    "description": task_out.description,
                    "result": task_out.raw
                })
        
        log_agent_query(user_query, model_used, output_str, status="success", duration_sec=duration)
        
        return jsonify({
            "status": "success",
            "query": user_query,
            "answer": output_str,
            "model_used": model_used,
            "steps": logs,
            "duration": round(duration, 2)
        })
    except Exception as e:
        duration = time.time() - start_time
        err_text = f"Agent Execution Error: {str(e)}"
        log_agent_query(user_query, model_used or selected_model, err_text, status="error", duration_sec=duration)
        return jsonify({"status": "error", "error": err_text}), 500

@app.route("/report", methods=["POST"])
def process_report():
    start_time = time.time()
    data = request.json or {}
    issue_text = data.get("issue_text", "")
    selected_model = data.get("model", "default")
    
    if not issue_text:
        return jsonify({"error": "No issue_text provided in the request body"}), 400
        
    community_crew, model_used, error_msg = get_crew(selected_model)
    if error_msg:
        return jsonify({"error": error_msg}), 500

    try:
        result = community_crew.kickoff(inputs={'issue_text': issue_text})
        duration = time.time() - start_time
        
        progress_text = f"### Agent Tracking Progress ({model_used}) ###\n\n"
        if hasattr(result, 'tasks_output'):
            for task_output in result.tasks_output:
                progress_text += f"[✔] Agent Task Completed: {task_output.description}\n"
                progress_text += f"{task_output.raw}\n\n"
        
        final_output = f"{progress_text}---\n### Final Result ###\n{str(result)}"
        
        log_agent_query(issue_text, model_used, str(result), status="success", duration_sec=duration)
        
        return jsonify({
            "status": "success", 
            "output": final_output,
            "model_used": model_used
        })
    except Exception as e:
        duration = time.time() - start_time
        log_agent_query(issue_text, model_used or selected_model, str(e), status="error", duration_sec=duration)
        return jsonify({
            "status": "error",
            "error": f"AI Processing Error: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)

