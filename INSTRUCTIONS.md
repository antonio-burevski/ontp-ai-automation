# Инструкции за користење (v2)

## Подготовка

### Потребни фајлови

Ставете ги DOCX фајловите во соодветните папки:

```
projects/
├── training/          # Проекти СО професорски оценки (за калибрација)
│   ├── no_AI.docx
│   ├── only_AI.docx
│   └── hybrid.docx
└── evaluation/        # Проекти БЕЗ оценки (за самостојна евалуација)
    ├── no_AI.docx
    ├── only_AI.docx
    └── hybrid.docx
```

### Системски барања
- Python 3.10+
- Claude Code CLI инсталиран и автентициран
- `python-docx` пакет (`pip install python-docx`)

---

## Фаза 1: Тренинг (калибрација)

Моделите ги учат оценувачките стандарди на професорот.

```bash
# Тренинг со сите 3 модели
./run_v2.sh train

# Тренинг само со еден модел
./run_v2.sh train --models haiku

# Тест режим (еден модел, брзо)
./run_v2.sh test --phase train
```

Резултатот се зачувува во `training_data/calibration.json`.

---

## Фаза 2: Евалуација

Моделите самостојно оценуваат нови проекти, калибрирани според тренингот.

```bash
# Евалуација со сите 3 модели
./run_v2.sh evaluate

# Евалуација само со opus и sonnet
./run_v2.sh evaluate --models opus sonnet

# Евалуација на специфични проекти
./run_v2.sh evaluate --projects evaluation_noAI_01 evaluation_hybrid_03

# Тест режим
./run_v2.sh test --phase evaluate
```

---

## Модели

| Име | Model ID | Опис |
|-----|----------|------|
| opus | claude-opus-4-6 | Најквалитетен, најбавен |
| sonnet | claude-sonnet-4-6 | Баланс квалитет/брзина |
| haiku | claude-haiku-4-5 | Најбрз, добар за тестирање |

---

## Излезни фајлови

| Фајл/Папка | Опис |
|-------------|------|
| `training_data/calibration.json` | Калибрациски примери по тип |
| `training_data/training_results.json` | Детални тренинг резултати |
| `evaluations_v2.csv` | Финален CSV (професор + AI оценки) |
| `evaluation_results_v2/` | Поединечни JSON резултати |

### CSV формат

| Колона | Опис |
|--------|------|
| project_id | Уникатен ID |
| project_name | Тема |
| project_type | noAI / onlyAI / hybrid |
| evaluator | ПРОФЕСОР или AI-OPUS/SONNET/HAIKU |
| metap | Фактор извори (0.0-1.0) |
| tocnost | Фактор точност (0.0-1.0) |
| izmama | Плагијаризам коментар |
| kviz | Поени (0-100) |
| vkupno | metap x tocnost x kviz |
| komentar | Текстуален коментар |

---

## Критериуми за оценување

### Квиз компоненти (100 поени)

| Компонента | Поени |
|------------|-------|
| Три групи прашања | 30 (3x10) |
| Вовед | 10 |
| Разработка | 35 |
| Заклучок + критички став | 25 |

### Метаподатоци фактор (metap)
- 9+ извори → 1.0
- < 9 извори → казна 0.05 за секој што недостасува

### Финална формула
```
Вкупно = metap x tocnost x kviz
```

---

## Проблеми и решенија

| Проблем | Решение |
|---------|---------|
| `claude: command not found` | Инсталирајте Claude Code CLI |
| `Permission denied` | `chmod +x run_v2.sh` |
| Timeout грешки | Зголемете `timeout` во `evaluator_v2.py` |
| Нема калибрациски податоци | Прво извршете `./run_v2.sh train` |
