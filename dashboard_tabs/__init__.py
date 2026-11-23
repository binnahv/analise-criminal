"""Funções de cada aba do dashboard principal (enhanced_app.py)."""
from .mapa import create_scatter_map
from .padroes import show_temporal_analysis, show_cluster_analysis, show_anomaly_analysis
from .previsao import show_risk_prediction
from .investigacao import show_investigative_performance, show_suspect_profile, PESOS_CRIME, PESOS_ARMA, calcular_indice_gravidade, show_gravity_index, show_modus_operandi_analysis
from .estatisticas import show_statistics_insights

__all__ = [
    'create_scatter_map',
    'show_temporal_analysis',
    'show_cluster_analysis',
    'show_anomaly_analysis',
    'show_risk_prediction',
    'show_investigative_performance',
    'show_suspect_profile',
    'PESOS_CRIME',
    'PESOS_ARMA',
    'calcular_indice_gravidade',
    'show_gravity_index',
    'show_modus_operandi_analysis',
    'show_statistics_insights',
]
