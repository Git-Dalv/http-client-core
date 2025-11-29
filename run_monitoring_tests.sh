#!/bin/bash

# Скрипт для запуска тестов MonitoringPlugin

echo "================================================"
echo "Запуск тестов для MonitoringPlugin"
echo "================================================"
echo ""

# Устанавливаем переменные окружения
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверяем наличие pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}pytest не установлен. Установите его с помощью: pip install pytest${NC}"
    exit 1
fi

# Запускаем тесты с подробным выводом
echo -e "${YELLOW}Запуск тестов...${NC}"
echo ""

# Запускаем только тесты monitoring_plugin с подробным выводом
# Используем -o для переопределения настроек из pyproject.toml
pytest tests/unit/test_monitoring_plugin.py -v --tb=short --color=yes -o addopts=""

# Сохраняем код возврата
TEST_EXIT_CODE=$?

echo ""
echo "================================================"

# Выводим результат
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Все тесты пройдены успешно!${NC}"
else
    echo -e "${RED}Некоторые тесты провалились. Код возврата: $TEST_EXIT_CODE${NC}"
fi

echo "================================================"

exit $TEST_EXIT_CODE
