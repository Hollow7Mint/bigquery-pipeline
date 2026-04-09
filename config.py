import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GCPConfig:
    project_id: str
    region: str = "us-central1"
    zone: str = "us-central1-a"
    credentials_file: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "GCPConfig":
        project = os.environ.get("GCP_PROJECT_ID", "")
        if not project:
            raise EnvironmentError("GCP_PROJECT_ID is not set")
        return cls(
            project_id=project,
            region=os.environ.get("GCP_REGION", "us-central1"),
            zone=os.environ.get("GCP_ZONE", "us-central1-a"),
            credentials_file=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            timeout=int(os.environ.get("GCP_TIMEOUT", "30")),
            max_retries=int(os.environ.get("GCP_MAX_RETRIES", "3")),
        )

    def validate(self) -> None:
        if not self.project_id:
            raise ValueError("project_id must not be empty")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
