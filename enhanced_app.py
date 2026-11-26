import streamlit as st
import folium
from streamlit_folium import st_folium
from map_utils import new_folium_map
from ui import definir_idioma_pt, formatar_numero, horario_constante, metrica
from folium.plugins import HeatMap
import pydeck as pdk
from datetime import datetime
import os
from security_utils import SecurityManager, LGPDCompliance, DataValidator, show_model_limitations
from dashboard_tabs import (
    create_scatter_map, show_temporal_analysis, show_cluster_analysis,
    show_anomaly_analysis, show_risk_prediction, show_statistics_insights,
    show_investigative_performance, show_suspect_profile, show_gravity_index,
    show_modus_operandi_analysis
)

# Configuração da página
st.set_page_config(
    page_title="Sistema de Análise Criminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para melhor aparência
st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid #2a5298;
}
.warning-box {
    background: #fff3cd;
    border: 1px solid #ffeaa7;
    border-radius: 5px;
    padding: 1rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

class EnhancedCriminalDashboard:
    """Dashboard aprimorado para análise criminal"""

    def __init__(self):
        self.security_manager = SecurityManager()
        self.security_manager.ensure_default_user()  # cria o admin (e mostra a senha no terminal) na 1ª execução
        self.lgpd = LGPDCompliance()
        self.validator = DataValidator()

    def authenticate(self):
        """Sistema de autenticação"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False

        if not st.session_state.authenticated:
            st.markdown('<div class="main-header"><h1> Sistema de Análise Criminal</h1><p>Projeto acadêmico • dados fictícios</p></div>', unsafe_allow_html=True)

            with st.form("login_form"):
                st.subheader("🔐 Autenticação Necessária")
                username = st.text_input("Usuário")
                password = st.text_input("Senha", type="password")
                submit = st.form_submit_button("Entrar")

                if submit:
                    success, user_data = self.security_manager.authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = username
                        st.session_state.user_data = user_data
                        st.session_state.login_time = datetime.now()
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos")

            st.info("**Login de demonstração** — usuário: `admin`. A senha é exibida no terminal na primeira execução (ou definida em `ADMIN_PASSWORD`).")
            return False

        # Verificar timeout da sessão
        if self.security_manager.check_session_timeout():
            st.warning("Sessão expirada. Faça login novamente.")
            return False

        return True

    def load_data(self):
        """Carrega dados com cache e tratamento de erros"""
        try:
            # Tentar carregar dados seguros primeiro
            if os.path.exists('analysis_results_secure.pkl'):
                results = self.security_manager.load_encrypted_model('analysis_results_secure.pkl')
                return results['data'], results.get('silhouette_score', 0)

            # Fallback para dados não criptografados
            elif os.path.exists('analysis_results.pkl'):
                import pickle
                with open('analysis_results.pkl', 'rb') as f:
                    results = pickle.load(f)
                return results['data'], results.get('silhouette_score', 0)

            else:
                st.error("❌ Dados não encontrados. Execute primeiro o script de análise.")
                st.code("python advanced_analysis.py")
                return None, 0

        except Exception as e:
            st.error(f"Erro ao carregar dados: {str(e)}")
            return None, 0

    def create_sidebar_filters(self, df):
        """Cria filtros globais na sidebar"""
        st.sidebar.markdown("## Filtros Globais")

        # Filtro de data baseado no dataset
        if 'data_ocorrencia' in df.columns:
            # Filtrar apenas datas válidas (não futuras)
            today = datetime.now().date()
            df_valid_dates = df[df['data_ocorrencia'].dt.date <= today]

            if len(df_valid_dates) > 0:
                min_date = df_valid_dates['data_ocorrencia'].min().date()
                max_date = df_valid_dates['data_ocorrencia'].max().date()

                # Mostrar informações sobre o período
                st.sidebar.info(f"📊 Dataset: {min_date.strftime('%d/%m/%Y')} até {max_date.strftime('%d/%m/%Y')}")

                date_range = st.sidebar.date_input(
                    "Período de Análise", format='DD/MM/YYYY',
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=min(max_date, today),
                    help=f"Selecione o período para análise. Dataset contém dados de {min_date} até {max_date}"
                )
            else:
                st.sidebar.error("❌ Nenhuma data válida encontrada no dataset")
                date_range = (today, today)

        # Filtro de tipo de crime
        crime_types = sorted(df['tipo_crime'].unique().tolist())
        selected_crimes = st.sidebar.multiselect(
            " Tipos de Crime", placeholder='Selecione...',
            options=crime_types,
            default=[],  # Sem seleção padrão
            help="Deixe vazio para incluir todos os tipos"
        )

        # Filtro de bairros
        bairros = sorted(df['bairro'].unique().tolist())
        selected_bairros = st.sidebar.multiselect(
            " Bairros", placeholder='Selecione...',
            options=bairros,
            default=[],  # Sem seleção padrão
            help="Deixe vazio para incluir todos os bairros"
        )

        # Filtro de hora (escondido quando todas as ocorrências têm o mesmo horário)
        if horario_constante(df):
            hour_range = (0, 23)
            st.sidebar.caption(f"🕒 Filtro de horário indisponível: todas as ocorrências "
                               f"estão às {int(df['hora'].iloc[0])}h no dataset.")
        else:
            hour_range = st.sidebar.slider(
                "Horário",
                min_value=0,
                max_value=23,
                value=(0, 23),  # Todo o dia por padrão
                format="%d:00",
                help="Selecione a faixa horária de interesse"
            )

        # Filtro de dia da semana
        dias_semana = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
        selected_days = st.sidebar.multiselect(
            " Dias da Semana", placeholder='Selecione...',
            options=dias_semana,
            default=[],  # Sem seleção padrão
            help="Deixe vazio para incluir todos os dias"
        )



        return {
            'date_range': date_range,
            'crime_types': selected_crimes,
            'bairros': selected_bairros,
            'hour_range': hour_range,
            'days': selected_days
        }

    def filter_data(self, df, filters):
        """Aplica filtros aos dados"""
        df_filtered = df.copy()

        # Filtro de data
        if filters['date_range'] and len(filters['date_range']) == 2:
            start_date, end_date = filters['date_range']
            df_filtered = df_filtered[
                (df_filtered['data_ocorrencia'].dt.date >= start_date) &
                (df_filtered['data_ocorrencia'].dt.date <= end_date)
            ]

        # Filtro de crimes
        if filters['crime_types']:
            df_filtered = df_filtered[df_filtered['tipo_crime'].isin(filters['crime_types'])]

        # Filtro de bairros
        if filters['bairros']:
            df_filtered = df_filtered[df_filtered['bairro'].isin(filters['bairros'])]

        # Filtro de horário
        df_filtered = df_filtered[
            (df_filtered['hora'] >= filters['hour_range'][0]) &
            (df_filtered['hora'] <= filters['hour_range'][1])
        ]

        # Filtro de dias da semana
        if filters['days']:
            df_filtered = df_filtered[df_filtered['dia_semana'].isin(filters['days'])]


        return df_filtered

    def show_kpis(self, df, df_filtered):
        """Exibe KPIs principais"""
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            metrica(
                "📊 Total de Ocorrências",
                f"{len(df_filtered):,}",
                f"{len(df_filtered) - len(df):+,}" if len(df_filtered) != len(df) else None
            )

        with col2:
            anomalies = len(df_filtered[df_filtered['anomalia'] == -1]) if 'anomalia' in df_filtered.columns else 0
            metrica("🚨 Anomalias", f"{anomalies:,}")

        with col3:
            clusters = df_filtered['cluster'].nunique() if 'cluster' in df_filtered.columns else 0
            metrica("👥 Clusters Ativos", f"{clusters}")

        with col4:
            if 'nivel_risco' in df_filtered.columns:
                alto_risco = len(df_filtered[df_filtered['nivel_risco'] == 'Alto Risco'])
                metrica("⚠️ Alto Risco", f"{alto_risco:,}")
            else:
                metrica("⚠️ Alto Risco", "N/A")

        with col5:
            bairros_afetados = df_filtered['bairro'].nunique()
            metrica("🏘️ Bairros Afetados", f"{bairros_afetados}")

def main():
    """Função principal do dashboard"""
    definir_idioma_pt()
    dashboard = EnhancedCriminalDashboard()

    # Autenticação
    if not dashboard.authenticate():
        return

    # Header principal
    st.markdown('<div class="main-header"><h1> Sistema de Análise Criminal</h1><p>Aluna: Sabrina Vidal</p></div>', unsafe_allow_html=True)

    # Carregar dados
    df, sil_score = dashboard.load_data()
    if df is None:
        return

    # Mostrar avisos e limitações
    show_model_limitations()

    # Filtros na sidebar
    filters = dashboard.create_sidebar_filters(df)

    # Aplicar filtros
    df_filtered = dashboard.filter_data(df, filters)

    # Mostrar KPIs
    dashboard.show_kpis(df, df_filtered)

    # Verificar se há dados filtrados
    if len(df_filtered) == 0:
        st.warning("⚠️ Nenhuma ocorrência encontrada com os filtros aplicados.")
        return

    # Abas principais
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "  Geográfica",
        "  Temporal",
        "  Clusters",
        "  Anomalias",
        "  Previsão",
        "  Investigação",
        "  Perfil Suspeitos",
        "  Gravidade",
        "  Modus Operandi",
        "  Estatísticas"
    ])

    # Implementar cada aba
    with tab1:
        show_geographic_analysis(df_filtered, filters)

    with tab2:
        show_temporal_analysis(df_filtered)

    with tab3:
        show_cluster_analysis(df_filtered, sil_score)

    with tab4:
        show_anomaly_analysis(df_filtered)

    with tab5:
        show_risk_prediction()

    with tab6:
        show_investigative_performance(df_filtered)

    with tab7:
        show_suspect_profile(df_filtered)

    with tab8:
        show_gravity_index(df_filtered)

    with tab9:
        show_modus_operandi_analysis(df_filtered)

    with tab10:
        show_statistics_insights(df_filtered)


    # Logout
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()


def show_geographic_analysis(df, filters):
    """Aba de análise geográfica"""
    st.header("🌎 Análise Geográfica - Hotspots de Criminalidade")

    if len(df) == 0:
        st.warning("Nenhum dado disponível para visualização geográfica.")
        return

    # Valida as coordenadas uma única vez para todos os tipos de mapa
    if 'bairro' in df.columns:
        coerente = df.apply(
            lambda row: DataValidator.validate_coordinates_by_neighborhood(
                row['latitude'], row['longitude'], row['bairro']),
            axis=1)
    else:
        coerente = df.apply(
            lambda row: DataValidator.validate_coordinates(row['latitude'], row['longitude']),
            axis=1)
    n_coerentes = int(coerente.sum())

    # Opções de visualização
    col1, col2 = st.columns([3, 1])

    with col2:
        st.markdown("### Configurações do Mapa")

        map_type = st.selectbox(
            "Tipo de Mapa",
            ["Mapa de Calor", "Clusters", "Pontos Individuais", "Densidade 3D"]
        )

        incluir_inconsistentes = st.toggle(
            "Incluir coordenadas inconsistentes", False,
            help="Mostra também as ocorrências cuja coordenada não fica no bairro informado. "
                 "Útil para enxergar a inconsistência do dataset.")

        st.markdown("#### Opções de Visualização")

        show_anomalies_map = st.checkbox("Destacar Anomalias", True,
                                       help="Destacar ocorrências identificadas como anomalias")

        show_clusters_map = st.checkbox("Destacar Clusters", True,
                                      help="Destacar agrupamentos de crimes")

        show_only_anomalies = st.checkbox("Mostrar Apenas Anomalias", False,
                                        help="Filtrar apenas ocorrências anômalas")

    df_base = df if incluir_inconsistentes else df[coerente]
    no_mapa = len(df_base)

    with col1:
        m1, m2, m3 = st.columns(3)
        m1.metric("No mapa", formatar_numero(no_mapa))
        m2.metric("Total filtrado", formatar_numero(len(df)))
        m3.metric("Coordenadas coerentes", f"{formatar_numero(n_coerentes / len(df) * 100)}%")
        if incluir_inconsistentes:
            st.caption("⚠️ Exibindo **todas** as coordenadas, inclusive as que não batem com o bairro. "
                       "Repare que os pontos formam um retângulo regular: sinal de coordenadas "
                       "geradas aleatoriamente, e não de endereços reais.")
        else:
            st.caption(
                "ℹ️ O dataset da disciplina tem inconsistências (aparentemente intencionais): só parte das coordenadas fica "
                "dentro do bairro informado. O mapa mostra apenas os pontos coerentes. "
                "Ligue **Incluir coordenadas inconsistentes** para ver todos.")

        # Aplicar filtro de anomalias se selecionado
        df_map = df_base.copy()
        if show_only_anomalies and 'anomalia' in df_map.columns:
            df_map = df_map[df_map['anomalia'] == -1]
        if len(df_map) == 0:
            st.warning("⚠️ Nenhuma ocorrência para mostrar com as opções escolhidas.")
            return

        if map_type == "Mapa de Calor":
            create_heatmap(df_map, show_anomalies_map)
        elif map_type == "Clusters":
            create_cluster_map(df_map, show_anomalies_map, show_clusters_map)
        elif map_type == "Pontos Individuais":
            create_scatter_map(df_map, show_anomalies_map)
        else:  # Densidade 3D
            create_3d_density_map(df_map)

def create_heatmap(df, show_anomalies):
    """Cria mapa de calor"""
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        st.error("Coordenadas não disponíveis nos dados.")
        return

    df_valid = df.copy()  # coordenadas já filtradas na aba geográfica

    if len(df_valid) == 0:
        st.error("❌ Nenhuma coordenada válida encontrada para o Recife.")
        return


    # Centro do mapa (usando coordenadas válidas)
    center_lat = df_valid['latitude'].mean()
    center_lon = df_valid['longitude'].mean()

    # Criar mapa base
    m = new_folium_map([center_lat, center_lon], zoom_start=12, dark=True)

    # Dados para heatmap (usando coordenadas válidas)
    heat_data = [[row['latitude'], row['longitude']] for _, row in df_valid.iterrows()]

    # Adicionar heatmap
    HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(m)

    # Adicionar anomalias se solicitado (usando coordenadas válidas)
    if show_anomalies and 'anomalia' in df_valid.columns:
        anomalies = df_valid[df_valid['anomalia'] == -1]
        for _, row in anomalies.iterrows():
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=8,
                popup=f"Anomalia: {row.get('tipo_crime', 'N/A')} - {row.get('bairro', 'N/A')}",
                color='red',
                fill=True,
                fillColor='red'
            ).add_to(m)

    # Exibir mapa
    st_folium(m, use_container_width=True, height=500)

    st.caption("As áreas mais quentes indicam maior concentração de ocorrências.")

def create_cluster_map(df, show_anomalies, show_clusters=True):
    """Cria mapa com clusters"""
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        st.error("Coordenadas não disponíveis nos dados.")
        return

    df_valid = df.copy()  # coordenadas já filtradas na aba geográfica

    if len(df_valid) == 0:
        st.error("❌ Nenhuma coordenada válida encontrada para o Recife.")
        return


    center_lat = df_valid['latitude'].mean()
    center_lon = df_valid['longitude'].mean()

    m = new_folium_map([center_lat, center_lon], zoom_start=12, dark=True)

    # Cores para clusters
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen']

    if 'cluster' in df_valid.columns:
        for cluster_id in df_valid['cluster'].unique():
            if cluster_id == -1:  # Ruído no HDBSCAN
                continue

            cluster_data = df_valid[df_valid['cluster'] == cluster_id]
            color = colors[cluster_id % len(colors)]

            for _, row in cluster_data.iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=5,
                    popup=f"Cluster {cluster_id}: {row.get('tipo_crime', 'N/A')}",
                    color=color,
                    fill=True,
                    fillColor=color
                ).add_to(m)

    st_folium(m, use_container_width=True, height=500)

def create_3d_density_map(df):
    """Cria mapa 3D com PyDeck"""
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        st.error("Coordenadas não disponíveis nos dados.")
        return

    df_valid = df.copy()  # coordenadas já filtradas na aba geográfica

    if len(df_valid) == 0:
        st.error("❌ Nenhuma coordenada válida encontrada para o Recife.")
        return


    # Preparar dados (usando coordenadas válidas)
    df_map = df_valid[['latitude', 'longitude']].copy()
    df_map = df_map.dropna()

    # Configurar camada 3D
    layer = pdk.Layer(
        'HexagonLayer',
        df_map,
        get_position='[longitude, latitude]',
        radius=200,
        elevation_scale=4,
        elevation_range=[0, 1000],
        pickable=True,
        extruded=True,
    )

    # Configurar vista
    view_state = pdk.ViewState(
        longitude=df_map['longitude'].mean(),
        latitude=df_map['latitude'].mean(),
        zoom=11,
        pitch=50,
    )

    # Renderizar
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={'text': 'Concentração: {elevationValue}'}
    ))

if __name__ == "__main__":
    main()