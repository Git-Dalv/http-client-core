#!/bin/bash
# Wrapper для запуска check.py на Linux/Mac

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

python scripts/check.py "$@"
