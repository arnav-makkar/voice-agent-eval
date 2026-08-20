"""Environment-backed configuration for the Voice Agents API."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_ORG_ID = "019fe148-1997-7cc7-bb7a-8029929d4008"
DEFAULT_WORKSPACE_ID = "019fe148-199b-787e-b8d7-b0c2d4e6acda"
DEFAULT_APP_ID = "Conversatio-87b9b435-b466"
DEFAULT_APP_VERSION = 1
DEFAULT_CONNECTION_ID = "447935f5-f1-05fb7f39-88f4"


def load_env_file(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE entries without adding a runtime dependency."""

    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0:1] == value[-1:] and value.startswith(("'", '"')):
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True, slots=True)
class Settings:
    org_id: str
    workspace_id: str
    app_id: str
    app_version: int
    connection_id: str
    agent_phone_number: str
    user_phone_number: str
    api_key: str

    @classmethod
    def from_environment(
        cls,
        *,
        env_file: str | Path = ".env",
        user_phone_number: str | None = None,
    ) -> "Settings":
        load_env_file(env_file)
        version_text = os.getenv("SARVAM_APP_VERSION", str(DEFAULT_APP_VERSION))
        try:
            app_version = int(version_text)
        except ValueError as exc:
            raise ValueError("SARVAM_APP_VERSION must be an integer") from exc

        return cls(
            org_id=os.getenv("SARVAM_ORG_ID", DEFAULT_ORG_ID).strip(),
            workspace_id=os.getenv("SARVAM_WORKSPACE_ID", DEFAULT_WORKSPACE_ID).strip(),
            app_id=os.getenv("SARVAM_APP_ID", DEFAULT_APP_ID).strip(),
            app_version=app_version,
            connection_id=os.getenv(
                "SARVAM_CONNECTION_ID", DEFAULT_CONNECTION_ID
            ).strip(),
            agent_phone_number=os.getenv("SARVAM_AGENT_PHONE_NUMBER", "").strip(),
            user_phone_number=(
                user_phone_number
                or os.getenv("SARVAM_TEST_USER_PHONE_NUMBER", "")
            ).strip(),
            api_key=os.getenv("SARVAM_VOICE_AGENTS_API_KEY", "").strip(),
        )

    def missing_fields(self, *, require_api_key: bool) -> list[str]:
        fields = {
            "SARVAM_ORG_ID": self.org_id,
            "SARVAM_WORKSPACE_ID": self.workspace_id,
            "SARVAM_APP_ID": self.app_id,
            "SARVAM_CONNECTION_ID": self.connection_id,
            "SARVAM_AGENT_PHONE_NUMBER": self.agent_phone_number,
            "SARVAM_TEST_USER_PHONE_NUMBER": self.user_phone_number,
        }
        if require_api_key:
            fields["SARVAM_VOICE_AGENTS_API_KEY"] = self.api_key
        return [name for name, value in fields.items() if not value]

