"""Abas descritivas: KPIs, mapa, análise temporal, perfil dos suspeitos, efetividade policial, modus operandi e correlações."""

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from map_utils import new_folium_map

from .dados import clean_geographic_data


def show_kpis(df):
    """Exibe KPIs específicos para Polícia Civil"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_casos = len(df)
        st.metric("Total de Casos", f"{total_casos:,}")
    
    with col2:
        # Usar status_caso que é o campo mapeado corretamente
        if 'status_caso' in df.columns:
            casos_concluidos = len(df[df['status_caso'] == 'Concluído'])
            taxa_resolucao = (casos_concluidos / total_casos * 100) if total_casos > 0 else 0
            st.metric("Taxa de Resolução", f"{taxa_resolucao:.1f}%")
        else:
            st.metric("Taxa de Resolução", "N/A", help="Coluna 'status_caso' não disponível")
    
    with col3:
        casos_arma_fogo = len(df[df['arma_utilizada'] == 'Arma de Fogo']) if 'arma_utilizada' in df.columns else 0
        st.metric("Casos c/ Arma de Fogo", f"{casos_arma_fogo:,}")
    
    with col4:
        casos_multiplas_vitimas = len(df[df['quantidade_vitimas'] > 1]) if 'quantidade_vitimas' in df.columns else 0
        st.metric("Múltiplas Vítimas", f"{casos_multiplas_vitimas:,}")
    
    with col5:
        # Garantir que atualiza com os filtros aplicados
        delegacias_ativas = df['orgao_responsavel'].nunique() if 'orgao_responsavel' in df.columns and len(df) > 0 else 0
        st.metric("Delegacias Envolvidas", f"{delegacias_ativas:,}")


def show_mapa_violencia(df):
    """Exibe mapa específico de violência doméstica"""
    st.subheader("Distribuição Geográfica dos Casos")
    
    if len(df) == 0:
        st.warning("Nenhum caso encontrado com os filtros aplicados.")
        return
    
    # Aplicar limpeza geográfica
    df_clean = clean_geographic_data(df, show_info=True)
    
    if len(df_clean) == 0:
        st.error("Nenhuma coordenada válida encontrada após limpeza geográfica.")
        return
    
    # Informações dos dados filtrados
    if 'bairro' in df_clean.columns:
        bairros_unicos = df_clean['bairro'].unique()
        st.info(f"**Dados no mapa:** {len(df_clean)} ocorrências em {len(bairros_unicos)} bairro(s): {', '.join(sorted(bairros_unicos))}")
        
        # Verificar se há inconsistências geográficas
        if len(bairros_unicos) == 1:
            bairro_selecionado = bairros_unicos[0]
            coords_range = f"Lat: {df_clean['latitude'].min():.4f} a {df_clean['latitude'].max():.4f}, Lon: {df_clean['longitude'].min():.4f} a {df_clean['longitude'].max():.4f}"
            st.write(f"**Range de coordenadas para {bairro_selecionado}:** {coords_range}")
    else:
        st.info(f"**Dados no mapa:** {len(df_clean)} ocorrências")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### Opções do Mapa")
        tipo_mapa = st.selectbox(
            "Tipo de Visualização",
            ["Mapa de Calor", "Pontos por Tipo", "Clusters por Bairro"]
        )
        
        st.markdown("### Controles")
        if st.button("Atualizar Mapa", help="Força atualização do mapa com filtros atuais"):
            st.cache_data.clear()
            st.rerun()
        
        # Mostrar estatísticas de limpeza
        total_original = len(df)
        total_limpo = len(df_clean)
        removidos = total_original - total_limpo
        
        if removidos > 0:
            st.warning(f"**Dados removidos:** {removidos} de {total_original} ({(removidos/total_original*100):.1f}%)")
        else:
            st.success(f"**Todos os dados válidos:** {total_limpo} ocorrências")
    
    with col1:
        center_lat = df_clean['latitude'].mean()
        center_lon = df_clean['longitude'].mean()
        
        m = new_folium_map([center_lat, center_lon], zoom_start=12)
        
        if tipo_mapa == "Mapa de Calor":
            from folium.plugins import HeatMap
            heat_data = [[row['latitude'], row['longitude']] for _, row in df_clean.iterrows()]
            HeatMap(heat_data, radius=15, blur=10, gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'orange', 1: 'red'}).add_to(m)
        
        elif tipo_mapa == "Pontos por Tipo":
            cores_tipos = {
                'Estupro': 'red',
                'Violência Doméstica': 'darkred',
                'Ameaça': 'orange',
                'Lesão Corporal': 'purple',
                'Injúria': 'blue'
            }
            
            for _, row in df_clean.iterrows():
                cor = cores_tipos.get(row['tipo_crime'], 'gray')
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=6,
                    popup=f"<b>{row['tipo_crime']}</b><br>Bairro: {row['bairro']}<br>Data: {row['data_ocorrencia'].strftime('%d/%m/%Y') if pd.notna(row['data_ocorrencia']) else 'N/A'}",
                    color=cor,
                    fill=True,
                    fillColor=cor,
                    fillOpacity=0.7
                ).add_to(m)
        
        else:  # Clusters por Bairro
            from folium.plugins import MarkerCluster
            marker_cluster = MarkerCluster().add_to(m)
            
            for _, row in df_clean.iterrows():
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=f"<b>{row['tipo_crime']}</b><br>Bairro: {row['bairro']}",
                    icon=folium.Icon(color='red', icon='exclamation-sign')
                ).add_to(marker_cluster)
        
        st_folium(m, use_container_width=True, height=500)


def show_analise_temporal(df):
    """Análise temporal específica para violência doméstica"""
    st.subheader("Padrões Temporais da Violência Doméstica")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Distribuição por Hora do Dia")
        if 'hora' in df.columns:
            hourly_data = df['hora'].value_counts().sort_index()
            
            fig_hora = px.bar(
                x=hourly_data.index,
                y=hourly_data.values,
                title="Casos por Hora",
                labels={'x': 'Hora do Dia', 'y': 'Número de Casos'},
                color=hourly_data.values,
                color_continuous_scale='Reds'
            )
            fig_hora.update_layout(showlegend=False)
            st.plotly_chart(fig_hora, width='stretch')
            
            # Identificar horário crítico
            hora_pico = hourly_data.idxmax()
            st.info(f"**Horário mais crítico:** {hora_pico}:00 com {hourly_data[hora_pico]} casos")
    
    with col2:
        st.markdown("#### Distribuição por Dia da Semana")
        if 'dia_semana' in df.columns:
            dias_ordem = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
            daily_data = df['dia_semana'].value_counts().reindex(dias_ordem).fillna(0)
            
            fig_dia = px.bar(
                x=daily_data.index,
                y=daily_data.values,
                title="Casos por Dia da Semana",
                labels={'x': 'Dia da Semana', 'y': 'Número de Casos'},
                color=daily_data.values,
                color_continuous_scale='Reds'
            )
            fig_dia.update_xaxes(tickangle=45)
            st.plotly_chart(fig_dia, width='stretch')
            
            # Identificar dia crítico
            dia_pico = daily_data.idxmax()
            st.info(f"**Dia mais crítico:** {dia_pico} com {daily_data[dia_pico]} casos")


def show_perfil_suspeitos(df):
    """Análise do perfil dos suspeitos para Polícia Civil"""
    st.subheader("Perfil dos Suspeitos - Inteligência Policial")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Gênero dos Suspeitos")
        if 'sexo_suspeito' in df.columns:
            genero_suspeito = df['sexo_suspeito'].value_counts()
            
            fig_genero = px.pie(
                values=genero_suspeito.values,
                names=genero_suspeito.index,
                title="Suspeitos por Gênero",
                color_discrete_sequence=['#1f77b4', '#ff7f0e', '#d62728']
            )
            st.plotly_chart(fig_genero, width='stretch')
            
            # Insight policial
            if 'Masculino' in genero_suspeito.index:
                perc_masc = (genero_suspeito['Masculino'] / genero_suspeito.sum() * 100)
                st.info(f"**Insight:** {perc_masc:.1f}% dos suspeitos são do sexo masculino")
    
    with col2:
        st.markdown("#### Faixa Etária dos Suspeitos")
        if 'idade_suspeito' in df.columns:
            # Criar faixas etárias
            df_idade = df.dropna(subset=['idade_suspeito'])
            if len(df_idade) > 0:
                df_idade['faixa_etaria'] = pd.cut(
                    df_idade['idade_suspeito'], 
                    bins=[0, 18, 25, 35, 50, 100],
                    labels=['<18', '18-25', '26-35', '36-50', '>50']
                )
                
                idade_dist = df_idade['faixa_etaria'].value_counts()
                
                fig_idade = px.bar(
                    x=idade_dist.index,
                    y=idade_dist.values,
                    title="Suspeitos por Faixa Etária",
                    color=idade_dist.values,
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_idade, width='stretch')
                
                # Insight policial
                faixa_principal = idade_dist.idxmax()
                st.info(f"**Perfil predominante:** {faixa_principal} anos ({idade_dist[faixa_principal]} casos)")
    
    with col3:
        st.markdown("#### Quantidade de Suspeitos")
        if 'quantidade_suspeitos' in df.columns:
            qtd_suspeitos = df['quantidade_suspeitos'].value_counts().sort_index()
            
            fig_qtd = px.bar(
                x=qtd_suspeitos.index,
                y=qtd_suspeitos.values,
                title="Casos por Nº de Suspeitos",
                color=qtd_suspeitos.values,
                color_continuous_scale='Oranges'
            )
            st.plotly_chart(fig_qtd, width='stretch')
            
            # Insight policial
            casos_multiplos = len(df[df['quantidade_suspeitos'] > 1])
            perc_multiplos = (casos_multiplos / len(df) * 100) if len(df) > 0 else 0
            st.info(f"**Casos com múltiplos suspeitos:** {perc_multiplos:.1f}%")
    
    # Análise cruzada por tipo de crime
    st.markdown("---")
    st.markdown("### Análise por Tipo de Crime")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Perfil por Crime")
        if 'sexo_suspeito' in df.columns and 'tipo_crime' in df.columns:
            cross_tab = pd.crosstab(df['tipo_crime'], df['sexo_suspeito'], normalize='index') * 100
            
            fig_cross = px.imshow(
                cross_tab.values,
                x=cross_tab.columns,
                y=cross_tab.index,
                title="% Gênero do Suspeito por Tipo de Crime",
                color_continuous_scale='RdYlBu',
                text_auto='.1f'
            )
            st.plotly_chart(fig_cross, width='stretch')
    
    with col2:
        st.markdown("#### Idade Média por Crime")
        if 'idade_suspeito' in df.columns and 'tipo_crime' in df.columns:
            idade_media = df.groupby('tipo_crime')['idade_suspeito'].mean().sort_values(ascending=False)
            
            fig_idade_media = px.bar(
                x=idade_media.values,
                y=idade_media.index,
                orientation='h',
                title="Idade Média dos Suspeitos",
                color=idade_media.values,
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_idade_media, width='stretch')


def show_efetividade_policial(df):
    """Análise da efetividade das investigações policiais"""
    st.subheader("Efetividade Policial - Indicadores de Performance")
    
    # Isso Verifica se as colunas "necessárias" existem
    if 'status_caso' not in df.columns:
        st.warning("⚠️ Análise de efetividade não disponível: coluna 'status_caso' não encontrada no dataset.")
        st.info("💡 Para análise completa, o dataset deve conter as colunas: 'status_caso', 'orgao_responsavel'")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Taxa de Resolução Geral")
        status_counts = df['status_caso'].value_counts()
        total_casos = len(df)
        concluidos = status_counts.get('Concluído', 0)
        taxa_resolucao = (concluidos / total_casos * 100) if total_casos > 0 else 0
        
        st.metric("Taxa de Resolução", f"{taxa_resolucao:.1f}%")
        
        # O gráfico de status
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Status das Investigações",
            color_discrete_map={
                'Concluído': '#28a745',
                'Em Investigação': '#ffc107', 
                'Arquivado': '#dc3545'
            }
        )
        st.plotly_chart(fig_status, width='stretch')
    
    with col2:
        st.markdown("#### Performance por Delegacia")
        if 'orgao_responsavel' in df.columns:
            delegacia_stats = df.groupby('orgao_responsavel').agg({
                'status_caso': lambda x: (x == 'Concluído').sum() / len(x) * 100
            }).round(1)
            delegacia_stats.columns = ['Taxa_Resolucao']
            delegacia_stats = delegacia_stats.sort_values('Taxa_Resolucao', ascending=False)
            
            fig_delegacia = px.bar(
                x=delegacia_stats.values.flatten(),
                y=delegacia_stats.index,
                orientation='h',
                title="Taxa de Resolução por Delegacia (%)",
                color=delegacia_stats.values.flatten(),
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig_delegacia, width='stretch')
            
            # A melhor e pior delegacia
            if len(delegacia_stats) > 0:
                melhor = delegacia_stats.index[0]
                pior = delegacia_stats.index[-1]
                st.info(f"**Melhor:** {melhor} ({delegacia_stats.iloc[0,0]:.1f}%)")
                st.warning(f"**Precisa melhorar:** {pior} ({delegacia_stats.iloc[-1,0]:.1f}%)")
        else:
            st.warning("Coluna 'orgao_responsavel' não disponível")
    
    with col3:
        st.markdown("#### Efetividade por Tipo de Crime")
        crime_stats = df.groupby('tipo_crime').agg({
            'status_caso': lambda x: (x == 'Concluído').sum() / len(x) * 100
        }).round(1)
        crime_stats.columns = ['Taxa_Resolucao']
        crime_stats = crime_stats.sort_values('Taxa_Resolucao', ascending=False)
        
        fig_crime = px.bar(
            x=crime_stats.index,
            y=crime_stats.values.flatten(),
            title="Taxa de Resolução por Crime (%)",
            color=crime_stats.values.flatten(),
            color_continuous_scale='RdYlGn'
        )
        fig_crime.update_xaxes(tickangle=45)
        st.plotly_chart(fig_crime, width='stretch')


def show_modus_operandi(df):
    """Análise dos padrões de modus operandi"""
    st.subheader("Modus Operandi - Padrões Criminais")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Armas Utilizadas")
        if 'arma_utilizada' in df.columns:
            armas = df['arma_utilizada'].value_counts().head(8)
            
            fig_armas = px.bar(
                x=armas.values,
                y=armas.index,
                orientation='h',
                title="Tipos de Arma Mais Utilizados",
                color=armas.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_armas, width='stretch')
            
            # Insight sobre armas
            arma_principal = armas.index[0] if len(armas) > 0 else "N/A"
            casos_arma = armas.iloc[0] if len(armas) > 0 else 0
            st.info(f"**Arma predominante:** {arma_principal} ({casos_arma} casos)")
    
    with col2:
        st.markdown("#### Descrição do Modus Operandi")
        if 'descricao_modus_operandi' in df.columns:
            modus = df['descricao_modus_operandi'].value_counts().head(8)
            
            fig_modus = px.bar(
                x=modus.values,
                y=modus.index,
                orientation='h',
                title="Padrões de Modus Operandi",
                color=modus.values,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_modus, width='stretch')
            
            # Insight sobre modus
            modus_principal = modus.index[0] if len(modus) > 0 else "N/A"
            casos_modus = modus.iloc[0] if len(modus) > 0 else 0
            st.info(f"**Padrão predominante:** {modus_principal} ({casos_modus} casos)")
    
    # Análise cruzada
    st.markdown("---")
    st.markdown("### Correlação: Arma vs Tipo de Crime")
    
    if 'arma_utilizada' in df.columns and 'tipo_crime' in df.columns:
        # Criar tabela cruzada
        cross_arma_crime = pd.crosstab(df['tipo_crime'], df['arma_utilizada'])
        
        # Mostrar apenas as 5 armas mais comuns
        top_armas = df['arma_utilizada'].value_counts().head(5).index
        cross_filtered = cross_arma_crime[top_armas]
        
        fig_cross = px.imshow(
            cross_filtered.values,
            x=cross_filtered.columns,
            y=cross_filtered.index,
            title="Heatmap: Tipo de Crime vs Arma Utilizada",
            color_continuous_scale='Reds',
            text_auto=True
        )
        st.plotly_chart(fig_cross, width='stretch')
        
        # Insights operacionais
        st.markdown("#### Insights Operacionais:")
        for crime in df['tipo_crime'].unique():
            crime_data = df[df['tipo_crime'] == crime]
            if len(crime_data) > 0:
                arma_mais_usada = crime_data['arma_utilizada'].mode()
                if len(arma_mais_usada) > 0:
                    st.markdown(f"- **{crime}:** Arma predominante = {arma_mais_usada.iloc[0]}")


def show_correlacoes(df):
    """Análise de correlações e padrões"""
    st.subheader("Correlações e Padrões Criminais")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Vítimas vs Gravidade")
        if 'quantidade_vitimas' in df.columns and 'arma_utilizada' in df.columns:
            # Análise de múltiplas vítimas
            df_analise = df.copy()
            df_analise['multiplas_vitimas'] = df_analise['quantidade_vitimas'] > 1
            df_analise['arma_letal'] = df_analise['arma_utilizada'].isin(['Arma de Fogo', 'Faca'])
            
            cross_vitimas = pd.crosstab(df_analise['multiplas_vitimas'], df_analise['arma_letal'], normalize='index') * 100
            
            fig_vitimas = px.imshow(
                cross_vitimas.values,
                x=['Arma Não Letal', 'Arma Letal'],
                y=['Vítima Única', 'Múltiplas Vítimas'],
                title="% Uso de Arma Letal vs Nº de Vítimas",
                color_continuous_scale='Reds',
                text_auto='.1f'
            )
            st.plotly_chart(fig_vitimas, width='stretch')
    
    with col2:
        st.markdown("#### Sazonalidade por Crime")
        if 'data_ocorrencia' in df.columns:
            df_temp = df.copy()
            df_temp['mes'] = df_temp['data_ocorrencia'].dt.month
            
            sazonalidade = df_temp.groupby(['mes', 'tipo_crime']).size().unstack(fill_value=0)
            
            fig_sazon = px.line(
                sazonalidade,
                title="Sazonalidade dos Crimes por Mês",
                labels={'index': 'Mês', 'value': 'Número de Casos'}
            )
            st.plotly_chart(fig_sazon, width='stretch')
    
    # Indicadores de risco
    st.markdown("---")
    st.markdown("### Indicadores de Risco")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Casos com arma de fogo
        if 'arma_utilizada' in df.columns:
            casos_arma_fogo = len(df[df['arma_utilizada'] == 'Arma de Fogo'])
            perc_arma_fogo = (casos_arma_fogo / len(df) * 100) if len(df) > 0 else 0
            st.metric("Casos com Arma de Fogo", f"{casos_arma_fogo}", f"{perc_arma_fogo:.1f}%")
    
    with col2:
        # Casos com múltiplas vítimas
        if 'quantidade_vitimas' in df.columns:
            casos_multiplas = len(df[df['quantidade_vitimas'] > 1])
            perc_multiplas = (casos_multiplas / len(df) * 100) if len(df) > 0 else 0
            st.metric("Múltiplas Vítimas", f"{casos_multiplas}", f"{perc_multiplas:.1f}%")
    
    with col3:
        # Casos com múltiplos suspeitos
        if 'quantidade_suspeitos' in df.columns:
            casos_mult_susp = len(df[df['quantidade_suspeitos'] > 1])
            perc_mult_susp = (casos_mult_susp / len(df) * 100) if len(df) > 0 else 0
            st.metric("Múltiplos Suspeitos", f"{casos_mult_susp}", f"{perc_mult_susp:.1f}%")
