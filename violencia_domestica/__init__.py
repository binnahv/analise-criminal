"""Módulos do dashboard de Violência Doméstica (dashboard_violencia_domestica.py)."""
from .dados import clean_geographic_data, load_domestic_violence_data, create_sidebar_filters, apply_filters, UPLOAD_TEMPLATE_PATH, REQUIRED_COLUMNS, OPTIONAL_COLUMNS, show_upload_instructions, WEEKDAYS_PT, prepare_uploaded_dataset
from .graficos import show_kpis, show_violence_map, show_temporal_patterns, show_suspect_profiles, show_police_effectiveness, show_modus_operandi, show_correlations
from .relatorio import generate_html_report
from .modelos import show_clustering_analysis, show_anomaly_detection, show_supervised_model

__all__ = [
    'clean_geographic_data',
    'load_domestic_violence_data',
    'create_sidebar_filters',
    'apply_filters',
    'UPLOAD_TEMPLATE_PATH',
    'REQUIRED_COLUMNS',
    'OPTIONAL_COLUMNS',
    'show_upload_instructions',
    'WEEKDAYS_PT',
    'prepare_uploaded_dataset',
    'show_kpis',
    'show_violence_map',
    'show_temporal_patterns',
    'show_suspect_profiles',
    'show_police_effectiveness',
    'show_modus_operandi',
    'show_correlations',
    'generate_html_report',
    'show_clustering_analysis',
    'show_anomaly_detection',
    'show_supervised_model',
]
