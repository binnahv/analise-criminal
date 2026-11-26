"""Utilitários de interface compartilhados pelos dois dashboards.

- Formatação de números no padrão brasileiro (3.482 e 33,7%).
- Exibição padronizada dos gráficos Plotly (títulos de eixo em português,
  sem barras de cor repetidas).
- Tratamento do horário constante do dataset da disciplina.
- Marca a página como português, para a tradução do navegador funcionar.
"""
import re
from numbers import Integral, Real
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

MESES_PT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
            'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

# Nomes de coluna que aparecem como título de eixo/legenda nos gráficos
NOMES_AMIGAVEIS = {
    'Taxa_Resolucao': 'Taxa de resolução (%)',
    'orgao_responsavel': 'Delegacia',
    'importance': 'Importância',
    'feature': 'Variável',
    'count': 'Quantidade',
    'mes_str': 'Mês',
    'descricao_modus_operandi': 'Modus operandi',
    'tipo_crime': 'Tipo de crime',
    'bairro': 'Bairro',
    'cluster': 'Cluster',
    'value': 'Quantidade',
    'index': '',
    'variable': '',
    'color': '',
}


def formatar_numero(valor: Any, casas: int = 1) -> Any:
    """3482 -> '3.482'; 33.7 -> '33,7'. Textos como '33.7%' viram '33,7%'."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, Integral):
        return f"{int(valor):,}".replace(",", ".")
    if isinstance(valor, Real):
        if float(valor).is_integer():
            return f"{int(valor):,}".replace(",", ".")
        texto = f"{float(valor):,.{casas}f}"
        return texto.replace(",", "§").replace(".", ",").replace("§", ".")
    # Já está no padrão brasileiro ('1.468', '3.482.000'): não mexe
    if isinstance(valor, str) and re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})+(,\d+)?%?", valor.strip()):
        return valor
    # Textos já formatados no padrão americano: '3,482', '+1,234', '33.7%', '1,234.5'
    if isinstance(valor, str) and re.fullmatch(r"[+-]?\d{1,3}(,\d{3})*(\.\d+)?%?|[+-]?\d+\.\d+%?",
                                               valor.strip()):
        return valor.replace(",", "§").replace(".", ",").replace("§", ".")
    return valor


def metrica_delta(delta: Any) -> Any:
    return formatar_numero(delta) if delta is not None else None


def metrica(label: str, value: Any, *args: Any, **kwargs: Any) -> None:
    """st.metric com o valor (e a variação, se houver) no formato brasileiro."""
    if args:
        args = (metrica_delta(args[0]),) + args[1:]
    if 'delta' in kwargs:
        kwargs['delta'] = metrica_delta(kwargs['delta'])
    st.metric(label, formatar_numero(value), *args, **kwargs)


def _eixo_numerico(fig: Any, eixo: str) -> bool:
    for trace in fig.data:
        valores = getattr(trace, eixo, None)
        if valores is None or len(valores) == 0:
            continue
        return pd.api.types.is_numeric_dtype(pd.Series(list(valores)))
    return False


def mostrar_grafico(fig: Any, **kwargs: Any) -> None:
    """Exibe um gráfico Plotly com títulos de eixo em português e sem a
    barra de cor quando ela só repete a informação do tamanho da barra."""
    # Em mapas de calor a escala de cor é a informação principal: mantém
    if not any(trace.type == 'heatmap' for trace in fig.data):
        fig.update_coloraxes(showscale=False)
    for eixo in ('x', 'y'):
        layout_eixo = fig.layout[f'{eixo}axis']
        titulo = layout_eixo.title.text if layout_eixo and layout_eixo.title else None
        if titulo in ('x', 'y'):
            novo = 'Número de ocorrências' if _eixo_numerico(fig, eixo) else ''
            fig.update_layout({f'{eixo}axis_title_text': novo})
        elif titulo in NOMES_AMIGAVEIS:
            fig.update_layout({f'{eixo}axis_title_text': NOMES_AMIGAVEIS[titulo]})
    legenda = fig.layout.legend.title.text if fig.layout.legend and fig.layout.legend.title else None
    if legenda in NOMES_AMIGAVEIS:
        fig.update_layout(legend_title_text=NOMES_AMIGAVEIS[legenda])
    fig.update_layout(separators=',.')  # vírgula decimal e ponto de milhar
    kwargs.setdefault('width', 'stretch')
    st.plotly_chart(fig, **kwargs)


def horario_constante(df: pd.DataFrame) -> bool:
    """True quando todas as ocorrências têm a mesma hora (caso do dataset da
    disciplina: todos os registros foram gerados às 19:48)."""
    return 'hora' in df.columns and df['hora'].dropna().nunique() <= 1 and len(df) > 1


def aviso_horario_constante(df: pd.DataFrame) -> None:
    hora = int(df['hora'].dropna().iloc[0]) if df['hora'].notna().any() else 0
    st.info(
        f"🕒 **Horário indisponível nestes dados.** Todas as ocorrências estão registradas "
        f"às {hora}h — mais uma inconsistência do dataset da disciplina, aparentemente intencional. "
        "Por isso a análise por hora foi substituída pela distribuição por **mês do ano**."
    )


def grafico_mes_do_ano(df: pd.DataFrame, titulo: str = "Ocorrências por mês do ano") -> None:
    """Barras com o total de ocorrências em cada mês (Jan a Dez), somando todos os anos."""
    contagem = df['data_ocorrencia'].dt.month.value_counts().reindex(range(1, 13), fill_value=0)
    fig = px.bar(x=MESES_PT, y=contagem.values, title=titulo,
                 labels={'x': 'Mês', 'y': 'Número de ocorrências'})
    mostrar_grafico(fig)
    mes_pico = int(contagem.idxmax())
    st.info(f"📅 **Mês com mais registros:** {MESES_PT[mes_pico - 1]} "
            f"({formatar_numero(int(contagem.max()))} ocorrências)")


def heatmap_mes_dia(df: pd.DataFrame, ordem_dias: list[str], titulo: str) -> None:
    """Mapa de calor Mês x Dia da semana (alternativa ao Hora x Dia)."""
    tabela = pd.crosstab(df['data_ocorrencia'].dt.month, df['dia_semana'])
    tabela = tabela.reindex(index=range(1, 13), columns=[d for d in ordem_dias if d in tabela.columns],
                            fill_value=0)
    fig = px.imshow(tabela.values, x=tabela.columns, y=MESES_PT, aspect='auto',
                    color_continuous_scale='Reds', title=titulo,
                    labels={'x': 'Dia da semana', 'y': 'Mês', 'color': 'Ocorrências'})
    fig.update_xaxes(tickangle=45)
    fig.update_layout(separators=',.')
    st.plotly_chart(fig, width='stretch')  # aqui a escala de cor é a informação principal


def definir_idioma_pt() -> None:
    """Marca o documento como pt-BR. O Streamlit declara a página como inglês,
    o que confunde a tradução automática do navegador."""
    components.html(
        "<script>try{window.parent.document.documentElement.lang='pt-BR';}catch(e){}</script>",
        height=0,
    )
