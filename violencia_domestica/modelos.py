"""Abas de Machine Learning: clustering, detecção de anomalias e modelo supervisionado.

Cada aba é dividida em duas partes:
- funções de cálculo (com @st.cache_data), que treinam os modelos uma vez para cada
  combinação de dados e parâmetros, em vez de a cada clique na página;
- funções de exibição pequenas, uma por seção da tela.
"""
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.cluster import DBSCAN, KMeans
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, silhouette_score
from sklearn.model_selection import GridSearchCV, cross_val_score, train_test_split
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import LabelEncoder, StandardScaler

from map_utils import apply_plotly_basemap
from ui import has_constant_hour, show_chart, show_metric

MIN_CASES_CLUSTERING = 10
MIN_CASES_ANOMALIES = 10
MIN_CASES_SUPERVISED = 20


def _with_hour(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'hora' not in df.columns:
        df['hora'] = df['data_ocorrencia'].dt.hour
    return df


def _is_night(hour: pd.Series) -> pd.Series:
    """Período noturno/madrugada: das 22h às 6h."""
    return (hour >= 22) | (hour <= 6)


# ============================================================ clustering
@st.cache_data(max_entries=20, show_spinner="Agrupando os casos...")
def _prepare_cluster_data(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Codifica as colunas categóricas e padroniza as variáveis usadas no clustering."""
    data = _with_hour(df)
    data['tipo_crime_encoded'] = LabelEncoder().fit_transform(data['tipo_crime'])
    data['bairro_encoded'] = LabelEncoder().fit_transform(data['bairro'])
    features = ['latitude', 'longitude', 'hora', 'tipo_crime_encoded', 'bairro_encoded']
    data = data.dropna(subset=features)
    scaled = StandardScaler().fit_transform(data[features].values) if len(data) else np.empty((0, 5))
    return data, scaled


@st.cache_data(max_entries=50, show_spinner=False)
def _run_kmeans(scaled: np.ndarray, n_clusters: int) -> tuple[np.ndarray, float]:
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(scaled)
    return labels, float(silhouette_score(scaled, labels))


@st.cache_data(max_entries=50, show_spinner=False)
def _run_dbscan(scaled: np.ndarray, eps: float, min_samples: int) -> dict[str, Any]:
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(scaled)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    mask = labels != -1
    silhouette = (float(silhouette_score(scaled[mask], labels[mask]))
                  if n_clusters > 1 and mask.sum() > 1 else None)
    return {'n_clusters': n_clusters, 'n_noise': int((labels == -1).sum()), 'silhouette': silhouette}


def _show_kmeans_section(data: pd.DataFrame, scaled: np.ndarray) -> pd.DataFrame:
    st.markdown("#### KMeans Clustering")
    n_clusters = st.slider("Número de Clusters", 2, min(8, len(data) // 2), 4)
    labels, silhouette = _run_kmeans(scaled, n_clusters)
    show_metric("Silhouette Score", f"{silhouette:.3f}")

    data = data.assign(cluster_kmeans=labels)
    fig = px.scatter_map(data, lat='latitude', lon='longitude', color='cluster_kmeans',
                         title="Clusters Geográficos (KMeans)", zoom=10, height=400)
    apply_plotly_basemap(fig)
    show_chart(fig)
    return data


def _show_dbscan_section(scaled: np.ndarray) -> None:
    st.markdown("#### DBSCAN Clustering")
    eps = st.slider("Epsilon (DBSCAN)", 0.1, 2.0, 0.5, 0.1)
    min_samples = st.slider("Min Samples", 2, 10, 3)
    result = _run_dbscan(scaled, eps, min_samples)
    show_metric("Clusters Encontrados", result['n_clusters'])
    show_metric("Pontos de Ruído", result['n_noise'])
    if result['silhouette'] is not None:
        show_metric("Silhouette Score", f"{result['silhouette']:.3f}")


def _show_cluster_profiles(data: pd.DataFrame, show_hour: bool) -> None:
    st.markdown("#### Características dos Clusters (KMeans)")
    for cluster_id, group in data.groupby('cluster_kmeans'):
        st.markdown(f"**Cluster {cluster_id} ({len(group)} casos):**")
        st.markdown(f"- Crime predominante: {group['tipo_crime'].mode().iloc[0]}")
        st.markdown(f"- Bairro predominante: {group['bairro'].mode().iloc[0]}")
        if show_hour:
            st.markdown(f"- Horário médio: {group['hora'].mean():.1f}h")


def _show_cluster_distribution(data: pd.DataFrame) -> None:
    st.markdown("#### Distribuição por Cluster")
    counts = data['cluster_kmeans'].value_counts().sort_index()
    show_chart(px.bar(x=counts.index, y=counts.values, title="Distribuição de Casos por Cluster",
                      labels={'x': 'Cluster', 'y': 'Número de Casos'}))
    summary = data.groupby('cluster_kmeans')[['hora', 'tipo_crime_encoded', 'bairro_encoded']].mean().round(2)
    show_chart(px.imshow(summary.T, title="Características Médias por Cluster",
                         color_continuous_scale='Blues'))


def _show_cluster_insights(data: pd.DataFrame, show_hour: bool) -> None:
    st.markdown("### Insights Operacionais dos Clusters")
    for cluster_id, group in data.groupby('cluster_kmeans'):
        if show_hour:
            mean_hour = group['hora'].mean()
            if mean_hour >= 22 or mean_hour <= 6:
                st.info(f"💡 Cluster {cluster_id}: Padrão noturno/madrugada - Reforçar patrulhamento noturno")
            elif 6 < mean_hour <= 12:
                st.info(f"💡 Cluster {cluster_id}: Padrão matinal - Monitoramento diurno")
        top = group['bairro'].value_counts()
        share = top.iloc[0] / len(group) * 100
        if share > 70:
            st.info(f"💡 Cluster {cluster_id}: Alta concentração em {top.index[0]} ({share:.1f}%) - Foco geográfico")


def show_clustering_analysis(df: pd.DataFrame) -> None:
    """Análise de Clusterização - Machine Learning Não Supervisionado"""
    st.subheader("Análise de Clusters - Agrupamento de Padrões Criminais")
    if len(df) < MIN_CASES_CLUSTERING:
        st.warning(f"Dados insuficientes para análise de clustering (mínimo {MIN_CASES_CLUSTERING} casos).")
        return

    data, scaled = _prepare_cluster_data(df)
    if len(data) < 5:
        st.error("Dados insuficientes após limpeza.")
        return

    col1, col2 = st.columns(2)
    with col1:
        data = _show_kmeans_section(data, scaled)
    with col2:
        _show_dbscan_section(scaled)

    show_hour = not has_constant_hour(data)
    st.markdown("---")
    st.markdown("### Interpretação dos Clusters")
    col1, col2 = st.columns(2)
    with col1:
        _show_cluster_profiles(data, show_hour)
    with col2:
        _show_cluster_distribution(data)

    st.markdown("---")
    _show_cluster_insights(data, show_hour)


# ============================================================ anomalias
@st.cache_data(max_entries=50, show_spinner="Procurando casos atípicos...")
def _detect_anomalies(df: pd.DataFrame, contamination: float, n_neighbors: int) -> pd.DataFrame:
    """Marca anomalias com Isolation Forest e LOF (-1 = anomalia, 1 = normal)."""
    data = _with_hour(df)
    data['tipo_crime_encoded'] = LabelEncoder().fit_transform(data['tipo_crime'])
    features = ['latitude', 'longitude', 'hora', 'tipo_crime_encoded']
    features += [c for c in ('quantidade_vitimas', 'quantidade_suspeitos') if c in data.columns]
    data = data.dropna(subset=features)
    if len(data) < 5:
        return data.iloc[0:0]
    scaled = StandardScaler().fit_transform(data[features].values)
    data['anomaly_iso'] = IsolationForest(contamination=contamination, random_state=42).fit_predict(scaled)
    lof = LocalOutlierFactor(n_neighbors=min(n_neighbors, len(data) - 1), contamination=contamination)
    data['anomaly_lof'] = lof.fit_predict(scaled)
    return data


def _show_anomaly_counts(data: pd.DataFrame, column: str) -> None:
    n = int((data[column] == -1).sum())
    show_metric("Anomalias Detectadas", n)
    show_metric("Taxa de Anomalias", f"{n / len(data) * 100:.1f}%")


def _show_anomaly_charts(data: pd.DataFrame, anomalies: pd.DataFrame, show_hour: bool) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Mapa de Anomalias (Isolation Forest)")
        fig = px.scatter_map(data, lat='latitude', lon='longitude', color='anomaly_iso',
                             title="Anomalias Geográficas", color_discrete_map={1: 'blue', -1: 'red'},
                             zoom=10, height=400)
        apply_plotly_basemap(fig)
        show_chart(fig)
    with col2:
        if show_hour:
            st.markdown("#### Distribuição Temporal das Anomalias")
            by_hour = anomalies['hora'].value_counts().sort_index()
            if len(by_hour):
                show_chart(px.bar(x=by_hour.index, y=by_hour.values, title="Anomalias por Hora do Dia",
                                  labels={'x': 'Hora', 'y': 'Número de Anomalias'}))
        else:
            st.markdown("#### Anomalias por Tipo de Crime")
            by_type = anomalies['tipo_crime'].value_counts()
            show_chart(px.bar(x=by_type.values, y=by_type.index, orientation='h',
                              title="Anomalias por Tipo de Crime"))


def _show_anomaly_details(anomalies: pd.DataFrame) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Características das Anomalias")
        st.markdown("**Tipos de crime mais anômalos:**")
        for crime, count in anomalies['tipo_crime'].value_counts().head(3).items():
            st.markdown(f"- {crime}: {count} casos ({count / len(anomalies) * 100:.1f}%)")
        st.markdown("**Bairros com mais anomalias:**")
        for bairro, count in anomalies['bairro'].value_counts().head(3).items():
            st.markdown(f"- {bairro}: {count} casos")
    with col2:
        st.markdown("#### Casos Anômalos Específicos")
        st.dataframe(anomalies[['data_ocorrencia', 'tipo_crime', 'bairro', 'hora']].head(5), width='stretch')
        st.markdown("**Possíveis razões para anomalias:**")
        st.markdown("- Horários incomuns para o tipo de crime\n- Localização atípica para o padrão\n"
                    "- Combinação incomum de características\n- Casos com múltiplas vítimas/suspeitos")


def _show_anomaly_recommendations(anomalies: pd.DataFrame, show_hour: bool) -> None:
    st.markdown("### Recomendações Operacionais")
    st.info("💡 **Investigação Prioritária:** Casos anômalos podem indicar padrões criminais "
            "emergentes ou situações de alto risco.")
    st.warning("⚠️ **Atenção Especial:** Monitorar locais e horários onde anomalias são frequentes.")
    if show_hour and _is_night(anomalies['hora']).mean() > 0.5:
        st.error("🌙 **Alerta Noturno:** Muitas anomalias no período noturno - Reforçar patrulhamento.")
    top = anomalies['bairro'].value_counts()
    if top.iloc[0] > len(anomalies) * 0.3:
        st.error(f"📍 **Alerta Geográfico:** Concentração de anomalias em {top.index[0]} - "
                 "Investigação especial necessária.")


def show_anomaly_detection(df: pd.DataFrame) -> None:
    """Detecção de Anomalias - Machine Learning Não Supervisionado"""
    st.subheader("Detecção de Anomalias - Casos Atípicos")
    if len(df) < MIN_CASES_ANOMALIES:
        st.warning(f"Dados insuficientes para detecção de anomalias (mínimo {MIN_CASES_ANOMALIES} casos).")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Isolation Forest")
        contamination = st.slider("Taxa de Contaminação", 0.05, 0.3, 0.1, 0.05)
    with col2:
        st.markdown("#### Local Outlier Factor")
        n_neighbors = st.slider("Número de Vizinhos", 5, 20, 10)

    data = _detect_anomalies(df, contamination, n_neighbors)
    if data.empty:
        st.error("Dados insuficientes após limpeza.")
        return
    with col1:
        _show_anomaly_counts(data, 'anomaly_iso')
    with col2:
        _show_anomaly_counts(data, 'anomaly_lof')

    anomalies = data[data['anomaly_iso'] == -1]
    show_hour = not has_constant_hour(data)
    st.markdown("---")
    st.markdown("### Visualização das Anomalias")
    _show_anomaly_charts(data, anomalies, show_hour)
    if anomalies.empty:
        return
    st.markdown("---")
    st.markdown("### Análise das Anomalias Detectadas")
    _show_anomaly_details(anomalies)
    st.markdown("---")
    _show_anomaly_recommendations(anomalies, show_hour)


# ============================================================ modelo supervisionado
TARGETS = {"Gravidade do Caso": "gravidade", "Tipo de Crime": "tipo_crime", "Uso de Arma": "arma_utilizada"}


def _add_severity_target(df: pd.DataFrame) -> pd.DataFrame:
    """Gravidade (Baixa/Média/Alta) calculada pela arma e pela quantidade de vítimas."""
    df = df.copy()
    score = pd.Series(0, index=df.index, dtype=float)
    if 'arma_utilizada' in df.columns:
        score += df['arma_utilizada'].map({'Arma de Fogo': 3, 'Faca': 2}).fillna(0)
    if 'quantidade_vitimas' in df.columns:
        score += df['quantidade_vitimas'] - 1
    # o score mínimo é -1 (0 vítimas e sem arma)
    df['gravidade'] = pd.cut(score, bins=[-2, 0, 2, 10], labels=['Baixa', 'Média', 'Alta'])
    return df


@st.cache_data(max_entries=30, show_spinner="Treinando o modelo...")
def _train_supervised_model(df: pd.DataFrame, target_label: str, test_size: float,
                            tune: bool) -> dict[str, Any]:
    """Treina um Random Forest e devolve modelo, métricas e dados de teste."""
    data = _with_hour(df)
    target = TARGETS[target_label]
    if target == 'gravidade':
        data = _add_severity_target(data)

    bairro_encoder = LabelEncoder().fit(data['bairro'])
    data['bairro_encoded'] = bairro_encoder.transform(data['bairro'])
    features = ['latitude', 'longitude', 'hora', 'bairro_encoded']
    # A quantidade de vítimas faz parte do cálculo da gravidade: usá-la como entrada
    # nesse caso seria vazamento de alvo (target leakage).
    if 'quantidade_vitimas' in data.columns and target != 'gravidade':
        features.append('quantidade_vitimas')

    data = data.dropna(subset=features + [target])
    if len(data) < 10:
        return {'ok': False}
    target_encoder = LabelEncoder()
    y = pd.Series(target_encoder.fit_transform(data[target].astype(str)), index=data.index)
    X_train, X_test, y_train, y_test = train_test_split(data[features], y, test_size=test_size,
                                                        random_state=42)
    if tune:
        grid = {'n_estimators': [50, 100, 200], 'max_depth': [3, 5, 10, None],
                'min_samples_split': [2, 5, 10]}
        search = GridSearchCV(RandomForestClassifier(random_state=42), grid, cv=3, scoring='accuracy')
        model = search.fit(X_train, y_train).best_estimator_
        best_params = search.best_params_
    else:
        model = RandomForestClassifier(n_estimators=100, random_state=42).fit(X_train, y_train)
        best_params = None

    y_pred = model.predict(X_test)
    test_rows = data.loc[X_test.index, ['bairro']].assign(y_true=y_test.values, y_pred=y_pred)
    return {
        'ok': True, 'model': model, 'features': features, 'best_params': best_params,
        'bairro_encoder': bairro_encoder, 'target_encoder': target_encoder,
        'bairros': sorted(data['bairro'].unique()),
        'accuracy': accuracy_score(y_test, y_pred),
        'baseline': DummyClassifier(strategy='most_frequent').fit(X_train, y_train).score(X_test, y_test),
        'cv_scores': cross_val_score(model, X_train, y_train, cv=5),
        'confusion': confusion_matrix(y_test, y_pred),
        'report': classification_report(y_test, y_pred, output_dict=True, zero_division=0),
        'test_rows': test_rows,
    }


def _show_training_metrics(result: dict[str, Any]) -> None:
    st.markdown("#### Treinamento do Modelo")
    if result['best_params']:
        st.success(f"Melhores parâmetros: {result['best_params']}")
    accuracy, baseline = result['accuracy'], result['baseline']
    show_metric("Acurácia", f"{accuracy:.3f}", delta=f"{accuracy - baseline:+.3f} vs. baseline")
    st.caption(f"Baseline (sempre a classe mais frequente): {baseline:.3f}. "
               "Se a acurácia não supera o baseline, o modelo não aprendeu padrão real.")
    show_metric("CV Score Médio", f"{result['cv_scores'].mean():.3f}")
    show_metric("CV Desvio Padrão", f"{result['cv_scores'].std():.3f}")


def _show_feature_importance(result: dict[str, Any]) -> None:
    st.markdown("#### Importância das Features")
    importance = pd.DataFrame({'feature': result['features'],
                               'importance': result['model'].feature_importances_})
    fig = px.bar(importance.sort_values('importance'), x='importance', y='feature', orientation='h',
                 title="Importância das Variáveis")
    show_chart(fig)


def _show_evaluation(result: dict[str, Any]) -> None:
    st.markdown("### Avaliação do Modelo")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Matriz de Confusão")
        show_chart(px.imshow(result['confusion'], title="Matriz de Confusão",
                             color_continuous_scale='Blues', text_auto=True))
    with col2:
        st.markdown("#### Relatório de Classificação")
        macro = result['report']['macro avg']
        show_metric("Precisão Macro", f"{macro['precision']:.3f}")
        show_metric("Recall Macro", f"{macro['recall']:.3f}")
        show_metric("F1-Score Macro", f"{macro['f1-score']:.3f}")


def _show_fairness(result: dict[str, Any]) -> None:
    st.markdown("### Análise de Fairness")
    rows = result['test_rows'].assign(erro=lambda d: (d['y_pred'] != d['y_true']).astype(int))
    error_by_bairro = rows.groupby('bairro')['erro'].mean().sort_values(ascending=False)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Erro por Bairro")
        show_chart(px.bar(x=error_by_bairro.values, y=error_by_bairro.index, orientation='h',
                          title="Taxa de Erro por Bairro"))
    with col2:
        st.markdown("#### Análise de Viés")
        high_error = error_by_bairro[error_by_bairro > rows['erro'].mean() * 1.5]
        if high_error.empty:
            st.success("✅ **Modelo aparenta ser justo entre bairros**")
            return
        st.warning("⚠️ **Possível viés detectado:**")
        for bairro, error in high_error.items():
            st.markdown(f"- {bairro}: {error:.1%} de erro")
        st.markdown("**Recomendações:**\n- Coletar mais dados desses bairros\n"
                    "- Revisar features específicas\n- Considerar balanceamento")


def _show_prediction_form(result: dict[str, Any]) -> None:
    st.markdown("### Predição em Tempo Real")
    features = result['features']
    with st.expander("Fazer Predição"):
        col1, col2, col3 = st.columns(3)
        with col1:
            lat = st.number_input("Latitude", value=-8.1)
            lon = st.number_input("Longitude", value=-34.9)
        with col2:
            hour = st.slider("Hora", 0, 23, 12)
            bairro = st.selectbox("Bairro", result['bairros'])
        with col3:
            victims = st.number_input("Quantidade de Vítimas", 0, 10, 1) if 'quantidade_vitimas' in features else 1

        if st.button("Fazer Predição"):
            values = [lat, lon, hour, result['bairro_encoder'].transform([bairro])[0]]
            if 'quantidade_vitimas' in features:
                values.append(victims)
            row = pd.DataFrame([values], columns=features)
            label = result['target_encoder'].inverse_transform(result['model'].predict(row))[0]
            st.success(f"**Predição:** {label}")
            st.info(f"**Confiança:** {result['model'].predict_proba(row)[0].max():.1%}")


def show_supervised_model(df: pd.DataFrame) -> None:
    """Modelo supervisionado com baseline, avaliação, fairness e predição."""
    st.subheader("Modelo Supervisionado - Predição e Análise")
    if len(df) < MIN_CASES_SUPERVISED:
        st.warning(f"Dados insuficientes para modelo supervisionado (mínimo {MIN_CASES_SUPERVISED} casos).")
        return

    st.markdown("### Configuração do Modelo")
    target_label = st.selectbox("Escolha o que prever:", list(TARGETS))
    if TARGETS[target_label] == 'gravidade':
        st.caption("ℹ️ `quantidade_vitimas` não é usada como entrada aqui porque faz parte "
                   "do cálculo da gravidade (evita vazamento de alvo).")
    test_size = st.slider("Tamanho do conjunto de teste", 0.1, 0.4, 0.2, 0.05)
    tune = st.checkbox("Tunagem de Hiperparâmetros", False)

    try:
        result = _train_supervised_model(df, target_label, test_size, tune)
    except ValueError as erro:  # ex.: poucas amostras por classe para a validação cruzada
        st.error(f"Não foi possível treinar o modelo com estes dados: {erro}")
        return
    if not result['ok']:
        st.error("Dados insuficientes após limpeza.")
        return

    col1, col2 = st.columns(2)
    with col1:
        _show_training_metrics(result)
    with col2:
        _show_feature_importance(result)
    st.markdown("---")
    _show_evaluation(result)
    st.markdown("---")
    _show_fairness(result)
    st.markdown("---")
    _show_prediction_form(result)
