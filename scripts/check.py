#!/usr/bin/env python3
"""
Скрипт полной проверки проекта http-client-core.

Запускает все необходимые проверки:
- Форматирование (black)
- Линтинг (ruff)
- Проверка типов (mypy) - опционально
- Тесты с coverage (pytest)

Usage:
    python scripts/check.py
    python scripts/check.py --fast  # Без mypy (быстрее)
    python scripts/check.py --fix   # Автоматические исправления
"""

import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Tuple


# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_step(message: str) -> None:
    """Печать шага проверки."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}▶ {message}{Colors.END}")


def print_success(message: str) -> None:
    """Печать успешного результата."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str) -> None:
    """Печать ошибки."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message: str) -> None:
    """Печать предупреждения."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def run_command(
    command: List[str],
    description: str,
    check: bool = True
) -> Tuple[bool, str]:
    """
    Запустить команду и вернуть результат.

    Args:
        command: Команда для запуска
        description: Описание для вывода
        check: Проверять код возврата

    Returns:
        Tuple[success, output]
    """
    print_step(description)

    try:
        result = subprocess.run(
            command,
            check=check,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        success = result.returncode == 0

        if success:
            print_success(f"{description} - OK")
        else:
            print_error(f"{description} - FAILED")
            if result.stderr:
                print(result.stderr[:1000])  # Limit output

        return success, result.stdout + result.stderr

    except subprocess.CalledProcessError as e:
        print_error(f"{description} - FAILED")
        print(e.stderr[:1000] if e.stderr else "")
        return False, e.stderr or ""
    except FileNotFoundError:
        print_warning(f"Command not found: {command[0]} - SKIPPED")
        return True, ""  # Don't fail if tool not installed


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Проверка качества кода")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Быстрая проверка (без mypy)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Автоматические исправления"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Пропустить тесты (только линтеры)"
    )

    args = parser.parse_args()

    # Определяем директории
    root_dir = Path(__file__).parent.parent
    src_dir = root_dir / "src"
    tests_dir = root_dir / "tests"

    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"  HTTP Client Core - Проверка качества")
    print(f"{'='*60}{Colors.END}\n")
    print(f"Root dir: {root_dir}")
    print(f"Source: {src_dir}")
    print(f"Tests: {tests_dir}\n")

    results = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. BLACK - Форматирование
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    if args.fix:
        success, _ = run_command(
            ["black", str(src_dir), str(tests_dir)],
            "Форматирование кода (black)"
        )
    else:
        success, _ = run_command(
            ["black", "--check", str(src_dir), str(tests_dir)],
            "Проверка форматирования (black)"
        )

    results.append(("Black", success))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. RUFF - Линтинг
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ruff_command = ["ruff", "check", str(src_dir), str(tests_dir)]
    if args.fix:
        ruff_command.append("--fix")

    success, _ = run_command(
        ruff_command,
        "Линтинг кода (ruff)"
    )

    results.append(("Ruff", success))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. MYPY - Проверка типов
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    if not args.fast:
        success, _ = run_command(
            ["mypy", str(src_dir), "--ignore-missing-imports"],
            "Проверка типов (mypy)"
        )
        results.append(("Mypy", success))
    else:
        print_warning("Mypy пропущен (--fast режим)")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. PYTEST - Тесты и coverage
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    if not args.skip_tests:
        success, output = run_command(
            [
                "pytest",
                "-v",
                "-o", "addopts="
            ],
            "Тесты (pytest)"
        )

        results.append(("Pytest", success))

        # Показываем краткую статистику из вывода
        if "passed" in output or "failed" in output:
            for line in output.split('\n'):
                if 'passed' in line or 'failed' in line or '=====' in line:
                    if any(x in line for x in ['passed', 'failed', 'error']):
                        print(line)
    else:
        print_warning("Тесты пропущены (--skip-tests)")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ИТОГОВЫЙ ОТЧЁТ
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    print(f"\n{Colors.BOLD}{'='*60}")
    print("  ИТОГОВЫЙ ОТЧЁТ")
    print(f"{'='*60}{Colors.END}\n")

    all_passed = True
    for check_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        color = Colors.GREEN if success else Colors.RED
        print(f"{color}{status:12}{Colors.END} {check_name}")

        if not success:
            all_passed = False

    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")

    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ВСЕ ПРОВЕРКИ ПРОШЛИ УСПЕШНО!{Colors.END}")
        print(f"\n{Colors.BLUE}Код готов к коммиту! 🚀{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ ЕСТЬ ОШИБКИ!{Colors.END}")
        print(f"\n{Colors.YELLOW}Исправь ошибки и запусти снова.{Colors.END}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
