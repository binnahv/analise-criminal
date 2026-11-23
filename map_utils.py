"""Utilitários de mapa: usa tiles gratuitos e sem chave de API.

Por que existe: o OpenStreetMap bloqueia o uso direto de seus tiles em apps
que não seguem a política de uso, e os tiles do CARTO agora exigem chave de API
(sem ela aparece a marca d'água "API KEY REQUIRED"). Por isso o mapa base padrão
é o Esri Light/Dark Gray Canvas, que não pede chave.

Para trocar de provedor sem mexer no código, defina variáveis de ambiente:
    MAP_TILE_URL  (ex.: https://exemplo.com/{z}/{x}/{y}.png)
    MAP_TILE_ATTR (texto de atribuição exigido pelo provedor)
"""
import os
from typing import Any

import folium

_ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/{name}/MapServer/tile/{{z}}/{{y}}/{{x}}"
_ATTR = "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
_NATIVE_ZOOM = 16  # o Esri Canvas não tem tiles acima do zoom 16


def tile_config(dark: bool = False) -> tuple[str, str]:
    """Retorna (url, atribuição) do mapa base."""
    url = os.getenv("MAP_TILE_URL")
    if url:
        return url, os.getenv("MAP_TILE_ATTR", "Map tiles")
    name = "World_Dark_Gray_Base" if dark else "World_Light_Gray_Base"
    return _ESRI.format(name=name), _ATTR


def new_folium_map(location: list[float], zoom_start: int = 12, dark: bool = False,
                   **kwargs: Any) -> folium.Map:
    """Cria um folium.Map com mapa base gratuito e sem chave."""
    url, attr = tile_config(dark)
    m = folium.Map(location=location, zoom_start=zoom_start, tiles=None,
                   max_zoom=18, **kwargs)
    folium.TileLayer(tiles=url, attr=attr, name="Mapa base",
                     max_native_zoom=_NATIVE_ZOOM, max_zoom=18).add_to(m)
    return m


def apply_plotly_basemap(fig: Any, dark: bool = False) -> Any:
    """Aplica o mesmo mapa base a uma figura do px.scatter_map (Plotly)."""
    url, attr = tile_config(dark)
    fig.update_layout(
        map_style="white-bg",
        map_layers=[{
            "below": "traces",
            "sourcetype": "raster",
            "sourceattribution": attr.replace("&copy;", "©").replace("&mdash;", "—"),
            "source": [url],
        }],
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )
    return fig
