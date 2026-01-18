"""
Tests for workflow state migrator
"""
import pytest
from pydantic import BaseModel

from src.dynamic_workflows.migration.state_migrator import (
    WorkflowMigrator,
    MigrationStep,
)


class MockState(BaseModel):
    """Mock state"""
    value: int = 0
    _version: str = "1.0"


class TestWorkflowMigrator:
    """Test WorkflowMigrator"""

    def test_create_migrator(self):
        """Test creating a migrator"""
        migrator = WorkflowMigrator()

        assert migrator is not None
        assert len(migrator.migrations) == 0

    def test_register_migration(self):
        """Test registering a migration"""
        migrator = WorkflowMigrator()

        def migrate_v1_to_v2(state):
            return state

        migrator.register_migration(
            workflow_name="test_workflow",
            from_version="1.0",
            to_version="2.0",
            migrate_func=migrate_v1_to_v2
        )

        assert "test_workflow" in migrator.migrations
        assert len(migrator.migrations["test_workflow"]) == 1

    @pytest.mark.asyncio
    async def test_migrate_state_same_version(self):
        """Test migrating to same version"""
        migrator = WorkflowMigrator()
        state = MockState(value=42, _version="1.0")

        result = await migrator.migrate_state(state, "1.0")

        assert result.value == 42
        assert result._version == "1.0"

    @pytest.mark.asyncio
    async def test_check_compatibility_same_version(self):
        """Test compatibility check with same version"""
        migrator = WorkflowMigrator()
        state = MockState(_version="1.0")

        is_compatible = await migrator.check_compatibility(state, "1.0")

        assert is_compatible is True

    @pytest.mark.asyncio
    async def test_check_compatibility_different_major(self):
        """Test compatibility check with different major version"""
        migrator = WorkflowMigrator()
        state = MockState(_version="1.0")

        is_compatible = await migrator.check_compatibility(state, "2.0")

        assert is_compatible is False

    @pytest.mark.asyncio
    async def test_check_compatibility_same_major(self):
        """Test compatibility check with same major version"""
        migrator = WorkflowMigrator()
        state = MockState(_version="1.5")

        is_compatible = await migrator.check_compatibility(state, "1.9")

        assert is_compatible is True

    @pytest.mark.asyncio
    async def test_get_migration_path_same_version(self):
        """Test migration path for same version"""
        migrator = WorkflowMigrator()

        path = await migrator.get_migration_path("1.0", "1.0")

        assert path == []

    @pytest.mark.asyncio
    async def test_get_migration_path_different_version(self):
        """Test migration path for different versions"""
        migrator = WorkflowMigrator()

        path = await migrator.get_migration_path("1.0", "2.0")

        assert "1.0" in path
        assert "2.0" in path

    def test_get_latest_version_no_history(self):
        """Test getting latest version without history"""
        migrator = WorkflowMigrator()

        version = migrator.get_latest_version("nonexistent")

        assert version == "1.0"

    def test_get_latest_version_with_history(self):
        """Test getting latest version with history"""
        migrator = WorkflowMigrator()

        migrator.register_migration(
            "test_workflow",
            "1.0",
            "2.0",
            lambda s: s
        )

        version = migrator.get_latest_version("test_workflow")

        assert version == "2.0"

    def test_list_versions_no_history(self):
        """Test listing versions without history"""
        migrator = WorkflowMigrator()

        versions = migrator.list_versions("nonexistent")

        assert versions == ["1.0"]

    def test_list_versions_with_history(self):
        """Test listing versions with history"""
        migrator = WorkflowMigrator()

        migrator.register_migration("test", "1.0", "2.0", lambda s: s)
        migrator.register_migration("test", "2.0", "3.0", lambda s: s)

        versions = migrator.list_versions("test")

        assert "2.0" in versions
        assert "3.0" in versions
