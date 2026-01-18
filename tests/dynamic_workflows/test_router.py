"""
Tests for dynamic workflow router
"""
import pytest
from typing import Any, Dict

from src.dynamic_workflows.router import (
    DynamicRouter,
    RouteCondition,
    RoutingStrategy,
    ConditionalRouting,
    create_router,
)


class TestRouteCondition:
    """Test RouteCondition"""

    def test_create_condition(self):
        """Test creating a route condition"""
        condition = RouteCondition(
            name="test_condition",
            expression="state.value > 10",
            target_node="process_large"
        )

        assert condition.name == "test_condition"
        assert condition.expression == "state.value > 10"
        assert condition.target_node == "process_large"

    def test_evaluate_condition(self):
        """Test evaluating a condition"""
        condition = RouteCondition(
            name="check_value",
            expression="state.get('value', 0) > 5",
            target_node="greater_than_five"
        )

        # Test true condition
        assert condition.evaluate({"value": 10}) is True

        # Test false condition
        assert condition.evaluate({"value": 3}) is False

        # Test missing key
        assert condition.evaluate({}) is False


class TestDynamicRouter:
    """Test DynamicRouter"""

    def test_create_router(self):
        """Test creating a router"""
        router = DynamicRouter(name="test_router")

        assert router.name == "test_router"
        assert len(router.conditions) == 0
        assert router.default_target is None

    def test_add_condition(self):
        """Test adding a condition"""
        router = DynamicRouter(name="test_router")
        condition = RouteCondition(
            name="cond1",
            expression="state.type == 'A'",
            target_node="handle_a"
        )

        router.add_condition(condition)

        assert len(router.conditions) == 1
        assert router.conditions[0].name == "cond1"

    def test_route_with_single_condition(self):
        """Test routing with a single condition"""
        router = DynamicRouter(name="single_router")
        router.add_condition(
            RouteCondition(
                name="check_type",
                expression="state.get('type') == 'urgent'",
                target_node="urgent_handler"
            )
        )
        router.set_default("normal_handler")

        # Urgent route
        result = router.route({"type": "urgent"})
        assert result == "urgent_handler"

        # Normal route
        result = router.route({"type": "normal"})
        assert result == "normal_handler"

    def test_route_with_multiple_conditions(self):
        """Test routing with multiple conditions"""
        router = DynamicRouter(name="multi_router")
        router.add_condition(
            RouteCondition(
                name="check_vip",
                expression="state.get('user_level') == 'vip'",
                target_node="vip_handler"
            )
        )
        router.add_condition(
            RouteCondition(
                name="check_premium",
                expression="state.get('user_level') == 'premium'",
                target_node="premium_handler"
            )
        )
        router.set_default("regular_handler")

        # VIP user
        result = router.route({"user_level": "vip"})
        assert result == "vip_handler"

        # Premium user
        result = router.route({"user_level": "premium"})
        assert result == "premium_handler"

        # Regular user
        result = router.route({"user_level": "regular"})
        assert result == "regular_handler"

    def test_route_priority(self):
        """Test that conditions are evaluated in order"""
        router = DynamicRouter(name="priority_router")
        # Add conditions in specific order
        router.add_condition(
            RouteCondition(
                name="first_check",
                expression="True",  # Always true
                target_node="first_target"
            )
        )
        router.add_condition(
            RouteCondition(
                name="second_check",
                expression="True",  # Also always true
                target_node="second_target"
            )
        )

        # Should match first condition
        result = router.route({})
        assert result == "first_target"


class TestRoutingStrategy:
    """Test RoutingStrategy"""

    def test_first_match_strategy(self):
        """Test first-match routing strategy"""
        strategy = RoutingStrategy.FIRST_MATCH

        router = DynamicRouter(name="strategy_router", strategy=strategy)
        router.add_condition(
            RouteCondition("always_true", "True", "target_a")
        )
        router.add_condition(
            RouteCondition("also_true", "True", "target_b")
        )

        result = router.route({})
        assert result == "target_a"  # First match

    def test_all_match_strategy(self):
        """Test all-match routing strategy"""
        strategy = RoutingStrategy.ALL_MATCH

        router = DynamicRouter(name="all_match_router", strategy=strategy)
        router.add_condition(
            RouteCondition("cond_a", "state.get('a')", "target_a")
        )
        router.add_condition(
            RouteCondition("cond_b", "state.get('b')", "target_b")
        )

        # Both match
        result = router.route({"a": True, "b": True})
        assert set(result) == {"target_a", "target_b"}

        # Only one matches
        result = router.route({"a": True, "b": False})
        assert result == ["target_a"]

    def test_priority_strategy(self):
        """Test priority-based routing"""
        router = DynamicRouter(name="priority_router", strategy=RoutingStrategy.PRIORITY)
        router.add_condition(
            RouteCondition("low_priority", "True", "low", priority=1)
        )
        router.add_condition(
            RouteCondition("high_priority", "True", "high", priority=10)
        )

        # Should pick highest priority
        result = router.route({})
        assert result == "high"


class TestConditionalRouting:
    """Test ConditionalRouting"""

    def test_create_conditional_routing(self):
        """Test creating conditional routing"""
        routing = ConditionalRouting(
            name="conditional_flow",
            default_target="default"
        )

        routing.add_route(
            condition="state.get('status') == 'success'",
            target="success_handler"
        )
        routing.add_route(
            condition="state.get('status') == 'error'",
            target="error_handler"
        )

        # Success case
        result = routing.evaluate({"status": "success"})
        assert result == "success_handler"

        # Error case
        result = routing.evaluate({"status": "error"})
        assert result == "error_handler"

        # Default case
        result = routing.evaluate({"status": "unknown"})
        assert result == "default"


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_create_router(self):
        """Test create_router convenience function"""
        router = create_router(
            name="convenience_router",
            routes=[
                {
                    "name": "route_a",
                    "expression": "state.get('type') == 'A'",
                    "target": "handler_a"
                },
                {
                    "name": "route_b",
                    "expression": "state.get('type') == 'B'",
                    "target": "handler_b"
                }
            ],
            default="default_handler"
        )

        result = router.route({"type": "A"})
        assert result == "handler_a"

        result = router.route({"type": "B"})
        assert result == "handler_b"

        result = router.route({"type": "C"})
        assert result == "default_handler"

    def test_router_from_config(self):
        """Test creating router from configuration dict"""
        config = {
            "name": "config_router",
            "strategy": "first_match",
            "routes": [
                {
                    "name": "route1",
                    "expression": "state.get('value', 0) > 100",
                    "target": "high"
                },
                {
                    "name": "route2",
                    "expression": "state.get('value', 0) > 50",
                    "target": "medium"
                }
            ],
            "default": "low"
        }

        router = create_router(**config)

        # High value
        result = router.route({"value": 150})
        assert result == "high"

        # Medium value
        result = router.route({"value": 75})
        assert result == "medium"

        # Low value
        result = router.route({"value": 25})
        assert result == "low"
