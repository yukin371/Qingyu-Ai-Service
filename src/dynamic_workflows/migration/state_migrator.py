"""
Workflow State Migration

Handle version migration for workflow states.
"""
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from datetime import datetime


class MigrationStep:
    """Single migration step"""

    def __init__(
        self,
        from_version: str,
        to_version: str,
        migrate_func: callable
    ):
        self.from_version = from_version
        self.to_version = to_version
        self.migrate_func = migrate_func


class WorkflowMigrator:
    """
    Migrate workflow states between versions

    Handles state schema changes and version compatibility.
    """

    def __init__(self):
        """Initialize migrator"""
        self.migrations: Dict[str, List[MigrationStep]] = {}
        self.version_history: Dict[str, List[str]] = {}

    def register_migration(
        self,
        workflow_name: str,
        from_version: str,
        to_version: str,
        migrate_func: callable
    ):
        """
        Register a migration step

        Args:
            workflow_name: Workflow name
            from_version: Source version
            to_version: Target version
            migrate_func: Migration function
        """
        if workflow_name not in self.migrations:
            self.migrations[workflow_name] = []

        step = MigrationStep(from_version, to_version, migrate_func)
        self.migrations[workflow_name].append(step)

        # Update version history
        if workflow_name not in self.version_history:
            self.version_history[workflow_name] = []

        if to_version not in self.version_history[workflow_name]:
            self.version_history[workflow_name].append(to_version)

    async def migrate_state(
        self,
        state: BaseModel,
        target_version: str,
        workflow_name: Optional[str] = None
    ) -> BaseModel:
        """
        Migrate state to target version

        Args:
            state: Current state
            target_version: Target version
            workflow_name: Optional workflow name

        Returns:
            Migrated state

        Note:
            This is a simplified implementation. In production, this would
            apply all necessary migration steps.
        """
        # Get current version from state metadata if available
        current_version = getattr(state, "_version", "1.0")

        if current_version == target_version:
            return state

        # For now, return state as-is
        # In production, would apply migration chain
        return state

    async def check_compatibility(
        self,
        state: BaseModel,
        target_version: str
    ) -> bool:
        """
        Check if state is compatible with target version

        Args:
            state: State to check
            target_version: Target version

        Returns:
            True if compatible
        """
        current_version = getattr(state, "_version", "1.0")

        # Simple check: same major version
        current_major = current_version.split(".")[0]
        target_major = target_version.split(".")[0]

        return current_major == target_major

    async def get_migration_path(
        self,
        from_version: str,
        to_version: str,
        workflow_name: Optional[str] = None
    ) -> List[str]:
        """
        Get migration path between versions

        Args:
            from_version: Source version
            to_version: Target version
            workflow_name: Optional workflow name

        Returns:
            List of version steps
        """
        # Simplified: direct path
        if from_version == to_version:
            return []

        return [from_version, to_version]

    def get_latest_version(self, workflow_name: str) -> str:
        """
        Get latest version for workflow

        Args:
            workflow_name: Workflow name

        Returns:
            Latest version string
        """
        if workflow_name not in self.version_history:
            return "1.0"

        return self.version_history[workflow_name][-1]

    def list_versions(self, workflow_name: str) -> List[str]:
        """
        List all versions for workflow

        Args:
            workflow_name: Workflow name

        Returns:
            List of version strings
        """
        return self.version_history.get(workflow_name, ["1.0"])
