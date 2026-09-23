"""
Async ServiceNow Live REST API Client
Provides native asyncio / httpx integration for high-performance non-blocking IT service automation.
"""

import os
import re
import json
import base64
import asyncio
from typing import Dict, Any, Optional
import httpx

class AsyncServiceNowClient:
    """
    High-performance Asynchronous ServiceNow Client using httpx.AsyncClient.
    Provides non-blocking incident creation, work notes updates, and incident lifecycle management.
    """
    def __init__(
        self,
        instance_url: str,
        username: str,
        password: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: float = 20.0
    ):
        self.instance_url = instance_url.rstrip("/")
        self.username = username
        self.password = password
        self.client_id = client_id or os.getenv("SERVICENOW_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SERVICENOW_CLIENT_SECRET")
        self.timeout = timeout
        
        # HTTP Basic Auth credentials
        self.auth = httpx.BasicAuth(username=self.username, password=self.password)
        self.basic_auth_header = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
        self.bearer_token: Optional[str] = None
        self._authenticated = False

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Microsoft-Teams-AEBot/2.0 (AsyncIO)",
            "Authorization": f"Basic {self.basic_auth_header}"
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    async def authenticate(self) -> bool:
        """Verifies authentication against the ServiceNow Table API asynchronously."""
        test_url = f"{self.instance_url}/api/now/table/incident?sysparm_limit=1"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(test_url, headers=self._get_headers())
                if resp.status_code == 200:
                    self._authenticated = True
                    return True
        except Exception as e:
            print(f"[Async ServiceNow Auth Error] {e}")
        return False

    async def create_incident(
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
        """Asynchronously creates an incident ticket in ServiceNow via Table API."""
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
            "contact_type": "Microsoft Teams (AE Bot Async)",
            "work_notes": work_notes or f"[AE Bot Intake] Request received via Microsoft Teams from {caller}."
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, json=payload, headers=self._get_headers())
                
                if resp.status_code in [200, 201]:
                    data = resp.json().get("result", {})
                    ticket_number = data.get("number")
                    sys_id = data.get("sys_id")
                    ret_priority = data.get("priority", str(priority))
                    
                    print(f"[Async ServiceNow Created] {ticket_number} (sys_id: {sys_id}, Priority: {ret_priority})")
                    return {
                        "success": True,
                        "ticket_number": ticket_number,
                        "sys_id": sys_id,
                        "short_description": data.get("short_description"),
                        "state": data.get("state"),
                        "priority": ret_priority,
                        "urgency": data.get("urgency", str(urgency_val)),
                        "impact": data.get("impact", str(impact_val)),
                        "link": f"{self.instance_url}/nav_to.do?uri=incident.do?sys_id={sys_id}"
                    }
                else:
                    print(f"[Async ServiceNow Create Error] Status {resp.status_code}: {resp.text}")
                    return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            print(f"[Async ServiceNow Exception] {e}")
            return {"success": False, "error": str(e)}

    async def get_incident_by_number(self, ticket_number: str) -> Optional[Dict[str, Any]]:
        """Asynchronously retrieves an incident by number (e.g., 'INC0010028')."""
        endpoint = f"{self.instance_url}/api/now/table/incident"
        params = {
            "sysparm_query": f"number={ticket_number}",
            "sysparm_limit": "1"
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(endpoint, params=params, headers=self._get_headers())
                if resp.status_code == 200:
                    results = resp.json().get("result", [])
                    if results:
                        return results[0]
        except Exception as e:
            print(f"[Async ServiceNow Query Error] {e}")
        return None

    async def update_work_notes(
        self,
        sys_id: str,
        notes: str,
        state: Optional[str] = None,
        customer_visible: bool = True
    ) -> bool:
        """Asynchronously adds work notes / comments and updates state on an incident."""
        endpoint = f"{self.instance_url}/api/now/table/incident/{sys_id}"
        payload: Dict[str, Any] = {"work_notes": notes}
        if customer_visible:
            payload["comments"] = notes
        if state:
            payload["state"] = str(state)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.patch(endpoint, json=payload, headers=self._get_headers())
                print(f"[Async ServiceNow Note Updated] sys_id={sys_id}, state={state}")
                return resp.status_code in [200, 204]
        except Exception as e:
            print(f"[Async ServiceNow Update Error] {e}")
            return False

    async def close_incident(self, sys_id: str, resolution_notes: str) -> bool:
        """Asynchronously resolves an incident in ServiceNow (State 6 = Resolved)."""
        endpoint = f"{self.instance_url}/api/now/table/incident/{sys_id}"
        payload = {
            "state": "6",
            "close_code": "Solved (Permanently)",
            "close_notes": resolution_notes,
            "work_notes": f"[AE Bot Fulfillment] {resolution_notes}"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.patch(endpoint, json=payload, headers=self._get_headers())
                print(f"[Async ServiceNow Resolved] sys_id={sys_id}")
                return resp.status_code in [200, 204]
        except Exception as e:
            print(f"[Async ServiceNow Close Error] {e}")
            return await self.update_work_notes(sys_id, f"Resolved: {resolution_notes}", state="6")


# Backward-compatible Sync Wrapper for any non-async callers
class ServiceNowLiveClient(AsyncServiceNowClient):
    """
    Synchronous / Async Hybrid Client wrapper for backward compatibility.
    """
    def create_incident_sync(self, *args, **kwargs) -> Dict[str, Any]:
        return asyncio.run(self.create_incident(*args, **kwargs))
    
    def get_incident_by_number_sync(self, ticket_number: str) -> Optional[Dict[str, Any]]:
        return asyncio.run(self.get_incident_by_number(ticket_number))

    def update_work_notes_sync(self, sys_id: str, notes: str, state: Optional[str] = None, customer_visible: bool = True) -> bool:
        return asyncio.run(self.update_work_notes(sys_id, notes, state=state, customer_visible=customer_visible))

    def close_incident_sync(self, sys_id: str, resolution_notes: str) -> bool:
        return asyncio.run(self.close_incident(sys_id, resolution_notes))
