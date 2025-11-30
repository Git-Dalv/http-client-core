# HTTP Client Core

![CI](https://github.com/Git-Dalv/http-client-core/workflows/CI/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Extensible HTTP client library built on top of `requests` with plugin architecture and advanced features.

## Features

-  **Plugin Architecture** - Extend functionality with custom plugins
-  **Automatic Retries** - Configurable retry logic with exponential backoff
-  **Rate Limiting** - Built-in rate limiting support
-  **Metrics & Logging** - Comprehensive request/response tracking
-  **Authentication** - Multiple auth methods support
-  **Type Hints** - Full type annotation support
-  **Well Tested** - High test coverage

## Installation

```bash
pip install http-client-core

###For development:
pip install -e ".[dev]"

###Quick Start:
from http_client import HTTPClient

# Create client
client = HTTPClient(base_url="https://api.example.com")

# Make requests
response = client.get("/users")
print(response.json())

# POST with data
response = client.post("/users", json={"name": "John"})

```

# Advanced Usage
 With Plugins


```bash
from http_client import HTTPClient
from http_client.plugins import RetryPlugin, LoggingPlugin

client = HTTPClient(
    base_url="https://api.example.com",
    plugins=[
        RetryPlugin(max_retries=3),
        LoggingPlugin(level="DEBUG")
    ]
)

##Custom Authentication

client = HTTPClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

```

# Development
Setup

```bash
#Clone repository
git clone https://github.com/Git-Dalv/http-client-core.git
cd http-client-core

#Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

#Install dependencies
pip install -e ".[dev]"
```

## Running Tests
```bash
#Run all tests
pytest

#With coverage
pytest --cov=src/http_client --cov-report=html

#Run specific test
pytest tests/unit/core/test_client.py

## Code Quality
#Format code
black src tests

#Lint
ruff check src tests

#Type checking
mypy src
```

# Project Structure
```bash
http-client-core/
├── src/
│   └── http_client/
│       ├── core/           ` Core functionality
│       ├── plugins/        ` Plugin implementations
│       └── utils/          ` Utility functions
├── tests/
│   ├── unit/              ` Unit tests
│   └── integration/       ` Integration tests
├── docs/                  ` Documentation
└── examples/              ` Usage examples
```

# Roadmap
```bash
Core HTTP client implementation
 * Plugin system
 * Retry mechanism
 * Rate limiting
 * Caching support
 * Async support (httpx backend)
 * WebSocket support
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/Git-Dalv/http-client-core
cd http-client-core

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Quick check (fast, skips mypy)
python scripts/check.py --fast

# Full check (includes all linters and type checking)
python scripts/check.py

# With auto-fix for formatting and linting issues
python scripts/check.py --fix

# Or run manually
pytest -v --cov=src/http_client

# Run specific test file
pytest tests/unit/test_monitoring_plugin.py -v

# Run integration tests only
pytest tests/integration/ -v -m integration

# Run unit tests only
pytest tests/unit/ -v -m unit
```

### Code Quality Tools

The project uses several tools to maintain code quality:

- **black** - Code formatting
- **ruff** - Fast Python linter
- **mypy** - Static type checking
- **pytest** - Testing framework
- **pytest-cov** - Coverage reporting

### Pre-commit Checks

Before committing, run:

```bash
python scripts/check.py --fix
```

This will:
1. Format code with black
2. Fix linting issues with ruff
3. Run all tests with coverage
4. Generate coverage report

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linters (`python scripts/check.py`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see LICENSE file for details.
