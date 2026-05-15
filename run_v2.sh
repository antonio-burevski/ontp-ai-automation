#!/bin/bash
# Евалуатор v2 - со тренинг и евалуација фази
#
# Употреба:
#   ./run_v2.sh train                      # Тренинг фаза (калибрација)
#   ./run_v2.sh evaluate                   # Евалуација (самостојна)
#   ./run_v2.sh train --models haiku       # Тренинг само со haiku
#   ./run_v2.sh evaluate --models opus sonnet  # Евалуација со opus и sonnet
#   ./run_v2.sh test --phase train         # Тест на тренинг фаза
#   ./run_v2.sh test --phase evaluate      # Тест на евалуација фаза
#
# Потребни фајлови:
#   projects/training/   -> no_AI.docx, only_AI.docx, hybrid.docx (со оценки)
#   projects/evaluation/  -> no_AI.docx, only_AI.docx, hybrid.docx (без оценки)

cd "$(dirname "$0")"

source venv/bin/activate

COMMAND="${1:-}"

if [ -z "$COMMAND" ]; then
    echo "Употреба: ./run_v2.sh <train|evaluate|test> [опции]"
    echo ""
    echo "  train     - Тренинг фаза (калибрација со професорски оценки)"
    echo "  evaluate  - Евалуација фаза (самостојно оценување)"
    echo "  test      - Тест режим (еден модел)"
    exit 1
fi

# Parse phase for auto-parsing
if [ "$COMMAND" = "train" ] || [ "$COMMAND" = "test" ]; then
    PARSE_PHASE="training"
elif [ "$COMMAND" = "evaluate" ]; then
    PARSE_PHASE="evaluation"
fi

# Auto-parse if needed
PARSED_FILE="parsed_projects_v2/${PARSE_PHASE}/all_projects.json"
if [ ! -f "$PARSED_FILE" ]; then
    echo "Парсирам ${PARSE_PHASE} проекти..."
    python3 project_parser_v2.py "$PARSE_PHASE"
    echo ""
fi

# For evaluate, also ensure training is parsed
if [ "$COMMAND" = "evaluate" ] && [ ! -f "parsed_projects_v2/training/all_projects.json" ]; then
    echo "Парсирам training проекти (потребни за калибрација)..."
    python3 project_parser_v2.py training
    echo ""
fi

echo "Започнувам: $COMMAND..."
python3 evaluator_v2.py "$@"

echo ""
echo "=== СТАТИСТИКА ==="
if [ -f "evaluations_v2.csv" ]; then
    total_rows=$(tail -n +2 evaluations_v2.csv | grep -v "^," | wc -l)
    echo "Вкупно редови во CSV: $total_rows"
    echo "CSV: $(pwd)/evaluations_v2.csv"
fi
if [ -d "training_data" ] && [ -f "training_data/calibration.json" ]; then
    echo "Калибрациски податоци: $(pwd)/training_data/calibration.json"
fi
echo "Резултати: $(pwd)/evaluation_results_v2/"
