"""
Migration checker tool for detecting deprecated HTTP Client API usage.

This tool scans Python files and reports usage of deprecated APIs that will be
removed in v2.0.0. It helps developers migrate from v1.x to v2.0 smoothly.

Usage:
    # Check single file
    python -m http_client.tools.migration_check path/to/file.py

    # Check directory (non-recursive)
    python -m http_client.tools.migration_check path/to/dir/

    # Check directory recursively
    python -m http_client.tools.migration_check path/to/dir/ --recursive

    # Save report to file
    python -m http_client.tools.migration_check src/ --recursive --output report.txt

    # Show detailed help
    python -m http_client.tools.migration_check --help

Exit Codes:
    0 - No deprecated usage found
    1 - Deprecated usage found
    2 - Error (invalid path, parse error, etc.)

Example Output:
    Checking: src/app.py
      Line 15: LoggingPlugin import - Use HTTPClientConfig.logging instead
      Line 42: Parameter 'max_retries' - Use config.retry.max_attempts

    Found 2 issues in 1 file.
    Migration guide: https://github.com/Git-Dalv/http-client-core/blob/main/docs/migration/v1-to-v2.md
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Tuple, Set

# Deprecated imports and their replacements
DEPRECATED_IMPORTS = {
    "LoggingPlugin": "Use HTTPClientConfig.logging instead. "
                     "Example: config = HTTPClientConfig.create(logging=LoggingConfig.create(level='DEBUG'))",
    "RetryPlugin": "Use built-in retry system with HTTPClientConfig.retry instead. "
                   "Example: config = HTTPClientConfig.create(retry=RetryConfig(max_attempts=3))",
}

# Deprecated constructor parameters and their replacements
DEPRECATED_PARAMS = {
    "max_retries": "Use config.retry.max_attempts. "
                   "Example: HTTPClientConfig.create(retry=RetryConfig(max_attempts=3))",
    "pool_connections": "Use config.pool.pool_connections. "
                       "Example: HTTPClientConfig.create(pool=ConnectionPoolConfig(pool_connections=10))",
    "pool_maxsize": "Use config.pool.pool_maxsize. "
                   "Example: HTTPClientConfig.create(pool=ConnectionPoolConfig(pool_maxsize=10))",
    "max_redirects": "Use config.pool.max_redirects. "
                    "Example: HTTPClientConfig.create(pool=ConnectionPoolConfig(max_redirects=5))",
    "verify_ssl": "Use config.security.verify_ssl. "
                 "Example: HTTPClientConfig.create(security=SecurityConfig(verify_ssl=True))",
}

# Migration guide URL
MIGRATION_GUIDE_URL = "https://github.com/Git-Dalv/http-client-core/blob/main/docs/migration/v1-to-v2.md"


class DeprecationChecker(ast.NodeVisitor):
    """AST visitor for finding deprecated HTTP Client API usage."""

    def __init__(self, filename: str):
        """Initialize checker.

        Args:
            filename: Name of file being checked (for reporting)
        """
        self.filename = filename
        self.issues: List[Tuple[int, str, str]] = []  # (line, issue, suggestion)
        self._imported_names: Set[str] = set()  # Track imported names

    def visit_Import(self, node: ast.Import) -> None:
        """Check for deprecated imports in 'import' statements."""
        for alias in node.names:
            # Check if importing from http_client.plugins
            if alias.name.startswith("http_client.plugins"):
                # Extract class name
                parts = alias.name.split(".")
                if len(parts) > 2:
                    class_name = parts[-1]
                    if class_name in DEPRECATED_IMPORTS:
                        self.issues.append((
                            node.lineno,
                            f"Import '{class_name}' from {alias.name}",
                            DEPRECATED_IMPORTS[class_name]
                        ))
                        self._imported_names.add(class_name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for deprecated imports in 'from ... import' statements."""
        if node.module and "http_client.plugins" in node.module:
            for alias in node.names:
                name = alias.name
                if name in DEPRECATED_IMPORTS:
                    self.issues.append((
                        node.lineno,
                        f"Import '{name}' from {node.module}",
                        DEPRECATED_IMPORTS[name]
                    ))
                    self._imported_names.add(name)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for deprecated constructor parameters in function calls."""
        # Check if this is HTTPClient() call
        is_http_client_call = False

        if isinstance(node.func, ast.Name) and node.func.id == "HTTPClient":
            is_http_client_call = True
        elif isinstance(node.func, ast.Attribute):
            # Handle cases like http_client.HTTPClient()
            if node.func.attr == "HTTPClient":
                is_http_client_call = True

        if is_http_client_call:
            # Check keyword arguments
            for keyword in node.keywords:
                if keyword.arg in DEPRECATED_PARAMS:
                    self.issues.append((
                        node.lineno,
                        f"Parameter '{keyword.arg}' in HTTPClient constructor",
                        DEPRECATED_PARAMS[keyword.arg]
                    ))

        # Check for deprecated plugin usage (e.g., client.add_plugin(LoggingPlugin()))
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_plugin" and len(node.args) > 0:
                # Check if first argument is a deprecated plugin
                arg = node.args[0]
                if isinstance(arg, ast.Call):
                    if isinstance(arg.func, ast.Name):
                        plugin_name = arg.func.id
                        if plugin_name in self._imported_names and plugin_name in DEPRECATED_IMPORTS:
                            self.issues.append((
                                node.lineno,
                                f"Usage of deprecated plugin '{plugin_name}'",
                                DEPRECATED_IMPORTS[plugin_name]
                            ))

        self.generic_visit(node)


def check_file(path: Path) -> List[Tuple[int, str, str]]:
    """Check a Python file for deprecated API usage.

    Args:
        path: Path to Python file

    Returns:
        List of (line_number, issue, suggestion) tuples

    Raises:
        SyntaxError: If file has invalid Python syntax
        IOError: If file cannot be read
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(path))
        checker = DeprecationChecker(str(path))
        checker.visit(tree)

        return checker.issues

    except SyntaxError as e:
        raise SyntaxError(f"Syntax error in {path}: {e}")
    except Exception as e:
        raise IOError(f"Error reading {path}: {e}")


def check_path(path: Path, recursive: bool = False) -> dict:
    """Check a file or directory for deprecated API usage.

    Args:
        path: Path to file or directory
        recursive: If True, recursively check subdirectories

    Returns:
        Dictionary mapping file paths to lists of issues
    """
    results = {}

    if path.is_file():
        if path.suffix == ".py":
            try:
                issues = check_file(path)
                if issues:
                    results[path] = issues
            except (SyntaxError, IOError) as e:
                print(f"Warning: {e}", file=sys.stderr)

    elif path.is_dir():
        if recursive:
            pattern = "**/*.py"
        else:
            pattern = "*.py"

        for py_file in path.glob(pattern):
            if py_file.is_file():
                try:
                    issues = check_file(py_file)
                    if issues:
                        results[py_file] = issues
                except (SyntaxError, IOError) as e:
                    print(f"Warning: {e}", file=sys.stderr)

    return results


def format_report(results: dict, output_file: Path = None) -> str:
    """Format check results as a readable report.

    Args:
        results: Dictionary mapping file paths to issues
        output_file: Optional file to write report to

    Returns:
        Formatted report string
    """
    lines = []
    total_issues = 0
    total_files = len(results)

    for file_path, issues in sorted(results.items()):
        lines.append(f"\nChecking: {file_path}")

        for line_no, issue, suggestion in sorted(issues):
            lines.append(f"  Line {line_no}: {issue}")
            lines.append(f"    → {suggestion}")
            total_issues += 1

    lines.append("\n" + "=" * 80)
    lines.append(f"\nFound {total_issues} issue(s) in {total_files} file(s).")
    lines.append(f"\nMigration guide: {MIGRATION_GUIDE_URL}")
    lines.append("\nTo fix these issues:")
    lines.append("  1. Review the migration guide")
    lines.append("  2. Update deprecated imports and parameters")
    lines.append("  3. Run tests to ensure nothing breaks")
    lines.append("  4. Enable strict mode: HTTP_CLIENT_STRICT_DEPRECATION=1")

    report = "\n".join(lines)

    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\nReport saved to: {output_file}")
        except IOError as e:
            print(f"Warning: Could not write to {output_file}: {e}", file=sys.stderr)

    return report


def main():
    """CLI entrypoint for migration checker."""
    parser = argparse.ArgumentParser(
        description="Check for deprecated HTTP Client API usage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Check single file
  python -m http_client.tools.migration_check app.py

  # Check directory recursively
  python -m http_client.tools.migration_check src/ --recursive

  # Save report to file
  python -m http_client.tools.migration_check src/ -r -o report.txt

Migration guide: {MIGRATION_GUIDE_URL}
        """
    )

    parser.add_argument(
        "path",
        type=Path,
        help="Path to Python file or directory to check"
    )

    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively check subdirectories"
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Save report to file"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only show summary, not individual issues"
    )

    args = parser.parse_args()

    # Validate path
    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        return 2

    # Check for deprecated usage
    print(f"Checking {'recursively' if args.recursive else ''}: {args.path}")
    print("=" * 80)

    results = check_path(args.path, recursive=args.recursive)

    if not results:
        print("\n✓ No deprecated API usage found!")
        print(f"\nYour code is ready for v2.0.0 🎉")
        return 0

    # Generate and display report
    report = format_report(results, output_file=args.output)

    if not args.quiet:
        print(report)

    return 1


if __name__ == "__main__":
    sys.exit(main())
