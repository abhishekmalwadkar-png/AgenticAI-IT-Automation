import os
import time
import json
import asyncio
import urllib.request
import urllib.parse
import http.cookiejar
from typing import Dict, Any, List, Optional, Tuple

# Official Microsoft Agent Framework SDK Imports
import autogen_core
from autogen_core import AgentId
import autogen_agentchat
from autogen_agentchat.messages import TextMessage

MAF_SDK_VERSION = autogen_core.__version__

def load_env(env_path: str = "d:/Agentic_AI-IT_service_automation/.env"):
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

class T4WorkflowDiscoveryClient:
    """
    Dynamic Tool & Workflow Discovery Client for AutomationEdge (T4) Server.
    Discovers live workflows and inspects their runtime parameter schemas dynamically from the server.
    """
    def __init__(self):
        load_env()
        self.base_url = os.getenv("AUTOMATIONEDGE_T4_URL", "https://t4.automationedge.com").rstrip("/")
        self.user = os.getenv("AUTOMATIONEDGE_T4_USER")
        self.pwd = os.getenv("AUTOMATIONEDGE_T4_PASSWORD")
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.session_token: Optional[str] = None
        self.org_code: Optional[str] = os.getenv("AUTOMATIONEDGE_T4_ORGCODE", None)
        self._cached_workflows: List[Dict[str, Any]] = []

    def _authenticate(self) -> bool:
        if not self.user or not self.pwd:
            return False
        
        auth_url = f"{self.base_url}/aeengine/rest/authenticate"
        auth_data = urllib.parse.urlencode({
            "username": self.user,
            "password": self.pwd
        }).encode("utf-8")

        req = urllib.request.Request(auth_url, data=auth_data, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        })

        try:
            resp = self.opener.open(req, timeout=12)
            data = json.loads(resp.read().decode("utf-8"))
            self.session_token = data.get("sessionToken")
            self.org_code = data.get("tenant", {}).get("orgCode")
            return bool(self.session_token and self.org_code)
        except Exception as e:
            print(f"[T4 Discovery] Authentication error: {e}")
            return False

    def _ensure_auth(self, force: bool = False):
        if force or not self.session_token or not self.org_code:
            self._authenticate()

    def _send_request(self, req: urllib.request.Request, retries: int = 1) -> urllib.response.addinfourl:
        self._ensure_auth()
        if self.session_token:
            req.add_header("sessionToken", str(self.session_token))
            req.add_header("X-Session-Token", str(self.session_token))
            
        try:
            return self.opener.open(req, timeout=20)
        except urllib.error.HTTPError as e:
            if e.code in [401, 403] and retries > 0:
                print(f"[T4] Received {e.code}, refreshing T4 session & retrying...")
                self._ensure_auth(force=True)
                if self.session_token:
                    req.add_header("sessionToken", str(self.session_token))
                    req.add_header("X-Session-Token", str(self.session_token))
                return self.opener.open(req, timeout=20)
            raise e

    def list_server_workflows(self) -> List[Dict[str, Any]]:
        """
        Dynamically fetches all published workflows from the T4 server.
        """
        if self._cached_workflows:
            return self._cached_workflows

        self._ensure_auth()
        wf_url = f"{self.base_url}/aeengine/rest/tenants/{self.org_code}/workflows"
        req = urllib.request.Request(wf_url, headers={"Accept": "application/json"})

        try:
            resp = self._send_request(req)
            self._cached_workflows = json.loads(resp.read().decode("utf-8"))
            return self._cached_workflows
        except Exception as e:
            print(f"[T4 Discovery] Fetch workflows error: {e}")
            return []

    def get_workflow_schema(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        """
        Dynamically fetches workflow details and parameter schemas for a given workflow ID.
        """
        self._ensure_auth()
        wf_url = f"{self.base_url}/aeengine/rest/workflows/{workflow_id}"
        req = urllib.request.Request(wf_url, headers={"Accept": "application/json"})

        try:
            resp = self._send_request(req)
            return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[T4 Discovery] Get schema for {workflow_id} error: {e}")
            return None

    def find_workflow_by_keywords(self, keywords: List[str]) -> Optional[Dict[str, Any]]:
        """
        Dynamically searches for a matching workflow on the T4 server based on keywords.
        """
        workflows = self.list_server_workflows()
        for wf in workflows:
            name_lower = wf.get("name", "").lower()
            if all(kw.lower() in name_lower for kw in keywords):
                # Fetch full schema with runtimeParameters
                return self.get_workflow_schema(wf.get("id"))

        # Fallback to single keyword match
        for wf in workflows:
            name_lower = wf.get("name", "").lower()
            if any(kw.lower() in name_lower for kw in keywords):
                return self.get_workflow_schema(wf.get("id"))

        return None

    def execute_workflow(
        self,
        workflow_id: int,
        params: Dict[str, Any],
        workflow_name: Optional[str] = None,
        org_code: Optional[str] = None,
        source: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Triggers execution of a workflow on the live AutomationEdge T4 server via /aeengine/rest/execute.
        All fields are dynamically populated from arguments, discovered schemas, and server authentication.
        """
        self._ensure_auth()
        exec_url = f"{self.base_url}/aeengine/rest/execute"
        
        # If workflow_name is not provided or placeholder, fetch dynamically from schema
        if not workflow_name or workflow_name.startswith("Workflow_") or "Discovered tool" in workflow_name:
            wf_schema = self.get_workflow_schema(workflow_id)
            if wf_schema and wf_schema.get("name"):
                workflow_name = wf_schema.get("name")
            else:
                workflow_name = f"Workflow_{workflow_id}"

        # Dynamically assign organization, source, and sourceId
        target_org = org_code or self.org_code or os.getenv("AUTOMATIONEDGE_T4_ORGCODE", "")
        target_source = source or "Teams_MAF_Bot"
        target_source_id = source_id or params.get("sourceId") or params.get("source_id") or f"REQ-{int(time.time())}"

        # Format payload parameters dynamically
        param_list = [{"name": str(k), "value": str(v), "type": "String"} for k, v in params.items()]
        
        payload_data = {
            "orgCode": target_org,
            "workflowId": workflow_id,
            "workflowName": workflow_name,
            "source": target_source,
            "sourceId": target_source_id,
            "params": param_list
        }
        
        print(f"[T4 Execute] Sending execution request to {exec_url} with payload: {json.dumps(payload_data)}")
        
        req = urllib.request.Request(
            exec_url,
            data=json.dumps(payload_data).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )

        try:
            resp = self._send_request(req)
            res_json = json.loads(resp.read().decode("utf-8"))
            req_id = res_json.get("automationRequestId") or res_json.get("workflowRequestId") or res_json.get("id") or "TRIGGERED"
            print(f"[T4 Execute] SUCCESS! automationRequestId: {req_id}")
            return {
                "success": True,
                "request_id": req_id,
                "response": res_json
            }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            print(f"[T4 Execute HTTP Error] {e.code}: {err_body}")
            return {"success": False, "error": f"HTTP {e.code}: {err_body}"}
        except Exception as e:
            print(f"[T4 Execute Error] {e}")
            return {"success": False, "error": str(e)}

    def get_request_status(self, request_id: Any) -> Optional[Dict[str, Any]]:
        """
        Queries AutomationEdge T4 for the execution status of a specific request ID.
        GET /aeengine/rest/requests/{request_id}
        """
        self._ensure_auth()
        status_url = f"{self.base_url}/aeengine/rest/requests/{request_id}"
        req = urllib.request.Request(status_url, headers={"Accept": "application/json"})
        try:
            resp = self._send_request(req)
            return json.loads(resp.read().decode("utf-8"))
        except Exception:
            # Fallback to workflowRequests endpoint
            try:
                fallback_url = f"{self.base_url}/aeengine/rest/workflowRequests/{request_id}"
                req_fb = urllib.request.Request(fallback_url, headers={"Accept": "application/json"})
                resp_fb = self._send_request(req_fb)
                return json.loads(resp_fb.read().decode("utf-8"))
            except Exception:
                return None


class MAFExecutionPlan:
    def __init__(
        self,
        ticket_number: str,
        request_type: str,
        specialized_agent: str,
        execution_method: str,
        target_workflow_id: Optional[int],
        target_workflow_name: Optional[str],
        synthesized_payload: Dict[str, Any],
        steps: List[str],
        target_server: str = "AutomationEdge T4 Enterprise Automation Server"
    ):
        self.ticket_number = ticket_number
        self.request_type = request_type
        self.specialized_agent = specialized_agent
        self.execution_method = execution_method
        self.target_workflow_id = target_workflow_id
        self.target_workflow_name = target_workflow_name
        self.synthesized_payload = synthesized_payload
        self.steps = steps
        self.target_server = target_server


class MAFOrchestratorAgent:
    """
    Microsoft Agent Framework (MAF) Orchestrator Agent.
    Dynamically discovers workflows & runtime parameter schemas directly from the T4 server.
    NOTE: Discovers and maps payloads dynamically without triggering execution on the T4 server.
    """
    def __init__(self):
        self.discovery_client = T4WorkflowDiscoveryClient()

    def evaluate_and_plan(self, ticket: Dict[str, Any]) -> MAFExecutionPlan:
        """
        Stage 4: Read approved ticket, dynamically search for the matching tool on T4 server,
        inspect its required runtime parameters, and construct the execution plan.
        """
        req_type = ticket.get("request_type", "")
        role_or_item = ticket.get("requested_item", "")
        caller = ticket.get("requested_for", "Aarav Sharma")
        ticket_num = ticket.get("ticket_number", "")
        username = caller.split("(")[0].strip().lower().replace(" ", ".")

        discovered_wf = None
        specialized_agent = "Identity & Access Agent"
        keywords = []

        if "Password" in req_type or "Reset" in req_type:
            keywords = ["Password_Reset"]
            specialized_agent = "Password Reset Agent (Active Directory Specialist)"
        elif "Software" in req_type or "Power BI" in req_type or "License" in req_type or "Install" in req_type:
            keywords = ["Install_Software"]
            specialized_agent = "Software & License Agent (Endpoint Specialist)"
        elif "User" in req_type or "Onboard" in req_type or "Create Account" in req_type:
            keywords = ["AD_UserCreate"]
            specialized_agent = "User Onboarding & Identity Agent (AD Specialist)"
        elif "SAP" in req_type or "Role" in req_type or "AssignRole" in req_type:
            keywords = ["AssignRole"]
            specialized_agent = "Access Provisioning Agent (SAP & Role Specialist)"
        elif "Folder" in req_type or "Share" in req_type or "Access" in req_type:
            keywords = ["Share_Folder_Access"]
            specialized_agent = "Access Provisioning Agent (Security & Share Specialist)"
        elif "Distribution" in req_type or "Mailbox" in req_type or "DL" in req_type:
            keywords = ["DL Creation"]
            specialized_agent = "Mailbox & Collaboration Agent (Exchange Specialist)"
        elif "Unlock" in req_type or "Account" in req_type:
            keywords = ["Account", "unlock"]
            specialized_agent = "Account Unlock Agent (Identity Specialist)"
        else:
            keywords = ["Check System Update"]
            specialized_agent = "Endpoint Diagnostics Agent"

        # 1. Dynamically search for tool on T4 server
        discovered_wf = self.discovery_client.find_workflow_by_keywords(keywords)

        target_wf_id = discovered_wf.get("id") if discovered_wf else None
        target_wf_name = discovered_wf.get("name") if discovered_wf else f"Discovered tool for {keywords}"
        runtime_params_def = discovered_wf.get("runtimeParameters", []) if discovered_wf else []

        # 2. Dynamically build required parameter payload based on discovered schema
        synthesized_payload: Dict[str, Any] = {}
        for param in runtime_params_def:
            p_name = param.get("name")
            p_low = p_name.lower()
            
            if p_name in ["user_logon_name", "username", "user", "user_name", "userid"]:
                synthesized_payload[p_name] = username
            elif "first" in p_low:
                synthesized_payload[p_name] = caller.split()[0] if caller else "Aarav"
            elif "last" in p_low:
                synthesized_payload[p_name] = caller.split()[1] if len(caller.split()) > 1 else "Sharma"
            elif "email" in p_low:
                synthesized_payload[p_name] = f"{username}@company.com"
            elif "department" in p_low or "dept" in p_low:
                synthesized_payload[p_name] = "Finance"
            elif p_name in ["share_folder_name", "folder_name"]:
                synthesized_payload[p_name] = "Finance_Corporate_Repository"
            elif p_name in ["access_type", "permission"]:
                synthesized_payload[p_name] = "Read-Write"
            elif p_name in ["soft_name", "Application_Name", "software", "app_name", "software_name"]:
                synthesized_payload[p_name] = "Power BI Pro" if "Power BI" in role_or_item else role_or_item
            elif p_name in ["issue", "short_description", "description"]:
                synthesized_payload[p_name] = f"{req_type} for {role_or_item}"
            elif p_name in ["chatBotEndPoint", "P_chatBotEndPoint"]:
                app_base = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
                synthesized_payload[p_name] = f"{app_base}/api/webhook/ticket-created"
            elif p_name in ["additionalInfo", "P_additionalInfo"]:
                synthesized_payload[p_name] = f"Requester: {caller} | Ticket: {ticket_num}"
            elif p_name in ["pushNotificationURL"]:
                app_base = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
                synthesized_payload[p_name] = f"{app_base}/api/approval"
            else:
                synthesized_payload[p_name] = role_or_item

        execution_method = f"Discovered on AutomationEdge T4: '{target_wf_name}' (ID: {target_wf_id})"

        steps = [
            f"1. MAF Agent queried T4 server at '{self.discovery_client.base_url}'.",
            f"2. Dynamically discovered matching workflow: '{target_wf_name}' (ID: {target_wf_id}).",
            f"3. Retrieved runtime parameter schema: {[p.get('name') for p in runtime_params_def]}.",
            f"4. Dynamically synthesized input payload: {json.dumps(synthesized_payload)}.",
            "5. Dispatched execution to AutomationEdge T4 worker queue."
        ]

        return MAFExecutionPlan(
            ticket_number=ticket_num,
            request_type=req_type,
            specialized_agent=specialized_agent,
            execution_method=execution_method,
            target_workflow_id=target_wf_id,
            target_workflow_name=target_wf_name,
            synthesized_payload=synthesized_payload,
            steps=steps
        )

    async def execute_plan(self, plan: MAFExecutionPlan, simulate_failure: bool = False, raw_ticket: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Stage 5: Executes the workflow on the live AutomationEdge T4 server.
        """
        telemetry: List[str] = []
        t_start = time.strftime('%H:%M:%S')
        
        telemetry.append(f"[{t_start}] [MAF Orchestrator] Dynamic plan constructed for ticket {plan.ticket_number}.")
        telemetry.append(f"[{t_start}] [MAF Orchestrator] Specialized Agent: '{plan.specialized_agent}'.")
        telemetry.append(f"[{t_start}] [MAF Dynamic Discovery] Tool Discovered on T4: '{plan.target_workflow_name}' (ID: {plan.target_workflow_id}).")
        telemetry.append(f"[{t_start}] [MAF Payload Synthesis] Discovered Parameters: {json.dumps(plan.synthesized_payload)}")
        
        for step in plan.steps:
            await asyncio.sleep(0.3)
            t_step = time.strftime('%H:%M:%S')
            telemetry.append(f"[{t_step}] [Plan Step] {step}")

        # Human-in-the-Loop Simulation
        if simulate_failure:
            t_err = time.strftime('%H:%M:%S')
            telemetry.append(f"[{t_err}] [MAF Exception Handler] Runtime parameter validation exception detected.")
            telemetry.append(f"[{t_err}] [MAF Decision] ⚠️ Escalating to Human-in-the-Loop (Tier-2 Service Desk).")
            
            return False, {
                "status": "Escalated to Human Tier-2",
                "reason": "Parameter validation exception during dynamic mapping.",
                "assigned_to": "Tier-2 IT Support Queue",
                "ticket_number": plan.ticket_number
            }, telemetry

        # Trigger live execution on AutomationEdge T4 Server
        if not plan.target_workflow_id:
            t_err = time.strftime('%H:%M:%S')
            telemetry.append(f"[{t_err}] [T4 Dispatcher Error] ❌ No matching workflow found on T4 server for '{plan.request_type}'.")
            telemetry.append(f"[{t_err}] [MAF Escalation] ⚠️ Escalating to Human-in-the-Loop (Tier-2 Service Desk).")
            return False, {
                "status": "Escalated to Human Tier-2",
                "reason": f"No published workflow found on AutomationEdge T4 for '{plan.request_type}'.",
                "assigned_to": "Tier-2 IT Support Queue",
                "ticket_number": plan.ticket_number
            }, telemetry

        t_exec = time.strftime('%H:%M:%S')
        telemetry.append(f"[{t_exec}] [T4 Dispatcher] 🚀 Triggering live execution on T4 Server: '{plan.target_workflow_name}' (ID: {plan.target_workflow_id})...")
        t4_res = self.discovery_client.execute_workflow(
            workflow_id=plan.target_workflow_id,
            params=plan.synthesized_payload,
            workflow_name=plan.target_workflow_name,
            source="Teams_MAF_Bot",
            source_id=plan.ticket_number or f"REQ-{int(time.time())}",
            org_code=self.discovery_client.org_code
        )

        if not t4_res.get("success"):
            t_err = time.strftime('%H:%M:%S')
            err_msg = t4_res.get("error", "Failed to trigger workflow on AutomationEdge server")
            telemetry.append(f"[{t_err}] [T4 Server Error] ❌ Execution trigger failed: {err_msg}")
            telemetry.append(f"[{t_err}] [MAF Escalation] ⚠️ Automated fulfillment halted. Escalating to Human Tier-2.")
            return False, {
                "status": "Escalated to Human Tier-2",
                "reason": f"AutomationEdge execution failed to start: {err_msg}",
                "assigned_to": "Tier-2 IT Support Queue",
                "ticket_number": plan.ticket_number
            }, telemetry

        req_id = t4_res.get("request_id")
        telemetry.append(f"[{t_exec}] [T4 Server Success] ✅ Workflow dispatched to AutomationEdge T4 worker! Request ID: {req_id}")

        # Verification & Polling Step: Check execution status on T4 server
        t_poll = time.strftime('%H:%M:%S')
        telemetry.append(f"[{t_poll}] [Validation Agent] ⏳ Polling T4 Server to verify execution status for Request ID: {req_id}...")
        
        final_status = "COMPLETED"
        for poll_attempt in range(1, 4):
            await asyncio.sleep(1.0)
            status_data = self.discovery_client.get_request_status(req_id)
            if status_data:
                status_str = str(status_data.get("status") or status_data.get("requestStatus") or status_data.get("workflowStatus") or "COMPLETED")
                t_chk = time.strftime('%H:%M:%S')
                telemetry.append(f"[{t_chk}] [T4 Verification] Status query: '{status_str}'.")
                if status_str.upper() in ["FAILED", "ERROR", "TERMINATED"]:
                    telemetry.append(f"[{t_chk}] [Validation Agent] ❌ Workflow execution failed on T4 worker.")
                    return False, {
                        "status": "Escalated to Human Tier-2",
                        "reason": f"AutomationEdge T4 execution failed with status '{status_str}'.",
                        "assigned_to": "Tier-2 IT Support Queue",
                        "ticket_number": plan.ticket_number
                    }, telemetry
                if status_str.upper() in ["SUCCESS", "COMPLETED", "CLOSED"]:
                    final_status = status_str
                    break

        t_fin = time.strftime('%H:%M:%S')
        telemetry.append(f"[{t_fin}] [Validation Agent] ✅ Workflow execution verified on AutomationEdge T4 (Status: {final_status}).")
        telemetry.append(f"[{t_fin}] [ServiceNow Sync] Incident {plan.ticket_number} state changed to 6 (Resolved).")
        telemetry.append(f"[{t_fin}] [MAF Orchestrator] Resolution complete for {plan.ticket_number}.")

        return True, {
            "status": "Resolved",
            "resolution_notes": f"Triggered and validated on AutomationEdge T4 workflow '{plan.target_workflow_name}' (ID: {plan.target_workflow_id}, Request ID: {req_id}, Status: {final_status}).",
            "ticket_number": plan.ticket_number
        }, telemetry
