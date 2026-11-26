"""Aba de previsão: estimativa de ocorrência grave pelo modelo treinado."""
import os
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import plotly.express as px
import streamlit as st
from cryptography.fernet import InvalidToken

from security_utils import SecurityManager
from ui import MONTHS_PT, show_chart, show_metric

MODEL_FILE = 'risk_model_secure.pkl'
WEEKEND_DAYS = {'sábado', 'domingo'}

FEATURE_PREFIXES = {
    'bairro_': 'Bairro: ',
    'dia_semana_': 'Dia: ',
    'periodo_dia_': 'Período: ',
}
FEATURE_NAMES = {'mes': 'Mês', 'hora': 'Hora', 'fim_semana': 'Fim de semana',
                 'fim_semana_True': 'Fim de semana'}


def feature_label(column: str) -> str:
    """'dia_semana_terça-feira' -> 'Dia: terça-feira'; 'mes' -> 'Mês'."""
    if column in FEATURE_NAMES:
        return FEATURE_NAMES[column]
    for prefix, label in FEATURE_PREFIXES.items():
        if column.startswith(prefix):
            return label + column[len(prefix):]
    return column


def period_of_day(hour: int) -> str:
    """Mesma regra usada no treino (advanced_analysis._categorize_time_period)."""
    if 6 <= hour < 12:
        return 'Manhã'
    if 12 <= hour < 18:
        return 'Tarde'
    if 18 <= hour < 24:
        return 'Noite'
    return 'Madrugada'


def build_input_row(columns: list[str], bairro: str, weekday: str, hour: int, month: int) -> pd.DataFrame:
    """Monta a linha de entrada do modelo com todas as variáveis usadas no treino:
    bairro, dia da semana, hora, mês, período do dia e fim de semana."""
    row = pd.DataFrame(0, index=[0], columns=columns)
    for column in (f"bairro_{bairro}", f"dia_semana_{weekday}", f"periodo_dia_{period_of_day(hour)}"):
        if column in row.columns:
            row[column] = 1
    if 'hora' in row.columns:
        row['hora'] = hour
    if 'mes' in row.columns:
        row['mes'] = month
    is_weekend = weekday in WEEKEND_DAYS
    for column in ('fim_semana', 'fim_semana_True'):
        if column in row.columns:
            row[column] = int(is_weekend)
    return row


@st.cache_resource(max_entries=1, show_spinner=False)
def _load_model(modified_at: float) -> dict[str, Any]:
    """Carrega o modelo criptografado (o cache é renovado quando o arquivo muda)."""
    return SecurityManager().load_encrypted_model(MODEL_FILE)


def _get_model() -> Optional[dict[str, Any]]:
    if not os.path.exists(MODEL_FILE):
        st.error("❌ Modelo de previsão não encontrado. Rode `python advanced_analysis.py`.")
        return None
    try:
        return _load_model(os.path.getmtime(MODEL_FILE))
    except (InvalidToken, OSError) as erro:
        st.error(f"Não foi possível carregar o modelo ({type(erro).__name__}).")
        return None


def _show_estimate(model_data: dict[str, Any], row: pd.DataFrame) -> None:
    probability = float(model_data['model'].predict_proba(row)[0][1]) * 100
    st.subheader("📊 Resultado da Estimativa")
    metrics = model_data.get('metrics', {})
    col1, col2 = st.columns(2)
    with col1:
        show_metric("Probabilidade de ocorrência grave", f"{probability:.1f}%")
    with col2:
        if 'baseline_accuracy' in metrics:
            show_metric("Referência (baseline)", f"{(1 - metrics['baseline_accuracy']) * 100:.1f}%",
                        help="Proporção de ocorrências graves no conjunto de treino/teste.")
    if metrics:
        st.caption(
            f"Validação cruzada: acurácia {metrics['cv_accuracy']:.3f} | "
            f"baseline {metrics['baseline_accuracy']:.3f} | ROC AUC {metrics['cv_roc_auc']:.3f} "
            "(0,5 = acaso). Se a acurácia não supera o baseline e o AUC fica perto de 0,5, "
            "o modelo não encontrou padrão real nos dados.")


def _show_feature_importance(model_data: dict[str, Any]) -> None:
    model = model_data['model']
    if not hasattr(model, 'feature_importances_'):
        return
    st.subheader("📈 Importância das Variáveis")
    importance = (pd.DataFrame({'feature': model_data['model_columns'],
                                'importance': model.feature_importances_})
                  .sort_values('importance', ascending=False).head(10))
    importance['feature'] = importance['feature'].map(feature_label)
    fig = px.bar(importance, x='importance', y='feature', orientation='h',
                 title="Top 10 Variáveis Mais Importantes")
    fig.update_yaxes(categoryorder='total ascending')
    show_chart(fig)
    st.caption("Com o modelo no nível do acaso (ROC AUC ≈ 0,49), a importância "
               "das variáveis não indica um padrão real.")


def show_risk_prediction() -> None:
    """Aba de previsão de ocorrência grave."""
    st.header("🔮 Estimativa: ocorrência grave por local e horário")
    st.info("Modelo demonstrativo: estima a probabilidade de uma ocorrência ser um crime grave "
            "(homicídio, latrocínio, estupro ou sequestro) a partir de bairro, dia e hora. "
            "Como o dataset é fictício, o modelo tende a não superar o acaso; veja as métricas abaixo.")
    model_data = _get_model()
    if model_data is None:
        return

    st.subheader("🎯 Fazer Previsão de Risco")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        bairro = st.selectbox("Selecione o Bairro", options=sorted(model_data['bairros_list']))
    with col2:
        weekday = st.selectbox("Selecione o Dia da Semana", options=model_data['dias_semana_list'])
    with col3:
        month = st.selectbox("Selecione o Mês", options=range(1, 13), index=datetime.now().month - 1,
                             format_func=lambda m: MONTHS_PT[m - 1])
    with col4:
        hour = st.slider("Selecione a Hora", 0, 23, 19)
        st.caption("No dataset todas as ocorrências estão às 19h, então a hora "
                   "praticamente não altera a estimativa.")

    if st.button("🔮 Estimar probabilidade", type="primary"):
        _show_estimate(model_data, build_input_row(model_data['model_columns'], bairro, weekday, hour, month))
    _show_feature_importance(model_data)
