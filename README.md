# HTTP Client Core

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


#Advanced Usage
##With Plugins

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

#Development
##Setup

`Clone repository
git clone https://github.com/Git-Dalv/http-client-core.git
cd http-client-core

`Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

`Install dependencies
pip install -e ".[dev]"

##Running Tests

` Run all tests
pytest

` With coverage
pytest --cov=src/http_client --cov-report=html

` Run specific test
pytest tests/unit/core/test_client.py

##Code Quality
`Format code
black src tests

`Lint
ruff check src tests

`Type checking
mypy src


#Project Structure
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


#Roadmap
Core HTTP client implementation
 Plugin system
 Retry mechanism
 Rate limiting
 Caching support
 Async support (httpx backend)
 WebSocket support

#License

##MIT License - see LICENSE file for details.