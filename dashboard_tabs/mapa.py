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


    df_valid = df.copy()  # coordenadas já filtradas na aba geográfica

    if len(df_valid) == 0:
        st.error("❌ Nenhuma coordenada válida encontrada para o Recife.")
        st.info("💡 Verifique se os dados contêm coordenadas da região metropolitana do Recife.")
        return


    center_lat = df_valid['latitude'].mean()
    center_lon = df_valid['longitude'].mean()

    m = new_folium_map([center_lat, center_lon], zoom_start=12, dark=True)

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
