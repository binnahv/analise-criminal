"""Aba geográfica: mapa de pontos das ocorrências."""

import folium
import streamlit as st
from streamlit_folium import st_folium

from map_utils import new_folium_map


def create_scatter_map(df, show_anomalies):
    """Cria mapa com pontos individuais"""
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        st.error("Coordenadas não disponíveis nos dados.")
        return
    
    
    # Filtrar apenas coordenadas válidas para Recife
    from security_utils import DataValidator
    
    # Sempre usar validação específica por bairro quando possível
    if 'bairro' in df.columns:
        # Validação individual por bairro para cada linha
        valid_coords = df.apply(
            lambda row: DataValidator.validate_coordinates_by_neighborhood(
                row['latitude'], row['longitude'], row['bairro']
            ), 
            axis=1
        )
        bairros_unicos = df['bairro'].unique()
        if len(bairros_unicos) == 1:
            st.info(f"🎯 Usando validação específica para: {bairros_unicos[0]}")
        else:
            st.info(f"🎯 Usando validação específica para {len(bairros_unicos)} bairros: {', '.join(sorted(bairros_unicos))}")
    else:
        # Fallback para validação geral mais restritiva
        valid_coords = df.apply(
            lambda row: DataValidator.validate_coordinates(row['latitude'], row['longitude']), 
            axis=1
        )
        st.info("🎯 Usando validação geral (sem informação de bairro)")
    
    df_valid = df[valid_coords].copy()
    
    if len(df_valid) == 0:
        st.error("❌ Nenhuma coordenada válida encontrada para o Recife.")
        st.info("💡 Verifique se os dados contêm coordenadas da região metropolitana do Recife.")
        return
    
    # Mostrar estatísticas de limpeza
    removed_count = len(df) - len(df_valid)
    if removed_count > 0:
        st.warning(f"⚠️ {removed_count} pontos com coordenadas inválidas foram removidos do mapa.")
    
    center_lat = df_valid['latitude'].mean()
    center_lon = df_valid['longitude'].mean()
    
    m = new_folium_map([center_lat, center_lon], zoom_start=12)
    
    # Adicionar pontos normais (usando apenas coordenadas válidas)
    normal_data = df_valid[df_valid['anomalia'] != -1] if 'anomalia' in df_valid.columns else df_valid
    
    for _, row in normal_data.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=3,
            popup=f"{row.get('tipo_crime', 'N/A')} - {row.get('bairro', 'N/A')}",
            color='blue',
            fill=True,
            fillColor='blue'
        ).add_to(m)
    
    # Adicionar anomalias se solicitado (usando apenas coordenadas válidas)
    if show_anomalies and 'anomalia' in df_valid.columns:
        anomalies = df_valid[df_valid['anomalia'] == -1]
        for _, row in anomalies.iterrows():
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=6,
                popup=f"ANOMALIA: {row.get('tipo_crime', 'N/A')} - {row.get('bairro', 'N/A')}",
                color='red',
                fill=True,
                fillColor='red'
            ).add_to(m)
    
    st_folium(m, use_container_width=True, height=500)
