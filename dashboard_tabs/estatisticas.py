"""Aba de estatísticas gerais e insights."""
import pandas as pd
import plotly.express as px
import streamlit as st

from ui import has_constant_hour, show_chart, show_metric

RISK_COLORS = {'Alto Risco': '#ff4444', 'Médio Risco': '#ffaa00', 'Baixo Risco': '#44ff44'}


def _show_summary_metrics(df: pd.DataFrame) -> None:
    st.subheader("📈 Resumo Estatístico")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        show_metric("📊 Total de Crimes", len(df))
    with col2:
        show_metric("🏘️ Bairros Afetados", df['bairro'].nunique())
    with col3:
        show_metric("📅 Período (dias)", (df['data_ocorrencia'].max() - df['data_ocorrencia'].min()).days)
    with col4:
        show_metric("🎯 Tipos de Crime", df['tipo_crime'].nunique())


def _show_top_chart(counts: pd.Series, subtitle: str, title: str) -> None:
    st.subheader(subtitle)
    top = counts.head(10)
    show_chart(px.bar(x=top.values, y=top.index, orientation='h', title=title))


def _show_risk_distribution(df: pd.DataFrame) -> None:
    st.subheader("⚠️ Distribuição por Nível de Risco")
    risk = df['nivel_risco'].value_counts()
    col1, col2 = st.columns(2)
    with col1:
        show_chart(px.pie(values=risk.values, names=risk.index, title="Distribuição de Níveis de Risco",
                          color=risk.index, color_discrete_map=RISK_COLORS))
    with col2:
        stats = (df.groupby('nivel_risco')
                 .agg(**{'Total Ocorrências': ('tipo_crime', 'count'), 'Bairros Únicos': ('bairro', 'nunique')}))
        st.write("**Estatísticas por Nível de Risco:**")
        st.dataframe(stats, width='stretch')


def general_insights(df: pd.DataFrame) -> list[str]:
    """Frases-resumo sobre horário, concentração, diversidade e anomalias."""
    insights = []
    if 'hora' in df.columns and not has_constant_hour(df):
        peaks = df['hora'].value_counts().head(3).index
        insights.append(f"🕐 **Horários de pico:** {', '.join(f'{h}:00' for h in peaks)}")
    share_top3 = df['bairro'].value_counts().head(3).sum() / len(df) * 100
    insights.append(f"🏘️ **Concentração:** Top 3 bairros representam {share_top3:.1f}% dos crimes")
    diversity = df.groupby('bairro')['tipo_crime'].nunique().mean()
    insights.append(f"🎯 **Diversidade criminal:** Média de {diversity:.1f} tipos de crime por bairro")
    if 'anomalia' in df.columns:
        rate = (df['anomalia'] == -1).mean() * 100
        insights.append(f"🚨 **Taxa de anomalias:** {rate:.2f}% das ocorrências são atípicas")
    return insights


def _show_sample_table(df: pd.DataFrame) -> None:
    st.subheader("📋 Dados Filtrados (Amostra)")
    columns = ['data_ocorrencia', 'tipo_crime', 'bairro']
    columns += [c for c in ('nivel_risco', 'cluster') if c in df.columns]
    st.dataframe(df[columns].head(20), width='stretch')


def show_statistics_insights(df: pd.DataFrame) -> None:
    """Aba de estatísticas e insights"""
    st.header("📊 Estatísticas e Insights Gerais")
    if df.empty:
        st.warning("Nenhum dado disponível para análise estatística.")
        return

    _show_summary_metrics(df)
    col1, col2 = st.columns(2)
    with col1:
        _show_top_chart(df['tipo_crime'].value_counts(), "🏆 Top 10 Crimes Mais Frequentes",
                        "Crimes Mais Frequentes")
    with col2:
        _show_top_chart(df['bairro'].value_counts(), "🏘️ Top 10 Bairros Mais Afetados",
                        "Bairros Mais Afetados")
    if 'nivel_risco' in df.columns:
        _show_risk_distribution(df)

    st.subheader("🔍 Insights Avançados")
    for insight in general_insights(df):
        st.info(insight)
    _show_sample_table(df)
