# Agentic AI - IT Service Automation

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Microsoft Agent Framework](https://img.shields.io/badge/Agent-MAF%20%7C%20Semantic%20Kernel-purple.svg)](https://github.com/microsoft/semantic-kernel)
[![AutomationEdge RPA](https://img.shields.io/badge/RPA-AutomationEdge%20T4-orange.svg)](https://automationedge.com)
[![ServiceNow](https://img.shields.io/badge/ITSM-ServiceNow%20REST%20API-green.svg)](https://developer.servicenow.com)

An enterprise-grade **Agentic AI & Robotic Process Automation (RPA) IT Service Management (ITSM)** solution. This project simulates a **Microsoft Teams AI Assistant** that interacts with enterprise employees, dynamically interprets IT queries, gathers required parameters via **Microsoft Adaptive Cards 1.5**, registers/tracks tickets in **ServiceNow**, and triggers automated fulfillment via **AutomationEdge (T4) RPA Workflows**.

---

## Key Features

### 1. Microsoft Teams AI Bot Simulator
* **Authentic Teams Experience**: Built with a Microsoft Teams Dark Theme, interactive adaptive cards, and real-time status updates.
* **Microsoft Adaptive Cards 1.5**: Dynamic intake forms (`Input.Text`, `Input.ChoiceSet`, `Action.Submit`) formatted strictly according to official Microsoft Adaptive Card schemas.
* **Role Personas**: Seamless switching between:
  * **Requester**: `Aarav Sharma (Finance Analyst)` (`aarav.sharma@company.com`)
  * **Approver**: `Priya Patel (Finance Director)` (`priya.patel@company.com`)

### 2. Microsoft Agent Framework (MAF) & Intent Engine
* **Context-Aware Intent Classification**: Automatically recognizes and maps user queries to RPA workflows.
* **Dynamic SLA & Priority Matrix**: Automatically calculates **Impact** (1-3), **Urgency** (1-3), and **Priority** (P1-P4) based on sentiment and urgency cues (e.g., *"emergency"*, *"production block"* -> P1 / High Priority).
* **Slot-Filling & Multi-Turn Conversations**: Interactively prompts for missing required parameters before triggering RPA actions.

### 3. AutomationEdge (T4) RPA Integration
* **Automated Workflow Execution**: Invokes live AutomationEdge RPA workflows via REST APIs.
* **Execution Validation & Polling**: Actively monitors execution status (`NEW` -> `RUNNING` -> `COMPLETE`) before notifying the user and closing ServiceNow tickets.
* **Supported Workflows**:
  * **Active Directory Password Reset** (`AD Password_Reset` - ID: 10383)
  * **Account Unlock** (`IOCO Account unlock` - ID: 10381)
  * **Distribution List (DL) Creation** (`DL Creation - iOCO` - ID: 10394)
  * **SAP Access & Role Assignment** (`AD_UserCreate_AssignRole` - ID: 10387)
  * **Shared Folder Access** (`BG-Create_Service_Request_Share_Folder_Access` - ID: 9723)

### 4. Live ServiceNow Integration
* **Real-time Incident Management**: Creates, updates, tracks, and resolves incidents in ServiceNow.
* **Dynamic Fields**: Sets caller (`Aarav Sharma`), Urgency, Impact, Priority, Short Description, and Work Notes.
* **Flexible Authentication**: Full support for both **HTTP Basic Auth** (via dedicated integration account) and **OAuth 2.0 Bearer Tokens**.
* **Automated Lifecycle**: Moves incident from `New (1)` -> `In Progress (2)` -> `Resolved (6)` upon successful RPA completion.

---

## Architecture Flow

```
+------------------------+
|  Enterprise Requester  |
|  (Teams AI Bot UI)     |
+-----------+------------+
            | 1. User Query / Adaptive Form
            v
+------------------------+
|  MAF Agent Engine      | <---> [ Google Gemini / LLM ]
|  (FastAPI Backend)     |
+-----------+------------+
            | 2. Create Incident (Urgency/Impact)
            v
+------------------------+
|  ServiceNow Table API  |  (Incident: INC0010025, State: In Progress)
+------------------------+
            | 3. Trigger & Validate Workflow
            v
+------------------------+
|  AutomationEdge (T4)   |  (Processes Password Reset / DL Creation / SAP)
|  RPA Engine            |
+-----------+------------+
            | 4. RPA Execution Confirmed -> State: Resolved (6)
            v
+------------------------+
|  Microsoft Teams Bot   |  (Delivers Resolution Confirmation)
+------------------------+
```

---

## Repository Structure

```
AgenticAI-IT-Automation/
├── .gitignore                                       # Git ignore file (excludes secrets & cache)
├── MAF_ARCHITECTURE_AND_DESIGN.md                  # Comprehensive Architecture & Design Guide
├── MAF_Agent_IT_Service_Automation_Documentation.pdf# Complete project documentation
├── README.md                                       # Project README
├── run_teams_bot.bat                               # Windows launcher script
└── teams_bot_app/
    ├── main.py                                     # FastAPI application, routing & endpoints
    ├── maf_agent_engine.py                         # Microsoft Agent Framework orchestration & T4 RPA connector
    ├── servicenow_client.py                        # ServiceNow REST API client (Basic & OAuth 2.0)
    └── static/
        ├── index.html                              # Microsoft Teams Simulator interface
        ├── app.js                                  # Adaptive Cards 1.5, Persona state & chat rendering
        └── style.css                               # Teams Dark Theme styling
```

---

## Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/abhishekmalwadkar-png/AgenticAI-IT-Automation.git
cd AgenticAI-IT-Automation
```

### 2. Install Dependencies
Ensure you have **Python 3.10+** installed:
```bash
pip install fastapi uvicorn requests google-generativeai pydantic
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# ServiceNow Configuration
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com/
SERVICENOW_USER=your_servicenow_username
SERVICENOW_PASSWORD=your_servicenow_password

# AutomationEdge (T4) RPA Server Configuration
AUTOMATIONEDGE_T4_URL=https://t4.automationedge.com
AUTOMATIONEDGE_T4_USER=your_email@company.com
AUTOMATIONEDGE_T4_PASSWORD=your_password
AUTOMATIONEDGE_T4_ORGCODE=your_org_code

# LLM Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash

# Base URL for Webhooks & Notifications
APP_BASE_URL=http://127.0.0.1:8000
```

### 4. Run the Application in Production

#### Option A: Windows (Automatic Self-Healing Runner)
```cmd
run_teams_bot.bat
```
*(Automatically verifies Python, auto-installs missing dependencies from requirements.txt, and starts the server).*

#### Option B: Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

#### Option C: Docker & Docker Compose (Recommended for Enterprise Clouds)
```bash
docker-compose up -d --build
```

#### Option D: Manual Uvicorn Command
```bash
uvicorn teams_bot_app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Open your browser and navigate to:
**`http://127.0.0.1:8000`**

---

## Health Check & Monitoring
The application includes a production-ready health probe for load balancers and Kubernetes:
* **Endpoint**: `http://127.0.0.1:8000/health`
* **Response**:
```json
{
  "status": "healthy",
  "service": "Agentic_AI_Teams_Bot",
  "version": "2.0.0",
  "uptime_seconds": 120,
  "environment": {
    "python_version": "3.11.x",
    "servicenow_configured": true,
    "automationedge_t4_configured": true,
    "llm_model": "gemini-3.7-flash"
  }
}
```

---

## Production Reliability & Self-Healing
* **Dynamic Dependency Auto-Installer**: On startup, `bootstrap.py` checks all required packages and automatically installs missing libraries on-the-fly without crashing.
* **Non-Blocking Resilience**: If optional extended packages encounter environmental limits, the application falls back gracefully to structured heuristic agent planning.
* **On-Demand Configuration Reloading**: Changes to `.env` (ServiceNow URL, user, password) are loaded on-the-fly with zero downtime.

---

## Author
**Abhishek Malwadkar**  
GitHub: [@abhishekmalwadkar-png](https://github.com/abhishekmalwadkar-png)
