"""Abas de padrões: análise temporal, clusters e anomalias."""

import plotly.express as px
import streamlit as st

from ui import show_constant_hour_notice, show_month_of_year_chart, show_month_weekday_heatmap, has_constant_hour, show_metric, show_chart


def show_temporal_analysis(df):
    """Aba de análise temporal"""
    st.header("🕒 Análise Temporal - Padrões de Criminalidade")

    if len(df) == 0:
        st.warning("Nenhum dado disponível para análise temporal.")
        return

    sem_horario = has_constant_hour(df)
    if sem_horario:
        show_constant_hour_notice(df)

    # Análise por hora do dia (ou por mês, se a hora for constante)
    col1, col2 = st.columns(2)

    with col1:
        if sem_horario:
            st.subheader("📊 Distribuição por Mês do Ano")
            show_month_of_year_chart(df)
        elif 'hora' in df.columns:
            st.subheader("📊 Distribuição por Hora do Dia")
            hourly_counts = df['hora'].value_counts().sort_index()

            fig_hour = px.bar(
                x=hourly_counts.index,
                y=hourly_counts.values,
                labels={'x': 'Hora do Dia', 'y': 'Número de Ocorrências'},
                title="Ocorrências por Hora"
            )
            fig_hour.update_layout(showlegend=False)
            show_chart(fig_hour)

            # Identificar pico
            peak_hour = hourly_counts.idxmax()
            st.info(f"🕐 **Pico de criminalidade:** {peak_hour}:00 com {hourly_counts[peak_hour]} ocorrências")

    with col2:
        st.subheader("📅 Distribuição por Dia da Semana")
        if 'dia_semana' in df.columns:
            day_order = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
            daily_counts = df['dia_semana'].value_counts().reindex(day_order).fillna(0)

            fig_day = px.bar(
                x=daily_counts.index,
                y=daily_counts.values,
                labels={'x': 'Dia da Semana', 'y': 'Número de Ocorrências'},
                title="Ocorrências por Dia da Semana"
            )
            fig_day.update_xaxes(tickangle=45)
            show_chart(fig_day)

            # Identificar dia mais crítico
            peak_day = daily_counts.idxmax()
            st.info(f"📅 **Dia mais crítico:** {peak_day} com {daily_counts[peak_day]} ocorrências")

    # Análise mensal
    if 'data_ocorrencia' in df.columns:
        st.subheader("📈 Evolução Temporal")

        df_temp = df.copy()
        df_temp['mes_ano'] = df_temp['data_ocorrencia'].dt.to_period('M')
        monthly_counts = df_temp['mes_ano'].value_counts().sort_index()

        fig_monthly = px.line(
            x=monthly_counts.index.astype(str),
            y=monthly_counts.values,
            labels={'x': 'Mês/Ano', 'y': 'Número de Ocorrências'},
            title="Evolução Mensal das Ocorrências"
        )
        show_chart(fig_monthly)
        st.caption("O primeiro e o último mês do período podem estar incompletos, "
                   "por isso a linha cai nas pontas.")

    # Heatmap de hora (ou mês) vs dia da semana
    if sem_horario and 'dia_semana' in df.columns:
        st.subheader("🔥 Mapa de Calor: Mês vs Dia da Semana")
        show_month_weekday_heatmap(df, ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira',
                             'sexta-feira', 'sábado', 'domingo'],
                        "Intensidade de Ocorrências por Mês e Dia da Semana")
    elif 'hora' in df.columns and 'dia_semana' in df.columns:
        st.subheader("🔥 Mapa de Calor: Hora vs Dia da Semana")

        pivot_data = df.pivot_table(
            values='tipo_crime',
            index='hora',
            columns='dia_semana',
            aggfunc='count',
            fill_value=0
        )

        # Reordenar colunas
        day_order = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
        pivot_data = pivot_data.reindex(columns=[d for d in day_order if d in pivot_data.columns])

        fig_heatmap = px.imshow(
            pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            aspect="auto",
            color_continuous_scale="Reds",
            title="Intensidade de Crimes por Hora e Dia da Semana"
        )
        fig_heatmap.update_xaxes(tickangle=45)
        show_chart(fig_heatmap)


def show_cluster_analysis(df, sil_score):
    """Aba de análise de clusters"""
    st.header("👥 Clusters de Ocorrências - Agrupamentos Semelhantes")

    if 'cluster' not in df.columns:
        st.warning("Dados de clusterização não disponíveis.")
        return

    # Informações gerais sobre clustering
    col1, col2, col3 = st.columns(3)

    with col1:
        n_clusters = df['cluster'].nunique()
        show_metric("🎯 Número de Clusters", n_clusters)

    with col2:
        show_metric("📊 Silhouette Score", f"{sil_score:.3f}")

    with col3:
        noise_points = len(df[df['cluster'] == -1]) if -1 in df['cluster'].values else 0
        show_metric("🔍 Pontos de Ruído", noise_points)

    # Seletor de cluster
    clusters_available = sorted([c for c in df['cluster'].unique() if c != -1])

    if clusters_available:
        selected_cluster = st.selectbox(
            "Selecione um Cluster para Análise Detalhada",
            options=clusters_available
        )

        # Análise do cluster selecionado
        cluster_data = df[df['cluster'] == selected_cluster]

        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"📋 Perfil do Cluster {selected_cluster}")
            st.write(f"**Total de Ocorrências:** {len(cluster_data)}")

            # Top crimes
            if 'tipo_crime' in cluster_data.columns:
                top_crimes = cluster_data['tipo_crime'].value_counts().head(5)
                st.write("**Principais Tipos de Crime:**")
                for crime, count in top_crimes.items():
                    percentage = (count / len(cluster_data)) * 100
                    st.write(f"• {crime}: {count} ({percentage:.1f}%)")

        with col2:
            st.subheader(f"🏘️ Localização do Cluster {selected_cluster}")

            # Top bairros
            if 'bairro' in cluster_data.columns:
                top_bairros = cluster_data['bairro'].value_counts().head(5)
                st.write("**Principais Bairros:**")
                for bairro, count in top_bairros.items():
                    percentage = (count / len(cluster_data)) * 100
                    st.write(f"• {bairro}: {count} ({percentage:.1f}%)")

        # Tabela de exemplos
        st.subheader("📄 Exemplos de Ocorrências do Cluster")
        display_cols = ['data_ocorrencia', 'tipo_crime', 'bairro']
        if 'descricao_modus_operandi' in cluster_data.columns:
            display_cols.append('descricao_modus_operandi')

        st.dataframe(
            cluster_data[display_cols].head(10),
            width='stretch'
        )

    # Visualização de todos os clusters
    st.subheader("📊 Comparação entre Clusters")

    # Gráfico de barras por cluster
    cluster_counts = df[df['cluster'] != -1]['cluster'].value_counts().sort_index()

    fig_clusters = px.bar(
        x=cluster_counts.index,
        y=cluster_counts.values,
        labels={'x': 'Cluster ID', 'y': 'Número de Ocorrências'},
        title="Distribuição de Ocorrências por Cluster"
    )
    show_chart(fig_clusters)


def show_anomaly_analysis(df):
    """Aba de análise de anomalias"""
    st.header("🚨 Ocorrências Atípicas - Alertas de Segurança")

    if 'anomalia' not in df.columns:
        st.warning("Dados de detecção de anomalias não disponíveis.")
        return

    anomalies = df[df['anomalia'] == -1]
    normal_cases = df[df['anomalia'] == 1]

    # KPIs de anomalias
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        show_metric("🚨 Total de Anomalias", len(anomalies))

    with col2:
        percentage = (len(anomalies) / len(df)) * 100 if len(df) > 0 else 0
        show_metric("📊 Percentual", f"{percentage:.2f}%")

    with col3:
        if len(anomalies) > 0:
            most_common_crime = anomalies['tipo_crime'].mode().iloc[0] if 'tipo_crime' in anomalies.columns else "N/A"
            show_metric("🎯 Crime Mais Comum", most_common_crime)

    with col4:
        if len(anomalies) > 0:
            most_affected_area = anomalies['bairro'].mode().iloc[0] if 'bairro' in anomalies.columns else "N/A"
            show_metric("🏘️ Área Mais Afetada", most_affected_area)

    if len(anomalies) == 0:
        st.info("✅ Nenhuma anomalia detectada nos dados filtrados.")
        return

    # Análise detalhada das anomalias
    st.subheader("🔍 Análise Detalhada das Anomalias")

    col1, col2 = st.columns(2)

    with col1:
        # Distribuição por tipo de crime
        if 'tipo_crime' in anomalies.columns:
            crime_dist = anomalies['tipo_crime'].value_counts()
            fig_crime = px.pie(
                values=crime_dist.values,
                names=crime_dist.index,
                title="Anomalias por Tipo de Crime"
            )
            show_chart(fig_crime)

    with col2:
        # Distribuição por bairro
        if 'bairro' in anomalies.columns:
            bairro_dist = anomalies['bairro'].value_counts().head(10)
            fig_bairro = px.bar(
                x=bairro_dist.values,
                y=bairro_dist.index,
                orientation='h',
                title="Top 10 Bairros com Anomalias"
            )
            show_chart(fig_bairro)

    # Tabela de anomalias
    st.subheader("📋 Lista de Anomalias Detectadas")

    # Filtros para anomalias
    col1, col2 = st.columns(2)

    with col1:
        if 'tipo_crime' in anomalies.columns:
            crime_filter = st.multiselect(
                "Filtrar por Tipo de Crime", placeholder='Selecione...',
                options=anomalies['tipo_crime'].unique(),
                default=anomalies['tipo_crime'].unique()[:3]
            )
            anomalies_filtered = anomalies[anomalies['tipo_crime'].isin(crime_filter)]
        else:
            anomalies_filtered = anomalies

    with col2:
        if 'bairro' in anomalies.columns:
            bairro_filter = st.multiselect(
                "Filtrar por Bairro", placeholder='Selecione...',
                options=anomalies['bairro'].unique(),
                default=anomalies['bairro'].unique()[:5]
            )
            anomalies_filtered = anomalies_filtered[anomalies_filtered['bairro'].isin(bairro_filter)]

    # Exibir tabela
    display_cols = ['data_ocorrencia', 'tipo_crime', 'bairro']
    if 'descricao_modus_operandi' in anomalies_filtered.columns:
        display_cols.append('descricao_modus_operandi')

    st.dataframe(
        anomalies_filtered[display_cols].sort_values('data_ocorrencia', ascending=False),
        width='stretch'
    )

    # Insights sobre anomalias
    st.subheader("💡 Insights sobre Anomalias")

    insights = []

    if len(anomalies) > 0:
        # Análise temporal
        if 'hora' in anomalies.columns and not has_constant_hour(anomalies):
            peak_hour = anomalies['hora'].mode().iloc[0]
            insights.append(f"🕐 Horário mais comum para anomalias: {peak_hour}:00")

        # Análise geográfica
        if 'bairro' in anomalies.columns:
            top_bairro = anomalies['bairro'].value_counts().index[0]
            count_bairro = anomalies['bairro'].value_counts().iloc[0]
            insights.append(f"🏘️ Bairro com mais anomalias: {top_bairro} ({count_bairro} casos)")

        # Comparação com casos normais
        if len(normal_cases) > 0 and 'tipo_crime' in df.columns:
            anomaly_crimes = set(anomalies['tipo_crime'].unique())
            normal_crimes = set(normal_cases['tipo_crime'].unique())
            unique_anomaly_crimes = anomaly_crimes - normal_crimes

            if unique_anomaly_crimes:
                insights.append(f"🎯 Crimes únicos em anomalias: {', '.join(unique_anomaly_crimes)}")

    for insight in insights:
        st.info(insight)
