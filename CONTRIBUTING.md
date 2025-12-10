# Contributing to HTTP Client Core

Thank you for your interest in contributing to HTTP Client Core! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Plugin Development](#plugin-development)

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributions from everyone.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment
4. Create a branch for your changes
5. Make your changes
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.9 or higher
- pip
- git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/http-client-core.git
cd http-client-core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev,all]"

# Verify installation
pytest --version
python -c "from http_client import HTTPClient; print('OK')"
```

### IDE Setup

#### VS Code

Recommended extensions:
- Python
- Pylance
- Black Formatter
- Ruff

`.vscode/settings.json`:
```json
{
    "python.linting.enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter"
    }
}
```

#### PyCharm

- Enable Black as external tool
- Enable Ruff plugin
- Set Python interpreter to virtual environment

## Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Test additions/changes

### Commit Messages

Follow conventional commits format:

```
type(scope): short description

Longer description if needed.

Closes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(plugins): add rate limiting plugin
fix(retry): handle Retry-After header correctly
docs(readme): update installation instructions
test(cache): add thread safety tests
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/http_client --cov-report=html

# Run specific test file
pytest tests/unit/test_http_client.py

# Run specific test
pytest tests/unit/test_http_client.py::test_get_request

# Run tests matching pattern
pytest -k "cache"

# Run only unit tests
pytest -m unit

# Run with verbose output
pytest -v

# Skip slow/integration tests
pytest -m "not slow and not integration"
```

### Writing Tests

```python
# tests/unit/plugins/test_my_plugin.py

import pytest
import responses
from http_client import HTTPClient
from http_client.plugins import MyPlugin


class TestMyPlugin:
    """Test MyPlugin functionality."""
    
    def test_initialization(self):
        """Test plugin initializes correctly."""
        plugin = MyPlugin(option="value")
        assert plugin.option == "value"
    
    @responses.activate
    def test_before_request_hook(self):
        """Test before_request modifies request."""
        responses.add(
            responses.GET,
            "https://api.example.com/test",
            json={"status": "ok"},
        )
        
        client = HTTPClient(base_url="https://api.example.com")
        client.add_plugin(MyPlugin())
        
        response = client.get("/test")
        
        assert response.status_code == 200
        # Verify plugin modified request
        assert "X-Custom-Header" in responses.calls[0].request.headers
    
    @pytest.mark.asyncio
    async def test_async_support(self):
        """Test plugin works with async client."""
        # Async test implementation
        pass
```

### Test Organization

```
tests/
├── unit/                    # Unit tests (no network)
│   ├── core/               # Core module tests
│   ├── plugins/            # Plugin tests
│   └── utils/              # Utility tests
├── integration/            # Integration tests (require network)
├── conftest.py            # Shared fixtures
└── fixtures/              # Test data files
```

## Code Style

### Formatting

We use Black for code formatting and Ruff for linting:

```bash
# Format code
black src tests

# Check formatting
black --check src tests

# Lint code
ruff check src tests

# Fix auto-fixable issues
ruff check src tests --fix
```

### Type Hints

Use type hints for all public APIs:

```python
from typing import Optional, Dict, Any, List

def process_response(
    response: requests.Response,
    *,
    extract_json: bool = True,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Process HTTP response.
    
    Args:
        response: The response to process
        extract_json: Whether to extract JSON body
        headers: Additional headers to include
        
    Returns:
        Processed response data
        
    Raises:
        ValueError: If response is invalid
    """
    ...
```

### Documentation

- All public classes/functions need docstrings
- Use Google-style docstrings
- Include examples in docstrings for complex functions

```python
class MyPlugin(Plugin):
    """
    Plugin for custom functionality.
    
    This plugin adds X functionality to HTTP requests.
    
    Attributes:
        option: Description of option
        
    Example:
        >>> plugin = MyPlugin(option="value")
        >>> client.add_plugin(plugin)
        >>> response = client.get("/api")
    """
    
    def __init__(self, option: str = "default"):
        """
        Initialize plugin.
        
        Args:
            option: Configuration option
        """
        self.option = option
```

## Submitting Changes

### Pull Request Process

1. Ensure all tests pass: `pytest`
2. Run code quality checks: `python scripts/check.py`
3. Update documentation if needed
4. Update CHANGELOG.md if appropriate
5. Create pull request with clear description

### PR Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-reviewed code
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
```

## Plugin Development

### Creating a New Plugin

1. Create plugin file in `src/http_client/plugins/`
2. Inherit from `Plugin` base class
3. Implement required hooks
4. Add tests
5. Export from `__init__.py`

### Plugin Template

```python
# src/http_client/plugins/my_plugin.py

"""
My Plugin - Description of what it does.
"""

import logging
from typing import Any, Dict

import requests

from .plugin import Plugin, PluginPriority


logger = logging.getLogger(__name__)


class MyPlugin(Plugin):
    """
    Plugin description.
    
    Priority: NORMAL (50) - or explain different priority.
    
    Example:
        >>> from http_client import HTTPClient
        >>> from http_client.plugins import MyPlugin
        >>> 
        >>> client = HTTPClient(base_url="https://api.example.com")
        >>> client.add_plugin(MyPlugin(option="value"))
        >>> response = client.get("/data")
    """
    
    priority = PluginPriority.NORMAL
    
    def __init__(self, option: str = "default"):
        """
        Initialize plugin.
        
        Args:
            option: Description of option
        """
        self.option = option
    
    def before_request(
        self, 
        method: str, 
        url: str, 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Called before each request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Request parameters
            
        Returns:
            Modified kwargs (or empty dict for no changes)
        """
        logger.debug(f"MyPlugin: before request to {url}")
        
        # Modify request
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"]["X-Custom"] = "value"
        
        return kwargs
    
    def after_response(
        self, 
        response: requests.Response
    ) -> requests.Response:
        """
        Called after each response.
        
        Args:
            response: HTTP response
            
        Returns:
            Response (possibly modified)
        """
        logger.debug(f"MyPlugin: response {response.status_code}")
        return response
    
    def on_error(
        self, 
        error: Exception, 
        **kwargs: Any
    ) -> None:
        """
        Called when request fails.
        
        Args:
            error: Exception that occurred
            **kwargs: Original request parameters
        """
        logger.error(f"MyPlugin: error {error}")
```

### Async Plugin Template

```python
# src/http_client/plugins/async_my_plugin.py

from typing import Any, Dict
import httpx

from .async_plugin import AsyncPlugin
from .plugin import PluginPriority


class AsyncMyPlugin(AsyncPlugin):
    """Async version of MyPlugin."""
    
    priority = PluginPriority.NORMAL
    
    async def before_request(
        self, 
        method: str, 
        url: str, 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Async before request hook."""
        # Can use async operations here
        return kwargs
    
    async def after_response(
        self, 
        response: httpx.Response
    ) -> httpx.Response:
        """Async after response hook."""
        return response
    
    async def on_error(
        self, 
        error: Exception, 
        **kwargs: Any
    ) -> None:
        """Async error hook."""
        pass
```

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Check existing issues/discussions first

Thank you for contributing!
