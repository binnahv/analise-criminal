"""Dashboard de Violência Doméstica (Streamlit).

Execute com:  streamlit run dashboard_violencia_domestica.py
A lógica fica no pacote violencia_domestica/; aqui ficam a página e o main().
"""
from datetime import datetime

import pandas as pd
import streamlit as st

from violencia_domestica import (
    clean_geographic_data,
    load_violencia_domestica_data,
    create_sidebar_filters,
    apply_filters,
    COLUNAS_OBRIGATORIAS,
    mostrar_instrucoes_upload,
    preparar_dataset_upload,
    show_kpis,
    show_mapa_violencia,
    show_analise_temporal,
    show_perfil_suspeitos,
    show_efetividade_policial,
    show_modus_operandi,
    show_correlacoes,
    generate_html_report,
    show_clustering_analysis,
    show_anomaly_detection,
    show_supervised_model,
)

# Configuração da página
st.set_page_config(
    page_title="Dashboard Violência Doméstica - DEAM",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para violência doméstica
st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #8B0000 0%, #DC143C 100%);
    padding: 1.5rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}
.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid #DC143C;
    margin: 0.5rem 0;
}
.alert-box {
    background: #ffe6e6;
    border: 1px solid #ff9999;
    border-radius: 5px;
    padding: 1rem;
    margin: 1rem 0;
    color: #cc0000;
}
</style>
""", unsafe_allow_html=True)


def main():
    """Função principal do dashboard"""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>Dashboard de Violência Doméstica</h1>  
        <p><strong>Aluna:</strong> Sabrina Vidal</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Upload de dataset ou usar padrão
    st.sidebar.markdown("## Upload de Dataset")
    uploaded_file = st.sidebar.file_uploader(
        "Carregar arquivo CSV personalizado",
        type=['csv'],
        help="Opcional: carregue seu próprio dataset ou use o padrão"
    )
    mostrar_instrucoes_upload()

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.sidebar.success(f"Dataset carregado: {len(df)} registros")
            
            # Verificar se tem as colunas mínimas necessárias
            required_cols = [c for c, _ in COLUNAS_OBRIGATORIAS]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.sidebar.warning(f"Colunas faltantes: {', '.join(missing_cols)}")
                st.sidebar.info("Usando dataset padrão...")
                df = load_violencia_domestica_data()
            else:
                df = preparar_dataset_upload(df)
                if df.empty:
                    st.sidebar.warning("Nenhuma data válida em 'data_ocorrencia'. Usando dataset padrão...")
                    df = load_violencia_domestica_data()
                else:
                    st.sidebar.success("✅ Dataset compatível carregado!")
                
        except Exception as e:
            st.sidebar.error(f"Erro ao carregar arquivo: {str(e)}")
            df = load_violencia_domestica_data()
    else:
        df = load_violencia_domestica_data()
    
    if df.empty:
        st.error("Não foi possível carregar os dados.")
        return
    
    # Mostrar informações sobre os dados
    tipos_encontrados = df['tipo_crime'].value_counts()
    st.info(f"**Dataset carregado:** {len(df)} casos encontrados | Estupro: {tipos_encontrados.get('Estupro', 0)} | Ameaça: {tipos_encontrados.get('Ameaça', 0)} | Violência Doméstica: {tipos_encontrados.get('Violência Doméstica', 0)}")
    
    # Aplicar limpeza geográfica inicial para estatísticas
    df_clean_stats = clean_geographic_data(df)
    if len(df_clean_stats) < len(df):
        removidos = len(df) - len(df_clean_stats)
        st.warning(f"**Limpeza geográfica aplicada:** {removidos} casos com coordenadas inválidas foram identificados ({(removidos/len(df)*100):.1f}% do total)")
    
    # Filtros
    filters = create_sidebar_filters(df)
    df_filtered = apply_filters(df, filters)
    
    # Verificar se há dados após filtros
    if len(df_filtered) == 0:
        st.warning("Nenhum caso encontrado com os filtros aplicados. Ajuste os filtros.")
        return
    
    # KPIs
    show_kpis(df_filtered)
    
    # Abas principais
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "Mapa Geográfico",
        "Análise Temporal",
        "Perfil dos Suspeitos",
        "Efetividade Policial",
        "Modus Operandi",
        "Correlações",
        "Clusters (ML)",
        "Anomalias (ML)",
        "Modelo Supervisionado",
        "Dados Detalhados"
    ])
    
    with tab1:
        show_mapa_violencia(df_filtered)
    
    with tab2:
        show_analise_temporal(df_filtered)
    
    with tab3:
        show_perfil_suspeitos(df_filtered)
    
    with tab4:
        show_efetividade_policial(df_filtered)
    
    with tab5:
        show_modus_operandi(df_filtered)
    
    with tab6:
        show_correlacoes(df_filtered)
    
    with tab7:
        show_clustering_analysis(df_filtered)
    
    with tab8:
        show_anomaly_detection(df_filtered)
    
    with tab9:
        show_supervised_model(df_filtered)
    
    with tab10:
        st.subheader("Dados Detalhados")
        
        # Mostrar estatísticas resumidas
        st.markdown("### Resumo Estatístico")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Registros", len(df_filtered))
        with col2:
            st.metric("Bairros Únicos", df_filtered['bairro'].nunique())
        with col3:
            st.metric("Tipos de Violência", df_filtered['tipo_crime'].nunique())
        
        # Tabela de dados
        st.markdown("### Tabela de Casos")
        colunas_exibir = ['data_ocorrencia', 'tipo_crime', 'bairro']
        
        # Adicionar colunas opcionais se existirem
        if 'sexo_suspeito' in df_filtered.columns:
            colunas_exibir.append('sexo_suspeito')
        if 'status_caso' in df_filtered.columns:
            colunas_exibir.append('status_caso')
        if 'orgao_responsavel' in df_filtered.columns:
            colunas_exibir.append('orgao_responsavel')
        
        df_display = df_filtered[colunas_exibir].copy()
        df_display['data_ocorrencia'] = df_display['data_ocorrencia'].dt.strftime('%d/%m/%Y %H:%M')
        
        st.dataframe(
            df_display,
            width='stretch',
            height=400
        )
        
        # Opções de download
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                label="Baixar dados filtrados (CSV)",
                data=csv,
                file_name=f"violencia_domestica_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            if st.button("Gerar Relatório HTML"):
                html_report = generate_html_report(df_filtered)
                st.download_button(
                    label="Baixar Relatório HTML",
                    data=html_report,
                    file_name=f"relatorio_violencia_domestica_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html"
                )
    
    # Rodapé
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #666;'>Dashboard de Violência Doméstica - DEAM | Projeto Acadêmico</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
