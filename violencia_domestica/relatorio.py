"""Geração do relatório HTML para download."""
from datetime import datetime


def generate_html_report(df):
    """Gera relatório HTML exportável com achados e métricas"""

    # Calcular métricas principais
    total_casos = len(df)
    tipos_crime = df['tipo_crime'].value_counts()
    bairros_top = df['bairro'].value_counts().head(5)

    # Calcular taxa de resolução
    casos_concluidos = len(df[df['status_caso'] == 'Concluído']) if 'status_caso' in df.columns else 0
    taxa_resolucao = (casos_concluidos / total_casos * 100) if total_casos > 0 else 0

    # Análise temporal
    if 'hora' not in df.columns:
        df_temp = df.copy()
        df_temp['hora'] = df_temp['data_ocorrencia'].dt.hour
    else:
        df_temp = df

    hora_pico = df_temp['hora'].mode().iloc[0] if len(df_temp) > 0 else 0
    hora_unica = df_temp['hora'].nunique() <= 1
    texto_horario = (f"indisponível (todos os registros às {hora_pico}h)" if hora_unica
                     else f"{hora_pico}:00h")

    # Template HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Relatório de Análise - Violência Doméstica</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                line-height: 1.6;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #dc3545;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .metric {{
                background: #f8f9fa;
                padding: 15px;
                margin: 10px 0;
                border-left: 4px solid #dc3545;
            }}
            .section {{
                margin: 30px 0;
            }}
            .insight {{
                background: #e3f2fd;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #2196f3;
            }}
            .warning {{
                background: #fff3cd;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #ffc107;
            }}
            .footer {{
                text-align: center;
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #666;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Relatório de Análise - Violência Doméstica</h1>
            <p><strong>Delegacia Especializada de Atendimento à Mulher - DEAM</strong></p>
            <p>Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>

        <div class="section">
            <h2>📊 Resumo Executivo</h2>
            <div class="metric">
                <strong>Total de Casos Analisados:</strong> {total_casos:,}
            </div>
            <div class="metric">
                <strong>Taxa de Resolução:</strong> {taxa_resolucao:.1f}%
            </div>
            <div class="metric">
                <strong>Horário de Maior Incidência:</strong> {texto_horario}
            </div>
        </div>

        <div class="section">
            <h2>🚨 Distribuição por Tipo de Crime</h2>
            <table>
                <tr>
                    <th>Tipo de Crime</th>
                    <th>Número de Casos</th>
                    <th>Percentual</th>
                </tr>
    """

    # Adicionar dados dos tipos de crime
    for tipo, casos in tipos_crime.items():
        percentual = (casos / total_casos * 100)
        html_content += f"""
                <tr>
                    <td>{tipo}</td>
                    <td>{casos}</td>
                    <td>{percentual:.1f}%</td>
                </tr>
        """

    html_content += """
            </table>
        </div>

        <div class="section">
            <h2>📍 Bairros Mais Afetados</h2>
            <table>
                <tr>
                    <th>Bairro</th>
                    <th>Número de Casos</th>
                    <th>Percentual do Total</th>
                </tr>
    """

    # Adicionar dados dos bairros
    for bairro, casos in bairros_top.items():
        percentual = (casos / total_casos * 100)
        html_content += f"""
                <tr>
                    <td>{bairro}</td>
                    <td>{casos}</td>
                    <td>{percentual:.1f}%</td>
                </tr>
        """

    # Gerar insights automáticos
    insights = []

    # Insight sobre concentração
    if len(bairros_top) > 0:
        bairro_principal = bairros_top.index[0]
        concentracao = (bairros_top.iloc[0] / total_casos * 100)
        if concentracao > 20:
            insights.append(f"Alta concentração de casos em {bairro_principal} ({concentracao:.1f}% do total) - Requer atenção especial")

    # Insight sobre taxa de resolução
    if taxa_resolucao < 70:
        insights.append(f"Taxa de resolução baixa ({taxa_resolucao:.1f}%) - Necessário revisar processos investigativos")
    elif taxa_resolucao > 85:
        insights.append(f"Excelente taxa de resolução ({taxa_resolucao:.1f}%) - Manter padrão de qualidade")

    # Insight sobre horário
    if not hora_unica and (hora_pico >= 22 or hora_pico <= 6):
        insights.append(f"Pico de ocorrências no período noturno ({hora_pico}h) - Reforçar patrulhamento noturno")

    html_content += """
            </table>
        </div>

        <div class="section">
            <h2>💡 Insights e Recomendações</h2>
    """

    for insight in insights:
        html_content += f'<div class="insight">• {insight}</div>'

    # Adicionar limitações
    html_content += f"""
        </div>

        <div class="section">
            <h2>⚠️ Limitações do Estudo</h2>
            <div class="warning">
                <strong>Qualidade dos Dados:</strong> Este relatório é baseado em {total_casos} casos válidos após limpeza geográfica.
                Coordenadas inválidas foram removidas para garantir precisão das análises espaciais.
            </div>
            <div class="warning">
                <strong>Período de Análise:</strong> Os dados refletem o período disponível no dataset e podem não representar
                tendências de longo prazo.
            </div>
            <div class="warning">
                <strong>Interpretação:</strong> As análises são baseadas em dados históricos e devem ser complementadas
                com conhecimento operacional local.
            </div>
        </div>

        <div class="section">
            <h2>📈 Métricas de Machine Learning</h2>
            <div class="metric">
                <strong>Algoritmos Utilizados:</strong> KMeans, DBSCAN, Isolation Forest, Random Forest
            </div>
            <div class="metric">
                <strong>Features Analisadas:</strong> Localização geográfica, padrões temporais, tipos de crime, características dos casos
            </div>
            <div class="metric">
                <strong>Validação:</strong> Silhouette Score para clustering, Cross-validation para modelos supervisionados
            </div>
        </div>

        <div class="footer">
            <p><strong>Dashboard de Violência Doméstica - DEAM</strong></p>
            <p>Projeto Acadêmico | Análise de Dados Criminais</p>
            <p><em>Este relatório foi gerado automaticamente pelo sistema de análise de dados.</em></p>
        </div>
    </body>
    </html>
    """

    return html_content
