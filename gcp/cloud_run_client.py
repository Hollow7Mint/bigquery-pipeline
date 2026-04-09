import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from googleapiclient import discovery
    from google.oauth2 import service_account
except ImportError:
    discovery = None  # type: ignore
    service_account = None  # type: ignore


class CloudRunClient:
    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

    def __init__(self, project_id: str, region: str = "us-central1",
                 credentials_file: Optional[str] = None) -> None:
        self.project_id = project_id
        self.region     = region
        if discovery is None:
            raise ImportError("google-api-python-client is not installed")
        if credentials_file and service_account:
            creds = service_account.Credentials.from_service_account_file(
                credentials_file, scopes=self.SCOPES
            )
        else:
            import google.auth
            creds, _ = google.auth.default(scopes=self.SCOPES)
        self._svc = discovery.build("run", "v1", credentials=creds)
        self._parent = f"namespaces/{project_id}"
        logger.debug("Cloud Run client for %s/%s", project_id, region)

    def list_services(self) -> list[dict[str, Any]]:
        response = (
            self._svc.namespaces()
            .services()
            .list(parent=self._parent)
            .execute()
        )
        return [
            {
                "name":   svc["metadata"]["name"],
                "url":    svc.get("status", {}).get("url", ""),
                "ready":  any(
                    c.get("type") == "Ready" and c.get("status") == "True"
                    for c in svc.get("status", {}).get("conditions", [])
                ),
            }
            for svc in response.get("items", [])
        ]

    def get_service(self, service_name: str) -> dict[str, Any]:
        name = f"{self._parent}/services/{service_name}"
        svc  = self._svc.namespaces().services().get(name=name).execute()
        return {
            "name":        svc["metadata"]["name"],
            "url":         svc.get("status", {}).get("url"),
            "image":       (svc.get("spec", {})
                             .get("template", {})
                             .get("spec", {})
                             .get("containers", [{}])[0]
                             .get("image")),
            "annotations": svc.get("metadata", {}).get("annotations", {}),
        }

    def update_traffic(self, service_name: str,
                       traffic: list[dict[str, Any]]) -> None:
        name = f"{self._parent}/services/{service_name}"
        svc  = self._svc.namespaces().services().get(name=name).execute()
        svc["spec"]["traffic"] = traffic
        self._svc.namespaces().services().replaceService(
            name=name, body=svc
        ).execute()
        logger.info("Updated traffic for service %s", service_name)

    def delete_service(self, service_name: str) -> None:
        name = f"{self._parent}/services/{service_name}"
        self._svc.namespaces().services().delete(name=name).execute()
        logger.info("Deleted Cloud Run service %s", service_name)
