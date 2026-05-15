#!/usr/bin/env python3
"""
Евалуатор v2 за студентски проекти со Claude CLI.
Две фази: train (калибрација со професорски оценки) и evaluate (самостојна оценка).
Модели: claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5
"""

import os
import json
import subprocess
import csv
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARSED_DIR = os.path.join(BASE_DIR, 'parsed_projects_v2')
TRAINING_DATA_DIR = os.path.join(BASE_DIR, 'training_data')
RESULTS_DIR = os.path.join(BASE_DIR, 'evaluation_results_v2')
OUTPUT_CSV = os.path.join(BASE_DIR, 'evaluations_v2.csv')

MODELS = {
    'opus': 'claude-opus-4-6',
    'sonnet': 'claude-sonnet-4-6',
    'haiku': 'claude-haiku-4-5',
}

RUBRIC = """
### Критериуми за оценување (вкупно 100 поени):

**А) Три групи прашања за истражување (30 поени)**
За проекти БЕЗ AI (noAI): Оцени дали студентот јасно објаснил:
- Што прво пребарувал на интернет (10п)
- Кои извори ги нашол (10п)
- Кои клучни информации ги искористил (10п)

За проекти СО AI (onlyAI): Оцени дали студентот јасно објаснил:
- Кои прашања ги поставил до ГЈМ (10п)
- Каков одговор добил од ГЈМ (10п)
- Кои извори ја потврдуваат релевантноста на генерираниот одговор (10п)

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

### Метаподатоци фактор (metap):
- 9+ извори: фактор = 1.0
- За помалку од 9: казна 0.05 за секој што недостасува
- Минимум ~800 зборови

### Измама:
- Знаци на плагијаризам
- Дали изворите се наведени во текстот
- Недозволено користење на AI (за noAI проекти)
"""

TRAINING_PROMPT = """
Ти си професор кој евалуира студентски проект. Оцени го следниов проект според дадените критериуми.

## КРИТЕРИУМИ ЗА ОЦЕНУВАЊЕ:
{rubric}

## ПРОЕКТ ЗА ЕВАЛУАЦИЈА:

**Име на проект:** {project_name}
**Тип на проект:** {project_type}
**Број на зборови:** {word_count}
**Пронајдени извори:** {source_count}

**СОДРЖИНА:**
{content}

## ПРОФЕСОРСКА ОЦЕНКА (РЕФЕРЕНТНА):
Професорот го оценил овој проект со следните оценки:
- kviz (вкупно поени): {prof_kviz}
- metap (фактор извори): {prof_metap}
- tocnost (фактор точност): {prof_tocnost}
- vkupno (финална оценка): {prof_vkupno}
- izmama: {prof_izmama}
- komentar: {prof_komentar}

Анализирај ја професорската оценка и објасни ја логиката зад секоја компонента.
Одговори САМО во следниов JSON формат:

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
  "komentar": "<краток коментар за проектот>",
  "analiza_na_profesorska_ocenka": "<објасни зошто професорот ја дал таа оценка>"
}}
"""

EVALUATION_PROMPT = """
Ти си професор кој евалуира студентски проект. Оцени го следниов проект според дадените критериуми.

## КРИТЕРИУМИ ЗА ОЦЕНУВАЊЕ:
{rubric}

## КАЛИБРАЦИСКИ ПРИМЕРИ:
Следат примери од истиот тип проекти оценети од професор. Користи ги како референца за нивото на строгост и стилот на оценување.

{calibration_examples}

## ПРОЕКТ ЗА ЕВАЛУАЦИЈА:

**Име на проект:** {project_name}
**Тип на проект:** {project_type}
**Број на зборови:** {word_count}
**Пронајдени извори:** {source_count}

**СОДРЖИНА:**
{content}

## ТВОЈА ОЦЕНКА:
Оценувај со истото ниво на строгост како професорот од примерите погоре.
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


def call_claude(prompt: str, model_id: str, timeout: int = 180) -> str:
    try:
        result = subprocess.run(
            ['claude', '--print', '--model', model_id, '--dangerously-skip-permissions', prompt],
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
    json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    return {}


def response_to_evaluation(response: str, model_name: str) -> AIEvaluation:
    evaluation = AIEvaluation(model=model_name, raw_response=response)
    if response.startswith("ERROR:"):
        evaluation.error = response
        return evaluation

    parsed = parse_evaluation_response(response)
    if not parsed:
        evaluation.error = "Failed to parse JSON response"
        return evaluation

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
    return evaluation


# ─── TRAINING PHASE ───────────────────────────────────────────────────────────

def run_training(models: Optional[List[str]] = None):
    """Parse training projects and run calibration evaluations with professor grades."""
    os.makedirs(TRAINING_DATA_DIR, exist_ok=True)

    training_file = os.path.join(PARSED_DIR, 'training', 'all_projects.json')
    if not os.path.exists(training_file):
        print("Грешка: Нема парсирани training проекти. Прво извршете:")
        print("  python3 project_parser_v2.py training")
        return

    with open(training_file, 'r', encoding='utf-8') as f:
        projects = json.load(f)

    if models is None:
        models = list(MODELS.keys())

    projects_with_grades = [p for p in projects if p.get('professor_eval')]
    if not projects_with_grades:
        print("Грешка: Нема проекти со професорски оценки во training сетот.")
        return

    print(f"\n{'=' * 60}")
    print(f"ТРЕНИНГ ФАЗА - КАЛИБРАЦИЈА")
    print(f"{'=' * 60}")
    print(f"Проекти со оценки: {len(projects_with_grades)}")
    print(f"Модели: {', '.join(models)}")
    print(f"{'=' * 60}\n")

    training_results = {}

    for i, project in enumerate(projects_with_grades, 1):
        pid = project['project_id']
        ptype = project['project_type']
        prof = project['professor_eval']

        print(f"\n[{i}/{len(projects_with_grades)}] {pid}: {project['project_name'][:50]}...")

        prompt = TRAINING_PROMPT.format(
            rubric=RUBRIC,
            project_name=project['project_name'],
            project_type=ptype,
            word_count=project['word_count'],
            source_count=project['source_count'],
            content=project['content'][:15000],
            prof_kviz=prof.get('kviz', 0),
            prof_metap=prof.get('metap', 1.0),
            prof_tocnost=prof.get('tocnost', 1.0),
            prof_vkupno=prof.get('vkupno', 0),
            prof_izmama=prof.get('izmama', 'нема'),
            prof_komentar=prof.get('komentar', ''),
        )

        model_results = {}
        for model_name in models:
            model_id = MODELS[model_name]
            print(f"    Тренирам со {model_name} ({model_id})...", end=" ", flush=True)
            start = time.time()

            response = call_claude(prompt, model_id)
            elapsed = time.time() - start

            evaluation = response_to_evaluation(response, model_name)
            if evaluation.error:
                print(f"ГРЕШКА ({elapsed:.1f}s)")
            else:
                print(f"OK - Вкупно: {evaluation.vkupno:.1f} vs Проф: {prof.get('vkupno', 0)} ({elapsed:.1f}s)")

            model_results[model_name] = asdict(evaluation)

        training_results[pid] = {
            'project': project,
            'ai_evaluations': model_results,
        }

    # Save training data grouped by project type for calibration
    calibration = {'noAI': [], 'onlyAI': [], 'hybrid': []}
    for pid, data in training_results.items():
        ptype = data['project']['project_type']
        calibration[ptype].append({
            'project_name': data['project']['project_name'],
            'word_count': data['project']['word_count'],
            'source_count': data['project']['source_count'],
            'professor_eval': data['project']['professor_eval'],
            'content_preview': data['project']['content'][:500],
        })

    calibration_file = os.path.join(TRAINING_DATA_DIR, 'calibration.json')
    with open(calibration_file, 'w', encoding='utf-8') as f:
        json.dump(calibration, f, ensure_ascii=False, indent=2)

    full_results_file = os.path.join(TRAINING_DATA_DIR, 'training_results.json')
    with open(full_results_file, 'w', encoding='utf-8') as f:
        json.dump(training_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"ТРЕНИНГ ЗАВРШЕН")
    print(f"Калибрациски податоци: {calibration_file}")
    print(f"Полни резултати: {full_results_file}")
    for ptype, examples in calibration.items():
        print(f"  {ptype}: {len(examples)} примери")
    print(f"{'=' * 60}\n")


# ─── EVALUATION PHASE ─────────────────────────────────────────────────────────

def build_calibration_text(calibration_examples: List[dict]) -> str:
    """Format calibration examples for inclusion in the evaluation prompt."""
    if not calibration_examples:
        return "(нема калибрациски примери за овој тип)"

    parts = []
    for i, ex in enumerate(calibration_examples, 1):
        prof = ex.get('professor_eval', {})
        parts.append(
            f"--- Пример {i}: {ex['project_name'][:60]} ---\n"
            f"Зборови: {ex['word_count']}, Извори: {ex['source_count']}\n"
            f"Содржина (преглед): {ex['content_preview'][:300]}...\n"
            f"Професорска оценка: kviz={prof.get('kviz', 0)}, metap={prof.get('metap', 1.0)}, "
            f"tocnost={prof.get('tocnost', 1.0)}, vkupno={prof.get('vkupno', 0)}\n"
            f"Измама: {prof.get('izmama', 'нема')}\n"
            f"Коментар: {prof.get('komentar', '')}"
        )
    return '\n\n'.join(parts)


def run_evaluation(models: Optional[List[str]] = None, project_ids: Optional[List[str]] = None):
    """Evaluate projects using calibration data from training phase."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    calibration_file = os.path.join(TRAINING_DATA_DIR, 'calibration.json')
    if not os.path.exists(calibration_file):
        print("Грешка: Нема калибрациски податоци. Прво извршете тренинг фаза:")
        print("  python3 evaluator_v2.py train")
        return

    with open(calibration_file, 'r', encoding='utf-8') as f:
        calibration = json.load(f)

    eval_file = os.path.join(PARSED_DIR, 'evaluation', 'all_projects.json')
    if not os.path.exists(eval_file):
        print("Грешка: Нема парсирани evaluation проекти. Прво извршете:")
        print("  python3 project_parser_v2.py evaluation")
        return

    with open(eval_file, 'r', encoding='utf-8') as f:
        all_projects = json.load(f)

    if project_ids:
        projects = [p for p in all_projects if p['project_id'] in project_ids]
    else:
        projects = all_projects

    if models is None:
        models = list(MODELS.keys())

    print(f"\n{'=' * 60}")
    print(f"ЕВАЛУАЦИЈА - САМОСТОЈНО ОЦЕНУВАЊЕ")
    print(f"{'=' * 60}")
    print(f"Проекти: {len(projects)}")
    print(f"Модели: {', '.join(models)}")
    print(f"Калибрациски примери: {', '.join(f'{k}={len(v)}' for k, v in calibration.items())}")
    print(f"Вкупно евалуации: {len(projects) * len(models)}")
    print(f"{'=' * 60}\n")

    results = []

    for i, project in enumerate(projects, 1):
        pid = project['project_id']
        ptype = project['project_type']

        print(f"\n[{i}/{len(projects)}] {pid}: {project['project_name'][:50]}...")

        cal_examples = calibration.get(ptype, [])
        cal_text = build_calibration_text(cal_examples)

        prompt = EVALUATION_PROMPT.format(
            rubric=RUBRIC,
            calibration_examples=cal_text,
            project_name=project['project_name'],
            project_type=ptype,
            word_count=project['word_count'],
            source_count=project['source_count'],
            content=project['content'][:15000],
        )

        project_result = {
            'project_id': pid,
            'project_name': project['project_name'],
            'project_type': ptype,
            'word_count': project['word_count'],
            'source_count': project['source_count'],
            'professor_eval': project.get('professor_eval'),
            'ai_evaluations': {},
        }

        for model_name in models:
            model_id = MODELS[model_name]
            print(f"    Евалуирам со {model_name} ({model_id})...", end=" ", flush=True)
            start = time.time()

            response = call_claude(prompt, model_id)
            elapsed = time.time() - start

            evaluation = response_to_evaluation(response, model_name)
            if evaluation.error:
                print(f"ГРЕШКА ({elapsed:.1f}s)")
            else:
                print(f"OK - Вкупно: {evaluation.vkupno:.1f} ({elapsed:.1f}s)")

            project_result['ai_evaluations'][model_name] = asdict(evaluation)

            result_file = os.path.join(RESULTS_DIR, f"{pid}_{model_name}.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(evaluation), f, ensure_ascii=False, indent=2)

        results.append(project_result)

        project_result_file = os.path.join(RESULTS_DIR, f"{pid}_all.json")
        with open(project_result_file, 'w', encoding='utf-8') as f:
            json.dump(project_result, f, ensure_ascii=False, indent=2)

    generate_csv(results, models)

    print(f"\n{'=' * 60}")
    print(f"ЕВАЛУАЦИЈА ЗАВРШЕНА")
    print(f"Резултати: {RESULTS_DIR}")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"{'=' * 60}\n")

    return results


def generate_csv(results: List[Dict], models: List[str]):
    fieldnames = ['project_id', 'project_name', 'project_type', 'evaluator',
                  'metap', 'tocnost', 'izmama', 'kviz', 'vkupno', 'komentar']

    rows = []
    for result in results:
        prof_eval = result.get('professor_eval')
        if prof_eval:
            rows.append({
                'project_id': result['project_id'],
                'project_name': result['project_name'],
                'project_type': result['project_type'],
                'evaluator': 'ПРОФЕСОР',
                'metap': prof_eval.get('metap', 1.0),
                'tocnost': prof_eval.get('tocnost', 1.0),
                'izmama': prof_eval.get('izmama', 'нема'),
                'kviz': prof_eval.get('kviz', 0),
                'vkupno': prof_eval.get('vkupno', 0),
                'komentar': prof_eval.get('komentar', ''),
            })

        for model_name in models:
            ai_eval = result.get('ai_evaluations', {}).get(model_name, {})
            if ai_eval:
                rows.append({
                    'project_id': result['project_id'],
                    'project_name': result['project_name'],
                    'project_type': result['project_type'],
                    'evaluator': f'AI-{model_name.upper()}',
                    'metap': ai_eval.get('metap', 1.0),
                    'tocnost': ai_eval.get('tocnost', 1.0),
                    'izmama': ai_eval.get('izmama', 'нема'),
                    'kviz': ai_eval.get('kviz_total', 0),
                    'vkupno': ai_eval.get('vkupno', 0),
                    'komentar': ai_eval.get('komentar', ''),
                })

        rows.append({k: '' for k in fieldnames})

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Евалуатор v2 за студентски проекти')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Train subcommand
    train_parser = subparsers.add_parser('train', help='Тренинг фаза - калибрација со професорски оценки')
    train_parser.add_argument('--models', nargs='*', choices=list(MODELS.keys()),
                              default=list(MODELS.keys()), help='Модели за тренинг')

    # Evaluate subcommand
    eval_parser = subparsers.add_parser('evaluate', help='Евалуација - самостојно оценување')
    eval_parser.add_argument('--models', nargs='*', choices=list(MODELS.keys()),
                             default=list(MODELS.keys()), help='Модели за евалуација')
    eval_parser.add_argument('--projects', nargs='*', help='Специфични project_id за евалуација')

    # Test subcommand
    test_parser = subparsers.add_parser('test', help='Тест режим - еден проект, еден модел')
    test_parser.add_argument('--phase', choices=['train', 'evaluate'], default='evaluate',
                             help='Која фаза да се тестира')

    args = parser.parse_args()

    if args.command == 'train':
        run_training(models=args.models)
    elif args.command == 'evaluate':
        run_evaluation(models=args.models, project_ids=args.projects)
    elif args.command == 'test':
        if args.phase == 'train':
            run_training(models=['haiku'])
        else:
            run_evaluation(models=['haiku'], project_ids=None)


if __name__ == '__main__':
    main()
