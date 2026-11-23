"""Abas de investigação: desempenho das delegacias, perfil de suspeitos, índice de gravidade e modus operandi."""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


def show_investigative_performance(df):
    """Aba de desempenho investigativo"""
    st.header("👮 Desempenho Investigativo")
    
    if 'status_investigacao' not in df.columns or 'orgao_responsavel' not in df.columns:
        st.warning("Dados de investigação não disponíveis no dataset atual.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Taxa de Resolução por Delegacia")
        
        # Calcular taxa de resolução por delegacia
        delegacia_stats = df.groupby('orgao_responsavel').agg({
            'status_investigacao': ['count', lambda x: (x == 'Concluído').sum()]
        }).round(2)
        
        delegacia_stats.columns = ['Total_Casos', 'Casos_Concluidos']
        delegacia_stats['Taxa_Resolucao'] = (
            delegacia_stats['Casos_Concluidos'] / delegacia_stats['Total_Casos'] * 100
        ).round(1)
        
        # Gráfico de barras
        fig_resolucao = px.bar(
            delegacia_stats.reset_index(),
            x='orgao_responsavel',
            y='Taxa_Resolucao',
            title="Taxa de Resolução por Delegacia (%)",
            color='Taxa_Resolucao',
            color_continuous_scale='RdYlGn'
        )
        fig_resolucao.update_xaxes(tickangle=45)
        st.plotly_chart(fig_resolucao, width='stretch')
    
    with col2:
        st.subheader("📊 Volume de Casos por Delegacia")
        
        # Volume de casos
        volume_casos = df['orgao_responsavel'].value_counts()
        
        fig_volume = px.pie(
            values=volume_casos.values,
            names=volume_casos.index,
            title="Distribuição de Casos por Delegacia"
        )
        st.plotly_chart(fig_volume, width='stretch')
    
    # Tabela resumo
    st.subheader("📋 Resumo por Delegacia")
    delegacia_stats['Taxa_Resolucao'] = delegacia_stats['Taxa_Resolucao'].astype(str) + '%'
    st.dataframe(delegacia_stats, width='stretch')
    
    # Insights
    st.subheader("💡 Insights Investigativos")
    melhor_delegacia = delegacia_stats['Taxa_Resolucao'].str.rstrip('%').astype(float).idxmax()
    pior_delegacia = delegacia_stats['Taxa_Resolucao'].str.rstrip('%').astype(float).idxmin()
    
    st.success(f"🏆 **Melhor Performance:** {melhor_delegacia}")
    st.error(f"⚠️ **Necessita Atenção:** {pior_delegacia}")


def show_suspect_profile(df):
    """Aba de perfil dos suspeitos"""
    st.header("🔫 Perfil dos Suspeitos - Análise Demográfica")
    
    required_cols = ['idade_suspeito', 'sexo_suspeito', 'arma_utilizada', 'tipo_crime']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Colunas necessárias não encontradas no dataset: {', '.join(missing_cols)}")
        return

    if len(df) == 0:
        st.info("Nenhuma ocorrência nos filtros atuais.")
        return

    # Cópia para não alterar o DataFrame compartilhado entre as abas
    df = df.copy()
    df['genero_suspeito'] = df['sexo_suspeito']

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("👥 Distribuição por Gênero")
        genero_dist = df['genero_suspeito'].value_counts()
        
        fig_genero = px.pie(
            values=genero_dist.values,
            names=genero_dist.index,
            title="Suspeitos por Gênero",
            color_discrete_sequence=['#FF6B6B', '#4ECDC4']
        )
        st.plotly_chart(fig_genero, width='stretch')
    
    with col2:
        st.subheader("🎯 Faixa Etária")
        
        # Criar faixas etárias
        df['faixa_etaria'] = pd.cut(
            df['idade_suspeito'], 
            bins=[0, 18, 25, 35, 50, 100],
            labels=['<18', '18-25', '26-35', '36-50', '>50']
        )
        
        idade_dist = df['faixa_etaria'].value_counts()
        
        fig_idade = px.bar(
            x=idade_dist.index,
            y=idade_dist.values,
            title="Suspeitos por Faixa Etária",
            color=idade_dist.values,
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig_idade, width='stretch')
    
    with col3:
        st.subheader("🔫 Armas Utilizadas")
        arma_dist = df['arma_utilizada'].value_counts()
        
        fig_arma = px.bar(
            x=arma_dist.values,
            y=arma_dist.index,
            orientation='h',
            title="Tipos de Arma",
            color=arma_dist.values,
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_arma, width='stretch')
    
    # Análise cruzada
    st.subheader("🔍 Análise Cruzada: Crime vs Perfil")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Heatmap: Tipo de Crime vs Gênero
        crime_genero = pd.crosstab(df['tipo_crime'], df['genero_suspeito'])
        
        fig_heatmap1 = px.imshow(
            crime_genero.values,
            x=crime_genero.columns,
            y=crime_genero.index,
            title="Crime vs Gênero",
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_heatmap1, width='stretch')
    
    with col2:
        # Heatmap: Tipo de Crime vs Arma
        crime_arma = pd.crosstab(df['tipo_crime'], df['arma_utilizada'])
        
        fig_heatmap2 = px.imshow(
            crime_arma.values,
            x=crime_arma.columns,
            y=crime_arma.index,
            title="Crime vs Arma Utilizada",
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_heatmap2, width='stretch')
    
    # Insights
    st.subheader("💡 Insights do Perfil")
    
    genero_predominante = df['genero_suspeito'].mode()[0]
    faixa_predominante = df['faixa_etaria'].mode()[0]
    arma_predominante = df['arma_utilizada'].mode()[0]
    
    st.info(f"👤 **Perfil Típico:** {genero_predominante}, {faixa_predominante} anos, usando {arma_predominante}")
    
    # Estatísticas por tipo de crime
    crime_stats = df.groupby('tipo_crime').agg({
        'genero_suspeito': lambda x: x.mode()[0],
        'faixa_etaria': lambda x: x.mode()[0],
        'arma_utilizada': lambda x: x.mode()[0]
    })
    
    st.subheader("📊 Perfil por Tipo de Crime")
    st.dataframe(crime_stats, width='stretch')


# Pesos do índice de gravidade, alinhados aos valores que existem no dataset
PESOS_CRIME = {
    'Homicídio': 10, 'Latrocínio': 9, 'Sequestro': 8, 'Estupro': 8,
    'Roubo': 6, 'Violência Doméstica': 6, 'Tráfico de Drogas': 5,
    'Furto': 3, 'Estelionato': 2, 'Ameaça': 2
}


PESOS_ARMA = {
    'Explosivos': 5, 'Arma de Fogo': 5, 'Faca': 3,
    'Objeto Contundente': 2, 'Nenhum': 0
}


def calcular_indice_gravidade(df: pd.DataFrame) -> pd.Series:
    """Índice de gravidade = peso do crime + peso da arma + 2 x vítimas + suspeitos.
    Valores desconhecidos de crime/arma recebem peso 1."""
    return (
        df['tipo_crime'].map(PESOS_CRIME).fillna(1)
        + df['arma_utilizada'].map(PESOS_ARMA).fillna(1)
        + df['quantidade_vitimas'].fillna(0) * 2
        + df['quantidade_suspeitos'].fillna(0)
    )


def show_gravity_index(df):
    """Aba de índice de gravidade"""
    st.header("🧬 Índice de Gravidade dos Casos")
    
    st.info("💡 **Metodologia:** Índice calculado com base em: tipo de crime, arma utilizada, número de vítimas e suspeitos")

    required_cols = ['tipo_crime', 'arma_utilizada', 'quantidade_vitimas', 'quantidade_suspeitos', 'bairro']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"Colunas necessárias não encontradas no dataset: {', '.join(missing_cols)}")
        return

    if len(df) == 0:
        st.info("Nenhuma ocorrência nos filtros atuais.")
        return

    # Cópia para não alterar o DataFrame compartilhado entre as abas
    df = df.copy()

    df['indice_gravidade'] = calcular_indice_gravidade(df)
    
    # Classificar gravidade
    df['nivel_gravidade'] = pd.cut(
        df['indice_gravidade'],
        bins=[0, 10, 20, 100],
        labels=['Baixa', 'Média', 'Alta']
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🟢 Baixa Gravidade", 
                 len(df[df['nivel_gravidade'] == 'Baixa']),
                 f"{len(df[df['nivel_gravidade'] == 'Baixa'])/len(df)*100:.1f}%")
    
    with col2:
        st.metric("🟡 Média Gravidade", 
                 len(df[df['nivel_gravidade'] == 'Média']),
                 f"{len(df[df['nivel_gravidade'] == 'Média'])/len(df)*100:.1f}%")
    
    with col3:
        st.metric("🔴 Alta Gravidade", 
                 len(df[df['nivel_gravidade'] == 'Alta']),
                 f"{len(df[df['nivel_gravidade'] == 'Alta'])/len(df)*100:.1f}%")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribuição de Gravidade")
        
        gravidade_dist = df['nivel_gravidade'].value_counts()
        
        fig_gravidade = px.pie(
            values=gravidade_dist.values,
            names=gravidade_dist.index,
            title="Casos por Nível de Gravidade",
            color_discrete_sequence=['#2ECC71', '#F39C12', '#E74C3C']
        )
        st.plotly_chart(fig_gravidade, width='stretch')
    
    with col2:
        st.subheader("🗺️ Gravidade por Bairro")
        
        bairro_gravidade = df.groupby('bairro')['indice_gravidade'].mean().sort_values(ascending=False)
        
        fig_bairro = px.bar(
            x=bairro_gravidade.values[:10],
            y=bairro_gravidade.index[:10],
            orientation='h',
            title="Top 10 Bairros - Índice Médio de Gravidade",
            color=bairro_gravidade.values[:10],
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_bairro, width='stretch')
    
    # Casos de alta gravidade
    st.subheader("🚨 Casos de Alta Gravidade - Prioridade Investigativa")
    
    casos_alta = df[df['nivel_gravidade'] == 'Alta'].sort_values('indice_gravidade', ascending=False)
    
    if len(casos_alta) > 0:
        st.dataframe(
            casos_alta[['tipo_crime', 'bairro', 'arma_utilizada', 'quantidade_vitimas', 'indice_gravidade']].head(10),
            width='stretch'
        )
    else:
        st.info("Nenhum caso de alta gravidade encontrado nos filtros atuais.")


def show_modus_operandi_analysis(df):
    """Aba de análise de modus operandi"""
    st.header("📝 Análise de Modus Operandi - Padrões Criminais")
    
    if 'descricao_modus_operandi' not in df.columns:
        st.warning("Campo 'descricao_modus_operandi' não disponível no dataset.")
        st.info("Simulando análise de padrões textuais...")
        
        # Simular descrições para demonstração
        modus_exemplos = [
            "Golpe telefônico fingindo ser do banco",
            "Invasão de residência durante madrugada",
            "Furto de veículo em estacionamento",
            "Fraude online com cartão clonado",
            "Roubo em via pública com arma",
            "Estelionato por aplicativo falso",
            "Sequestro relâmpago no trânsito"
        ]
        
        np.random.seed(42)
        df['descricao_modus_operandi'] = np.random.choice(modus_exemplos, len(df))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔍 Padrões Mais Comuns")
        
        # Análise de frequência de padrões
        modus_freq = df['descricao_modus_operandi'].value_counts()
        
        fig_modus = px.bar(
            x=modus_freq.values,
            y=modus_freq.index,
            orientation='h',
            title="Modus Operandi Mais Frequentes",
            color=modus_freq.values,
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig_modus, width='stretch')
    
    with col2:
        st.subheader("📈 Evolução Temporal dos Padrões")
        
        if 'data_ocorrencia' in df.columns:
            # Converter para datetime e extrair ano-mês como string
            df['data_dt'] = pd.to_datetime(df['data_ocorrencia'])
            df['mes_str'] = df['data_dt'].dt.strftime('%Y-%m')
            
            # Top 3 modus operandi
            top_modus = modus_freq.head(3).index
            
            modus_temporal = df[df['descricao_modus_operandi'].isin(top_modus)].groupby(
                ['mes_str', 'descricao_modus_operandi']
            ).size().reset_index(name='count')
            
            # Ordenar por mês
            modus_temporal = modus_temporal.sort_values('mes_str')
            
            fig_temporal = px.line(
                modus_temporal,
                x='mes_str',
                y='count',
                color='descricao_modus_operandi',
                title="Evolução dos Principais Padrões"
            )
            fig_temporal.update_xaxes(tickangle=45)
            st.plotly_chart(fig_temporal, width='stretch')
        else:
            st.info("Campo 'data_ocorrencia' não disponível para análise temporal.")
    
    # Análise por bairro
    st.subheader("🗺️ Modus Operandi por Região")
    
    modus_bairro = pd.crosstab(df['bairro'], df['descricao_modus_operandi'])
    
    # Mostrar apenas top 5 bairros e top 5 modus operandi
    top_bairros = df['bairro'].value_counts().head(5).index
    top_modus_5 = modus_freq.head(5).index
    
    modus_bairro_filtered = modus_bairro.loc[top_bairros, top_modus_5]
    
    fig_heatmap = px.imshow(
        modus_bairro_filtered.values,
        x=modus_bairro_filtered.columns,
        y=modus_bairro_filtered.index,
        title="Modus Operandi vs Bairros (Top 5)",
        color_continuous_scale='Blues'
    )
    fig_heatmap.update_xaxes(tickangle=45)
    st.plotly_chart(fig_heatmap, width='stretch')
    
    # Insights e recomendações
    st.subheader("💡 Insights e Recomendações")
    
    modus_predominante = modus_freq.index[0]
    bairro_problema = df[df['descricao_modus_operandi'] == modus_predominante]['bairro'].mode()[0]
    
    insights = [
        f"🎯 **Padrão Dominante:** {modus_predominante} ({modus_freq.iloc[0]} casos)",
        f"🗺️ **Região Crítica:** {bairro_problema} concentra mais casos deste padrão",
        f"📊 **Diversidade:** {len(modus_freq)} padrões diferentes identificados",
        "⚠️ **Recomendação:** Focar operações preventivas no padrão dominante"
    ]
    
    for insight in insights:
        st.info(insight)
