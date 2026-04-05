from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Version:
    version_id: str
    version_number: str
    component_type: str
    content: Any
    created_at: datetime
    created_by: str = "system"
    description: str = ""
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "version_number": self.version_number,
            "component_type": self.component_type,
            "content": self.content if isinstance(self.content, (str, int, float, bool)) else str(self.content),
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "description": self.description,
            "metadata": self.metadata or {},
        }


class VersionManager:
    def __init__(self):
        self._versions: Dict[str, List[Version]] = {}
        self._current_versions: Dict[str, str] = {}

    def create_version(
        self,
        component_type: str,
        component_id: str,
        content: Any,
        created_by: str = "system",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Version:
        key = f"{component_type}:{component_id}"

        if key not in self._versions:
            self._versions[key] = []

        version_number = self._get_next_version(key)

        version_id = f"{key}:v{version_number}"
        version = Version(
            version_id=version_id,
            version_number=version_number,
            component_type=component_type,
            content=content,
            created_at=datetime.utcnow(),
            created_by=created_by,
            description=description,
            metadata=metadata,
        )

        self._versions[key].append(version)
        self._current_versions[key] = version_id

        logger.info(f"Created version {version_id} for {key}")
        return version

    def _get_next_version(self, key: str) -> str:
        if key not in self._versions or not self._versions[key]:
            return "1.0"

        last_version = self._versions[key][-1]
        parts = last_version.version_number.split(".")
        major = int(parts[0])
        minor = int(parts[1]) + 1
        return f"{major}.{minor}"

    def get_version(self, component_type: str, component_id: str, version_number: Optional[str] = None) -> Optional[Version]:
        key = f"{component_type}:{component_id}"

        if key not in self._versions:
            return None

        if version_number is None:
            latest = self._versions[key][-1]
            return latest

        for version in self._versions[key]:
            if version.version_number == version_number:
                return version

        return None

    def get_current_version(self, component_type: str, component_id: str) -> Optional[Version]:
        key = f"{component_type}:{component_id}"
        version_id = self._current_versions.get(key)

        if not version_id:
            return self.get_version(component_type, component_id)

        return self.get_version(component_type, component_id, version_id.split(":")[-1].replace("v", ""))

    def get_version_history(self, component_type: str, component_id: str) -> List[Version]:
        key = f"{component_type}:{component_id}"
        return self._versions.get(key, [])

    def rollback(self, component_type: str, component_id: str, target_version: str) -> bool:
        key = f"{component_type}:{component_id}"

        version = self.get_version(component_type, component_id, target_version)
        if not version:
            logger.error(f"Version {target_version} not found for {key}")
            return False

        self._current_versions[key] = version.version_id
        logger.info(f"Rolled back {key} to version {target_version}")
        return True

    def compare_versions(
        self, component_type: str, component_id: str, version1: str, version2: str
    ) -> Dict[str, Any]:
        v1 = self.get_version(component_type, component_id, version1)
        v2 = self.get_version(component_type, component_id, version2)

        if not v1 or not v2:
            return {"error": "One or both versions not found"}

        return {
            "version1": v1.to_dict(),
            "version2": v2.to_dict(),
            "same_content": v1.content == v2.content,
        }


version_manager = VersionManager()
