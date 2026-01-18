"""
Entity Memory Implementation

This module provides entity-based conversation memory that extracts, stores,
and manages entities (people, places, organizations, etc.) from conversations.
Compatible with LangChain 1.2.x.
"""

import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.common.types.memory_types import MemoryType, MemoryScope
from src.common.exceptions import MemoryValidationError, MemoryOperationError


# =============================================================================
# Entity Data Models
# =============================================================================

class Entity(BaseModel):
    """
    Represents a single entity (person, location, organization, etc.).

    Attributes:
        entity_type: Type of entity (PERSON, LOCATION, ORGANIZATION, etc.)
        name: Entity name/identifier
        attributes: Additional attributes and metadata
        first_seen: When entity was first encountered
        last_seen: When entity was last seen/updated
        count: Number of times entity has been mentioned
    """

    model_config = ConfigDict(use_enum_values=False)

    entity_type: str
    name: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    count: int = Field(default=1, ge=1)


class EntityRelation(BaseModel):
    """
    Represents a relationship between two entities.

    Attributes:
        from_entity: Source entity name
        to_entity: Target entity name
        relation_type: Type of relationship (knows, works_for, located_in, etc.)
        confidence: Confidence score for this relation (0-1)
        created_at: When relation was created
    """

    model_config = ConfigDict(use_enum_values=False)

    from_entity: str
    to_entity: str
    relation_type: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Entity Memory Implementation
# =============================================================================

class EntityMemory:
    """
    Entity-based conversation memory.

    Extracts, stores, and manages entities from conversations.
    Supports entity relationships, attribute tracking, and expiration.

    Attributes:
        session_id: Session identifier
        max_entities: Maximum number of entities to store
        ttl: Time-to-live for entities (None = no expiration)
        return_messages: Whether to return messages (LangChain compatibility)

    Example:
        >>> memory = EntityMemory(session_id="session123")
        >>> memory.add_entity("PERSON", "Alice", {"age": 30})
        >>> memory.add_relation("Alice", "Bob", "knows")
        >>> entity = memory.get_entity("PERSON", "Alice")
        >>> relations = memory.get_relations("Alice")
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        max_entities: int = 1000,
        ttl: Optional[timedelta] = None,
        return_messages: bool = True,
    ):
        """
        Initialize EntityMemory.

        Args:
            session_id: Session identifier
            max_entities: Maximum number of entities to store
            ttl: Time-to-live for entities (None = no expiration)
            return_messages: Whether to return messages (LangChain compatibility)

        Raises:
            MemoryValidationError: If parameters are invalid
        """
        if max_entities <= 0:
            raise MemoryValidationError(
                f"max_entities must be positive, got {max_entities}"
            )

        self.session_id = session_id or str(uuid4())
        self.max_entities = max_entities
        self.ttl = ttl
        self.return_messages = return_messages

        # Entity storage: {(entity_type, name): Entity}
        self._entities: Dict[Tuple[str, str], Entity] = {}
        # Relation storage
        self._relations: List[EntityRelation] = []

        # Thread safety
        self._lock = threading.Lock()

    def add_entity(
        self,
        entity_type: str,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Entity:
        """
        Add or update an entity.

        Args:
            entity_type: Type of entity (PERSON, LOCATION, etc.)
            name: Entity name
            attributes: Entity attributes

        Returns:
            The added/updated entity

        Raises:
            MemoryValidationError: If entity name is empty
        """
        if not name or not name.strip():
            raise MemoryValidationError("Entity name cannot be empty")

        attributes = attributes or {}
        key = (entity_type, name)

        try:
            with self._lock:
                now = datetime.utcnow()

                if key in self._entities:
                    # Update existing entity
                    entity = self._entities[key]
                    entity.attributes.update(attributes)
                    entity.last_seen = now
                    entity.count += 1
                else:
                    # Create new entity
                    if len(self._entities) >= self.max_entities:
                        # Remove oldest entity (FIFO)
                        oldest_key = min(
                            self._entities.keys(),
                            key=lambda k: self._entities[k].first_seen
                        )
                        del self._entities[oldest_key]

                    entity = Entity(
                        entity_type=entity_type,
                        name=name,
                        attributes=attributes,
                        first_seen=now,
                        last_seen=now,
                        count=1
                    )
                    self._entities[key] = entity

                return entity

        except Exception as e:
            raise MemoryOperationError(
                f"Failed to add entity '{name}': {str(e)}"
            )

    def get_entity(self, entity_type: str, name: str) -> Optional[Entity]:
        """
        Get an entity by type and name.

        Args:
            entity_type: Type of entity
            name: Entity name

        Returns:
            Entity or None if not found
        """
        with self._lock:
            key = (entity_type, name)
            entity = self._entities.get(key)

            # Check expiration
            if entity and self.ttl:
                if datetime.utcnow() - entity.last_seen > self.ttl:
                    return None

            return entity

    def get_all_entities(self) -> List[Entity]:
        """
        Get all entities.

        Returns:
            List of all entities
        """
        with self._lock:
            # Filter expired entities
            if self.ttl:
                now = datetime.utcnow()
                entities = [
                    e for e in self._entities.values()
                    if now - e.last_seen <= self.ttl
                ]
            else:
                entities = list(self._entities.values())

            return entities

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """
        Get all entities of a specific type.

        Args:
            entity_type: Type of entity to retrieve

        Returns:
            List of entities of the specified type
        """
        with self._lock:
            entities = [
                e for (t, _), e in self._entities.items()
                if t == entity_type
            ]

            # Filter expired
            if self.ttl:
                now = datetime.utcnow()
                entities = [e for e in entities if now - e.last_seen <= self.ttl]

            return entities

    def update_entity(
        self,
        entity_type: str,
        name: str,
        attributes: Dict[str, Any]
    ) -> Entity:
        """
        Update an entity's attributes.

        Args:
            entity_type: Type of entity
            name: Entity name
            attributes: Attributes to update

        Returns:
            Updated entity (creates if doesn't exist)
        """
        with self._lock:
            key = (entity_type, name)

            if key in self._entities:
                entity = self._entities[key]
                entity.attributes.update(attributes)
                entity.last_seen = datetime.utcnow()
                return entity
            else:
                # Create new entity directly (avoid calling add_entity to prevent deadlock)
                now = datetime.utcnow()
                entity = Entity(
                    entity_type=entity_type,
                    name=name,
                    attributes=attributes,
                    first_seen=now,
                    last_seen=now,
                    count=1
                )
                self._entities[key] = entity
                return entity

    def add_relation(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str,
        confidence: float = 1.0
    ) -> EntityRelation:
        """
        Add a relation between two entities.

        Args:
            from_entity: Source entity name
            to_entity: Target entity name
            relation_type: Type of relationship
            confidence: Confidence score (0-1)

        Returns:
            Created relation
        """
        try:
            with self._lock:
                relation = EntityRelation(
                    from_entity=from_entity,
                    to_entity=to_entity,
                    relation_type=relation_type,
                    confidence=confidence
                )
                self._relations.append(relation)
                return relation

        except Exception as e:
            raise MemoryOperationError(
                f"Failed to add relation: {str(e)}"
            )

    def get_relations(self, entity_name: str) -> List[EntityRelation]:
        """
        Get all relations for an entity.

        Args:
            entity_name: Entity name

        Returns:
            List of relations where entity is either source or target
        """
        with self._lock:
            return [
                r for r in self._relations
                if r.from_entity == entity_name or r.to_entity == entity_name
            ]

    def get_all_relations(self) -> List[EntityRelation]:
        """
        Get all relations.

        Returns:
            List of all relations
        """
        with self._lock:
            return self._relations.copy()

    def merge_entities(self, old_name: str, new_name: str) -> None:
        """
        Merge two entities (e.g., "Alice Smith" -> "Alice").

        Args:
            old_name: Old entity name to merge from
            new_name: New entity name to merge into
        """
        with self._lock:
            # Find all entities with old_name
            keys_to_merge = [
                (entity_type, name) for (entity_type, name) in self._entities
                if name == old_name
            ]

            for key in keys_to_merge:
                entity_type, _ = key
                old_entity = self._entities[key]
                new_key = (entity_type, new_name)

                if new_key in self._entities:
                    # Merge into existing entity
                    new_entity = self._entities[new_key]
                    new_entity.attributes.update(old_entity.attributes)
                    new_entity.count += old_entity.count
                    # Keep earliest first_seen
                    if old_entity.first_seen < new_entity.first_seen:
                        new_entity.first_seen = old_entity.first_seen
                    # Delete old entity after merging
                    del self._entities[key]
                else:
                    # Move entity to new name
                    entity = self._entities.pop(key)
                    entity.name = new_name
                    self._entities[new_key] = entity

                # Update relations
                for relation in self._relations:
                    if relation.to_entity == old_name:
                        relation.to_entity = new_name
                    if relation.from_entity == old_name:
                        relation.from_entity = new_name

    def clear_expired_entities(self) -> int:
        """
        Remove expired entities based on TTL.

        Returns:
            Number of entities removed
        """
        if not self.ttl:
            return 0

        with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, entity in self._entities.items()
                if now - entity.last_seen > self.ttl
            ]

            for key in expired_keys:
                del self._entities[key]

            return len(expired_keys)

    def clear(self) -> None:
        """Clear all entities and relations."""
        with self._lock:
            self._entities.clear()
            self._relations.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            entities = list(self._entities.values())

            # Count by type
            entities_by_type: Dict[str, int] = {}
            for entity in entities:
                entities_by_type[entity.entity_type] = \
                    entities_by_type.get(entity.entity_type, 0) + 1

            return {
                "total_entities": len(entities),
                "total_relations": len(self._relations),
                "entities_by_type": entities_by_type,
                "session_id": self.session_id,
                "max_entities": self.max_entities,
                "ttl_seconds": self.ttl.total_seconds() if self.ttl else None,
            }

    def search_entities(
        self,
        attribute_key: str,
        attribute_value: Any
    ) -> List[Entity]:
        """
        Search entities by attribute.

        Args:
            attribute_key: Attribute key to search
            attribute_value: Value to match

        Returns:
            List of matching entities
        """
        with self._lock:
            return [
                e for e in self._entities.values()
                if e.attributes.get(attribute_key) == attribute_value
            ]

    def get_entity_context(self, entity_name: str) -> Dict[str, Any]:
        """
        Get entity with its relations and context.

        Args:
            entity_name: Entity name

        Returns:
            Dictionary with entity and its context
        """
        with self._lock:
            # Find entity (any type)
            entity = next(
                (e for e in self._entities.values() if e.name == entity_name),
                None
            )

            if not entity:
                return {"entity": None, "relations": [], "related_entities": []}

            # Get relations directly without calling get_relations to avoid deadlock
            relations = [
                r for r in self._relations
                if r.from_entity == entity_name or r.to_entity == entity_name
            ]

            # Get related entities
            related_names = set()
            for rel in relations:
                related_names.add(rel.to_entity)
                related_names.add(rel.from_entity)
            related_names.discard(entity_name)

            related_entities = [
                e for e in self._entities.values()
                if e.name in related_names
            ]

            return {
                "entity": entity,
                "relations": relations,
                "related_entities": related_entities,
            }

    # ========================================================================
    # LangChain Compatibility Methods
    # ========================================================================

    def save_context(
        self,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> None:
        """
        Save context from conversation (LangChain compatibility).

        In a full implementation, this would extract entities from the text.
        For now, it's a placeholder for future NLP integration.

        Args:
            inputs: Input dictionary
            outputs: Output dictionary
        """
        # Placeholder: In production, you would use NLP to extract entities
        # from inputs["input"] and outputs["output"]
        pass

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load memory variables (LangChain compatibility).

        Args:
            inputs: Input variables

        Returns:
            Dictionary with entities and context
        """
        entities = self.get_all_entities()

        return {
            "entities": [e.model_dump() for e in entities],
            "entity_count": len(entities),
            "relations": [r.model_dump() for r in self.get_all_relations()],
        }

    @property
    def memory_type(self) -> MemoryType:
        """Get memory type (for compatibility)."""
        return MemoryType.WORKING

    @property
    def scope(self) -> MemoryScope:
        """Get memory scope (for compatibility)."""
        return MemoryScope.SESSION

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"EntityMemory("
            f"entities={len(self._entities)}, "
            f"relations={len(self._relations)}, "
            f"max={self.max_entities}, "
            f"session={self.session_id[:8]})"
        )


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "EntityMemory",
    "Entity",
    "EntityRelation",
]
