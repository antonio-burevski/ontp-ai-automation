#!/usr/bin/env python3
"""Generate a visual HTML report for the evaluation comparison."""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import base64
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# Settings
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (10, 5)
plt.rcParams['font.size'] = 11
COLORS = {'Професор': '#2ecc71', 'Opus': '#3498db', 'Sonnet': '#9b59b6', 'Haiku': '#e74c3c'}

def fig_to_base64(fig):
    """Convert matplotlib figure to base64 string."""
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=130, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

def load_data():
    """Load and prepare the data."""
    df = pd.read_csv('../../evaluations.csv')
    df = df.dropna(subset=['project_id', 'evaluator'])

    evaluator_map = {'ПРОФЕСОР': 'Професор', 'AI-OPUS': 'Opus', 'AI-SONNET': 'Sonnet', 'AI-HAIKU': 'Haiku'}
    df['evaluator'] = df['evaluator'].map(evaluator_map)

    for col in ['metap', 'tocnost', 'kviz', 'vkupno']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

def create_distribution_chart(df):
    """Create score distribution chart."""
    fig, ax = plt.subplots(figsize=(10, 5))

    order = ['Професор', 'Opus', 'Sonnet', 'Haiku']
    colors = [COLORS[e] for e in order]

    sns.boxplot(data=df, x='evaluator', y='vkupno', order=order, palette=colors, ax=ax)
    ax.set_title('Како се распределени оценките?', fontsize=14, fontweight='bold')
    ax.set_xlabel('')
    ax.set_ylabel('Оценка (поени)')
    ax.set_ylim(0, 100)

    plt.tight_layout()
    result = fig_to_base64(fig)
    plt.close()
    return result

def create_scatter_charts(df):
    """Create correlation scatter charts."""
    vkupno_pivot = df.pivot_table(index='project_id', columns='evaluator', values='vkupno').reset_index()

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    models = ['Opus', 'Sonnet', 'Haiku']

    for i, model in enumerate(models):
        valid = vkupno_pivot[['Професор', model]].dropna()

        axes[i].scatter(valid['Професор'], valid[model], alpha=0.6, s=50, color=COLORS[model])
        axes[i].plot([0, 100], [0, 100], 'k--', alpha=0.4, label='Исто')

        z = np.polyfit(valid['Професор'], valid[model], 1)
        p = np.poly1d(z)
        axes[i].plot([0, 100], [p(0), p(100)], color=COLORS[model], linewidth=2)

        r = stats.pearsonr(valid['Професор'], valid[model])[0]
        axes[i].set_title(f'{model}\n(сличност: {r*100:.0f}%)', fontsize=12, fontweight='bold')
        axes[i].set_xlabel('Професор')
        axes[i].set_ylabel(model)
        axes[i].set_xlim(0, 100)
        axes[i].set_ylim(0, 100)

    plt.tight_layout()
    result = fig_to_base64(fig)
    plt.close()
    return result

def create_difference_chart(df):
    """Create difference histogram."""
    vkupno_pivot = df.pivot_table(index='project_id', columns='evaluator', values='vkupno').reset_index()

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    models = ['Opus', 'Sonnet', 'Haiku']

    for i, model in enumerate(models):
        diff = (vkupno_pivot[model] - vkupno_pivot['Професор']).dropna()

        axes[i].hist(diff, bins=12, color=COLORS[model], alpha=0.7, edgecolor='white')
        axes[i].axvline(x=0, color='black', linestyle='--', linewidth=2)
        axes[i].axvline(x=diff.mean(), color='#e74c3c', linestyle='-', linewidth=2)

        direction = "повисоко" if diff.mean() > 0 else "пониско"
        axes[i].set_title(f'{model}\nво просек {abs(diff.mean()):.1f} поени {direction}', fontsize=11, fontweight='bold')
        axes[i].set_xlabel('Разлика од Професор')
        axes[i].set_ylabel('Број проекти')

    plt.tight_layout()
    result = fig_to_base64(fig)
    plt.close()
    return result

def create_metap_chart(df):
    """Create metap comparison chart."""
    fig, ax = plt.subplots(figsize=(10, 5))

    order = ['Професор', 'Opus', 'Sonnet', 'Haiku']
    colors = [COLORS[e] for e in order]

    means = df.groupby('evaluator')['metap'].mean().reindex(order)
    bars = ax.bar(order, means.values, color=colors, edgecolor='white', linewidth=2)

    ax.set_title('Просечна оценка за метаподатоци (извори)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Фактор (0-1)')
    ax.set_ylim(0.85, 1.0)

    for bar, val in zip(bars, means.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f'{val:.3f}', ha='center', va='bottom', fontsize=12, fontweight='bold')

    plt.tight_layout()
    result = fig_to_base64(fig)
    plt.close()
    return result

def create_type_chart(df):
    """Create chart by project type."""
    fig, ax = plt.subplots(figsize=(11, 5))

    type_means = df.groupby(['project_type', 'evaluator'])['vkupno'].mean().unstack()
    type_means = type_means[['Професор', 'Opus', 'Sonnet', 'Haiku']]

    type_means.plot(kind='bar', ax=ax, width=0.8,
                    color=[COLORS['Професор'], COLORS['Opus'], COLORS['Sonnet'], COLORS['Haiku']],
                    edgecolor='white', linewidth=1)

    ax.set_title('Просечни оценки по тип на проект', fontsize=14, fontweight='bold')
    ax.set_xlabel('')
    ax.set_ylabel('Просечна оценка')
    ax.set_xticklabels(['Без AI', 'Хибрид', 'Само AI'], rotation=0, fontsize=11)
    ax.legend(title='', bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.set_ylim(0, 70)

    plt.tight_layout()
    result = fig_to_base64(fig)
    plt.close()
    return result

def create_agreement_chart(df):
    """Create agreement categories chart."""
    vkupno_pivot = df.pivot_table(index='project_id', columns='evaluator', values='vkupno').reset_index()

    def categorize(diff):
        if abs(diff) <= 10:
            return 'Слично'
        elif diff > 10:
            return 'AI повисоко'
        else:
            return 'AI пониско'

    fig, ax = plt.subplots(figsize=(10, 4))

    data = []
    for model in ['Opus', 'Sonnet', 'Haiku']:
        diff = (vkupno_pivot[model] - vkupno_pivot['Професор']).dropna()
        cats = diff.apply(categorize).value_counts(normalize=True) * 100
        data.append({
            'Модел': model,
            'Слично (±10)': cats.get('Слично', 0),
            'AI повисоко': cats.get('AI повисоко', 0),
            'AI пониско': cats.get('AI пониско', 0)
        })

    agree_df = pd.DataFrame(data).set_index('Модел')
    agree_df.plot(kind='barh', stacked=True, ax=ax,
                  color=['#27ae60', '#e74c3c', '#3498db'], edgecolor='white', linewidth=1)

    ax.set_title('Колку често се согласуваат со Професорот?', fontsize=14, fontweight='bold')
    ax.set_xlabel('Процент од проекти')
    ax.set_ylabel('')
    ax.legend(title='', bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.set_xlim(0, 100)

    plt.tight_layout()
    result = fig_to_base64(fig)
    plt.close()
    return result

def calculate_stats(df):
    """Calculate summary statistics."""
    vkupno_pivot = df.pivot_table(index='project_id', columns='evaluator', values='vkupno').reset_index()

    stats_data = {}
    for model in ['Opus', 'Sonnet', 'Haiku']:
        valid = vkupno_pivot[['Професор', model]].dropna()
        diff = (vkupno_pivot[model] - vkupno_pivot['Професор']).dropna()

        r = stats.pearsonr(valid['Професор'], valid[model])[0]
        mae = diff.abs().mean()
        avg_diff = diff.mean()
        agree_10 = (diff.abs() <= 10).mean() * 100

        stats_data[model] = {
            'avg': df[df['evaluator']==model]['vkupno'].mean(),
            'correlation': r,
            'mae': mae,
            'bias': avg_diff,
            'agreement': agree_10
        }

    stats_data['Професор'] = {
        'avg': df[df['evaluator']=='Професор']['vkupno'].mean()
    }

    return stats_data

def generate_html(charts, stats_data):
    """Generate the HTML report."""

    html = f'''<!DOCTYPE html>
<html lang="mk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Споредба: Професор vs AI модели</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            color: white;
            padding: 40px 20px;
            margin-bottom: 30px;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}

        header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .card {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}

        .card h2 {{
            color: #333;
            font-size: 1.5em;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}

        .card p {{
            color: #666;
            margin-bottom: 20px;
            font-size: 1.05em;
        }}

        .card img {{
            width: 100%;
            border-radius: 8px;
            margin-top: 10px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .stat-box {{
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            padding: 25px;
            border-radius: 12px;
            text-align: center;
        }}

        .stat-box.professor {{
            border-left: 5px solid #2ecc71;
        }}

        .stat-box.opus {{
            border-left: 5px solid #3498db;
        }}

        .stat-box.sonnet {{
            border-left: 5px solid #9b59b6;
        }}

        .stat-box.haiku {{
            border-left: 5px solid #e74c3c;
        }}

        .stat-box h3 {{
            font-size: 1.3em;
            margin-bottom: 15px;
            color: #333;
        }}

        .stat-box .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }}

        .stat-box .label {{
            color: #888;
            font-size: 0.95em;
            margin-top: 5px;
        }}

        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        .comparison-table th,
        .comparison-table td {{
            padding: 15px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }}

        .comparison-table th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }}

        .comparison-table tr:hover {{
            background: #f8f9fa;
        }}

        .highlight {{
            background: linear-gradient(135deg, #667eea22 0%, #764ba222 100%);
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
        }}

        .highlight h3 {{
            color: #667eea;
            margin-bottom: 10px;
        }}

        footer {{
            text-align: center;
            color: white;
            padding: 30px;
            opacity: 0.8;
        }}

        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            margin: 20px 0;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}

        @media (max-width: 768px) {{
            header h1 {{
                font-size: 1.8em;
            }}

            .card {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Професор vs AI модели</h1>
            <p>Споредба на оценки за студентски проекти</p>
        </header>

        <div class="card">
            <h2>🎯 Главни бројки</h2>
            <p>Просечните оценки од секој евалуатор покажуваат како различно гледаат на истите проекти.</p>

            <div class="stats-grid">
                <div class="stat-box professor">
                    <h3>Професор</h3>
                    <div class="number">{stats_data['Професор']['avg']:.1f}</div>
                    <div class="label">просечна оценка</div>
                </div>
                <div class="stat-box opus">
                    <h3>Opus</h3>
                    <div class="number">{stats_data['Opus']['avg']:.1f}</div>
                    <div class="label">просечна оценка</div>
                </div>
                <div class="stat-box sonnet">
                    <h3>Sonnet</h3>
                    <div class="number">{stats_data['Sonnet']['avg']:.1f}</div>
                    <div class="label">просечна оценка</div>
                </div>
                <div class="stat-box haiku">
                    <h3>Haiku</h3>
                    <div class="number">{stats_data['Haiku']['avg']:.1f}</div>
                    <div class="label">просечна оценка</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📈 Распределба на оценки</h2>
            <p>Овој график покажува како се распределени оценките - каде е најголемата концентрација и колку варираат. Кутијата ја покажува средината (50% од оценките), а линиите екстремите.</p>
            <img src="data:image/png;base64,{charts['distribution']}" alt="Распределба на оценки">
        </div>

        <div class="card">
            <h2>🔗 Колку се слични оценките?</h2>
            <p>Секоја точка е еден проект. Ако AI и Професор се согласуваат, точката е близу до дијагоналната линија. Процентот покажува колку "исто размислуваат" - 100% би значело идентични оценки.</p>
            <img src="data:image/png;base64,{charts['scatter']}" alt="Корелација">

            <div class="highlight">
                <h3>Што значи сличноста?</h3>
                <p>Opus има <strong>{stats_data['Opus']['correlation']*100:.0f}%</strong> сличност, Sonnet <strong>{stats_data['Sonnet']['correlation']*100:.0f}%</strong>, а Haiku <strong>{stats_data['Haiku']['correlation']*100:.0f}%</strong>. Сите три покажуваат силна поврзаност со оценките на Професорот.</p>
            </div>
        </div>

        <div class="card">
            <h2>⚖️ Кој оценува повисоко, кој пониско?</h2>
            <p>Овие графици покажуваат разликата меѓу AI и Професор за секој проект. Ако столбот е лево од нулата - AI дал пониска оценка. Ако е десно - повисока.</p>
            <img src="data:image/png;base64,{charts['difference']}" alt="Разлики">

            <table class="comparison-table">
                <tr>
                    <th>AI Модел</th>
                    <th>Тенденција</th>
                    <th>Просечна разлика</th>
                    <th>Типична грешка</th>
                </tr>
                <tr>
                    <td><strong>Opus</strong></td>
                    <td>{"Оценува пониско" if stats_data['Opus']['bias'] < 0 else "Оценува повисоко"}</td>
                    <td>{stats_data['Opus']['bias']:+.1f} поени</td>
                    <td>±{stats_data['Opus']['mae']:.1f} поени</td>
                </tr>
                <tr>
                    <td><strong>Sonnet</strong></td>
                    <td>{"Оценува пониско" if stats_data['Sonnet']['bias'] < 0 else "Оценува повисоко"}</td>
                    <td>{stats_data['Sonnet']['bias']:+.1f} поени</td>
                    <td>±{stats_data['Sonnet']['mae']:.1f} поени</td>
                </tr>
                <tr>
                    <td><strong>Haiku</strong></td>
                    <td>{"Оценува пониско" if stats_data['Haiku']['bias'] < 0 else "Оценува повисоко"}</td>
                    <td>{stats_data['Haiku']['bias']:+.1f} поени</td>
                    <td>±{stats_data['Haiku']['mae']:.1f} поени</td>
                </tr>
            </table>
        </div>

        <div class="card">
            <h2>✅ Колку често се согласуваат?</h2>
            <p>Ако разликата е помала од 10 поени, сметаме дека AI и Професор "се согласуваат". Зелената боја покажува согласување, сината и црвената покажуваат кога AI оценува значително различно.</p>
            <img src="data:image/png;base64,{charts['agreement']}" alt="Согласување">

            <div class="stats-grid">
                <div class="stat-box opus">
                    <h3>Opus</h3>
                    <div class="number">{stats_data['Opus']['agreement']:.0f}%</div>
                    <div class="label">согласување со Професор</div>
                </div>
                <div class="stat-box sonnet">
                    <h3>Sonnet</h3>
                    <div class="number">{stats_data['Sonnet']['agreement']:.0f}%</div>
                    <div class="label">согласување со Професор</div>
                </div>
                <div class="stat-box haiku">
                    <h3>Haiku</h3>
                    <div class="number">{stats_data['Haiku']['agreement']:.0f}%</div>
                    <div class="label">согласување со Професор</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📚 Оценка за метаподатоци (извори)</h2>
            <p>Овој фактор (0-1) покажува колку добро студентот ги навел изворите. Вредност 1.0 значи дека сите критериуми за извори се исполнети.</p>
            <img src="data:image/png;base64,{charts['metap']}" alt="Метаподатоци">
        </div>

        <div class="card">
            <h2>📋 Споредба по тип на проект</h2>
            <p>Проектите се поделени на три типа: без употреба на AI, само со AI, или хибридно. Овој график покажува како секој евалуатор ги оценува различните типови.</p>
            <img src="data:image/png;base64,{charts['by_type']}" alt="По тип">

            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #2ecc71;"></div>
                    <span>Професор</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #3498db;"></div>
                    <span>Opus</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #9b59b6;"></div>
                    <span>Sonnet</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #e74c3c;"></div>
                    <span>Haiku</span>
                </div>
            </div>
        </div>

        <footer>
            <p>Анализа на 41 студентски проект</p>
            <p>Евалуатори: 1 професор + 3 AI модели (Claude)</p>
        </footer>
    </div>
</body>
</html>'''

    return html

def main():
    print("Вчитување податоци...")
    df = load_data()

    print("Генерирање графици...")
    charts = {
        'distribution': create_distribution_chart(df),
        'scatter': create_scatter_charts(df),
        'difference': create_difference_chart(df),
        'metap': create_metap_chart(df),
        'by_type': create_type_chart(df),
        'agreement': create_agreement_chart(df)
    }

    print("Пресметување статистики...")
    stats_data = calculate_stats(df)

    print("Генерирање HTML...")
    html = generate_html(charts, stats_data)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("Готово! Фајлот е зачуван како index.html")

if __name__ == '__main__':
    main()
