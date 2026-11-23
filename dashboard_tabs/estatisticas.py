"""Aba de estatísticas gerais e insights."""

import plotly.express as px
import streamlit as st


def show_statistics_insights(df):
    """Aba de estatísticas e insights"""
    st.header("📊 Estatísticas e Insights Gerais")
    
    if len(df) == 0:
        st.warning("Nenhum dado disponível para análise estatística.")
        return
    
    # Estatísticas gerais
    st.subheader("📈 Resumo Estatístico")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_crimes = len(df)
        st.metric("📊 Total de Crimes", f"{total_crimes:,}")
    
    with col2:
        unique_locations = df['bairro'].nunique() if 'bairro' in df.columns else 0
        st.metric("🏘️ Bairros Afetados", unique_locations)
    
    with col3:
        if 'data_ocorrencia' in df.columns:
            date_range = (df['data_ocorrencia'].max() - df['data_ocorrencia'].min()).days
            st.metric("📅 Período (dias)", date_range)
    
    with col4:
        crime_types = df['tipo_crime'].nunique() if 'tipo_crime' in df.columns else 0
        st.metric("🎯 Tipos de Crime", crime_types)
    
    # Análises detalhadas
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top 10 Crimes Mais Frequentes")
        if 'tipo_crime' in df.columns:
            top_crimes = df['tipo_crime'].value_counts().head(10)
            fig_top_crimes = px.bar(
                x=top_crimes.values,
                y=top_crimes.index,
                orientation='h',
                title="Crimes Mais Frequentes"
            )
            st.plotly_chart(fig_top_crimes, width='stretch')
    
    with col2:
        st.subheader("🏘️ Top 10 Bairros Mais Afetados")
        if 'bairro' in df.columns:
            top_bairros = df['bairro'].value_counts().head(10)
            fig_top_bairros = px.bar(
                x=top_bairros.values,
                y=top_bairros.index,
                orientation='h',
                title="Bairros Mais Afetados"
            )
            st.plotly_chart(fig_top_bairros, width='stretch')
    
    # Distribuição de risco
    if 'nivel_risco' in df.columns:
        st.subheader("⚠️ Distribuição por Nível de Risco")
        
        risk_dist = df['nivel_risco'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_risk_pie = px.pie(
                values=risk_dist.values,
                names=risk_dist.index,
                title="Distribuição de Níveis de Risco",
                color_discrete_map={
                    'Alto Risco': '#ff4444',
                    'Médio Risco': '#ffaa00',
                    'Baixo Risco': '#44ff44'
                }
            )
            st.plotly_chart(fig_risk_pie, width='stretch')
        
        with col2:
            # Tabela de estatísticas por risco
            risk_stats = df.groupby('nivel_risco').agg({
                'tipo_crime': 'count',
                'bairro': 'nunique'
            }).rename(columns={
                'tipo_crime': 'Total Ocorrências',
                'bairro': 'Bairros Únicos'
            })
            
            st.write("**Estatísticas por Nível de Risco:**")
            st.dataframe(risk_stats, width='stretch')
    
    # Correlações e insights
    st.subheader("🔍 Insights Avançados")
    
    insights = []
    
    # Análise temporal
    if 'hora' in df.columns:
        peak_hours = df['hora'].value_counts().head(3)
        insights.append(f"🕐 **Horários de pico:** {', '.join([f'{h}:00' for h in peak_hours.index])}")
    
    # Análise de concentração
    if 'bairro' in df.columns:
        top_3_bairros = df['bairro'].value_counts().head(3)
        total_top_3 = top_3_bairros.sum()
        percentage = (total_top_3 / len(df)) * 100
        insights.append(f"🏘️ **Concentração:** Top 3 bairros representam {percentage:.1f}% dos crimes")
    
    # Análise de diversidade criminal
    if 'tipo_crime' in df.columns and 'bairro' in df.columns:
        crime_diversity = df.groupby('bairro')['tipo_crime'].nunique().mean()
        insights.append(f"🎯 **Diversidade criminal:** Média de {crime_diversity:.1f} tipos de crime por bairro")
    
    # Análise de anomalias
    if 'anomalia' in df.columns:
        anomaly_rate = (len(df[df['anomalia'] == -1]) / len(df)) * 100
        insights.append(f"🚨 **Taxa de anomalias:** {anomaly_rate:.2f}% das ocorrências são atípicas")
    
    for insight in insights:
        st.info(insight)
    
    # Tabela de dados filtrados
    st.subheader("📋 Dados Filtrados (Amostra)")
    
    display_cols = ['data_ocorrencia', 'tipo_crime', 'bairro']
    if 'nivel_risco' in df.columns:
        display_cols.append('nivel_risco')
    if 'cluster' in df.columns:
        display_cols.append('cluster')
    
    st.dataframe(
        df[display_cols].head(20),
        width='stretch'
    )
