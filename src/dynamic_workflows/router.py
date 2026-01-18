"""
Dynamic Workflow Router

Provides dynamic routing capabilities for LangGraph workflows.
Supports conditional routing, priority-based routing, and multiple strategies.
"""
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import re


class RoutingStrategy(Enum):
    """Routing strategies"""
    FIRST_MATCH = "first_match"  # Return first matching route
    ALL_MATCH = "all_match"      # Return all matching routes
    PRIORITY = "priority"        # Route by priority (highest first)


class RouteCondition:
    """
    Represents a routing condition

    Conditions are evaluated against workflow state to determine routing.
    """

    def __init__(
        self,
        name: str,
        expression: str,
        target_node: str,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize route condition

        Args:
            name: Unique name for this condition
            expression: Python expression to evaluate
                Can use 'state' variable to access state data
            target_node: Node to route to if condition matches
            priority: Priority for PRIORITY strategy (higher = more important)
            metadata: Additional metadata
        """
        self.name = name
        self.expression = expression
        self.target_node = target_node
        self.priority = priority
        self.metadata = metadata or {}

    def evaluate(self, state: Dict[str, Any]) -> bool:
        """
        Evaluate the condition against state

        Args:
            state: Workflow state dictionary

        Returns:
            True if condition matches, False otherwise
        """
        try:
            # Create a safe evaluation context
            context = {"state": state}

            # Evaluate expression
            result = eval(self.expression, {"__builtins__": {}}, context)
            return bool(result)
        except Exception:
            # If evaluation fails, return False
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "expression": self.expression,
            "target_node": self.target_node,
            "priority": self.priority,
            "metadata": self.metadata
        }


class DynamicRouter:
    """
    Dynamic router for workflow routing decisions

    Supports multiple routing strategies and condition evaluation.
    """

    def __init__(
        self,
        name: str,
        strategy: RoutingStrategy = RoutingStrategy.FIRST_MATCH,
        default_target: Optional[str] = None
    ):
        """
        Initialize router

        Args:
            name: Router name
            strategy: Routing strategy to use
            default_target: Default node if no conditions match
        """
        self.name = name
        self.strategy = strategy
        self.default_target = default_target
        self.conditions: List[RouteCondition] = []

    def add_condition(self, condition: RouteCondition) -> "DynamicRouter":
        """
        Add a routing condition

        Args:
            condition: Route condition to add

        Returns:
            Self for method chaining
        """
        self.conditions.append(condition)
        return self

    def set_default(self, target: str) -> "DynamicRouter":
        """
        Set default target node

        Args:
            target: Default node name

        Returns:
            Self for method chaining
        """
        self.default_target = target
        return self

    def route(self, state: Dict[str, Any]) -> Union[str, List[str]]:
        """
        Route to target node(s) based on state

        Args:
            state: Current workflow state

        Returns:
            Target node name(s)
        """
        if self.strategy == RoutingStrategy.FIRST_MATCH:
            return self._route_first_match(state)
        elif self.strategy == RoutingStrategy.ALL_MATCH:
            return self._route_all_match(state)
        elif self.strategy == RoutingStrategy.PRIORITY:
            return self._route_by_priority(state)
        else:
            return self.default_target

    def _route_first_match(self, state: Dict[str, Any]) -> str:
        """First-match routing"""
        for condition in self.conditions:
            if condition.evaluate(state):
                return condition.target_node
        return self.default_target

    def _route_all_match(self, state: Dict[str, Any]) -> List[str]:
        """All-match routing"""
        matches = [
            condition.target_node
            for condition in self.conditions
            if condition.evaluate(state)
        ]
        return matches if matches else [self.default_target]

    def _route_by_priority(self, state: Dict[str, Any]) -> str:
        """Priority-based routing"""
        matching_conditions = [
            condition
            for condition in self.conditions
            if condition.evaluate(state)
        ]

        if not matching_conditions:
            return self.default_target

        # Sort by priority (highest first)
        matching_conditions.sort(key=lambda c: c.priority, reverse=True)
        return matching_conditions[0].target_node

    def to_dict(self) -> Dict[str, Any]:
        """Convert router to dictionary"""
        return {
            "name": self.name,
            "strategy": self.strategy.value,
            "default_target": self.default_target,
            "conditions": [c.to_dict() for c in self.conditions]
        }


class ConditionalRouting:
    """
    High-level conditional routing

    Provides a simpler interface for common routing patterns.
    """

    def __init__(
        self,
        name: str,
        default_target: str
    ):
        """
        Initialize conditional routing

        Args:
            name: Routing name
            default_target: Default target node
        """
        self.name = name
        self.default_target = default_target
        self.router = DynamicRouter(name, default_target=default_target)

    def add_route(
        self,
        condition: str,
        target: str,
        priority: int = 0
    ) -> "ConditionalRouting":
        """
        Add a route

        Args:
            condition: Condition expression
            target: Target node
            priority: Route priority

        Returns:
            Self for method chaining
        """
        route_condition = RouteCondition(
            name=f"route_{len(self.router.conditions)}",
            expression=condition,
            target_node=target,
            priority=priority
        )
        self.router.add_condition(route_condition)
        return self

    def evaluate(self, state: Dict[str, Any]) -> str:
        """
        Evaluate routing

        Args:
            state: Workflow state

        Returns:
            Target node name
        """
        return self.router.route(state)


def create_router(
    name: str,
    routes: List[Dict[str, Any]],
    default: str,
    strategy: str = "first_match"
) -> DynamicRouter:
    """
    Convenience function to create a router

    Args:
        name: Router name
        routes: List of route definitions
            Each route should have:
            - name: Route name
            - expression: Condition expression
            - target: Target node
            - priority: Priority (optional)
        default: Default target node
        strategy: Routing strategy

    Returns:
        Configured router
    """
    # Parse strategy
    try:
        routing_strategy = RoutingStrategy(strategy)
    except ValueError:
        routing_strategy = RoutingStrategy.FIRST_MATCH

    router = DynamicRouter(
        name=name,
        strategy=routing_strategy,
        default_target=default
    )

    # Add routes
    for route_def in routes:
        condition = RouteCondition(
            name=route_def.get("name", f"route_{len(router.conditions)}"),
            expression=route_def["expression"],
            target_node=route_def["target"],
            priority=route_def.get("priority", 0),
            metadata=route_def.get("metadata", {})
        )
        router.add_condition(condition)

    return router
