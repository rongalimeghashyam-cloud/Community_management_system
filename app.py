import yaml
from crewai import Agent, Task, Crew, Process
from crewai import LLM
from tools import check_database_for_duplicates

# Connect directly to your local Ollama server running in the background
local_llm = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434"
)

def load_yaml(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

agents_config = load_yaml('config/agents.yaml')
tasks_config = load_yaml('config/tasks.yaml')

triage_agent = Agent(
    config=agents_config['triage_agent'],
    llm=local_llm,
    verbose=True
)

validation_agent = Agent(
    config=agents_config['validation_agent'],
    llm=local_llm,
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

if __name__ == "__main__":
    sample_complaint = (
        "There is a massive pothole right in front of the grocery store on Main Street. "
        "It almost popped my tire this morning, someone needs to fix this ASAP before it causes an accident!"
    )
    
    print("\n[!] Initializing Local ReAct-Enabled Multi-Agent Pipeline...\n")
    
    result = community_crew.kickoff(inputs={'issue_text': sample_complaint})
    
    print("\n###### SYSTEM OUTPUT ######\n")
    print(result)
