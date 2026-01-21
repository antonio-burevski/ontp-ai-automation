#!/bin/bash
# Скрипта за автоматизирана евалуација на студентски проекти
# Користење:
#   ./run_evaluation.sh           # Евалуација на сите проекти со сите модели
#   ./run_evaluation.sh --test    # Тест режим (еден проект, еден модел)
#   ./run_evaluation.sh --models haiku sonnet  # Специфични модели
#   ./run_evaluation.sh --projects noAI_01a noAI_02a  # Специфични проекти

cd "$(dirname "$0")"

# Активирај виртуелна околина
source venv/bin/activate

# Провери дали има парсирани проекти
if [ ! -f "parsed_projects/all_projects.json" ]; then
    echo "Парсирам проекти од docx фајлови..."
    python3 project_parser.py
    echo ""
fi

# Изврши евалуација
echo "Започнувам евалуација..."
python3 evaluator.py "$@"

# Прикажи статистика
echo ""
echo "=== СТАТИСТИКА ==="
if [ -f "evaluations.csv" ]; then
    total_rows=$(tail -n +2 evaluations.csv | grep -v "^," | wc -l)
    echo "Вкупно редови во CSV: $total_rows"
    echo ""
    echo "CSV фајл: $(pwd)/evaluations.csv"
    echo "Резултати: $(pwd)/evaluation_results/"
fi
