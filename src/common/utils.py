"""
Common Utility Functions

This module contains common utility functions used across the application.
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Callable, Awaitable

from pydantic import BaseModel


T = TypeVar('T')


# =============================================================================
# ID Generation
# =============================================================================

def generate_id() -> str:
    """
    Generate a unique ID.

    Returns:
        str: Unique identifier
    """
    return str(uuid.uuid4())


def generate_short_id() -> str:
    """
    Generate a short unique ID (8 characters).

    Returns:
        str: Short unique identifier
    """
    return str(uuid.uuid4())[:8]


# =============================================================================
# Hashing
# =============================================================================

def hash_string(text: str, algorithm: str = "sha256") -> str:
    """
    Hash a string using the specified algorithm.

    Args:
        text: Text to hash
        algorithm: Hash algorithm (default: sha256)

    Returns:
        str: Hexadecimal hash
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(text.encode())
    return hash_obj.hexdigest()


# =============================================================================
# Serialization
# =============================================================================

def to_json(obj: Any, pretty: bool = False) -> str:
    """
    Convert object to JSON string.

    Args:
        obj: Object to serialize
        pretty: Whether to pretty-print the JSON

    Returns:
        str: JSON string
    """
    if pretty:
        return json.dumps(obj, indent=2, default=str)
    return json.dumps(obj, default=str)


def from_json(json_str: str) -> Any:
    """
    Parse JSON string to object.

    Args:
        json_str: JSON string to parse

    Returns:
        Any: Parsed object
    """
    return json.loads(json_str)


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """
    Convert Pydantic model to dictionary.

    Args:
        model: Pydantic model

    Returns:
        Dict[str, Any]: Dictionary representation
    """
    return model.model_dump()


def model_to_json(model: BaseModel, pretty: bool = False) -> str:
    """
    Convert Pydantic model to JSON string.

    Args:
        model: Pydantic model
        pretty: Whether to pretty-print the JSON

    Returns:
        str: JSON string
    """
    if pretty:
        return model.model_dump_json(indent=2)
    return model.model_dump_json()


# =============================================================================
# Time Utilities
# =============================================================================

def get_timestamp() -> datetime:
    """
    Get current UTC timestamp.

    Returns:
        datetime: Current UTC timestamp
    """
    return datetime.utcnow()


def timestamp_to_iso(timestamp: datetime) -> str:
    """
    Convert timestamp to ISO format string.

    Args:
        timestamp: Datetime object

    Returns:
        str: ISO format string
    """
    return timestamp.isoformat()


def iso_to_timestamp(iso_string: str) -> datetime:
    """
    Parse ISO format string to timestamp.

    Args:
        iso_string: ISO format string

    Returns:
        datetime: Parsed timestamp
    """
    return datetime.fromisoformat(iso_string)


# =============================================================================
# Async Utilities
# =============================================================================

async def run_async(coro: Awaitable[T]) -> T:
    """
    Run a coroutine and return the result.

    Args:
        coro: Coroutine to run

    Returns:
        T: Result of the coroutine
    """
    return await coro


async def gather(*coros: Awaitable[Any]) -> List[Any]:
    """
    Gather multiple coroutines and run them concurrently.

    Args:
        *coros: Coroutines to run

    Returns:
        List[Any]: List of results
    """
    return await asyncio.gather(*coros)


async def run_with_timeout(
    coro: Awaitable[T],
    timeout: float
) -> T:
    """
    Run a coroutine with a timeout.

    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds

    Returns:
        T: Result of the coroutine

    Raises:
        asyncio.TimeoutError: If the coroutine times out
    """
    return await asyncio.wait_for(coro, timeout=timeout)


# =============================================================================
# Validation Utilities
# =============================================================================

def is_empty(value: Any) -> bool:
    """
    Check if a value is empty.

    Args:
        value: Value to check

    Returns:
        bool: True if the value is empty
    """
    if value is None:
        return True
    if isinstance(value, (str, list, dict, set, tuple)):
        return len(value) == 0
    return False


def is_not_empty(value: Any) -> bool:
    """
    Check if a value is not empty.

    Args:
        value: Value to check

    Returns:
        bool: True if the value is not empty
    """
    return not is_empty(value)


def require_non_empty(value: Any, field_name: str = "value") -> Any:
    """
    Require that a value is not empty.

    Args:
        value: Value to check
        field_name: Name of the field for error message

    Returns:
        Any: The value if not empty

    Raises:
        ValueError: If the value is empty
    """
    if is_empty(value):
        raise ValueError(f"{field_name} cannot be empty")
    return value


# =============================================================================
# String Utilities
# =============================================================================

def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def snake_to_camel(snake_str: str) -> str:
    """
    Convert snake_case to camelCase.

    Args:
        snake_str: Snake case string

    Returns:
        str: Camel case string
    """
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """
    Convert camelCase to snake_case.

    Args:
        camel_str: Camel case string

    Returns:
        str: Snake case string
    """
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


# =============================================================================
# List Utilities
# =============================================================================

def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """
    Split a list into chunks.

    Args:
        items: List to split
        chunk_size: Size of each chunk

    Returns:
        List[List[T]]: List of chunks
    """
    chunks = []
    for i in range(0, len(items), chunk_size):
        chunks.append(items[i:i + chunk_size])
    return chunks


def flatten_list(nested_list: List[List[T]]) -> List[T]:
    """
    Flatten a nested list.

    Args:
        nested_list: Nested list to flatten

    Returns:
        List[T]: Flattened list
    """
    return [item for sublist in nested_list for item in sublist]


def remove_duplicates(items: List[T]) -> List[T]:
    """
    Remove duplicates from a list while preserving order.

    Args:
        items: List to deduplicate

    Returns:
        List[T]: Deduplicated list
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# =============================================================================
# Dict Utilities
# =============================================================================

def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)

    Returns:
        Dict: Merged dictionary
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def filter_keys(dictionary: Dict, keys: List[str]) -> Dict:
    """
    Filter dictionary to only include specified keys.

    Args:
        dictionary: Dictionary to filter
        keys: Keys to include

    Returns:
        Dict: Filtered dictionary
    """
    return {k: v for k, v in dictionary.items() if k in keys}


def exclude_keys(dictionary: Dict, keys: List[str]) -> Dict:
    """
    Exclude specified keys from dictionary.

    Args:
        dictionary: Dictionary to filter
        keys: Keys to exclude

    Returns:
        Dict: Filtered dictionary
    """
    return {k: v for k, v in dictionary.items() if k not in keys}


# =============================================================================
# Logging Utilities
# =============================================================================

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


# =============================================================================
# Type Utilities
# =============================================================================

def get_type_name(obj: Any) -> str:
    """
    Get the type name of an object.

    Args:
        obj: Object to get type name for

    Returns:
        str: Type name
    """
    return type(obj).__name__


def is_model(obj: Any) -> bool:
    """
    Check if an object is a Pydantic model.

    Args:
        obj: Object to check

    Returns:
        bool: True if the object is a Pydantic model
    """
    return isinstance(obj, BaseModel)
