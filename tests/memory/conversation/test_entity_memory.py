"""
Tests for Entity Memory Implementation
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.memory.conversation.entity_memory import EntityMemory, Entity, EntityRelation
from src.common.types.memory_types import MemoryType, MemoryScope
from src.common.exceptions import (
    MemoryValidationError,
    MemoryOperationError,
)


class TestEntity:
    """Test suite for Entity data model."""

    def test_entity_creation(self):
        """Test creating a basic entity."""
        entity = Entity(
            entity_type="PERSON",
            name="Alice",
            attributes={"age": 30, "city": "New York"}
        )

        assert entity.entity_type == "PERSON"
        assert entity.name == "Alice"
        assert entity.attributes["age"] == 30
        assert entity.attributes["city"] == "New York"
        assert entity.count == 1
        assert isinstance(entity.first_seen, datetime)
        assert isinstance(entity.last_seen, datetime)

    def test_entity_with_custom_timestamps(self):
        """Test entity with custom timestamps."""
        now = datetime.utcnow()
        entity = Entity(
            entity_type="LOCATION",
            name="Paris",
            first_seen=now,
            last_seen=now,
            count=5
        )

        assert entity.first_seen == now
        assert entity.last_seen == now
        assert entity.count == 5

    def test_entity_model_dump(self):
        """Test entity serialization."""
        entity = Entity(
            entity_type="ORGANIZATION",
            name="OpenAI",
            attributes={"founded": 2015}
        )

        data = entity.model_dump()
        assert data["entity_type"] == "ORGANIZATION"
        assert data["name"] == "OpenAI"
        assert data["attributes"]["founded"] == 2015


class TestEntityRelation:
    """Test suite for EntityRelation data model."""

    def test_relation_creation(self):
        """Test creating a basic relation."""
        relation = EntityRelation(
            from_entity="Alice",
            to_entity="Bob",
            relation_type="knows"
        )

        assert relation.from_entity == "Alice"
        assert relation.to_entity == "Bob"
        assert relation.relation_type == "knows"
        assert relation.confidence == 1.0

    def test_relation_with_confidence(self):
        """Test relation with custom confidence."""
        relation = EntityRelation(
            from_entity="Alice",
            to_entity="Company",
            relation_type="works_for",
            confidence=0.8
        )

        assert relation.confidence == 0.8

    def test_relation_model_dump(self):
        """Test relation serialization."""
        relation = EntityRelation(
            from_entity="Paris",
            to_entity="France",
            relation_type="located_in",
            confidence=0.95
        )

        data = relation.model_dump()
        assert data["from_entity"] == "Paris"
        assert data["to_entity"] == "France"
        assert data["relation_type"] == "located_in"


class TestEntityMemory:
    """Test suite for EntityMemory class."""

    @pytest.fixture
    def entity_memory(self):
        """Create an EntityMemory instance for testing."""
        return EntityMemory(
            session_id=str(uuid4()),
            max_entities=100
        )

    def test_initialization(self, entity_memory):
        """Test memory initialization."""
        assert entity_memory.max_entities == 100
        assert entity_memory.session_id is not None
        assert len(entity_memory.get_all_entities()) == 0
        assert len(entity_memory.get_all_relations()) == 0

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        memory = EntityMemory(
            session_id="session123",
            max_entities=50,
            ttl=timedelta(hours=1)
        )

        assert memory.max_entities == 50
        assert memory.session_id == "session123"
        assert memory.ttl == timedelta(hours=1)

    def test_add_entity(self, entity_memory):
        """Test adding a single entity."""
        entity_memory.add_entity(
            entity_type="PERSON",
            name="Alice",
            attributes={"age": 30}
        )

        entities = entity_memory.get_all_entities()
        assert len(entities) == 1
        assert entities[0].name == "Alice"
        assert entities[0].entity_type == "PERSON"

    def test_add_multiple_entities(self, entity_memory):
        """Test adding multiple entities."""
        entity_memory.add_entity("PERSON", "Alice", {"age": 30})
        entity_memory.add_entity("PERSON", "Bob", {"age": 25})
        entity_memory.add_entity("LOCATION", "Paris", {"country": "France"})

        entities = entity_memory.get_all_entities()
        assert len(entities) == 3

    def test_add_entity_duplicate_increments_count(self, entity_memory):
        """Test that adding duplicate entity increments count."""
        import time

        entity_memory.add_entity("PERSON", "Alice", {"age": 30})

        entity = entity_memory.get_entity("PERSON", "Alice")
        assert entity.count == 1

        # Add same entity again after a small delay
        time.sleep(0.01)
        entity_memory.add_entity("PERSON", "Alice", {"age": 31})

        entity = entity_memory.get_entity("PERSON", "Alice")
        assert entity.count == 2
        assert entity.attributes["age"] == 31  # Updated
        assert entity.last_seen > entity.first_seen

    def test_get_entity(self, entity_memory):
        """Test retrieving an entity."""
        entity_memory.add_entity(
            "PERSON",
            "Alice",
            {"age": 30, "city": "NYC"}
        )

        entity = entity_memory.get_entity("PERSON", "Alice")
        assert entity is not None
        assert entity.name == "Alice"
        assert entity.attributes["age"] == 30
        assert entity.attributes["city"] == "NYC"

    def test_get_entity_not_found(self, entity_memory):
        """Test getting non-existent entity."""
        entity = entity_memory.get_entity("PERSON", "NonExistent")
        assert entity is None

    def test_get_entities_by_type(self, entity_memory):
        """Test getting entities filtered by type."""
        entity_memory.add_entity("PERSON", "Alice", {})
        entity_memory.add_entity("PERSON", "Bob", {})
        entity_memory.add_entity("LOCATION", "Paris", {})
        entity_memory.add_entity("ORGANIZATION", "OpenAI", {})

        persons = entity_memory.get_entities_by_type("PERSON")
        assert len(persons) == 2
        assert all(e.entity_type == "PERSON" for e in persons)

        locations = entity_memory.get_entities_by_type("LOCATION")
        assert len(locations) == 1

    def test_update_entity(self, entity_memory):
        """Test updating an entity."""
        entity_memory.add_entity("PERSON", "Alice", {"age": 30})

        entity_memory.update_entity(
            "PERSON",
            "Alice",
            {"age": 31, "city": "Boston"}
        )

        entity = entity_memory.get_entity("PERSON", "Alice")
        assert entity.attributes["age"] == 31
        assert entity.attributes["city"] == "Boston"
        assert entity.count == 1  # Not incremented by update

    def test_update_nonexistent_entity(self, entity_memory):
        """Test updating non-existent entity creates it."""
        entity_memory.update_entity(
            "PERSON",
            "Charlie",
            {"age": 35}
        )

        entity = entity_memory.get_entity("PERSON", "Charlie")
        assert entity is not None
        assert entity.attributes["age"] == 35

    def test_add_relation(self, entity_memory):
        """Test adding a relation."""
        entity_memory.add_relation("Alice", "Bob", "knows")

        relations = entity_memory.get_all_relations()
        assert len(relations) == 1
        assert relations[0].from_entity == "Alice"
        assert relations[0].to_entity == "Bob"
        assert relations[0].relation_type == "knows"

    def test_add_relation_with_confidence(self, entity_memory):
        """Test adding a relation with confidence."""
        entity_memory.add_relation(
            "Alice",
            "OpenAI",
            "works_for",
            confidence=0.9
        )

        relations = entity_memory.get_all_relations()
        assert len(relations) == 1
        assert relations[0].confidence == 0.9

    def test_get_relations(self, entity_memory):
        """Test getting relations for an entity."""
        entity_memory.add_relation("Alice", "Bob", "knows")
        entity_memory.add_relation("Alice", "Charlie", "knows")
        entity_memory.add_relation("Bob", "Alice", "knows")

        alice_relations = entity_memory.get_relations("Alice")
        # get_relations returns all relations where Alice is either from_entity or to_entity
        assert len(alice_relations) == 3
        assert all("Alice" in [r.from_entity, r.to_entity] for r in alice_relations)

        bob_relations = entity_memory.get_relations("Bob")
        assert len(bob_relations) == 2
        assert all("Bob" in [r.from_entity, r.to_entity] for r in bob_relations)

    def test_get_relations_not_found(self, entity_memory):
        """Test getting relations for non-existent entity."""
        relations = entity_memory.get_relations("NonExistent")
        assert len(relations) == 0

    def test_merge_entities(self, entity_memory):
        """Test merging two entities."""
        entity_memory.add_entity("PERSON", "Alice", {"age": 30})
        entity_memory.add_entity("PERSON", "Alice Smith", {"age": 30, "city": "NYC"})

        # Add relation before merging
        entity_memory.add_relation("Bob", "Alice Smith", "knows")

        # Merge Alice Smith into Alice
        entity_memory.merge_entities("Alice Smith", "Alice")

        # Old entity should be removed
        old_entity = entity_memory.get_entity("PERSON", "Alice Smith")
        assert old_entity is None

        # New entity should have merged attributes
        new_entity = entity_memory.get_entity("PERSON", "Alice")
        assert new_entity is not None
        assert new_entity.attributes.get("city") == "NYC"

        # Relations should be updated
        alice_relations = [r for r in entity_memory.get_all_relations()
                          if r.to_entity == "Alice"]
        assert len(alice_relations) > 0

    def test_clear_expired_entities(self, entity_memory):
        """Test clearing expired entities."""
        # Create entity with TTL
        entity_memory = EntityMemory(
            session_id=str(uuid4()),
            ttl=timedelta(seconds=1)
        )

        entity_memory.add_entity("PERSON", "Alice", {})
        entity_memory.add_entity("PERSON", "Bob", {})

        # Manually expire Alice
        alice = entity_memory.get_entity("PERSON", "Alice")
        alice.last_seen = datetime.utcnow() - timedelta(seconds=2)

        # Clear expired
        entity_memory.clear_expired_entities()

        entities = entity_memory.get_all_entities()
        assert len(entities) == 1
        assert entities[0].name == "Bob"

    def test_clear_all_entities(self, entity_memory):
        """Test clearing all entities."""
        entity_memory.add_entity("PERSON", "Alice", {})
        entity_memory.add_entity("PERSON", "Bob", {})
        entity_memory.add_relation("Alice", "Bob", "knows")

        assert len(entity_memory.get_all_entities()) == 2
        assert len(entity_memory.get_all_relations()) == 1

        entity_memory.clear()

        assert len(entity_memory.get_all_entities()) == 0
        assert len(entity_memory.get_all_relations()) == 0

    def test_max_entities_limit(self):
        """Test max entities limit."""
        memory = EntityMemory(
            session_id=str(uuid4()),
            max_entities=3
        )

        # Add more than max
        for i in range(5):
            memory.add_entity("PERSON", f"Person{i}", {})

        # Should only keep 3 entities
        entities = memory.get_all_entities()
        assert len(entities) <= 3

    def test_get_entity_statistics(self, entity_memory):
        """Test getting entity statistics."""
        entity_memory.add_entity("PERSON", "Alice", {})
        entity_memory.add_entity("PERSON", "Bob", {})
        entity_memory.add_entity("LOCATION", "Paris", {})
        entity_memory.add_relation("Alice", "Bob", "knows")
        entity_memory.add_relation("Alice", "Paris", "lives_in")

        stats = entity_memory.get_statistics()
        assert stats["total_entities"] == 3
        assert stats["total_relations"] == 2
        assert stats["entities_by_type"]["PERSON"] == 2
        assert stats["entities_by_type"]["LOCATION"] == 1

    def test_search_entities_by_attribute(self, entity_memory):
        """Test searching entities by attributes."""
        entity_memory.add_entity("PERSON", "Alice", {"city": "NYC", "age": 30})
        entity_memory.add_entity("PERSON", "Bob", {"city": "NYC", "age": 25})
        entity_memory.add_entity("PERSON", "Charlie", {"city": "Boston", "age": 35})

        # Search by city
        nyc_people = entity_memory.search_entities("city", "NYC")
        assert len(nyc_people) == 2
        assert all(e.attributes.get("city") == "NYC" for e in nyc_people)

    def test_get_entity_context(self, entity_memory):
        """Test getting entity with context."""
        entity_memory.add_entity("PERSON", "Alice", {"city": "NYC"})
        entity_memory.add_entity("PERSON", "Bob", {"city": "NYC"})
        entity_memory.add_relation("Alice", "Bob", "knows")
        entity_memory.add_relation("Alice", "NYC", "lives_in")

        context = entity_memory.get_entity_context("Alice")
        assert context["entity"].name == "Alice"
        assert len(context["relations"]) >= 1

    def test_concurrent_entity_access(self, entity_memory):
        """Test thread-safe entity operations."""
        import threading

        def add_entities():
            for i in range(10):
                entity_memory.add_entity("PERSON", f"Person{i}", {})

        threads = [threading.Thread(target=add_entities) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should handle concurrent access safely
        entities = entity_memory.get_all_entities()
        assert len(entities) <= entity_memory.max_entities

    def test_entity_persistence_interface(self, entity_memory):
        """Test that entity can be serialized for persistence."""
        entity_memory.add_entity("PERSON", "Alice", {"age": 30})
        entity_memory.add_relation("Alice", "Bob", "knows")

        # Get all data for persistence
        entities_data = [e.model_dump() for e in entity_memory.get_all_entities()]
        relations_data = [r.model_dump() for r in entity_memory.get_all_relations()]

        assert len(entities_data) == 1
        assert len(relations_data) == 1
        assert entities_data[0]["name"] == "Alice"
        assert relations_data[0]["from_entity"] == "Alice"

    def test_langchain_compatibility_save_context(self, entity_memory):
        """Test LangChain compatibility through save_context."""
        # This would be used by LangChain chains
        # In a real implementation, this would extract entities from the text
        entity_memory.save_context(
            {"input": "Alice met Bob in Paris"},
            {"output": "That's interesting!"}
        )

        # Entities should be extracted and stored
        # For now, just test that the method exists and doesn't fail
        assert True

    def test_langchain_compatibility_load_memory_variables(self, entity_memory):
        """Test LangChain compatibility through load_memory_variables."""
        entity_memory.add_entity("PERSON", "Alice", {})
        entity_memory.add_entity("LOCATION", "Paris", {})

        variables = entity_memory.load_memory_variables({})

        assert "entities" in variables
        assert len(variables["entities"]) >= 2

    def test_invalid_entity_type(self, entity_memory):
        """Test adding entity with invalid type."""
        # Should still allow custom types
        entity_memory.add_entity("CUSTOM_TYPE", "Test", {})
        entity = entity_memory.get_entity("CUSTOM_TYPE", "Test")
        assert entity is not None

    def test_empty_entity_name(self, entity_memory):
        """Test adding entity with empty name."""
        with pytest.raises(MemoryValidationError):
            entity_memory.add_entity("PERSON", "", {})

    def test_entity_attributes_update(self, entity_memory):
        """Test that entity attributes can be partially updated."""
        entity_memory.add_entity("PERSON", "Alice", {"age": 30, "city": "NYC"})

        # Update only age
        entity_memory.update_entity("PERSON", "Alice", {"age": 31})

        entity = entity_memory.get_entity("PERSON", "Alice")
        assert entity.attributes["age"] == 31
        assert entity.attributes["city"] == "NYC"  # Should preserve
