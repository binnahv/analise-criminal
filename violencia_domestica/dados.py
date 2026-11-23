"""Carregamento, validação e filtros dos dados de violência doméstica, incluindo o formato aceito no upload de CSV."""
import os

import pandas as pd
import streamlit as st

from security_utils import DataValidator


def clean_geographic_data(df: pd.DataFrame, show_info: bool = False) -> pd.DataFrame:
    """Limpa dados geográficos removendo coordenadas inválidas"""
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        return df
    
    # Aplicar validação geográfica
    if 'bairro' in df.columns:
        # Validação individual por bairro para cada linha
        valid_coords = df.apply(
            lambda row: DataValidator.validate_coordinates_flexible(
                row['latitude'], row['longitude'], row['bairro']
            ), 
            axis=1
        )
        
        removed_count = len(df) - valid_coords.sum()
        if removed_count > 0 and show_info:
            st.info(f"🧹 **Limpeza geográfica:** {removed_count} pontos com coordenadas inválidas foram removidos (longe do bairro informado ou fora do Recife)")
    else:
        # Sem bairro: aceita qualquer ponto dentro do Recife
        valid_coords = df.apply(
            lambda row: DataValidator.validate_coordinates_recife(row['latitude'], row['longitude']), 
            axis=1
        )
        
        removed_count = len(df) - valid_coords.sum()
        if removed_count > 0 and show_info:
            st.info(f"🧹 **Limpeza geográfica:** {removed_count} pontos com coordenadas inválidas foram removidos")
    
    return df[valid_coords].copy()


@st.cache_data
def load_violencia_domestica_data() -> pd.DataFrame:
    """Carrega e filtra dados específicos de violência doméstica"""
    try:
        # Carregar dataset completo
        df = pd.read_csv('data/dataset_ocorrencias_delegacia_5.csv')
        
        # Filtrar apenas casos específicos: Estupro, Ameaça e Violência Doméstica
        tipos_violencia_domestica = [
            'Violência Doméstica',
            'Estupro', 
            'Ameaça'
        ]
        
        # Filtrar dados
        df_vd = df[df['tipo_crime'].isin(tipos_violencia_domestica)].copy()
        
        # Verificar se encontrou dados
        if len(df_vd) == 0:
            st.error("❌ Nenhum caso de violência doméstica encontrado no dataset.")
            return pd.DataFrame()
        
        # Processar dados
        df_vd['data_ocorrencia'] = pd.to_datetime(df_vd['data_ocorrencia'], errors='coerce')
        df_vd['hora'] = df_vd['data_ocorrencia'].dt.hour
        df_vd['dia_semana'] = df_vd['data_ocorrencia'].dt.day_name()
        df_vd['mes'] = df_vd['data_ocorrencia'].dt.month
        df_vd['ano'] = df_vd['data_ocorrencia'].dt.year
        
        # Mapear dias da semana para português
        day_map = {
            'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira',
            'Wednesday': 'Quarta-feira', 'Thursday': 'Quinta-feira',
            'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        df_vd['dia_semana'] = df_vd['dia_semana'].map(day_map)
        
        # Observação: o dataset não tem dados da VÍTIMA (sexo ou idade).
        # Os filtros e tabelas usam apenas os campos do SUSPEITO, que existem nos dados.

        # Usar status real da investigação
        df_vd['status_caso'] = df_vd['status_investigacao']
        
        return df_vd
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


def create_sidebar_filters(df: pd.DataFrame) -> dict:
    """Cria filtros específicos para violência doméstica"""
    st.sidebar.markdown("## Filtros - Violência Doméstica")
    
    # Filtro por tipo de violência
    tipos_disponiveis = sorted(df['tipo_crime'].unique())
    tipos_selecionados = st.sidebar.multiselect(
        "Tipos de Violência",
        options=tipos_disponiveis,
        default=[],
        help="Selecione os tipos de violência para análise"
    )
    
    # Filtro por bairro
    bairros_disponiveis = sorted(df['bairro'].unique())
    bairros_selecionados = st.sidebar.multiselect(
        "Bairros",
        options=bairros_disponiveis,
        default=[],
        help="Selecione os bairros para análise"
    )
    
    # Filtro por sexo do suspeito (o dataset não informa o sexo da vítima)
    generos_selecionados = []
    if 'sexo_suspeito' in df.columns:
        generos_disponiveis = sorted(df['sexo_suspeito'].unique())
        generos_selecionados = st.sidebar.multiselect(
            "Sexo do Suspeito",
            options=generos_disponiveis,
            default=[]
        )
    
    # Filtro por status do caso (se disponível)
    status_selecionados = []
    if 'status_caso' in df.columns:
        status_disponiveis = sorted(df['status_caso'].unique())
        status_selecionados = st.sidebar.multiselect(
            "Status do Caso",
            options=status_disponiveis,
            default=[]
        )
    
    # Filtro por período - limitado ao range do dataset
    if not df['data_ocorrencia'].isna().all():
        min_date = df['data_ocorrencia'].min().date()
        max_date = df['data_ocorrencia'].max().date()
        
        st.sidebar.markdown(f"**Período disponível:** {min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')}")
        
        data_range = st.sidebar.date_input(
            "Período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    else:
        data_range = None
    
    return {
        'tipos': tipos_selecionados,
        'bairros': bairros_selecionados,
        'generos': generos_selecionados,
        'status': status_selecionados,
        'data_range': data_range
    }


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Aplica filtros aos dados"""
    df_filtered = df.copy()
    
    if filters['tipos']:
        df_filtered = df_filtered[df_filtered['tipo_crime'].isin(filters['tipos'])]
    
    if filters['bairros']:
        df_filtered = df_filtered[df_filtered['bairro'].isin(filters['bairros'])]
    
    if filters['generos'] and 'sexo_suspeito' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['sexo_suspeito'].isin(filters['generos'])]
    
    if filters['status'] and 'status_caso' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['status_caso'].isin(filters['status'])]
    
    if filters['data_range'] and len(filters['data_range']) == 2:
        start_date, end_date = filters['data_range']
        df_filtered = df_filtered[
            (df_filtered['data_ocorrencia'].dt.date >= start_date) &
            (df_filtered['data_ocorrencia'].dt.date <= end_date)
        ]
    
    return df_filtered


MODELO_UPLOAD = 'data/modelo_upload_violencia_domestica.csv'


# Colunas aceitas no upload: (nome, descrição/formato)
COLUNAS_OBRIGATORIAS = [
    ('data_ocorrencia', 'Data e hora: AAAA-MM-DD HH:MM:SS (sem hora, tudo cai em 0h)'),
    ('tipo_crime', 'Ex.: Violência Doméstica, Ameaça, Estupro'),
    ('bairro', 'Nome do bairro'),
    ('latitude', 'Número decimal com ponto, ex.: -8.112'),
    ('longitude', 'Número decimal com ponto, ex.: -34.897'),
]


COLUNAS_OPCIONAIS = [
    ('arma_utilizada', 'Nenhum, Faca, Arma de Fogo, Objeto Contundente, Explosivos'),
    ('quantidade_vitimas', 'Número inteiro'),
    ('quantidade_suspeitos', 'Número inteiro'),
    ('sexo_suspeito', 'Masculino, Feminino ou Não Informado'),
    ('idade_suspeito', 'Número inteiro'),
    ('status_investigacao', 'Ex.: Em Investigação, Concluído, Arquivado '
                            '(também aceita a coluna status_atendimento)'),
    ('orgao_responsavel', 'Delegacia/órgão responsável'),
    ('descricao_modus_operandi', 'Texto curto descrevendo o modus operandi'),
]


def mostrar_instrucoes_upload() -> None:
    """Mostra na barra lateral as colunas aceitas e o botão do CSV modelo."""
    with st.sidebar.expander("📋 Formato do CSV (colunas aceitas)"):
        st.markdown("**Obrigatórias**")
        st.markdown("\n".join(f"- `{c}`: {d}" for c, d in COLUNAS_OBRIGATORIAS))
        st.markdown("**Opcionais** (sem elas, algumas abas ficam limitadas)")
        st.markdown("\n".join(f"- `{c}`: {d}" for c, d in COLUNAS_OPCIONAIS))
        st.caption("Mapa: pontos dos 10 bairros do dataset original precisam estar perto do "
                   "centro do bairro; outros bairros são aceitos se estiverem dentro do Recife "
                   "(latitude -8,16 a -7,93; longitude -35,02 a -34,85).")
        if os.path.exists(MODELO_UPLOAD):
            with open(MODELO_UPLOAD, 'rb') as f:
                st.download_button("⬇️ Baixar CSV modelo", f.read(),
                                   file_name='modelo_upload_violencia_domestica.csv',
                                   mime='text/csv')


DIAS_SEMANA_PT = {
    'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira',
    'Wednesday': 'Quarta-feira', 'Thursday': 'Quinta-feira',
    'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
}


def preparar_dataset_upload(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza um CSV enviado pelo usuário para o formato que o dashboard espera.

    - Converte 'data_ocorrencia' para data SEMPRE. Não dá para checar
      `dtype == 'object'`: no pandas 3 colunas de texto têm o tipo `str`,
      e a conversão era pulada (erro "Can only use .dt accessor...").
    - Descarta linhas com data inválida e cria hora, dia da semana, mês e ano.
    - Usa 'status_investigacao' ou 'status_atendimento' como status do caso.
    """
    df = df.copy()
    df['data_ocorrencia'] = pd.to_datetime(df['data_ocorrencia'], errors='coerce')
    df = df.dropna(subset=['data_ocorrencia'])

    for col in ['latitude', 'longitude']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Colunas numéricas opcionais: textos como "Não informado" viram vazio (NaN).
    # Sem isso a coluna inteira fica como texto e cálculos como pd.cut quebram.
    for col in ['idade_suspeito', 'quantidade_vitimas', 'quantidade_suspeitos']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'hora' not in df.columns:
        df['hora'] = df['data_ocorrencia'].dt.hour
    if 'dia_semana' not in df.columns:
        df['dia_semana'] = df['data_ocorrencia'].dt.day_name().map(DIAS_SEMANA_PT)
    if 'mes' not in df.columns:
        df['mes'] = df['data_ocorrencia'].dt.month
    if 'ano' not in df.columns:
        df['ano'] = df['data_ocorrencia'].dt.year

    if 'status_caso' not in df.columns:
        for col in ['status_investigacao', 'status_atendimento']:
            if col in df.columns:
                df['status_caso'] = df[col]
                break

    return df
