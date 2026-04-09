import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ServiceAccountAuth:
    def __init__(self, credentials_file: Optional[str] = None) -> None:
        self._credentials_file = (
            credentials_file
            or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        )
        self._credentials: Optional[dict] = None

    def load(self) -> dict:
        if self._credentials is not None:
            return self._credentials
        if self._credentials_file:
            path = Path(self._credentials_file)
            if not path.exists():
                raise FileNotFoundError(
                    f"Credentials file not found: {self._credentials_file}"
                )
            with open(path) as f:
                self._credentials = json.load(f)
            logger.debug("Loaded credentials from %s", path)
        else:
            # Fall back to Application Default Credentials
            logger.debug("Using Application Default Credentials")
            self._credentials = {}
        return self._credentials

    @property
    def project_id(self) -> Optional[str]:
        creds = self.load()
        return creds.get("project_id")

    @property
    def client_email(self) -> Optional[str]:
        creds = self.load()
        return creds.get("client_email")

    def is_service_account(self) -> bool:
        creds = self.load()
        return creds.get("type") == "service_account"

    def summary(self) -> dict:
        return {
            "type": "service_account" if self.is_service_account() else "adc",
            "project_id": self.project_id,
            "client_email": self.client_email,
            "credentials_file": self._credentials_file,
        }


def load_auth(credentials_file: Optional[str] = None) -> ServiceAccountAuth:
    auth = ServiceAccountAuth(credentials_file)
    auth.load()
    return auth
