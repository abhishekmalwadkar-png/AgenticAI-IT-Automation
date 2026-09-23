import os
import re
import json
import base64
import urllib.request
import urllib.parse
import http.cookiejar
from typing import Dict, Any, Optional

class ServiceNowLiveClient:
    def __init__(self, instance_url: str, username: str, password: str, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.instance_url = instance_url.rstrip("/")
        self.username = username
        self.password = password
        self.client_id = client_id or os.getenv("SERVICENOW_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SERVICENOW_CLIENT_SECRET")
        self.bearer_token: Optional[str] = None
        self.basic_auth_header: str = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.g_ck: Optional[str] = None
        self._authenticated = False

    def authenticate_oauth(self) -> bool:
        if not self.client_id or not self.client_secret:
            return False
        try:
            token_url = f"{self.instance_url}/oauth_token.do"
            payload = {
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password
            }
            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(
                token_url,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0"
                }
            )
            resp = urllib.request.urlopen(req, timeout=12)
            token_data = json.loads(resp.read().decode("utf-8"))
            self.bearer_token = token_data.get("access_token")
            if self.bearer_token:
                self._authenticated = True
                print(f"[ServiceNow OAuth] Successfully authenticated with Bearer token.")
                return True
        except Exception as e:
            print(f"[ServiceNow OAuth Failed] {e}")
        return False

    def authenticate(self) -> bool:
        # 1. Test Direct Basic Auth header
        try:
            test_req = urllib.request.Request(f"{self.instance_url}/api/now/table/incident?sysparm_limit=1")
            test_req.add_header("Authorization", f"Basic {self.basic_auth_header}")
            test_req.add_header("Accept", "application/json")
            test_req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(test_req, timeout=8) as test_resp:
                if test_resp.status == 200:
                    self._authenticated = True
                    print(f"[ServiceNow Basic Auth] Successfully authenticated {self.username} via HTTP Basic Auth.")
                    return True
        except Exception:
            pass

        # 2. Try OAuth 2.0 if client credentials exist
        if self.authenticate_oauth():
            return True

        # 3. Fallback to UI Session Authentication
        self.cj.clear()
        self.g_ck = None
        self._authenticated = False
        
        login_url = f"{self.instance_url}/login.do"
        data = urllib.parse.urlencode({
            "user_name": self.username,
            "user_password": self.password,
            "sys_action": "sysverb_login"
        }).encode("utf-8")

        req = urllib.request.Request(login_url, data=data)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            self.opener.open(req, timeout=12)
            # Extract g_ck token from navpage
            req_nav = urllib.request.Request(f"{self.instance_url}/navpage.do")
            req_nav.add_header("User-Agent", "Mozilla/5.0")
            page_html = self.opener.open(req_nav, timeout=12).read().decode("utf-8", errors="ignore")
            
            match = re.search(r'g_ck\s*=\s*[\'"]([a-zA-Z0-9_-]+)[\'"]', page_html)
            if match:
                self.g_ck = match.group(1)
            self._authenticated = True
            print(f"[ServiceNow Auth] Successfully authenticated via session. g_ck={self.g_ck}")
            return True
        except Exception as e:
            print(f"[ServiceNow Auth Failed] {e}")
            return False

    def _ensure_auth(self, force: bool = False):
        if force or not self._authenticated:
            self.authenticate()

    def _send_request(self, endpoint: str, data: Optional[bytes] = None, method: str = "GET", retries: int = 1) -> urllib.response.addinfourl:
        self._ensure_auth()
        
        req = urllib.request.Request(endpoint, data=data, method=method)
        req.add_header("Accept", "application/json")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "Mozilla/5.0")
        
        # Primary: Basic Auth
        req.add_header("Authorization", f"Basic {self.basic_auth_header}")
        
        if self.bearer_token:
            req.add_header("Authorization", f"Bearer {self.bearer_token}")
        elif self.g_ck:
            req.add_header("X-UserToken", self.g_ck)
            
        try:
            return self.opener.open(req, timeout=15)
        except urllib.error.HTTPError as e:
            if e.code in [401, 403] and retries > 0:
                print(f"[ServiceNow] Received {e.code}, refreshing session & retrying...")
                self._ensure_auth(force=True)
                
                req_retry = urllib.request.Request(endpoint, data=data, method=method)
                req_retry.add_header("Accept", "application/json")
                req_retry.add_header("Content-Type", "application/json")
                req_retry.add_header("User-Agent", "Mozilla/5.0")
                req_retry.add_header("Authorization", f"Basic {self.basic_auth_header}")
                if self.bearer_token:
                    req_retry.add_header("Authorization", f"Bearer {self.bearer_token}")
                elif self.g_ck:
                    req_retry.add_header("X-UserToken", self.g_ck)
                return self.opener.open(req_retry, timeout=15)
            raise e

    def create_incident(
        self,
        short_description: str,
        description: str,
        category: str = "software",
        priority: int = 3,
        caller: str = "Aarav Sharma",
        work_notes: Optional[str] = None,
        urgency: Optional[int] = None,
        impact: Optional[int] = None
    ) -> Dict[str, Any]:
        endpoint = f"{self.instance_url}/api/now/table/incident"
        
        urgency_val = urgency if urgency is not None else priority
        impact_val = impact if impact is not None else priority

        payload = {
            "short_description": short_description,
            "description": description,
            "category": category,
            "urgency": str(urgency_val),
            "impact": str(impact_val),
            "priority": str(priority),
            "contact_type": "Microsoft Teams (AE Bot)",
            "work_notes": work_notes or f"[AE Bot Intake] Request received via Microsoft Teams from {caller}."
        }
        
        data = json.dumps(payload).encode("utf-8")

        try:
            resp = self._send_request(endpoint, data=data, method="POST")
            result = json.loads(resp.read().decode("utf-8")).get("result", {})
            ticket_number = result.get("number")
            sys_id = result.get("sys_id")
            ret_priority = result.get("priority", str(priority))
            print(f"[ServiceNow Created] {ticket_number} (sys_id: {sys_id}, Priority: {ret_priority}, Urgency: {urgency_val}, Impact: {impact_val})")
            return {
                "success": True,
                "ticket_number": ticket_number,
                "sys_id": sys_id,
                "short_description": result.get("short_description"),
                "state": result.get("state"),
                "priority": ret_priority,
                "urgency": result.get("urgency", str(urgency_val)),
                "impact": result.get("impact", str(impact_val)),
                "link": f"{self.instance_url}/nav_to.do?uri=incident.do?sys_id={sys_id}"
            }
        except Exception as e:
            print(f"Error creating incident in ServiceNow: {e}")
            return {"success": False, "error": str(e)}

    def get_incident_by_number(self, ticket_number: str) -> Optional[Dict[str, Any]]:
        endpoint = f"{self.instance_url}/api/now/table/incident?sysparm_query=number={urllib.parse.quote(ticket_number)}&sysparm_limit=1"
        try:
            resp = self._send_request(endpoint, method="GET")
            data = json.loads(resp.read().decode("utf-8")).get("result", [])
            if data and len(data) > 0:
                return data[0]
        except Exception as e:
            print(f"Error querying incident {ticket_number}: {e}")
        return None

    def update_work_notes(self, sys_id: str, notes: str, state: Optional[str] = None, customer_visible: bool = True) -> bool:
        endpoint = f"{self.instance_url}/api/now/table/incident/{sys_id}"
        
        payload: Dict[str, Any] = {"work_notes": notes}
        if customer_visible:
            payload["comments"] = notes
        if state:
            payload["state"] = state
            
        data = json.dumps(payload).encode("utf-8")

        try:
            resp = self._send_request(endpoint, data=data, method="PATCH")
            print(f"[ServiceNow Updated] {sys_id} state={state}")
            return resp.getcode() in [200, 204]
        except Exception as e:
            print(f"Error updating incident {sys_id}: {e}")
            return False

    def close_incident(self, sys_id: str, resolution_notes: str) -> bool:
        endpoint = f"{self.instance_url}/api/now/table/incident/{sys_id}"
        
        # State 6 = Resolved in ServiceNow
        payload = {
            "state": "6",
            "close_code": "Solved (Permanently)",
            "close_notes": resolution_notes,
            "work_notes": f"[AE Bot Fulfillment] {resolution_notes}"
        }
        
        data = json.dumps(payload).encode("utf-8")

        try:
            resp = self._send_request(endpoint, data=data, method="PATCH")
            print(f"[ServiceNow Closed] {sys_id}")
            return resp.getcode() in [200, 204]
        except Exception as e:
            # Fallback to updating work notes only
            return self.update_work_notes(sys_id, f"Resolved: {resolution_notes}", state="6")
