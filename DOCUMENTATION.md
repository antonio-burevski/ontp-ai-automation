# Техничка документација: Систем за автоматизирана евалуација

## Преглед на системот

Овој систем автоматски евалуира студентски проекти користејќи Claude AI модели (Opus, Sonnet, Haiku) и ги споредува резултатите со оценките од професорот.

### Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   DOCX фајлови  │────▶│  project_parser │────▶│   JSON проекти  │
│   (projects/)   │     │      .py        │     │(parsed_projects)│
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  evaluations    │◀────│   evaluator.py  │◀────│   Claude CLI    │
│     .csv        │     │                 │     │ (opus/sonnet/   │
└─────────────────┘     └─────────────────┘     │    haiku)       │
                                                └─────────────────┘
```

---

## Компоненти

### 1. project_parser.py

**Цел:** Екстракција на студентски проекти од DOCX фајлови.

**Влез:**
- `/projects/*.docx` - Оригинални документи

**Излез:**
- `/parsed_projects/all_projects.json` - Сите проекти
- `/parsed_projects/{project_id}.json` - Поединечни проекти

**Клучни функции:**

```python
parse_docx(filepath, project_type) -> List[StudentProject]
```
- Чита DOCX фајл
- Идентификува проекти по "Тема X:" паттерн
- Екстрахира содржина, табели со оценки, коментари

```python
extract_table_data(table) -> dict
```
- Парсира табела со оценки од професор
- Враќа: izmama, kviz, tocnost, metap, vkupno

```python
count_sources(text) -> int
```
- Брои референци/извори во текст
- Детектира URL-ови, нумерирани референци [1], bullet points

**Податочни структури:**

```python
@dataclass
class StudentProject:
    project_id: str      # Уникатен ID (пр. "noAI_01a")
    project_name: str    # "Тема 1: Наслов..."
    project_type: str    # noAI, onlyAI, hybrid
    source_file: str     # Име на DOCX фајл
    content: str         # Целосна содржина
    word_count: int      # Број на зборови
    source_count: int    # Број на пронајдени извори
    professor_eval: ProfessorEvaluation  # Оценка од професор

@dataclass
class ProfessorEvaluation:
    izmama: str          # Текст за измама/плагијат
    kviz: float          # Поени (0-100)
    tocnost: float       # Фактор (0-1)
    metap: float         # Фактор (0-1)
    vkupno: float        # Финална оценка
    komentar: str        # Коментар
```

---

### 2. evaluator.py

**Цел:** Евалуација на проекти со Claude AI модели.

**Влез:**
- `/parsed_projects/all_projects.json`
- Командни аргументи (--projects, --models, --test)

**Излез:**
- `/evaluations.csv` - Споредбена табела
- `/evaluation_results/*.json` - Детални резултати

**Клучни функции:**

```python
call_claude(prompt, model, timeout=120) -> str
```
- Повикува Claude CLI: `claude --print --model {model} --dangerously-skip-permissions`
- Враќа JSON одговор од моделот

```python
evaluate_project(project, model) -> AIEvaluation
```
- Генерира промпт со критериуми
- Повикува Claude за евалуација
- Парсира JSON одговор

```python
generate_csv(results, models)
```
- Креира CSV со споредба професор vs AI
- Групира по проект (прво професор, потоа AI модели)

**Промпт структура:**

Промптот вклучува:
1. Критериуми за оценување (квиз компоненти, метаподатоци, измама)
2. Податоци за проектот (име, тип, број зборови, број извори)
3. Содржина на проектот (ограничена на 15000 карактери)
4. Барање за JSON излез со специфични полиња

**CLI параметри:**

| Параметар | Опис | Default |
|-----------|------|---------|
| --projects | Листа на project_id | сите |
| --models | opus, sonnet, haiku | сите три |
| --test | Тест режим (1 проект, haiku) | false |

---

### 3. run_evaluation.sh

**Цел:** Shell wrapper за полесно извршување.

**Функционалност:**
1. Активира Python venv
2. Проверува дали има парсирани проекти (ако не, ги парсира)
3. Ја повикува evaluator.py со дадените аргументи
4. Прикажува статистика

---

## Процес на евалуација

### Чекор 1: Парсирање (project_parser.py)

```
DOCX → Детекција на "Тема X:" → Екстракција на содржина
     → Екстракција на табела  → Парсирање на оценка
     → Броење на извори       → JSON излез
```

### Чекор 2: Евалуација (evaluator.py)

```
За секој проект:
    За секој модел (opus, sonnet, haiku):
        1. Генерирај промпт со критериуми
        2. Повикај Claude CLI
        3. Парсирај JSON одговор
        4. Зачувај резултат
```

### Чекор 3: Генерирање на извештај

```
Собери сите резултати → Групирај по проект
→ Додај оценка од професор прва → Додај AI евалуации
→ Запиши CSV
```

---

## Критериуми за оценување (детално)

### За noAI проекти (без AI)
Три групи прашања (30 поени) проверуваат:
- Што студентот прво пребарувал на интернет
- Кои извори ги нашол
- Кои клучни информации ги искористил

### За onlyAI проекти (само AI)
Три групи прашања (30 поени) проверуваат:
- Кои прашања ги поставил до ГЈМ
- Каков одговор добил
- Кои извори ја потврдуваат релевантноста

### За hybrid проекти
Комбинација на двата пристапа.

### Метаподатоци фактор

```python
def calculate_metap(source_count):
    if source_count >= 9:
        return 1.0
    else:
        penalty = (9 - source_count) * 0.05
        return max(0.0, 1.0 - penalty)
```

---

## Зависности

### Python пакети (venv/)
- `python-docx` - Читање на DOCX фајлови
- `pandas` - Манипулација на податоци
- `anthropic` - (опционално, за идна API интеграција)

### Системски барања
- Python 3.10+
- Claude Code CLI инсталиран и автентициран
- Claude Pro претплата (за пристап до сите 3 модели)

---

## Проширување на системот

### Додавање нови критериуми
Модифицирај го `EVALUATION_PROMPT` во evaluator.py и додај нови полиња во JSON шемата.

### API интеграција
За директна API интеграција наместо CLI:

```python
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)
```

### Паралелна евалуација
За побрзо извршување, може да се додаде multiprocessing:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(evaluate_project, p, m)
               for p in projects for m in models]
```

---

## Структура на фајлови

```
/home/artorias/Desktop/OnTP/
├── projects/                      # Влезни DOCX фајлови
│   ├── noAI.docx
│   ├── noAI-2.docx
│   ├── onlyAI.docx
│   └── hybrid.docx
├── parsed_projects/               # Парсирани JSON проекти
│   ├── all_projects.json
│   ├── noAI_01a.json
│   ├── noAI_02a.json
│   └── ...
├── evaluation_results/            # Резултати од евалуација
│   ├── noAI_01a_haiku.json
│   ├── noAI_01a_sonnet.json
│   ├── noAI_01a_opus.json
│   ├── noAI_01a_all.json
│   └── ...
├── evaluations.csv                # Финален CSV извештај
├── project_parser.py              # Parser скрипта
├── evaluator.py                   # Evaluator скрипта
├── run_evaluation.sh              # Shell wrapper
├── project_description.pdf        # Опис на задачата
├── venv/                          # Python виртуелна околина
├── INSTRUCTIONS.md                # Упатство за користење
└── DOCUMENTATION.md               # Техничка документација
```

---

## Верзија и автор

- **Верзија:** 1.0
- **Датум:** Јануари 2026
- **Автор:** Антонио Буревски 
