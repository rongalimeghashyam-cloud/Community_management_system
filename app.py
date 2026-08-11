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
    Smart resolution of active LLM instance. Automatically picks the best operational
    model based on available API keys (Gemini -> Groq -> OpenAI -> Qwen -> Anthropic -> DeepSeek -> Ollama).
    """
    keys = get_api_keys()
    settings = get_settings()
    
    if not selected_model or selected_model in ["default", "auto", "auto_select"]:
        # Default smart auto-selection: check highest quality/fastest active key
        if keys.get("gemini"):
            llm = safe_create_llm("gemini/gemini-2.0-flash", api_key=keys["gemini"])
            if llm: return llm, "Google Gemini 2.0 Flash (Auto Selected)", None
            
        if keys.get("groq"):
            llm = safe_create_llm("groq/llama-3.1-8b-instant", api_key=keys["groq"])
            if llm: return llm, "Groq Llama 3.1 8B (Auto Selected)", None
            
        if keys.get("openai"):
            llm = safe_create_llm("gpt-4o-mini", api_key=keys["openai"])
            if llm: return llm, "OpenAI GPT-4o-mini (Auto Selected)", None
            
        if keys.get("qwen"):
            llm = safe_create_llm("qwen/qwen-2.5-72b-instruct", api_key=keys["qwen"])
            if llm: return llm, "Alibaba Qwen 2.5 72B (Auto Selected)", None
            
        if keys.get("anthropic"):
            llm = safe_create_llm("anthropic/claude-3-5-sonnet-20241022", api_key=keys["anthropic"])
            if llm: return llm, "Claude 3.5 Sonnet (Auto Selected)", None
            
        if keys.get("deepseek"):
            llm = safe_create_llm("deepseek/deepseek-chat", api_key=keys["deepseek"], base_url="https://api.deepseek.com")
            if llm: return llm, "DeepSeek V3 (Auto Selected)", None
        
        ollama_llm, name = get_local_ollama_llm(keys.get("ollama_url"))
        if ollama_llm:
            return ollama_llm, f"{name} (Auto Selected)", None

        selected_model = settings.get("default_model", "local_llama")

    selected_model = selected_model.lower().strip()

    # Try requested model preference if specified by user
    if selected_model in ["local_llama", "ollama"]:
        llm, name = get_local_ollama_llm(keys.get("ollama_url"))
        if llm:
            return llm, name, None
            
    elif selected_model == "gemini" and keys.get("gemini"):
        llm = safe_create_llm("gemini/gemini-2.0-flash", api_key=keys["gemini"])
        if llm: return llm, "Google Gemini 2.0 Flash", None
        
    elif selected_model == "groq" and keys.get("groq"):
        llm = safe_create_llm("groq/llama-3.1-8b-instant", api_key=keys["groq"])
        if llm: return llm, "Groq Llama 3.1 8B", None
        
    elif selected_model == "openai" and keys.get("openai"):
        llm = safe_create_llm("gpt-4o-mini", api_key=keys["openai"])
        if llm: return llm, "OpenAI GPT-4o-mini", None
        
    elif selected_model == "qwen" and keys.get("qwen"):
        llm = safe_create_llm("qwen/qwen-2.5-72b-instruct", api_key=keys["qwen"])
        if llm: return llm, "Alibaba Qwen 2.5 72B", None

    elif selected_model == "anthropic" and keys.get("anthropic"):
        llm = safe_create_llm("anthropic/claude-3-5-sonnet-20241022", api_key=keys["anthropic"])
        if llm: return llm, "Claude 3.5 Sonnet", None

    elif selected_model == "deepseek" and keys.get("deepseek"):
        llm = safe_create_llm("deepseek/deepseek-chat", api_key=keys["deepseek"], base_url="https://api.deepseek.com")
        if llm: return llm, "DeepSeek V3", None

    # Fallback Cascade: Check available keys in priority order
    if keys.get("gemini"):
        llm = safe_create_llm("gemini/gemini-2.0-flash", api_key=keys["gemini"])
        if llm: return llm, "Google Gemini 2.0 Flash (Fallback)", None
    if keys.get("groq"):
        llm = safe_create_llm("groq/llama-3.1-8b-instant", api_key=keys["groq"])
        if llm: return llm, "Groq Llama 3.1 (Fallback)", None
    if keys.get("openai"):
        llm = safe_create_llm("gpt-4o-mini", api_key=keys["openai"])
        if llm: return llm, "OpenAI GPT-4o-mini (Fallback)", None
    if keys.get("qwen"):
        llm = safe_create_llm("qwen/qwen-2.5-72b-instruct", api_key=keys["qwen"])
        if llm: return llm, "Qwen 2.5 (Fallback)", None
    if keys.get("anthropic"):
        llm = safe_create_llm("anthropic/claude-3-5-sonnet-20241022", api_key=keys["anthropic"])
        if llm: return llm, "Claude 3.5 (Fallback)", None
    if keys.get("deepseek"):
        llm = safe_create_llm("deepseek/deepseek-chat", api_key=keys["deepseek"], base_url="https://api.deepseek.com")
        if llm: return llm, "DeepSeek V3 (Fallback)", None

    ollama_llm, ollama_name = get_local_ollama_llm(keys.get("ollama_url"))
    if ollama_llm:
        return ollama_llm, f"{ollama_name} (Fallback)", None

    return None, None, "No active API key or local Ollama model found! Please configure API keys in the Admin Portal."


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
    llm_name = active_name or "No API Key Configured (Visit /admin)"
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

# --- ADMIN PORTAL ROUTES ---

@app.route("/admin", methods=["GET"])
def admin_portal():
    masked_keys = get_masked_api_keys()
    tickets = get_tickets()
    query_logs = get_query_logs()
    settings = get_settings()
    _, active_model_name, _ = resolve_active_llm()
    
    return render_template(
        "admin.html", 
        masked_keys=masked_keys, 
        tickets=tickets, 
        query_logs=query_logs, 
        settings=settings,
        active_model_name=active_model_name or "None Configured"
    )

@app.route("/admin/api-keys", methods=["GET", "POST"])
def admin_api_keys():
    if request.method == "POST":
        data = request.json or {}
        new_keys = data.get("api_keys", {})
        updated_masked = save_api_keys(new_keys)
        
        # Save optional default model
        if "default_model" in data:
            save_settings({"default_model": data["default_model"]})
            
        return jsonify({
            "status": "success",
            "message": "API Keys saved successfully!",
            "masked_keys": updated_masked
        })
    else:
        return jsonify({"masked_keys": get_masked_api_keys()})

@app.route("/admin/test-key", methods=["POST"])
def test_api_key():
    data = request.json or {}
    provider = data.get("provider", "").lower()
    raw_key = data.get("api_key", "").strip()
    
    keys = get_api_keys()
    key_to_use = raw_key if raw_key and not "..." in raw_key else keys.get(provider, "")
    
    if not key_to_use and provider != "ollama":
        return jsonify({"status": "error", "message": f"No API key provided for {provider}."}), 400

    try:
        if provider == "openai":
            res = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key_to_use}"}, timeout=5)
            if res.status_code == 200:
                return jsonify({"status": "success", "message": "OpenAI API Key is VALID and connected!"})
            else:
                return jsonify({"status": "error", "message": f"OpenAI Error ({res.status_code}): {res.json().get('error', {}).get('message', res.text)}"}), 400

        elif provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key_to_use}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return jsonify({"status": "success", "message": "Google Gemini API Key is VALID and connected!"})
            else:
                return jsonify({"status": "error", "message": f"Gemini Error ({res.status_code}): {res.text[:150]}"}), 400

        elif provider == "groq":
            res = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key_to_use}"}, timeout=5)
            if res.status_code == 200:
                return jsonify({"status": "success", "message": "Groq API Key is VALID and connected!"})
            else:
                return jsonify({"status": "error", "message": f"Groq Error ({res.status_code}): {res.text[:150]}"}), 400

        elif provider == "qwen":
            res = requests.get("https://dashscope.aliyuncs.com/compatible-mode/v1/models", headers={"Authorization": f"Bearer {key_to_use}"}, timeout=5)
            if res.status_code == 200:
                return jsonify({"status": "success", "message": "Alibaba Qwen / DashScope API Key is VALID!"})
            else:
                return jsonify({"status": "error", "message": f"Qwen Error ({res.status_code}): {res.text[:150]}"}), 400

        elif provider == "anthropic":
            res = requests.get("https://api.anthropic.com/v1/models", headers={"x-api-key": key_to_use, "anthropic-version": "2023-06-01"}, timeout=5)
            if res.status_code in [200, 404]: # Some endpoints may vary but 200 means active
                return jsonify({"status": "success", "message": "Anthropic Claude API Key is VALID!"})
            else:
                return jsonify({"status": "error", "message": f"Anthropic Error ({res.status_code}): {res.text[:150]}"}), 400

        elif provider == "deepseek":
            res = requests.get("https://api.deepseek.com/models", headers={"Authorization": f"Bearer {key_to_use}"}, timeout=5)
            if res.status_code == 200:
                return jsonify({"status": "success", "message": "DeepSeek API Key is VALID!"})
            else:
                return jsonify({"status": "error", "message": f"DeepSeek Error ({res.status_code}): {res.text[:150]}"}), 400

        elif provider == "ollama":
            ollama_url = raw_key or keys.get("ollama_url", "http://localhost:11434")
            res = requests.get(f"{ollama_url}/api/tags", timeout=3)
            if res.status_code == 200:
                models = [m.get("name") for m in res.json().get("models", [])]
                return jsonify({"status": "success", "message": f"Ollama Server Online! Available models: {', '.join(models[:5])}"})
            else:
                return jsonify({"status": "error", "message": f"Ollama Server not reachable at {ollama_url}"}), 400

        else:
            return jsonify({"status": "error", "message": f"Unknown provider: {provider}"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": f"Connection test failed: {str(e)}"}), 500

@app.route("/admin/tickets/status", methods=["POST"])
def admin_update_ticket_status():
    data = request.json or {}
    ticket_id = data.get("ticket_id")
    department = data.get("department", "maintenance")
    new_status = data.get("status", "Open")
    
    if not ticket_id:
        return jsonify({"status": "error", "message": "Ticket ID required"}), 400
        
    updated = update_ticket_status(ticket_id, department, new_status)
    if updated:
        return jsonify({"status": "success", "message": f"Ticket {ticket_id} status updated to '{new_status}'"})
    else:
        return jsonify({"status": "error", "message": f"Ticket {ticket_id} not found."}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
