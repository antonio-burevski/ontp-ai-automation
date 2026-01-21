#!/usr/bin/env python3
"""
Автоматизиран евалуатор за студентски проекти користејќи Claude CLI.
Евалуира со сите 3 модели: opus, sonnet, haiku
"""

import os
import json
import subprocess
import csv
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field


MODELS = ['opus', 'sonnet', 'haiku']

BASE_DIR = '/home/artorias/Desktop/OnTP'
PARSED_DIR = os.path.join(BASE_DIR, 'parsed_projects')
RESULTS_DIR = os.path.join(BASE_DIR, 'evaluation_results')
OUTPUT_CSV = os.path.join(BASE_DIR, 'evaluations.csv')

EVALUATION_PROMPT = """
Ти си професор кој евалуира студентски проект. Оцени го следниов проект според дадените критериуми.

## КРИТЕРИУМИ ЗА ОЦЕНУВАЊЕ:

### 1. Квиз компоненти (вкупно 100 поени):

**А) Три групи прашања за истражување (30 поени)**
За проекти БЕЗ AI (noAI): Оцени дали студентот јасно објаснил:
- Што прво пребарувал на интернет
- Кои извори ги нашол
- Кои клучни информации ги искористил
(10 поени за секоја од трите групи)

За проекти СО AI (onlyAI): Оцени дали студентот јасно објаснил:
- Кои прашања ги поставил до ГЈМ (Голем Јазичен Модел)
- Каков одговор добил од ГЈМ
- Кои извори ја потврдуваат релевантноста на генерираниот одговор
(10 поени за секоја од трите групи)

За хибридни проекти (hybrid): Комбинација на двата пристапа

**Б) Вовед (10 поени)**
- Дали јасно објаснува што се истражува
- Дали е добро напишан и воведува во темата

**В) Разработка (35 поени)**
- Длабочина на анализата
- Квалитет на аргументите
- Користење на извори
- Логичен тек

**Г) Заклучок и критички став (25 поени)**
- Дали има јасен заклучок
- Дали студентот покажува критички став
- Дали заклучокот произлегува од разработката

### 2. Метаподатоци фактор (metap):
- Провери дали има барем 10 независни извори
- Ако има 9 извори: фактор = 1.0
- За помалку од 9: казна 0.05 за секој што недостасува
- Пример: 4 извори = фактор 0.7 (казна 0.3 за 6 извори што недостасуваат)
- Провери и дали има соодветен број зборови (минимум ~800 зборови)

### 3. Измама:
- Провери дали има знаци на плагијаризам
- Провери дали изворите се наведени во текстот
- Провери дали има недозволено користење на AI (за noAI проекти)

## ПРОЕКТ ЗА ЕВАЛУАЦИЈА:

**Име на проект:** {project_name}
**Тип на проект:** {project_type}
**Број на зборови:** {word_count}
**Пронајдени извори:** {source_count}

**СОДРЖИНА:**
{content}

## ТВОЈА ОЦЕНКА:

Одговори САМО во следниов JSON формат (без дополнителен текст пред или после):

{{
  "tri_grupi_prasanja": <број од 0-30>,
  "voved": <број од 0-10>,
  "razrabotka": <број од 0-35>,
  "zakljucok_kriticki": <број од 0-25>,
  "kviz_total": <збир на претходните, 0-100>,
  "metap": <фактор од 0.0-1.0>,
  "tocnost": 1.0,
  "izmama": "<текст: 'нема' или опис на проблем>",
  "vkupno": <metap * tocnost * kviz_total>,
  "komentar": "<краток коментар за проектот>"
}}
"""


@dataclass
class AIEvaluation:
    """Евалуација од AI модел"""
    model: str
    tri_grupi_prasanja: float = 0.0
    voved: float = 0.0
    razrabotka: float = 0.0
    zakljucok_kriticki: float = 0.0
    kviz_total: float = 0.0
    metap: float = 1.0
    tocnost: float = 1.0
    izmama: str = "нема"
    vkupno: float = 0.0
    komentar: str = ""
    raw_response: str = ""
    error: str = ""


def call_claude(prompt: str, model: str, timeout: int = 120) -> str:
    """Повикај Claude CLI со дадениот промпт и модел"""
    try:
        result = subprocess.run(
            ['claude', '--print', '--model', model, '--dangerously-skip-permissions', prompt],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"ERROR: Timeout after {timeout} seconds"
    except Exception as e:
        return f"ERROR: {str(e)}"


def parse_evaluation_response(response: str) -> Dict:
    """Парсирај JSON одговор од Claude"""
    # Пробај да најдеш JSON во одговорот
    json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Пробај директно парсирање
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    return {}


def evaluate_project(project: Dict, model: str) -> AIEvaluation:
    """Евалуирај еден проект со еден модел"""
    prompt = EVALUATION_PROMPT.format(
        project_name=project['project_name'],
        project_type=project['project_type'],
        word_count=project['word_count'],
        source_count=project['source_count'],
        content=project['content'][:15000]  # Ограничи должина
    )

    print(f"    Евалуирам со {model}...", end=" ", flush=True)
    start_time = time.time()

    response = call_claude(prompt, model)
    elapsed = time.time() - start_time

    evaluation = AIEvaluation(model=model, raw_response=response)

    if response.startswith("ERROR:"):
        evaluation.error = response
        print(f"ГРЕШКА ({elapsed:.1f}s)")
    else:
        parsed = parse_evaluation_response(response)
        if parsed:
            evaluation.tri_grupi_prasanja = float(parsed.get('tri_grupi_prasanja', 0))
            evaluation.voved = float(parsed.get('voved', 0))
            evaluation.razrabotka = float(parsed.get('razrabotka', 0))
            evaluation.zakljucok_kriticki = float(parsed.get('zakljucok_kriticki', 0))
            evaluation.kviz_total = float(parsed.get('kviz_total', 0))
            evaluation.metap = float(parsed.get('metap', 1.0))
            evaluation.tocnost = float(parsed.get('tocnost', 1.0))
            evaluation.izmama = str(parsed.get('izmama', 'нема'))
            evaluation.vkupno = float(parsed.get('vkupno', 0))
            evaluation.komentar = str(parsed.get('komentar', ''))
            print(f"OK - Вкупно: {evaluation.vkupno:.1f} ({elapsed:.1f}s)")
        else:
            evaluation.error = "Failed to parse JSON response"
            print(f"PARSE ERROR ({elapsed:.1f}s)")

    return evaluation


def run_evaluation(project_ids: Optional[List[str]] = None, models: Optional[List[str]] = None):
    """Изврши евалуација на проекти"""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    if models is None:
        models = MODELS

    # Вчитај ги проектите
    with open(os.path.join(PARSED_DIR, 'all_projects.json'), 'r', encoding='utf-8') as f:
        all_projects = json.load(f)

    if project_ids:
        projects = [p for p in all_projects if p['project_id'] in project_ids]
    else:
        projects = all_projects

    print(f"\n{'='*60}")
    print(f"ЕВАЛУАЦИЈА НА СТУДЕНТСКИ ПРОЕКТИ")
    print(f"{'='*60}")
    print(f"Проекти: {len(projects)}")
    print(f"Модели: {', '.join(models)}")
    print(f"Вкупно евалуации: {len(projects) * len(models)}")
    print(f"{'='*60}\n")

    results = []

    for i, project in enumerate(projects, 1):
        print(f"\n[{i}/{len(projects)}] {project['project_id']}: {project['project_name'][:50]}...")

        project_result = {
            'project_id': project['project_id'],
            'project_name': project['project_name'],
            'project_type': project['project_type'],
            'word_count': project['word_count'],
            'source_count': project['source_count'],
            'professor_eval': project.get('professor_eval'),
            'ai_evaluations': {}
        }

        for model in models:
            evaluation = evaluate_project(project, model)
            project_result['ai_evaluations'][model] = asdict(evaluation)

            # Зачувај поединечен резултат
            result_file = os.path.join(RESULTS_DIR, f"{project['project_id']}_{model}.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(evaluation), f, ensure_ascii=False, indent=2)

        results.append(project_result)

        # Зачувај целосен резултат за проектот
        project_result_file = os.path.join(RESULTS_DIR, f"{project['project_id']}_all.json")
        with open(project_result_file, 'w', encoding='utf-8') as f:
            json.dump(project_result, f, ensure_ascii=False, indent=2)

    # Генерирај CSV
    generate_csv(results, models)

    print(f"\n{'='*60}")
    print(f"ЕВАЛУАЦИЈА ЗАВРШЕНА")
    print(f"Резултати зачувани во: {RESULTS_DIR}")
    print(f"CSV фајл: {OUTPUT_CSV}")
    print(f"{'='*60}\n")

    return results


def generate_csv(results: List[Dict], models: List[str]):
    """Генерирај CSV со споредба на професор vs AI евалуации"""
    rows = []

    for result in results:
        project_id = result['project_id']
        project_name = result['project_name']
        project_type = result['project_type']
        prof_eval = result.get('professor_eval')

        # Прво додај ја оценката од професорот
        if prof_eval:
            rows.append({
                'project_id': project_id,
                'project_name': project_name,
                'project_type': project_type,
                'evaluator': 'ПРОФЕСОР',
                'metap': prof_eval.get('metap', 1.0),
                'tocnost': prof_eval.get('tocnost', 1.0),
                'izmama': prof_eval.get('izmama', 'нема'),
                'kviz': prof_eval.get('kviz', 0),
                'vkupno': prof_eval.get('vkupno', 0),
                'komentar': prof_eval.get('komentar', '')
            })

        # Потоа додај ги AI евалуациите
        for model in models:
            ai_eval = result.get('ai_evaluations', {}).get(model, {})
            if ai_eval:
                rows.append({
                    'project_id': project_id,
                    'project_name': project_name,
                    'project_type': project_type,
                    'evaluator': f'AI-{model.upper()}',
                    'metap': ai_eval.get('metap', 1.0),
                    'tocnost': ai_eval.get('tocnost', 1.0),
                    'izmama': ai_eval.get('izmama', 'нема'),
                    'kviz': ai_eval.get('kviz_total', 0),
                    'vkupno': ai_eval.get('vkupno', 0),
                    'komentar': ai_eval.get('komentar', '')
                })

        # Додади празна линија за визуелна сепарација
        rows.append({
            'project_id': '',
            'project_name': '',
            'project_type': '',
            'evaluator': '',
            'metap': '',
            'tocnost': '',
            'izmama': '',
            'kviz': '',
            'vkupno': '',
            'komentar': ''
        })

    # Запиши CSV
    fieldnames = ['project_id', 'project_name', 'project_type', 'evaluator',
                  'metap', 'tocnost', 'izmama', 'kviz', 'vkupno', 'komentar']

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    """Главна функција"""
    import argparse

    parser = argparse.ArgumentParser(description='Евалуатор за студентски проекти')
    parser.add_argument('--projects', nargs='*', help='Листа на project_id за евалуација (default: сите)')
    parser.add_argument('--models', nargs='*', choices=MODELS, default=MODELS,
                        help='Модели за евалуација (default: сите)')
    parser.add_argument('--test', action='store_true', help='Тест режим - само еден проект')

    args = parser.parse_args()

    if args.test:
        # Тест со еден проект и еден модел
        run_evaluation(project_ids=['noAI_01'], models=['haiku'])
    else:
        run_evaluation(project_ids=args.projects, models=args.models)


if __name__ == '__main__':
    main()
