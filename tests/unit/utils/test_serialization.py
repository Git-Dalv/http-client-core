"""Tests for response serialization utilities."""

import pytest
import requests
from datetime import timedelta

from src.http_client.utils.serialization import serialize_response, deserialize_response


class TestSerializeResponse:
    """Test serialize_response function."""

    def test_serialize_response_basic(self):
        """Test basic response serialization."""
        # Create mock response
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b'{"key": "value"}'
        resp.headers = {'Content-Type': 'application/json'}
        resp.url = 'https://example.com/api'
        resp.encoding = 'utf-8'
        resp.reason = 'OK'
        resp.elapsed = timedelta(seconds=0.5)

        # Serialize
        data = serialize_response(resp)

        # Verify
        assert data['status_code'] == 200
        assert data['content'] == b'{"key": "value"}'
        assert data['headers']['Content-Type'] == 'application/json'
        assert data['url'] == 'https://example.com/api'
        assert data['encoding'] == 'utf-8'
        assert data['reason'] == 'OK'
        assert data['elapsed'] == 0.5

    def test_serialize_response_without_elapsed(self):
        """Test serialization when elapsed is None."""
        resp = requests.Response()
        resp.status_code = 404
        resp._content = b'Not Found'
        resp.headers = {}
        resp.url = 'https://example.com/missing'
        resp.elapsed = None

        data = serialize_response(resp)

        assert data['status_code'] == 404
        assert data['elapsed'] == 0

    def test_serialize_response_with_complex_headers(self):
        """Test serialization with various header types."""
        resp = requests.Response()
        resp.status_code = 201
        resp._content = b'created'
        resp.headers = {
            'Content-Type': 'application/json',
            'X-Custom-Header': 'custom-value',
            'Set-Cookie': 'session=abc123'
        }
        resp.url = 'https://api.example.com/resource'

        data = serialize_response(resp)

        assert 'Content-Type' in data['headers']
        assert 'X-Custom-Header' in data['headers']
        assert 'Set-Cookie' in data['headers']


class TestDeserializeResponse:
    """Test deserialize_response function."""

    def test_deserialize_response_basic(self):
        """Test basic response deserialization."""
        data = {
            'status_code': 200,
            'content': b'test data',
            'headers': {'X-Custom': 'value'},
            'url': 'https://example.com',
            'encoding': 'utf-8',
            'reason': 'OK',
            'elapsed': 1.5
        }

        # Deserialize
        resp = deserialize_response(data)

        # Verify
        assert resp.status_code == 200
        assert resp.content == b'test data'
        assert resp.headers['X-Custom'] == 'value'
        assert resp.url == 'https://example.com'
        assert resp.encoding == 'utf-8'
        assert resp.reason == 'OK'
        assert isinstance(resp.elapsed, timedelta)
        assert resp.elapsed.total_seconds() == 1.5

    def test_deserialize_response_without_elapsed(self):
        """Test deserialization without elapsed field."""
        data = {
            'status_code': 500,
            'content': b'error',
            'headers': {},
            'url': 'https://example.com/error'
        }

        resp = deserialize_response(data)

        assert resp.status_code == 500
        assert resp.elapsed.total_seconds() == 0

    def test_deserialize_response_json_method_works(self):
        """Test that .json() method works on deserialized response."""
        data = {
            'status_code': 200,
            'content': b'{"key": "value"}',
            'headers': {'Content-Type': 'application/json'},
            'url': 'https://example.com/api',
            'encoding': 'utf-8'
        }

        resp = deserialize_response(data)

        # .json() should work
        json_data = resp.json()
        assert json_data == {'key': 'value'}


class TestSerializeDeserializeRoundTrip:
    """Test serialize->deserialize round trip."""

    def test_round_trip_preserves_data(self):
        """Test that serialize->deserialize preserves data."""
        # Original
        original = requests.Response()
        original.status_code = 404
        original._content = b'Not Found'
        original.headers = {'Server': 'nginx', 'Content-Type': 'text/plain'}
        original.url = 'https://example.com/missing'
        original.encoding = 'utf-8'
        original.reason = 'Not Found'
        original.elapsed = timedelta(seconds=0.123)

        # Round trip
        data = serialize_response(original)
        restored = deserialize_response(data)

        # Verify
        assert restored.status_code == original.status_code
        assert restored.content == original.content
        assert dict(restored.headers) == dict(original.headers)
        assert restored.url == original.url
        assert restored.encoding == original.encoding
        assert restored.reason == original.reason
        assert abs(restored.elapsed.total_seconds() - original.elapsed.total_seconds()) < 0.001

    def test_round_trip_with_json_response(self):
        """Test round trip with JSON response."""
        original = requests.Response()
        original.status_code = 200
        original._content = b'{"users": [{"id": 1, "name": "Alice"}]}'
        original.headers = {'Content-Type': 'application/json; charset=utf-8'}
        original.url = 'https://api.example.com/users'
        original.encoding = 'utf-8'

        # Round trip
        data = serialize_response(original)
        restored = deserialize_response(data)

        # Verify JSON parsing works
        assert restored.json() == original.json()

    def test_round_trip_with_binary_content(self):
        """Test round trip with binary content."""
        original = requests.Response()
        original.status_code = 200
        original._content = b'\x00\x01\x02\x03\xff\xfe'
        original.headers = {'Content-Type': 'application/octet-stream'}
        original.url = 'https://example.com/file.bin'

        # Round trip
        data = serialize_response(original)
        restored = deserialize_response(data)

        # Verify binary content preserved
        assert restored.content == original.content
        assert len(restored.content) == len(original.content)
