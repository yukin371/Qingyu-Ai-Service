"""
Tests for AgentFactory

Tests the factory's ability to manage templates and configurations.
"""
import pytest
from typing import Dict, Any

from src.agent_runtime.factory import AgentFactory, AgentTemplate
from src.common.types.agent_types import (
    AgentConfig,
    AgentCapability,
)


# =============================================================================
# AgentTemplate Tests
# =============================================================================

class TestAgentTemplate:
    """Test AgentTemplate"""

    def test_template_creation(self):
        """Test creating a template"""
        config = AgentConfig(
            name="test",
            description="Test",
            model="gpt-4",
        )

        template = AgentTemplate(
            name="test_template",
            description="Test template",
            config=config,
            required_capabilities=[AgentCapability.TEXT_GENERATION],
        )

        assert template.name == "test_template"
        assert template.config == config
        assert template.required_capabilities == [AgentCapability.TEXT_GENERATION]

    def test_template_valid_success(self):
        """Test template validation - success"""
        config = AgentConfig(
            name="test",
            description="Test",
            model="gpt-4",
        )

        template = AgentTemplate(
            name="valid",
            description="Valid",
            config=config,
        )
        assert template.validate() is True

    def test_template_invalid_empty_name(self):
        """Test template validation - empty name"""
        config = AgentConfig(
            name="test",
            description="Test",
            model="gpt-4",
        )

        template = AgentTemplate(
            name="",
            description="Invalid",
            config=config,
        )

        with pytest.raises(ValueError, match="Template name cannot be empty"):
            template.validate()

    def test_template_invalid_no_model(self):
        """Test template validation - no model"""
        config = AgentConfig(
            name="test",
            description="Test",
            model="",
        )

        template = AgentTemplate(
            name="invalid",
            description="Invalid",
            config=config,
        )

        with pytest.raises(ValueError, match="Template must specify a model"):
            template.validate()


# =============================================================================
# AgentFactory Tests
# =============================================================================

class TestAgentFactory:
    """Test AgentFactory"""

    @pytest.fixture
    def factory(self):
        """Create a factory instance"""
        return AgentFactory()

    def test_factory_initialization(self, factory):
        """Test factory initialization"""
        assert factory is not None
        # Should have default templates
        assert len(factory._templates) > 0

    def test_register_template(self, factory):
        """Test registering a template"""
        template = AgentTemplate(
            name="analyst",
            description="Data analyst",
            config=AgentConfig(
                name="analyst",
                description="Data analyst",
                model="gpt-4",
            ),
        )

        factory.register_template(template)

        assert "analyst" in factory._templates
        assert factory._templates["analyst"] == template

    def test_unregister_template(self, factory):
        """Test unregistering a template"""
        template = AgentTemplate(
            name="temp",
            description="Temporary",
            config=AgentConfig(
                name="temp",
                description="Temporary",
                model="gpt-4",
            ),
        )

        factory.register_template(template)
        assert "temp" in factory._templates

        factory.unregister_template("temp")
        assert "temp" not in factory._templates

    def test_get_template(self, factory):
        """Test getting a template"""
        template = AgentTemplate(
            name="getter_test",
            description="Getter test",
            config=AgentConfig(
                name="getter_test",
                description="Getter test",
                model="gpt-4",
            ),
        )

        factory.register_template(template)

        retrieved = factory.get_template("getter_test")
        assert retrieved is not None
        assert retrieved.name == "getter_test"

    def test_get_template_not_found(self, factory):
        """Test getting a non-existent template"""
        retrieved = factory.get_template("nonexistent")
        assert retrieved is None

    def test_list_templates(self, factory):
        """Test listing all templates"""
        # Clear default templates first
        factory._templates.clear()

        template1 = AgentTemplate(
            name="template1",
            description="Template 1",
            config=AgentConfig(
                name="t1",
                description="T1",
                model="gpt-4",
            ),
        )
        template2 = AgentTemplate(
            name="template2",
            description="Template 2",
            config=AgentConfig(
                name="t2",
                description="T2",
                model="gpt-4",
            ),
        )

        factory.register_template(template1)
        factory.register_template(template2)

        templates = factory.list_templates()
        assert len(templates) == 2
        assert "template1" in templates
        assert "template2" in templates

    def test_default_templates_registered(self, factory):
        """Test that default templates are registered"""
        templates = factory.list_templates()

        # Check for default templates
        assert "writer" in templates
        assert "analyst" in templates
        assert "searcher" in templates

    def test_set_tool_registry(self, factory):
        """Test setting tool registry"""
        mock_registry = object()
        factory.set_tool_registry(mock_registry)
        assert factory._tool_registry is mock_registry

    def test_set_memory_backend(self, factory):
        """Test setting memory backend"""
        mock_memory = object()
        factory.set_memory_backend(mock_memory)
        assert factory._memory_backend is mock_memory

    def test_set_workflow_builder(self, factory):
        """Test setting workflow builder"""
        mock_builder = object()
        factory.set_workflow_builder(mock_builder)
        assert factory._workflow_builder is mock_builder

    @pytest.mark.asyncio
    async def test_create_agent_requires_model(self, factory):
        """Test that create_agent requires a model in config"""
        config = AgentConfig(
            name="test",
            description="Test",
            model="",  # Empty model
        )

        with pytest.raises(ValueError, match="Agent config must specify a model"):
            await factory.create_agent(
                name="test_agent",
                config=config,
            )

    @pytest.mark.asyncio
    async def test_create_from_template_not_found(self, factory):
        """Test creating from non-existent template"""
        with pytest.raises(ValueError, match="Template not found"):
            await factory.create_from_template(
                template_name="nonexistent",
                config={},
            )

    @pytest.mark.asyncio
    async def test_create_from_template_with_config_override(self, factory):
        """Test creating from template with config override"""
        # Get the default writer template
        template = factory.get_template("writer")
        assert template is not None

        # This test will be enabled when AgentExecutor is implemented
        # For now, just test that template exists
        assert "writer" in factory._templates
