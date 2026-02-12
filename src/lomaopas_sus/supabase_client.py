import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID

import httpx

class SupabaseClient:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase_schema = os.getenv("SUPABASE_SCHEMA", "public")
        self.worker_id = os.getenv("WORKER_ID", "default-worker")

        if not self.supabase_url or not self.service_role_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment variables.")

        self.headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation", # Ensures we get the updated row back
        }
        self.base_url = f"{self.supabase_url}/rest/v1"

    def _get_url(self, table_name: str) -> str:
        return f"{self.base_url}/{table_name}?select=*"

    async def _make_request(self, method: str, url: str, json_data: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, headers=self.headers, json=json_data, timeout=60)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"HTTP error for {url}: {e.response.status_code} - {e.response.text}")
                return None
            except httpx.RequestError as e:
                print(f"Request error for {url}: {e}")
                return None

    def _get_single_result(self, response: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        if response and len(response) > 0:
            return response[0]
        return None

    async def fetch_next_job(self) -> Optional[Dict[str, Any]]:
        url = (
            f"{self.base_url}/ingest_jobs?select=*&status=eq.queued&"
            f"scheduled_for=lte.{datetime.now(timezone.utc).isoformat()}&"
            "locked_at=is.null&order=scheduled_for.asc&limit=1"
        )
        response = await self._make_request("GET", url)
        return self._get_single_result(response)

    async def lock_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/ingest_jobs?id=eq.{job_id}"
        
        # Fetch current attempts to increment
        job = self._get_single_result(await self._make_request("GET", url))
        if not job:
            return None
        
        payload = {
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "locked_by": self.worker_id,
            "status": "running",
            "attempts": job["attempts"] + 1,
        }
        response = await self._make_request("PATCH", url, json_data=payload)
        return self._get_single_result(response)

    async def mark_job_success(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/ingest_jobs?id=eq.{job_id}"
        payload = {
            "status": "succeeded",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }
        response = await self._make_request("PATCH", url, json_data=payload)
        return self._get_single_result(response)

    async def mark_job_failed(self, job_id: UUID, error: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/ingest_jobs?id=eq.{job_id}"
        payload = {
            "status": "failed",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }
        response = await self._make_request("PATCH", url, json_data=payload)
        return self._get_single_result(response)

    async def get_entity(self, entity_id: UUID) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/entities?select=*&id=eq.{entity_id}"
        response = await self._make_request("GET", url)
        return self._get_single_result(response)

    async def get_entity_sources(self, entity_id: UUID) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/entity_sources?select=*&entity_id=eq.{entity_id}"
        response = await self._make_request("GET", url)
        return response if response else []

    async def get_current_snapshot(self, entity_id: UUID) -> Optional[Dict[str, Any]]:
        url = (
            f"{self.base_url}/facts_current?select=*,snapshot_id(*)&entity_id=eq.{entity_id}"
        )
        response = await self._make_request("GET", url)
        single_result = self._get_single_result(response)
        if single_result and single_result.get("snapshot_id"):
            return single_result["snapshot_id"]
        return None

    async def insert_snapshot(self, snapshot_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/facts_snapshots"
        response = await self._make_request("POST", url, json_data=snapshot_data)
        return self._get_single_result(response)

    async def upsert_current(self, entity_id: UUID, snapshot_id: UUID) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/facts_current"
        payload = {
            "entity_id": str(entity_id),
            "snapshot_id": str(snapshot_id),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": "service_role",
        }

        existing_current = self._get_single_result(await self._make_request("GET", url + f"?entity_id=eq.{entity_id}"))
        if existing_current:
            url = f"{self.base_url}/facts_current?entity_id=eq.{entity_id}"
            response = await self._make_request("PATCH", url, json_data=payload)
        else:
            url = f"{self.base_url}/facts_current"
            response = await self._make_request("POST", url, json_data=payload)

        return self._get_single_result(response)

    async def insert_proposed(self, entity_id: UUID, snapshot_id: UUID, diff_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/facts_proposed"
        payload = {
            "entity_id": str(entity_id),
            "snapshot_id": str(snapshot_id),
            "diff": diff_json,
            "status": "pending_review",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        response = await self._make_request("POST", url, json_data=payload)
        return self._get_single_result(response)

    async def update_entity_next_refresh(self, entity_id: UUID, next_refresh_at: datetime) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/entities?id=eq.{entity_id}"
        payload = {
            "next_refresh_at": next_refresh_at.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": self.worker_id,
        }
        response = await self._make_request("PATCH", url, json_data=payload)
        return self._get_single_result(response)

    async def update_entity_last_attempt_success(self, entity_id: UUID, is_success: bool) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/entities?id=eq.{entity_id}"
        payload = {
            "last_attempt_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": self.worker_id,
        }
        if is_success:
            payload["last_success_at"] = datetime.now(timezone.utc).isoformat()
        
        response = await self._make_request("PATCH", url, json_data=payload)
        return self._get_single_result(response)