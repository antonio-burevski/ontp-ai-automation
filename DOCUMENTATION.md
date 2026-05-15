# Техничка документација: Систем за евалуација v2

## Преглед

Систем за автоматска евалуација на студентски проекти со Claude AI модели. Работи во две фази: тренинг (калибрација со професорски оценки) и евалуација (самостојно оценување).

### Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    ТРЕНИНГ ФАЗА                         │
│                                                         │
│  projects/training/     project_parser_v2.py            │
│  ├── no_AI.docx    ──────▶  parsed_projects_v2/training/│
│  ├── only_AI.docx                  │                    │
│  └── hybrid.docx                   ▼                    │
│                         evaluator_v2.py train           │
│                                │                        │
│                                ▼                        │
│                         training_data/                  │
│                         └── calibration.json            │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                   ЕВАЛУАЦИЈА ФАЗА                       │
│                                                         │
│  projects/evaluation/   project_parser_v2.py            │
│  ├── no_AI.docx    ──────▶  parsed_projects_v2/eval/   │
│  ├── only_AI.docx                  │                    │
│  └── hybrid.docx                   ▼                    │
│                         evaluator_v2.py evaluate        │
│                         (+ calibration.json)            │
│                                │                        │
│                                ▼                        │
│                    evaluations_v2.csv                   │
│                    evaluation_results_v2/               │
└─────────────────────────────────────────────────────────┘
```

---

## Компоненти

### 1. project_parser_v2.py

Екстракција на студентски проекти од DOCX фајлови.

**Употреба:**
```bash
python3 project_parser_v2.py training    # Парсирај тренинг проекти
python3 project_parser_v2.py evaluation  # Парсирај евалуациони проекти
python3 project_parser_v2.py both        # Парсирај и двете
```

**Очекувани фајлови:** `no_AI.docx`, `only_AI.docx`, `hybrid.docx` во секоја фаза.

**Клучни функции:**

| Функција | Опис |
|----------|------|
| `parse_docx(filepath, project_type)` | Парсира DOCX, идентификува "Тема X:" проекти |
| `extract_table_data(table)` | Извлекува оценки од табела (izmama, kviz, tocnost, metap, vkupno) |
| `count_sources(text)` | Брои URL-ови, нумерирани референци, bullet points |
| `parse_phase(phase)` | Парсира сите DOCX за дадена фаза |

**Project ID формат:** `{phase}_{type}_{number}` (пр. `training_noAI_01`, `evaluation_hybrid_03`)

---

### 2. evaluator_v2.py

Двофазна евалуација со Claude AI модели.

**Употреба:**
```bash
python3 evaluator_v2.py train                        # Тренинг (сите модели)
python3 evaluator_v2.py train --models haiku          # Тренинг (само haiku)
python3 evaluator_v2.py evaluate                      # Евалуација (сите модели)
python3 evaluator_v2.py evaluate --models opus sonnet # Евалуација (opus + sonnet)
python3 evaluator_v2.py evaluate --projects eval_noAI_01  # Специфичен проект
python3 evaluator_v2.py test --phase train            # Тест режим
```

**Модели:**

| Кратко име | Model ID |
|------------|----------|
| opus | claude-opus-4-6 |
| sonnet | claude-sonnet-4-6 |
| haiku | claude-haiku-4-5 |

**Тренинг фаза (`train`):**
1. Вчитува тренинг проекти (со професорски оценки)
2. За секој проект, секој модел: испраќа промпт со содржина + професорска оценка
3. Моделот ја анализира логиката зад професорската оценка
4. Зачувува калибрациски примери во `training_data/calibration.json`

**Евалуација фаза (`evaluate`):**
1. Вчитува калибрациски примери од тренингот (по тип проект)
2. За секој нов проект: испраќа промпт со содржина + калибрациски примери од истиот тип
3. Моделот оценува со истото ниво на строгост како професорот
4. Зачувува резултати во `evaluation_results_v2/` и `evaluations_v2.csv`

**Калибрациски примери:**
- Групирани по тип: noAI, onlyAI, hybrid
- Секој пример содржи: име, зборови, извори, професорска оценка, преглед на содржина
- При евалуација, моделот добива примери само од истиот тип проект

---

### 3. run_v2.sh

Shell wrapper за полесно извршување.

1. Активира Python venv
2. Автоматски парсира DOCX ако нема парсирани проекти
3. Извршува соодветна фаза
4. Прикажува статистика

---

## Критериуми за оценување

### За noAI проекти
Три групи прашања (30п): пребарување, извори, клучни информации

### За onlyAI проекти
Три групи прашања (30п): прашања до ГЈМ, одговори, потврда на релевантност

### За hybrid проекти
Комбинација на двата пристапа

### Останати компоненти
- Вовед (10п): јасно објаснување, добар вовед
- Разработка (35п): анализа, аргументи, извори, логика
- Заклучок (25п): јасен заклучок, критички став

### Метаподатоци фактор (metap)
9+ извори = 1.0, казна 0.05 за секој што недостасува

### Финална формула
`vkupno = metap x tocnost x kviz_total`

---

## Зависности

- Python 3.10+
- `python-docx` - DOCX парсирање
- Claude Code CLI - автентициран
- `pandas`, `matplotlib`, `seaborn`, `scipy` - за анализа (опционално)

---

## Структура на фајлови

```
ontp-ai-automation/
├── projects/
│   ├── training/              # DOCX со професорски оценки
│   │   ├── no_AI.docx
│   │   ├── only_AI.docx
│   │   └── hybrid.docx
│   └── evaluation/            # DOCX без оценки
│       ├── no_AI.docx
│       ├── only_AI.docx
│       └── hybrid.docx
├── parsed_projects_v2/        # Парсирани JSON
│   ├── training/
│   └── evaluation/
├── training_data/             # Калибрациски податоци
│   ├── calibration.json
│   └── training_results.json
├── evaluation_results_v2/     # Резултати од евалуација
├── analysis/                  # Визуализации и анализа
│   ├── ui/
│   └── comparative_analysis.ipynb
├── project_parser_v2.py       # Parser
├── evaluator_v2.py            # Evaluator (train + evaluate)
├── run_v2.sh                  # Shell wrapper
├── INSTRUCTIONS.md            # Упатство
└── DOCUMENTATION.md           # Техничка документација
```

---

## Верзија

- **Верзија:** 2.0
- **Модели:** Claude Opus 4.6, Sonnet 4.6, Haiku 4.5
