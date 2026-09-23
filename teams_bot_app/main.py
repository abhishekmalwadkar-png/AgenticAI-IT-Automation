import teams_bot_app.bootstrap
import os
import sys
import asyncio
import json
import random
import time
from typing import Dict, Any, List, Optional, Tuple
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from teams_bot_app.servicenow_client import ServiceNowLiveClient

START_TIME = time.time()
app = FastAPI(
    title="Teams AE Bot - IT Service Automation Simulator",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """
    Production health probe endpoint. Returns service uptime, environment status,
    and connectivity health.
    """
    uptime_seconds = int(time.time() - START_TIME)
    snow_configured = bool(os.getenv("SERVICENOW_INSTANCE_URL") and os.getenv("SERVICENOW_USER"))
    t4_configured = bool(os.getenv("AUTOMATIONEDGE_T4_URL") and os.getenv("AUTOMATIONEDGE_T4_USER"))
    
    return JSONResponse({
        "status": "healthy",
        "service": "Agentic_AI_Teams_Bot",
        "version": "2.0.0",
        "uptime_seconds": uptime_seconds,
        "environment": {
            "python_version": sys.version.split()[0],
            "servicenow_configured": snow_configured,
            "automationedge_t4_configured": t4_configured,
            "llm_model": os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
        }
    })

# Load environment variables
def load_env(env_path: Optional[str] = None):
    if env_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

_cached_snow_client: Optional[ServiceNowLiveClient] = None
_cached_creds_tuple: Optional[Tuple[str, str, str, Optional[str], Optional[str]]] = None

def get_snow_client() -> ServiceNowLiveClient:
    """
    Dynamically reloads .env on each invocation and returns an authenticated
    ServiceNowLiveClient configured with the latest credentials.
    """
    global _cached_snow_client, _cached_creds_tuple
    load_env()
    url = os.getenv("SERVICENOW_INSTANCE_URL", "").rstrip("/")
    user = os.getenv("SERVICENOW_USER", "")
    pwd = os.getenv("SERVICENOW_PASSWORD", "")
    client_id = os.getenv("SERVICENOW_CLIENT_ID")
    client_secret = os.getenv("SERVICENOW_CLIENT_SECRET")
    
    current_creds = (url, user, pwd, client_id, client_secret)
    if _cached_snow_client is None or _cached_creds_tuple != current_creds:
        _cached_creds_tuple = current_creds
        print(f"[ServiceNow Config] Reloading ServiceNow client with instance: {url} (user: {user})")
        _cached_snow_client = ServiceNowLiveClient(
            instance_url=url,
            username=user,
            password=pwd,
            client_id=client_id,
            client_secret=client_secret
        )
    return _cached_snow_client

# In-Memory Session Store
class TicketStore:
    def __init__(self):
        self.tickets: Dict[str, Dict[str, Any]] = {}
        self.current_flow: Optional[Dict[str, Any]] = None

    def reset(self):
        self.tickets.clear()
        self.current_flow = None

store = TicketStore()

class UserMessage(BaseModel):
    text: str
    sender: str = "Aarav Sharma (Finance Analyst)"
    software_form: Optional[Dict[str, Any]] = None

class ApprovalAction(BaseModel):
    ticket_id: str
    action: str  # approve, reject, ask_info
    approver: str = "Priya Patel (Finance Director)"

# Supported intent catalogue with slot-filling metadata
INTENT_CATALOG = {
    "sap_access": {
        "keywords": ["sap", "sap access", "sap fi", "sap co", "finance access"],
        "category": "software",
        "title": "SAP Finance Access",
        "requires_approval": True,
        "specialized_agent": "Access Provisioning Agent",
        "execution_method": "RPA (SAP GUI Automation)",
        "tool": "run_legacy_sap_gui_rpa",
        "system": "SAP S/4HANA (Finance Module)",
        "default_role": "Z_FI_GENERAL_LEDGER_READ",
        "slot_question": "Sure! I can help with that. Which SAP role or module access do you need?",
        "slot_options": ["Read access to SAP FI", "SAP CO Controller Access", "SAP MM Purchasing Role"],
        "resolution_details": "Access has been provisioned via SAP GUI RPA Bot (SU01). You can now login to SAP."
    },
    "account_unlock": {
        "keywords": ["unlock", "locked", "account locked", "ad unlock", "entra unlock", "unlock ad"],
        "category": "hardware",
        "title": "Account Unlock Request",
        "requires_approval": True,
        "specialized_agent": "Account Unlock Agent",
        "execution_method": "API (Entra ID / Active Directory)",
        "tool": "unlock_entra_account",
        "system": "Microsoft Entra ID & On-Prem Active Directory",
        "default_role": "User Account (aarav.sharma@company.com)",
        "slot_question": None,
        "resolution_details": "Account lockout flags (badPwdCount & lockoutTime) have been cleared in Active Directory."
    },
    "password_reset": {
        "keywords": ["password", "reset password", "forgot password", "pwd reset"],
        "category": "hardware",
        "title": "Self-Service Password Reset",
        "requires_approval": True,
        "specialized_agent": "Password Reset Agent",
        "execution_method": "API (Entra ID Self-Service API)",
        "tool": "reset_entra_password",
        "system": "Microsoft Entra ID & Active Directory",
        "default_role": "aarav.sharma@company.com",
        "slot_question": None,
        "resolution_details": "Temporary password generated and delivered via secure MFA verification. Forced reset active on next login."
    },
    "mailbox_dl": {
        "keywords": ["mailbox", "distribution list", "dl", "dl creation", "email group", "m365 group"],
        "category": "software",
        "title": "Distribution List Creation",
        "requires_approval": True,
        "specialized_agent": "Mailbox / DL Agent",
        "execution_method": "API (Microsoft Graph / Exchange Online)",
        "tool": "create_distribution_list",
        "system": "Exchange Online (M365)",
        "default_role": "DL: Project Titan Core",
        "slot_question": "I can create that for you. What is the desired display name or alias for the Distribution List?",
        "slot_options": ["Project-Titan-Core", "Finance-Ops-Team", "Global-Sales-Leads"],
        "resolution_details": "Distribution List created and synced across Exchange Global Address List (GAL)."
    },
    "software_license": {
        "keywords": ["software", "license", "power bi", "install", "intune", "powerbi", "app"],
        "category": "software",
        "title": "Software License & Endpoint Deployment",
        "requires_approval": True,
        "specialized_agent": "Software / License Agent",
        "execution_method": "API & RPA (Microsoft Intune + License Portal)",
        "tool": "assign_intune_app_package",
        "system": "Microsoft Intune Endpoint Manager",
        "default_role": "Power BI Pro License + MSI Package",
        "slot_question": "Certainly! Which software package or license do you need installed?",
        "slot_options": ["Power BI Pro License", "Microsoft Visio Plan 2", "Visual Studio Enterprise"],
        "resolution_details": "License assigned in portal and package pushed silently to Windows endpoint via Intune Management Extension."
    }
}

def detect_intent(text: str) -> Optional[str]:
    lower_text = text.lower()
    for intent_key, data in INTENT_CATALOG.items():
        if any(kw in lower_text for kw in data["keywords"]):
            return intent_key
    return None

def detect_urgency_and_impact(text: str, intent_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Dynamically determines Urgency, Impact, Priority level and SLA label
    based on the user's natural language query and context.
    """
    lower = text.lower()
    
    # 1. Critical / P1: Outage, production down, severity 1
    p1_cues = ["production down", "prod down", "system down", "outage", "p1", "critical", "sev 1", "severity 1", "datacenter down", "entire team"]
    if any(cue in lower for cue in p1_cues):
        return {
            "urgency": 1,
            "impact": 1,
            "priority": 1,
            "priority_label": "Critical",
            "sla_text": "P1 (Critical / Emergency 1-Hour SLA)"
        }
    
    # 2. High / P2: Urgent, blocked, ASAP, emergency, month-end deadline
    p2_cues = ["urgent", "asap", "emergency", "immediately", "blocked", "blocking", "high priority", "month end", "quarter end", "p2", "sev 2", "cannot work", "deadline"]
    if any(cue in lower for cue in p2_cues):
        return {
            "urgency": 2,
            "impact": 2,
            "priority": 2,
            "priority_label": "High",
            "sla_text": "P2 (High / Fast-Track 4-Hour SLA)"
        }
        
    # 3. Low / P4: Minor, non-urgent, whenever possible
    p4_cues = ["low priority", "not urgent", "whenever possible", "when free", "take your time", "fyi", "p4", "minor"]
    if any(cue in lower for cue in p4_cues):
        return {
            "urgency": 3,
            "impact": 3,
            "priority": 4,
            "priority_label": "Low",
            "sla_text": "P4 (Low / Standard 3-Day SLA)"
        }
        
    # 4. Standard default (P3 - Medium / Moderate)
    return {
        "urgency": 3,
        "impact": 3,
        "priority": 3,
        "priority_label": "Medium",
        "sla_text": "P3 (Medium / Standard Business SLA)"
    }

def build_descriptive_snow_payload(intent_data: Dict[str, Any], slot_value: str, caller: str, original_query: str, urgency_info: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    if not urgency_info:
        urgency_info = detect_urgency_and_impact(original_query, intent_key=intent_data.get("keywords", [""])[0])
        
    prefix = f"[{urgency_info['priority_label'].upper()}] " if urgency_info['priority'] <= 2 else ""
    short_desc = f"{prefix}[AE Bot] {intent_data['title']} - {slot_value} ({caller})"
    if len(short_desc) > 160:
        short_desc = short_desc[:157] + "..."
        
    req_approval = intent_data.get("requires_approval", False)
    
    desc_lines = [
        "================================================================================",
        "                         IT SERVICE REQUEST DETAILS                             ",
        "================================================================================",
        "",
        "1. SERVICE REQUEST OVERVIEW:",
        f"   • Service Request Title : {intent_data['title']}",
        f"   • Target Enterprise App : {intent_data['system']}",
        f"   • Requested Role / Item : {slot_value}",
        f"   • ITSM Category         : {intent_data['category'].capitalize()}",
        f"   • Urgency & Impact      : {urgency_info['sla_text']} (Impact: {urgency_info['impact']}, Urgency: {urgency_info['urgency']})",
        "",
        "2. CALLER & INTAKE CONTEXT:",
        f"   • Requested For (User)  : {caller}",
        f"   • Intake Virtual Agent  : AE IT Assistant (Microsoft Teams Bot)",
        f"   • Original User Request : \"{original_query}\"",
        f"   • Submission Timestamp  : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "3. GOVERNANCE:",
        f"   • Approval Required     : {'YES (Manager Authorization Required)' if req_approval else 'NO (Pre-approved IT Standard Request)'}",
        "================================================================================"
    ]
    
    description = "\n".join(desc_lines)
    work_notes = (
        f"[AE Bot Intake] Request received from {caller} via Microsoft Teams.\n"
        f"Intent classified as '{intent_data['title']}' for '{slot_value}'. "
        f"Priority evaluated as {urgency_info['priority_label']} (Impact: {urgency_info['impact']}, Urgency: {urgency_info['urgency']})."
    )
    
    return {
        "short_description": short_desc,
        "description": description,
        "work_notes": work_notes
    }

def build_software_request_adaptive_card() -> Dict[str, Any]:
    """
    Constructs an official Microsoft Adaptive Card 1.5 JSON schema for Teams Bot Framework.
    Conforms to https://adaptivecards.io/schemas/adaptive-card.json
    """
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "body": [
            {
                "type": "TextBlock",
                "text": "📦 Software License & Installation Request",
                "weight": "Bolder",
                "size": "Medium",
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": "Select Software Package",
                "weight": "Bolder",
                "size": "Small",
                "spacing": "Medium"
            },
            {
                "type": "Input.ChoiceSet",
                "id": "software_name",
                "isRequired": True,
                "errorMessage": "Please select a software package",
                "value": "Power BI Pro License",
                "choices": [
                    {"title": "Power BI Pro License", "value": "Power BI Pro License"},
                    {"title": "PGadmin", "value": "PGadmin"},
                    {"title": "Visual Studio", "value": "Visual Studio"},
                    {"title": "Docker Desktop Enterprise", "value": "Docker Desktop Enterprise"},
                    {"title": "PyCharm Professional", "value": "PyCharm Professional"}
                ]
            },
            {
                "type": "TextBlock",
                "text": "Preferred Version",
                "weight": "Bolder",
                "size": "Small",
                "spacing": "Medium"
            },
            {
                "type": "Input.ChoiceSet",
                "id": "version",
                "value": "Latest Stable (2024 / v17.8)",
                "choices": [
                    {"title": "Latest Stable (2024 / v17.8)", "value": "Latest Stable (2024 / v17.8)"},
                    {"title": "2023 LTS Enterprise", "value": "2023 LTS Enterprise"},
                    {"title": "Previous Stable Release (v16.x)", "value": "Previous Stable Release (v16.x)"},
                    {"title": "Developer Preview / Beta", "value": "Developer Preview / Beta"}
                ]
            },
            {
                "type": "TextBlock",
                "text": "Username / Target Account",
                "weight": "Bolder",
                "size": "Small",
                "spacing": "Medium"
            },
            {
                "type": "Input.Text",
                "id": "username",
                "value": "aarav.sharma",
                "placeholder": "e.g. aarav.sharma / aarav.sharma@company.com",
                "isRequired": True
            },
            {
                "type": "TextBlock",
                "text": "Reason for Installation / Business Justification",
                "weight": "Bolder",
                "size": "Small",
                "spacing": "Medium"
            },
            {
                "type": "Input.Text",
                "id": "reason",
                "isMultiline": True,
                "placeholder": "e.g., Required for quarterly financial analysis, reporting dashboards & department project deliverables..."
            }
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Submit Software Request",
                "style": "positive",
                "data": {
                    "action": "submit_software_request"
                }
            }
        ]
    }

@app.post("/api/chat")
async def chat_endpoint(msg: UserMessage):
    text = msg.text.strip()
    
    # 1. Check if structured software form was submitted
    if msg.software_form:
        soft_name = msg.software_form.get("software_name", "Power BI Pro")
        version = msg.software_form.get("version", "Latest (2024)")
        username = msg.software_form.get("username", "aarav.sharma")
        reason = msg.software_form.get("reason", "Business requirement")
        
        intent_data = INTENT_CATALOG["software_license"]
        slot_value = f"{soft_name} ({version})"
        
        snow_desc_lines = [
            "================================================================================",
            "                   SOFTWARE INSTALLATION & LICENSE REQUEST                      ",
            "================================================================================",
            f"• Requested Application : {soft_name}",
            f"• Preferred Version     : {version}",
            f"• Target Username       : {username}",
            f"• Business Reason       : {reason}",
            f"• Requester / Caller    : {msg.sender}",
            f"• Policy Approval Req.  : YES (Line Manager Sign-off Required)",
            "================================================================================"
        ]
        
        urgency_info = detect_urgency_and_impact(f"{reason} {soft_name}", intent_key="software_license")
        prefix = f"[{urgency_info['priority_label'].upper()}] " if urgency_info['priority'] <= 2 else ""

        snow_res = get_snow_client().create_incident(
            short_description=f"{prefix}[AE Bot] Software Request: {soft_name} {version} for {username}",
            description="\n".join(snow_desc_lines),
            category="software",
            priority=urgency_info["priority"],
            urgency=urgency_info["urgency"],
            impact=urgency_info["impact"],
            caller=msg.sender,
            work_notes=f"[AE Bot Form Intake] Software: {soft_name}, Version: {version}, Target User: {username}, Reason: {reason} | Evaluated Priority: {urgency_info['priority_label']}"
        )
        
        ticket_number = snow_res.get("ticket_number") or f"INC{random.randint(1000000, 9999999)}"
        sys_id = snow_res.get("sys_id", "")
        snow_link = snow_res.get("link", f"{get_snow_client().instance_url}/nav_to.do?uri=incident.do")
        
        ticket = {
            "ticket_number": ticket_number,
            "sys_id": sys_id,
            "request_type": f"Software Request: {soft_name}",
            "category": "software",
            "priority": urgency_info["priority_label"],
            "requested_for": f"{msg.sender} (Account: {username})",
            "requested_item": f"{soft_name} (v{version}) for {username} - Reason: {reason}",
            "status": "Awaiting Approval",
            "approval_required": True,
            "approver": "Priya Patel (Finance Director)",
            "specialized_agent": "Software / License Agent",
            "execution_method": "API & RPA (Microsoft Intune + License Portal)",
            "tool": "assign_intune_app_package",
            "created_at": time.strftime("%H:%M:%S"),
            "resolution_details": f"License for {soft_name} ({version}) provisioned for {username} and package pushed to endpoint.",
            "snow_link": snow_link,
            "is_live_snow": snow_res.get("success", False),
            "logs": [
                f"[{time.strftime('%H:%M:%S')}] MAF Form Intake: Collected Software='{soft_name}', Version='{version}', Target User='{username}', Reason='{reason}'.",
                f"[{time.strftime('%H:%M:%S')}] Live ServiceNow incident created: {ticket_number} at {get_snow_client().instance_url}."
            ]
        }
        store.tickets[ticket_number] = ticket
        store.current_flow = {"intent_key": "software_license", "ticket_id": ticket_number, "awaiting_slot": False}
        
        bot_reply = f"Got it! I've created request **{ticket_number}** in ServiceNow for **{soft_name} ({version})** for user **{username}**."
        bot_reply += f"\n\n🔔 *An approval request for Incident ID **{ticket_number}** has been sent to your **Activity Bell (🔔) & Approvals Hub**.*"
        
        return JSONResponse({
            "reply": bot_reply,
            "ticket": ticket,
            "stage": 3,
            "requires_approval": True
        })

    # 2. Check if we are waiting for a missing slot in conversational flow
    if store.current_flow and store.current_flow.get("awaiting_slot"):
        intent_key = store.current_flow["intent_key"]
        intent_data = INTENT_CATALOG[intent_key]
        slot_value = text
        store.current_flow["slot_value"] = slot_value
        store.current_flow["awaiting_slot"] = False
        original_query = store.current_flow.get("initial_prompt", text)
        
        # Build rich, highly-descriptive ServiceNow payload with dynamic Urgency & Impact
        urgency_info = detect_urgency_and_impact(f"{original_query} {slot_value}", intent_key=intent_key)
        snow_payload = build_descriptive_snow_payload(
            intent_data=intent_data,
            slot_value=slot_value,
            caller=msg.sender,
            original_query=f"{original_query} -> Specified: {slot_value}",
            urgency_info=urgency_info
        )
        
        snow_res = get_snow_client().create_incident(
            short_description=snow_payload["short_description"],
            description=snow_payload["description"],
            category=intent_data["category"],
            priority=urgency_info["priority"],
            urgency=urgency_info["urgency"],
            impact=urgency_info["impact"],
            caller=msg.sender,
            work_notes=snow_payload["work_notes"]
        )
        
        ticket_number = snow_res.get("ticket_number") or f"INC{random.randint(1000000, 9999999)}"
        sys_id = snow_res.get("sys_id", "")
        snow_link = snow_res.get("link", f"{get_snow_client().instance_url}/nav_to.do?uri=incident.do")
        
        ticket = {
            "ticket_number": ticket_number,
            "sys_id": sys_id,
            "request_type": intent_data["title"],
            "category": intent_data["category"],
            "priority": urgency_info["priority_label"],
            "requested_for": msg.sender,
            "requested_item": f"{intent_data['system']} ({slot_value})",
            "status": "Awaiting Approval" if intent_data["requires_approval"] else "Approved (Auto-Policy)",
            "approval_required": intent_data["requires_approval"],
            "approver": "Priya Patel (Finance Director)" if intent_data["requires_approval"] else "Auto-Approved by Policy",
            "specialized_agent": intent_data["specialized_agent"],
            "execution_method": intent_data["execution_method"],
            "tool": intent_data["tool"],
            "created_at": time.strftime("%H:%M:%S"),
            "resolution_details": intent_data["resolution_details"],
            "snow_link": snow_link,
            "is_live_snow": snow_res.get("success", False),
            "logs": [
                f"[{time.strftime('%H:%M:%S')}] MAF Triage Agent extracted parameters: Intent='{intent_data['title']}', Role/Item='{slot_value}'.",
                f"[{time.strftime('%H:%M:%S')}] Descriptive LIVE ServiceNow incident created: {ticket_number} at {get_snow_client().instance_url}."
            ]
        }
        store.tickets[ticket_number] = ticket
        store.current_flow["ticket_id"] = ticket_number

        bot_reply = f"Got it! I've created request **{ticket_number}** in ServiceNow for **{slot_value}** and will keep you updated here."
        if intent_data["requires_approval"]:
            bot_reply += f"\n\n🔔 *An approval request for Incident ID **{ticket_number}** has been sent to your **Activity Bell (🔔) & Approvals Hub**.*"
            
        return JSONResponse({
            "reply": bot_reply,
            "ticket": ticket,
            "stage": 3 if intent_data["requires_approval"] else 2,
            "requires_approval": intent_data["requires_approval"]
        })

    # 3. Parse new incoming request
    intent_key = detect_intent(text)
    
    if not intent_key:
        return JSONResponse({
            "reply": "Hello! I can help you with IT requests such as SAP Access, Account Unlock, Password Reset, Distribution Lists, and Software Licenses. What would you like to request?",
            "stage": 1,
            "show_options": True
        })

    intent_data = INTENT_CATALOG[intent_key]

    # 4. Check for missing details (Conversational slot-filling)
    # If the user did not specify the specific role/details, ask for it
    lower_t = text.lower()
    needs_slot = False
    if intent_key == "software_license":
        # Always present the interactive software request form card for software requests
        needs_slot = True
    elif intent_data.get("slot_question"):
        if intent_key == "sap_access" and not any(r in lower_t for r in ["fi", "co", "mm", "sd", "read", "write", "controller"]):
            needs_slot = True
        elif intent_key == "mailbox_dl" and not any(r in lower_t for r in ["project", "team", "sales", "finance", "core", "ops"]):
            needs_slot = True

    if needs_slot:
        store.current_flow = {
            "intent_key": intent_key,
            "awaiting_slot": True,
            "initial_prompt": text
        }
        
        # If it is software installation, render the official Microsoft Adaptive Card 1.5!
        if intent_key == "software_license":
            adaptive_card_payload = build_software_request_adaptive_card()
            return JSONResponse({
                "reply": "Please complete the software installation request form below:",
                "stage": 1,
                "adaptive_card": adaptive_card_payload,
                "form_card": adaptive_card_payload
            })

        return JSONResponse({
            "reply": intent_data["slot_question"],
            "stage": 1,
            "suggestions": intent_data.get("slot_options", [])
        })

    # 4. Details already present in the prompt -> Create ticket immediately
    slot_value = intent_data["default_role"]
    for option in intent_data.get("slot_options", []):
        if option.lower() in lower_t:
            slot_value = option
            break

    # Build rich, highly-descriptive ServiceNow payload with dynamic Urgency & Impact
    urgency_info = detect_urgency_and_impact(text, intent_key=intent_key)
    snow_payload = build_descriptive_snow_payload(
        intent_data=intent_data,
        slot_value=slot_value,
        caller=msg.sender,
        original_query=text,
        urgency_info=urgency_info
    )

    snow_res = get_snow_client().create_incident(
        short_description=snow_payload["short_description"],
        description=snow_payload["description"],
        category=intent_data["category"],
        priority=urgency_info["priority"],
        urgency=urgency_info["urgency"],
        impact=urgency_info["impact"],
        caller=msg.sender,
        work_notes=snow_payload["work_notes"]
    )
    
    ticket_number = snow_res.get("ticket_number") or f"INC{random.randint(1000000, 9999999)}"
    sys_id = snow_res.get("sys_id", "")
    snow_link = snow_res.get("link", f"{get_snow_client().instance_url}/nav_to.do?uri=incident.do")

    ticket = {
        "ticket_number": ticket_number,
        "sys_id": sys_id,
        "request_type": intent_data["title"],
        "category": intent_data["category"],
        "priority": urgency_info["priority_label"],
        "requested_for": msg.sender,
        "requested_item": f"{intent_data['system']} ({slot_value})",
        "status": "New (Ticket Created)",
        "approval_required": intent_data["requires_approval"],
        "approver": "Priya Patel (Finance Director)" if intent_data["requires_approval"] else "Auto-Approved by Policy",
        "specialized_agent": intent_data["specialized_agent"],
        "execution_method": intent_data["execution_method"],
        "tool": intent_data["tool"],
        "created_at": time.strftime("%H:%M:%S"),
        "resolution_details": intent_data["resolution_details"],
        "snow_link": snow_link,
        "is_live_snow": snow_res.get("success", False),
        "logs": [
            f"[{time.strftime('%H:%M:%S')}] MAF Triage Agent extracted intent: '{intent_data['title']}'.",
            f"[{time.strftime('%H:%M:%S')}] Descriptive LIVE ServiceNow incident created: {ticket_number} at {get_snow_client().instance_url}."
        ]
    }
    store.tickets[ticket_number] = ticket
    store.current_flow = {"intent_key": intent_key, "ticket_id": ticket_number, "awaiting_slot": False}

    bot_reply = f"Got it! I've created request **{ticket_number}** in ServiceNow for **{intent_data['title']}**."
    if intent_data["requires_approval"]:
        bot_reply += f"\n\n🔔 *An approval request for Incident ID **{ticket_number}** has been sent to your **Activity Bell (🔔) & Approvals Hub**.*"
        
    return JSONResponse({
        "reply": bot_reply,
        "ticket": ticket,
        "stage": 3 if intent_data["requires_approval"] else 2,
        "requires_approval": intent_data["requires_approval"]
    })

@app.post("/api/approval")
async def approval_endpoint(payload: ApprovalAction):
    ticket_id = payload.ticket_id
    if ticket_id not in store.tickets:
        # Try fetching from live ServiceNow
        snow_inc = get_snow_client().get_incident_by_number(ticket_id)
        if snow_inc:
            store.tickets[ticket_id] = {
                "ticket_number": ticket_id,
                "sys_id": snow_inc.get("sys_id"),
                "request_type": snow_inc.get("short_description", "IT Service Request"),
                "category": snow_inc.get("category", "software"),
                "priority": snow_inc.get("priority", "3"),
                "requested_for": snow_inc.get("caller_id", "john.doe"),
                "requested_item": snow_inc.get("short_description", "Software Request"),
                "status": "Pending Approval",
                "approval_required": True,
                "approver": payload.approver,
                "specialized_agent": "IT Automation Agent",
                "execution_method": "RPA Automation",
                "tool": "AutomationEdge T4 Agent",
                "created_at": time.strftime("%H:%M:%S"),
                "resolution_details": "Automated fulfillment via AutomationEdge T4",
                "snow_link": f"{get_snow_client().instance_url}/nav_to.do?uri=incident.do?sys_id={snow_inc.get('sys_id')}",
                "is_live_snow": True,
                "logs": [f"[{time.strftime('%H:%M:%S')}] Ticket {ticket_id} loaded from live ServiceNow."]
            }
        else:
            return JSONResponse({"error": "Ticket not found"}, status_code=404)

    ticket = store.tickets[ticket_id]
    sys_id = ticket.get("sys_id")
    
    if payload.action == "approve":
        ticket["status"] = "Approved"
        t_now = time.strftime('%H:%M:%S')
        utc_now = time.strftime('%Y-%m-%d %H:%M:%S UTC')
        approval_note = f"Approved by: {payload.approver}\nAction: Approved via Microsoft Teams Adaptive Card\nTimestamp: {utc_now}\nStatus: Approved for Automated Execution"
        ticket["logs"].append(f"[{t_now}] Approval granted by {payload.approver} via Teams Adaptive Card.")
        ticket["logs"].append(f"[{t_now}] Live ServiceNow ticket note updated: 'Approved by: {payload.approver}'")
        
        # Update live ServiceNow ticket work notes & activity journal
        if sys_id:
            get_snow_client().update_work_notes(sys_id, approval_note, customer_visible=True)
        
        return JSONResponse({
            "status": "Approved",
            "ticket": ticket,
            "message": f"Approval confirmed by {payload.approver}. Note added to ServiceNow ticket."
        })
    elif payload.action == "reject":
        ticket["status"] = "Rejected"
        t_now = time.strftime('%H:%M:%S')
        utc_now = time.strftime('%Y-%m-%d %H:%M:%S UTC')
        rejection_note = f"Rejected by: {payload.approver}\nAction: Rejected via Microsoft Teams Adaptive Card\nTimestamp: {utc_now}\nStatus: Closed / Rejected"
        if sys_id:
            get_snow_client().update_work_notes(sys_id, rejection_note, state="8", customer_visible=True)
        ticket["logs"].append(f"[{t_now}] Request REJECTED by {payload.approver}.")
        ticket["logs"].append(f"[{t_now}] Live ServiceNow ticket note updated: 'Rejected by: {payload.approver}'")
        return JSONResponse({
            "status": "Rejected",
            "ticket": ticket,
            "message": f"Request {ticket_id} was rejected by {payload.approver}."
        })
    else:
        if sys_id:
            get_snow_client().update_work_notes(sys_id, f"Clarification requested by {payload.approver} in Microsoft Teams.")
        ticket["logs"].append(f"[{time.strftime('%H:%M:%S')}] Clarification requested by {payload.approver}.")
        return JSONResponse({
            "status": "Info Requested",
            "ticket": ticket,
            "message": "Clarification message sent to requester in Teams."
        })

@app.post("/api/webhook/ticket-created")
async def webhook_ticket_created(request: Request):
    """
    Webhook callback endpoint to ingest tickets created externally by the AE Teams Chatbot.
    Handles standard JSON as well as Process Studio MJS unquoted string outputs.
    """
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8", errors="ignore").strip()
    
    payload: Dict[str, Any] = {}
    if body_str:
        try:
            payload = json.loads(body_str)
        except Exception:
            # Fix unquoted values from Process Studio (e.g., {"additionalInfo":test,...})
            import re
            fixed_str = re.sub(r':\s*([a-zA-Z0-9_\-\./]+)\s*([,}])', r':"\1"\2', body_str)
            try:
                payload = json.loads(fixed_str)
            except Exception:
                payload = {"raw_message": body_str}

    # Check if this is an error payload from Process Studio
    if payload.get("status") == "Failure" or payload.get("success") == "false":
        return JSONResponse({
            "status": "acknowledged",
            "message": f"AE Bot reported execution notice: {payload.get('details', 'Failure')}",
            "payload": payload
        })

    raw_ticket = payload.get("incident_id") or payload.get("ticket_number") or payload.get("number") or payload.get("value") or ""
    import re
    match = re.search(r'(INC\d+)', str(raw_ticket), re.IGNORECASE)
    ticket_number = match.group(1).upper() if match else f"INC{random.randint(1000000, 9999999)}"
    
    sys_id = payload.get("sys_id", "")
    short_desc = payload.get("short_description") or payload.get("issue") or payload.get("workflow_name") or "IT Service Request"
    caller = payload.get("caller") or payload.get("requested_for") or payload.get("additionalInfo") or "Aarav Sharma"
    category = payload.get("category", "software")
    
    # Detect intent from short description
    intent_key = detect_intent(short_desc) or "account_unlock"
    intent_data = INTENT_CATALOG.get(intent_key, INTENT_CATALOG["account_unlock"])
    
    snow_base = get_snow_client().instance_url
    snow_link = f"{snow_base}/nav_to.do?uri=incident.do?sys_id={sys_id}" if sys_id else f"{snow_base}/nav_to.do?uri=incident.do"
    
    ticket = {
        "ticket_number": str(ticket_number),
        "sys_id": sys_id,
        "request_type": intent_data["title"],
        "category": category,
        "priority": "Medium",
        "requested_for": caller,
        "requested_item": f"{intent_data['system']} ({short_desc})",
        "status": "Awaiting Approval" if intent_data["requires_approval"] else "Approved",
        "approval_required": intent_data["requires_approval"],
        "approver": "Priya Patel (Finance Director)" if intent_data["requires_approval"] else "Auto-Approved by Policy",
        "specialized_agent": intent_data["specialized_agent"],
        "execution_method": intent_data["execution_method"],
        "tool": intent_data["tool"],
        "created_at": time.strftime("%H:%M:%S"),
        "resolution_details": intent_data["resolution_details"],
        "snow_link": snow_link,
        "is_live_snow": True,
        "logs": [
            f"[{time.strftime('%H:%M:%S')}] Ingested from external AE Teams Chatbot: {ticket_number}.",
            f"[{time.strftime('%H:%M:%S')}] MAF Triage Agent classified intent as '{intent_data['title']}'."
        ]
    }
    store.tickets[str(ticket_number)] = ticket
    store.current_flow = {"intent_key": intent_key, "ticket_id": str(ticket_number), "awaiting_slot": False}
    
    return JSONResponse({
        "status": "success",
        "message": f"Ticket {ticket_number} ingested successfully by MAF Orchestrator.",
        "ticket": ticket,
        "requires_approval": intent_data["requires_approval"]
    })

from teams_bot_app.maf_agent_engine import MAFOrchestratorAgent

maf_orchestrator = MAFOrchestratorAgent()

@app.post("/api/fulfill/{ticket_id}")
async def fulfill_endpoint(ticket_id: str, request: Request):
    if ticket_id not in store.tickets:
        snow_inc = get_snow_client().get_incident_by_number(ticket_id)
        if snow_inc:
            store.tickets[ticket_id] = {
                "ticket_number": ticket_id,
                "sys_id": snow_inc.get("sys_id"),
                "request_type": snow_inc.get("short_description", "IT Service Request"),
                "category": snow_inc.get("category", "software"),
                "priority": snow_inc.get("priority", "3"),
                "requested_for": snow_inc.get("caller_id", "john.doe"),
                "requested_item": snow_inc.get("short_description", "Software Request"),
                "status": "Approved",
                "approval_required": True,
                "approver": "Priya Patel (Finance Director)",
                "specialized_agent": "IT Automation Agent",
                "execution_method": "RPA Automation",
                "tool": "AutomationEdge T4 Agent",
                "created_at": time.strftime("%H:%M:%S"),
                "resolution_details": "Automated fulfillment via AutomationEdge T4",
                "snow_link": f"{get_snow_client().instance_url}/nav_to.do?uri=incident.do?sys_id={snow_inc.get('sys_id')}",
                "is_live_snow": True,
                "logs": [f"[{time.strftime('%H:%M:%S')}] Ticket {ticket_id} loaded from live ServiceNow."]
            }
        else:
            return JSONResponse({"error": "Ticket not found"}, status_code=404)

    ticket = store.tickets[ticket_id]
    ticket["status"] = "Fulfillment in Progress"
    sys_id = ticket.get("sys_id")
    
    # Check if simulation flag for failure was requested
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    simulate_failure = body.get("simulate_failure", False)

    # 1. MAF Stage 4: Evaluate approved ticket & construct Execution Plan
    plan = maf_orchestrator.evaluate_and_plan(ticket)
    
    # 2. MAF Stage 5: Execute Tool / T4 RPA Dispatch with Exception Handling & Human Escalation
    success, result_data, telemetry_logs = await maf_orchestrator.execute_plan(plan, simulate_failure=simulate_failure, raw_ticket=ticket)
    
    # Append logs to ticket
    for log in telemetry_logs:
        ticket["logs"].append(log)

    if success:
        ticket["status"] = "Resolved"
        resolution_msg = f"Successfully validated and fulfilled via AutomationEdge T4 workflow '{plan.target_workflow_name}' (ID: {plan.target_workflow_id})."
        if sys_id:
            get_snow_client().close_incident(sys_id, resolution_msg)
            ticket["logs"].append(f"[{time.strftime('%H:%M:%S')}] ServiceNow incident {ticket_id} state changed to 6 (Resolved).")

        completion_card = {
            "title": "Your request has been successfully resolved!",
            "ticket_number": ticket_id,
            "request_type": ticket["request_type"],
            "status": "Resolved",
            "details": resolution_msg,
            "snow_link": ticket.get("snow_link", "")
        }

        return JSONResponse({
            "success": True,
            "ticket": ticket,
            "plan": {
                "specialized_agent": plan.specialized_agent,
                "execution_method": plan.execution_method,
                "target_server": plan.target_server,
                "steps": plan.steps
            },
            "completion_card": completion_card
        })
    else:
        # Human-in-the-Loop Escalation to Tier-2
        ticket["status"] = "Escalated to Tier-2 Support"
        escalation_notes = f"MAF Automated fulfillment halted: {result_data.get('reason')}. Reassigned to {result_data.get('assigned_to')}."
        if sys_id:
            get_snow_client().update_work_notes(sys_id, f"[MAF Tier-2 Escalation] {escalation_notes}")

        return JSONResponse({
            "success": False,
            "escalated": True,
            "ticket": ticket,
            "plan": {
                "specialized_agent": plan.specialized_agent,
                "execution_method": plan.execution_method,
                "target_server": plan.target_server,
                "steps": plan.steps
            },
            "escalation": {
                "title": "Request Escalated to Human IT Support (Tier-2)",
                "ticket_number": ticket_id,
                "reason": result_data.get("reason"),
                "assigned_to": result_data.get("assigned_to"),
                "snow_link": ticket.get("snow_link", "")
            }
        })

@app.post("/api/reset")
async def reset_state():
    store.reset()
    return JSONResponse({"status": "reset"})

# Mount static files dynamically
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
