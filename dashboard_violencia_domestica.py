"""Dashboard de Violência Doméstica (Streamlit).

Execute com:  streamlit run dashboard_violencia_domestica.py
A lógica fica no pacote violencia_domestica/; aqui ficam a página e o main().
"""
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from ui import set_page_language_pt, show_metric
from violencia_domestica import (
    REQUIRED_COLUMNS,
    apply_filters,
    create_sidebar_filters,
    generate_html_report,
    load_domestic_violence_data,
    prepare_uploaded_dataset,
    show_anomaly_detection,
    show_clustering_analysis,
    show_correlations,
    show_kpis,
    show_modus_operandi,
    show_police_effectiveness,
    show_supervised_model,
    show_suspect_profiles,
    show_temporal_patterns,
    show_upload_instructions,
    show_violence_map,
)

st.set_page_config(
    page_title="Dashboard Violência Doméstica - DEAM",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
</style>
""", unsafe_allow_html=True)

# Abas: nome -> função que desenha o conteúdo (a aba "Dados" é desenhada em _show_details_tab)
TABS = {
    "Mapa": show_violence_map,
    "Tempo": show_temporal_patterns,
    "Suspeitos": show_suspect_profiles,
    "Delegacias": show_police_effectiveness,
    "Modus Operandi": show_modus_operandi,
    "Correlações": show_correlations,
    "Clusters": show_clustering_analysis,
    "Anomalias": show_anomaly_detection,
    "Modelo": show_supervised_model,
}
DETAILS_TAB = "Dados"


def _read_uploaded_csv(uploaded_file) -> Optional[pd.DataFrame]:
    """Lê e valida o CSV enviado. Devolve None se não der para usar (e explica o motivo)."""
    try:
        df = pd.read_csv(uploaded_file)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as erro:
        st.sidebar.error(f"Não foi possível ler o arquivo: {erro}")
        return None
    st.sidebar.success(f"Dataset carregado: {len(df)} registros")

    missing = [column for column, _ in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        st.sidebar.warning(f"Colunas faltantes: {', '.join(missing)}")
        return None
    df = prepare_uploaded_dataset(df)
    if df.empty:
        st.sidebar.warning("Nenhuma data válida em 'data_ocorrencia'.")
        return None
    st.sidebar.success("✅ Dataset compatível carregado!")
    return df


def _load_dataset() -> pd.DataFrame:
    """Usa o CSV enviado pelo usuário, se for válido; senão, o dataset padrão."""
    st.sidebar.markdown("## Upload de Dataset")
    uploaded_file = st.sidebar.file_uploader(
        "Carregar arquivo CSV personalizado",
        type=['csv'],
        help="Opcional: carregue seu próprio dataset ou use o padrão"
    )
    show_upload_instructions()
    if uploaded_file is not None:
        df = _read_uploaded_csv(uploaded_file)
        if df is not None:
            return df
        st.sidebar.info("Usando dataset padrão...")
    return load_domestic_violence_data()


def _show_details_tab(df: pd.DataFrame) -> None:
    st.subheader("Dados Detalhados")
    st.markdown("### Resumo Estatístico")
    col1, col2, col3 = st.columns(3)
    with col1:
        show_metric("Total de Registros", len(df))
    with col2:
        show_metric("Bairros Únicos", df['bairro'].nunique())
    with col3:
        show_metric("Tipos de Violência", df['tipo_crime'].nunique())

    st.markdown("### Tabela de Casos")
    optional = [c for c in ('sexo_suspeito', 'status_caso', 'orgao_responsavel') if c in df.columns]
    table = df[['data_ocorrencia', 'tipo_crime', 'bairro'] + optional].copy()
    table['data_ocorrencia'] = table['data_ocorrencia'].dt.strftime('%d/%m/%Y %H:%M')
    st.dataframe(table, width='stretch', height=400)

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Baixar dados filtrados (CSV)", data=df.to_csv(index=False),
                           file_name=f"violencia_domestica_{stamp}.csv", mime="text/csv")
    with col2:
        if st.button("Gerar Relatório HTML"):
            st.download_button("Baixar Relatório HTML", data=generate_html_report(df),
                               file_name=f"relatorio_violencia_domestica_{stamp}.html", mime="text/html")


def main() -> None:
    """Monta a página: cabeçalho, dados, filtros, KPIs e abas."""
    set_page_language_pt()
    st.markdown("""
    <div class="main-header">
        <h1>Dashboard de Violência Doméstica</h1>
        <p><strong>Aluna:</strong> Sabrina Vidal</p>
    </div>
    """, unsafe_allow_html=True)

    df = _load_dataset()
    if df.empty:
        st.error("Não foi possível carregar os dados.")
        return

    counts = df['tipo_crime'].value_counts()
    st.info(f"**Dataset carregado:** {len(df)} casos encontrados | Estupro: {counts.get('Estupro', 0)} | "
            f"Ameaça: {counts.get('Ameaça', 0)} | Violência Doméstica: {counts.get('Violência Doméstica', 0)}")

    df_filtered = apply_filters(df, create_sidebar_filters(df))
    if df_filtered.empty:
        st.warning("Nenhum caso encontrado com os filtros aplicados. Ajuste os filtros.")
        return

    show_kpis(df_filtered)

    # Abas dinâmicas: só a aba aberta é calculada (as de ML são as mais pesadas)
    names = list(TABS) + [DETAILS_TAB]
    for name, tab in zip(names, st.tabs(names, on_change="rerun", key="aba_vd")):
        if not tab.open:
            continue
        with tab:
            if name == DETAILS_TAB:
                _show_details_tab(df_filtered)
            else:
                TABS[name](df_filtered)

    st.markdown("---")
    st.caption("Dashboard de Violência Doméstica - DEAM | Projeto Acadêmico")


if __name__ == "__main__":
    main()
