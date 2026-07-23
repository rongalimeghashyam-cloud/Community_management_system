# 🏢 Premium Community Management System 

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0-blue.svg)
![CrewAI](https://img.shields.io/badge/CrewAI-Multi--Agent-orange)

> A state-of-the-art Community Management System for residential and societal management. It acts as a centralized digital platform to streamline daily operations, track infrastructure maintenance, handle security reports, and provide community-wide communication workflows within modern housing societies, apartments, or gated complexes.

---

## 🌟 Key Features

* **Multi-Agent AI Complaint Processing**: Integrates advanced LLMs utilizing CrewAI. Agents intelligently triage complaints, cross-reference tickets against duplicates in the database, and automatically route issues to appropriate physical departments (Maintenance vs. Security).
* **Dynamic Analytics Dashboard**: Clean, responsive aesthetic dashboard summarizing active residents, open maintenance requests, impending events, and security alerts.
* **Unified Database Sync**: Seamless integration with scalable database mechanisms utilizing both Firebase Firestore cloud storage and robust local JSON fallback logic. 
* **Zero-Config Operations**: Engineered with embedded cloud-based API tokens (OpenAI and Gemini Flash) that completely abstract configuration barriers away from standard users.

## 🛠️ Technology Stack

- **Backend**: Python 3.10, Flask
- **AI / Multi-Agent Orchestration**: CrewAI (OpenAI / Google Gemini integrated)
- **Database Architecture**: Firebase Admin SDK (Cloud Firestore)
- **Frontend Utilities**: HTML5, Vanilla JavaScript, DOM interactions
- **UI Design System**: Built with customized CSS to reflect highly-premium, aesthetically modern UI components (blur effects, transitions, grid layouts, Phosphor Web icons).

## 🗂️ Project Structure

```bash
├── app.py                     # Main Flask Application routing and CrewAI invocation
├── database.py                # Firebase and Local Storage utility logic
├── tools.py                   # Custom CrewAI specific tools (Ticket Creation & Duplication Search)
├── config/
│   ├── agents.yaml            # Blueprint for Triage, Validation, and Ticketing Agents
│   ├── tasks.yaml             # Blueprint detailing specific prompts for the Multi-Agent network
├── templates/                 
│   ├── base.html              # Unified wrapper including Sidebar and global Modal
│   ├── index.html             # Main Dashboard interface
│   ├── maintenance.html       # Automated Ticket Feed visualizer
│   ├── events.html            # Event tracker 
│   └── security.html          # Security logs tracker
└── requirements.txt           # Dependency tracker
```

## 🚀 Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/rongalimeghashyam-cloud/Community_management_system.git
cd Community_management_system
```

2. **Install the dependencies:**
```bash
pip install -r requirements.txt
```

3. **Start the localized server:**
```bash
python app.py
```
*Navigate to `http://127.0.0.1:5000` to interact with the application!*

## 🧠 AI Agent Workflow

When a user submits a complaint via the **AI Complaint Assistant**, the platform kicks off a sophisticated automated pipeline:
1. **Triage Agent** analyses text sentiment and categorizes it implicitly as either `Maintenance` or `Security`.
2. **Validation Agent** scans historical databases via `check_database_for_duplicates` tool to prevent spam or repetitive requests.
3. **Ticketing Agent** orchestrates finalization by formally routing legitimate tickets directly to the required cloud or local directories.

---

<p align="center">
  <i>Engineered for streamlined community moderation workflows.</i>
</p>
