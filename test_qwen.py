import os
import yaml
from crewai import Agent, Task, Crew, Process, LLM

def load_yaml(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

agents_config = load_yaml('config/agents.yaml')
tasks_config = load_yaml('config/tasks.yaml')

qwen_key = os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")

if qwen_key:
    active_llm = LLM(model="qwen/qwen-2.5-72b-instruct", api_key=qwen_key)
elif groq_key:
    active_llm = LLM(model="groq/qwen-2.5-32b", api_key=groq_key)
else:
    active_llm = LLM(model="ollama/qwen2.5", base_url="http://localhost:11434")

print(f"Qwen LLM configured: {active_llm.model}")
triage_agent = Agent(
    config=agents_config['triage_agent'],
    llm=active_llm,
    verbose=True
)
print("Agent configured with Qwen LLM successfully.")
