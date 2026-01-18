"""
Tests for common utility functions
"""

import pytest

from src.common.utils import (
    generate_id,
    generate_short_id,
    hash_string,
    to_json,
    from_json,
    get_timestamp,
    is_empty,
    is_not_empty,
    truncate,
    snake_to_camel,
    camel_to_snake,
    chunk_list,
    flatten_list,
    remove_duplicates,
    deep_merge,
    get_type_name,
)


class TestIdGeneration:
    """Test ID generation functions."""

    def test_generate_id(self):
        """Test generate_id."""
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) == 36  # UUID length

    def test_generate_short_id(self):
        """Test generate_short_id."""
        id1 = generate_short_id()
        id2 = generate_short_id()
        assert id1 != id2
        assert len(id1) == 8


class TestHashing:
    """Test hashing functions."""

    def test_hash_string(self):
        """Test hash_string."""
        hash1 = hash_string("test")
        hash2 = hash_string("test")
        assert hash1 == hash2

        hash3 = hash_string("different")
        assert hash1 != hash3


class TestSerialization:
    """Test serialization functions."""

    def test_to_json(self):
        """Test to_json."""
        data = {"key": "value"}
        json_str = to_json(data)
        assert "key" in json_str
        assert "value" in json_str

    def test_from_json(self):
        """Test from_json."""
        json_str = '{"key": "value"}'
        data = from_json(json_str)
        assert data["key"] == "value"


class TestTimeUtilities:
    """Test time utility functions."""

    def test_get_timestamp(self):
        """Test get_timestamp."""
        timestamp = get_timestamp()
        assert timestamp is not None


class TestValidationUtilities:
    """Test validation utilities."""

    def test_is_empty(self):
        """Test is_empty."""
        assert is_empty(None) is True
        assert is_empty("") is True
        assert is_empty([]) is True
        assert is_empty({}) is True
        assert is_empty("text") is False
        assert is_empty([1]) is False

    def test_is_not_empty(self):
        """Test is_not_empty."""
        assert is_not_empty("text") is True
        assert is_not_empty([1]) is True
        assert is_not_empty("") is False
        assert is_not_empty(None) is False


class TestStringUtilities:
    """Test string utility functions."""

    def test_truncate(self):
        """Test truncate."""
        text = "This is a long text"
        assert truncate(text, 10) == "This is..."
        assert truncate(text, 100) == text

    def test_snake_to_camel(self):
        """Test snake_to_camel."""
        assert snake_to_camel("hello_world") == "helloWorld"
        assert snake_to_camel("this_is_a_test") == "thisIsATest"

    def test_camel_to_snake(self):
        """Test camel_to_snake."""
        assert camel_to_snake("helloWorld") == "hello_world"
        assert camel_to_snake("thisIsATest") == "this_is_a_test"


class TestListUtilities:
    """Test list utility functions."""

    def test_chunk_list(self):
        """Test chunk_list."""
        items = [1, 2, 3, 4, 5]
        chunks = chunk_list(items, 2)
        assert len(chunks) == 3
        assert chunks[0] == [1, 2]
        assert chunks[-1] == [5]

    def test_flatten_list(self):
        """Test flatten_list."""
        nested = [[1, 2], [3, 4], [5]]
        flattened = flatten_list(nested)
        assert flattened == [1, 2, 3, 4, 5]

    def test_remove_duplicates(self):
        """Test remove_duplicates."""
        items = [1, 2, 2, 3, 3, 3]
        unique = remove_duplicates(items)
        assert unique == [1, 2, 3]


class TestDictUtilities:
    """Test dictionary utility functions."""

    def test_deep_merge(self):
        """Test deep_merge."""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}
        merged = deep_merge(dict1, dict2)
        assert merged["a"] == 1
        assert merged["b"]["c"] == 2
        assert merged["b"]["d"] == 3
        assert merged["e"] == 4


class TestTypeUtilities:
    """Test type utility functions."""

    def test_get_type_name(self):
        """Test get_type_name."""
        assert get_type_name("test") == "str"
        assert get_type_name(123) == "int"
        assert get_type_name([1, 2]) == "list"
