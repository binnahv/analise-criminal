"""Geração do relatório HTML para download."""
from datetime import datetime
from html import escape
from typing import Any

import pandas as pd

from ui import format_number

REPORT_CSS = """
    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }
    .header { text-align: center; border-bottom: 2px solid #dc3545; padding-bottom: 20px; margin-bottom: 30px; }
    .metric { background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #dc3545; }
    .section { margin: 30px 0; }
    .insight { background: #e3f2fd; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #2196f3; }
    .warning { background: #fff3cd; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #ffc107; }
    .footer { text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    th { background-color: #f2f2f2; }
"""

LIMITATIONS = [
    ("Qualidade dos Dados", "Os dados vêm de um dataset acadêmico com inconsistências conhecidas "
                            "(coordenadas e horários); veja o README do projeto."),
    ("Período de Análise", "Os dados refletem o período disponível no dataset e podem não representar "
                           "tendências de longo prazo."),
    ("Interpretação", "As análises são baseadas em dados históricos e devem ser complementadas "
                      "com conhecimento operacional local."),
]

ML_SUMMARY = [
    ("Algoritmos Utilizados", "KMeans, DBSCAN, Isolation Forest, Random Forest"),
    ("Features Analisadas", "Localização geográfica, padrões temporais, tipos de crime, características dos casos"),
    ("Validação", "Silhouette Score para clustering, validação cruzada e baseline para o modelo supervisionado"),
]


def _summary(df: pd.DataFrame) -> dict[str, Any]:
    """Métricas do resumo executivo."""
    total = len(df)
    concluded = int((df['status_caso'] == 'Concluído').sum()) if 'status_caso' in df.columns else 0
    hours = df['hora'] if 'hora' in df.columns else df['data_ocorrencia'].dt.hour
    peak_hour = int(hours.mode().iloc[0]) if total else 0
    single_hour = hours.nunique() <= 1
    return {
        'total': total,
        'resolution_rate': concluded / total * 100 if total else 0,
        'peak_hour': peak_hour,
        'single_hour': single_hour,
        'hour_text': (f"indisponível (todos os registros às {peak_hour}h)" if single_hour
                      else f"{peak_hour}:00h"),
    }


def _insights(df: pd.DataFrame, summary: dict[str, Any]) -> list[str]:
    insights = []
    top_bairros = df['bairro'].value_counts()
    if len(top_bairros) and top_bairros.iloc[0] / summary['total'] * 100 > 20:
        share = top_bairros.iloc[0] / summary['total'] * 100
        insights.append(f"Alta concentração de casos em {top_bairros.index[0]} ({share:.1f}% do total) "
                        "- Requer atenção especial")
    rate = summary['resolution_rate']
    if rate < 70:
        insights.append(f"Taxa de resolução baixa ({rate:.1f}%) - Necessário revisar processos investigativos")
    elif rate > 85:
        insights.append(f"Excelente taxa de resolução ({rate:.1f}%) - Manter padrão de qualidade")
    peak = summary['peak_hour']
    if not summary['single_hour'] and (peak >= 22 or peak <= 6):
        insights.append(f"Pico de ocorrências no período noturno ({peak}h) - Reforçar patrulhamento noturno")
    return insights


def _count_table(counts: pd.Series, total: int, column: str, share_label: str) -> str:
    rows = "".join(
        f"<tr><td>{escape(str(name))}</td><td>{count}</td><td>{count / total * 100:.1f}%</td></tr>"
        for name, count in counts.items()
    )
    return (f"<table><tr><th>{column}</th><th>Número de Casos</th><th>{share_label}</th></tr>"
            f"{rows}</table>")


def _boxes(items: list[tuple[str, str]], css_class: str) -> str:
    return "".join(f'<div class="{css_class}"><strong>{escape(title)}:</strong> {escape(text)}</div>'
                   for title, text in items)


def generate_html_report(df: pd.DataFrame) -> str:
    """Gera o relatório HTML com resumo, tabelas, insights e limitações."""
    summary = _summary(df)
    total = summary['total']
    insights = "".join(f'<div class="insight">• {escape(text)}</div>' for text in _insights(df, summary))
    executive = _boxes([
        ("Total de Casos Analisados", format_number(total)),
        ("Taxa de Resolução", f"{format_number(summary['resolution_rate'])}%"),
        ("Horário de Maior Incidência", summary['hour_text']),
    ], "metric")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório de Análise - Violência Doméstica</title>
    <style>{REPORT_CSS}</style>
</head>
<body>
    <div class="header">
        <h1>Relatório de Análise - Violência Doméstica</h1>
        <p><strong>Delegacia Especializada de Atendimento à Mulher - DEAM</strong></p>
        <p>Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    </div>
    <div class="section"><h2>📊 Resumo Executivo</h2>{executive}</div>
    <div class="section"><h2>🚨 Distribuição por Tipo de Crime</h2>
        {_count_table(df['tipo_crime'].value_counts(), total, 'Tipo de Crime', 'Percentual')}</div>
    <div class="section"><h2>📍 Bairros Mais Afetados</h2>
        {_count_table(df['bairro'].value_counts().head(5), total, 'Bairro', 'Percentual do Total')}</div>
    <div class="section"><h2>💡 Insights e Recomendações</h2>{insights}</div>
    <div class="section"><h2>⚠️ Limitações do Estudo</h2>{_boxes(LIMITATIONS, "warning")}</div>
    <div class="section"><h2>📈 Métricas de Machine Learning</h2>{_boxes(ML_SUMMARY, "metric")}</div>
    <div class="footer">
        <p><strong>Dashboard de Violência Doméstica - DEAM</strong></p>
        <p>Projeto Acadêmico | Análise de Dados Criminais</p>
        <p><em>Este relatório foi gerado automaticamente pelo sistema de análise de dados.</em></p>
    </div>
</body>
</html>
"""
