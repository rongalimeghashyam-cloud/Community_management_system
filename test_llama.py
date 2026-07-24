import os
import yaml
from crewai import Agent, Task, Crew, Process, LLM

def load_yaml(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

agents_config = load_yaml('config/agents.yaml')
tasks_config = load_yaml('config/tasks.yaml')

groq_key = os.environ.get("GROQ_API_KEY", "test")
active_llm = LLM(model="ollama/llama3.2:1b", base_url="http://localhost:11434")

print("LLM configured")
triage_agent = Agent(
    config=agents_config['triage_agent'],
    llm=active_llm,
    verbose=True
)
print("Agent configured")

task_triage = Task(
    config=tasks_config['task_triage'],
    agent=triage_agent
)

crew = Crew(
    agents=[triage_agent],
    tasks=[task_triage],
    process=Process.sequential
)
result = crew.kickoff(inputs={'issue_text': 'There is a massive pothole in front of building A'})
print(result)
