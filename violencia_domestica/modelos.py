"""Abas de Machine Learning: clustering, detecção de anomalias e modelo supervisionado."""

import pandas as pd
import plotly.express as px
import streamlit as st

from map_utils import apply_plotly_basemap


def show_clustering_analysis(df):
    """Análise de Clusterização - Machine Learning Não Supervisionado"""
    st.subheader("Análise de Clusters - Agrupamento de Padrões Criminais")
    
    if len(df) < 10:
        st.warning("Dados insuficientes para análise de clustering (mínimo 10 casos).")
        return
    
    # Preparar dados para clustering
    try:
        from sklearn.cluster import KMeans, DBSCAN
        from sklearn.preprocessing import StandardScaler, LabelEncoder
        from sklearn.metrics import silhouette_score
        import numpy as np
        
        # Feature engineering
        df_cluster = df.copy()
        
        # Encoding de variáveis categóricas
        le_tipo = LabelEncoder()
        le_bairro = LabelEncoder()
        
        df_cluster['tipo_crime_encoded'] = le_tipo.fit_transform(df_cluster['tipo_crime'])
        df_cluster['bairro_encoded'] = le_bairro.fit_transform(df_cluster['bairro'])
        
        # Extrair hora se disponível
        if 'hora' in df_cluster.columns:
            features = ['latitude', 'longitude', 'hora', 'tipo_crime_encoded', 'bairro_encoded']
        else:
            df_cluster['hora'] = df_cluster['data_ocorrencia'].dt.hour
            features = ['latitude', 'longitude', 'hora', 'tipo_crime_encoded', 'bairro_encoded']
        
        # Remover NaN
        df_cluster = df_cluster.dropna(subset=features)
        
        if len(df_cluster) < 5:
            st.error("Dados insuficientes após limpeza.")
            return
        
        X = df_cluster[features].values
        
        # Normalizar dados
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### KMeans Clustering")
            
            # Determinar número ótimo de clusters
            n_clusters = st.slider("Número de Clusters", 2, min(8, len(df_cluster)//2), 4)
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters_kmeans = kmeans.fit_predict(X_scaled)
            
            # Silhouette Score
            silhouette_avg = silhouette_score(X_scaled, clusters_kmeans)
            st.metric("Silhouette Score", f"{silhouette_avg:.3f}")
            
            # Adicionar clusters ao dataframe
            df_cluster['cluster_kmeans'] = clusters_kmeans
            
            # Visualização dos clusters no mapa
            if 'latitude' in df_cluster.columns and 'longitude' in df_cluster.columns:
                fig_map = px.scatter_map(
                    df_cluster,
                    lat='latitude',
                    lon='longitude',
                    color='cluster_kmeans',
                    title="Clusters Geográficos (KMeans)",
                    zoom=10,
                    height=400
                )
                apply_plotly_basemap(fig_map)
                st.plotly_chart(fig_map, width='stretch')
        
        with col2:
            st.markdown("#### DBSCAN Clustering")
            
            eps = st.slider("Epsilon (DBSCAN)", 0.1, 2.0, 0.5, 0.1)
            min_samples = st.slider("Min Samples", 2, 10, 3)
            
            dbscan = DBSCAN(eps=eps, min_samples=min_samples)
            clusters_dbscan = dbscan.fit_predict(X_scaled)
            
            n_clusters_dbscan = len(set(clusters_dbscan)) - (1 if -1 in clusters_dbscan else 0)
            n_noise = list(clusters_dbscan).count(-1)
            
            st.metric("Clusters Encontrados", n_clusters_dbscan)
            st.metric("Pontos de Ruído", n_noise)
            
            if n_clusters_dbscan > 1:
                # Silhouette para DBSCAN (excluindo ruído)
                mask = clusters_dbscan != -1
                if np.sum(mask) > 1:
                    silhouette_dbscan = silhouette_score(X_scaled[mask], clusters_dbscan[mask])
                    st.metric("Silhouette Score", f"{silhouette_dbscan:.3f}")
        
        # Análise dos clusters
        st.markdown("---")
        st.markdown("### Interpretação dos Clusters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Características dos Clusters (KMeans)")
            
            for i in range(n_clusters):
                cluster_data = df_cluster[df_cluster['cluster_kmeans'] == i]
                
                if len(cluster_data) > 0:
                    st.markdown(f"**Cluster {i} ({len(cluster_data)} casos):**")
                    
                    # Tipo de crime predominante
                    tipo_predominante = cluster_data['tipo_crime'].mode()
                    if len(tipo_predominante) > 0:
                        st.markdown(f"- Crime predominante: {tipo_predominante.iloc[0]}")
                    
                    # Bairro predominante
                    bairro_predominante = cluster_data['bairro'].mode()
                    if len(bairro_predominante) > 0:
                        st.markdown(f"- Bairro predominante: {bairro_predominante.iloc[0]}")
                    
                    # Horário médio
                    if 'hora' in cluster_data.columns:
                        hora_media = cluster_data['hora'].mean()
                        st.markdown(f"- Horário médio: {hora_media:.1f}h")
                    
                    st.markdown("")
        
        with col2:
            st.markdown("#### Distribuição por Cluster")
            
            # Gráfico de distribuição
            cluster_dist = pd.Series(clusters_kmeans).value_counts().sort_index()
            
            fig_dist = px.bar(
                x=cluster_dist.index,
                y=cluster_dist.values,
                title="Distribuição de Casos por Cluster",
                labels={'x': 'Cluster', 'y': 'Número de Casos'}
            )
            st.plotly_chart(fig_dist, width='stretch')
            
            # Heatmap de características
            cluster_summary = df_cluster.groupby('cluster_kmeans').agg({
                'hora': 'mean',
                'tipo_crime_encoded': 'mean',
                'bairro_encoded': 'mean'
            }).round(2)
            
            fig_heatmap = px.imshow(
                cluster_summary.T,
                title="Características Médias por Cluster",
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_heatmap, width='stretch')
        
        # Insights operacionais
        st.markdown("---")
        st.markdown("### Insights Operacionais dos Clusters")
        
        insights = []
        
        for i in range(n_clusters):
            cluster_data = df_cluster[df_cluster['cluster_kmeans'] == i]
            
            if len(cluster_data) > 0:
                # Análise temporal
                if 'hora' in cluster_data.columns:
                    hora_media = cluster_data['hora'].mean()
                    if hora_media >= 22 or hora_media <= 6:
                        insights.append(f"Cluster {i}: Padrão noturno/madrugada - Reforçar patrulhamento noturno")
                    elif 6 < hora_media <= 12:
                        insights.append(f"Cluster {i}: Padrão matinal - Monitoramento diurno")
                
                # Análise geográfica
                bairros_cluster = cluster_data['bairro'].value_counts()
                if len(bairros_cluster) > 0:
                    bairro_principal = bairros_cluster.index[0]
                    concentracao = (bairros_cluster.iloc[0] / len(cluster_data)) * 100
                    if concentracao > 70:
                        insights.append(f"Cluster {i}: Alta concentração em {bairro_principal} ({concentracao:.1f}%) - Foco geográfico")
        
        for insight in insights:
            st.info(f"💡 {insight}")
    
    except ImportError:
        st.error("Bibliotecas de Machine Learning não instaladas. Execute: pip install scikit-learn")
    except Exception as e:
        st.error(f"Erro na análise de clustering: {str(e)}")


def show_anomaly_detection(df):
    """Detecção de Anomalias - Machine Learning Não Supervisionado"""
    st.subheader("Detecção de Anomalias - Casos Atípicos")
    
    if len(df) < 10:
        st.warning("Dados insuficientes para detecção de anomalias (mínimo 10 casos).")
        return
    
    try:
        from sklearn.ensemble import IsolationForest
        from sklearn.neighbors import LocalOutlierFactor
        from sklearn.preprocessing import StandardScaler, LabelEncoder
        import numpy as np
        
        # Preparar dados
        df_anomaly = df.copy()
        
        # Encoding
        le_tipo = LabelEncoder()
        le_bairro = LabelEncoder()
        
        df_anomaly['tipo_crime_encoded'] = le_tipo.fit_transform(df_anomaly['tipo_crime'])
        df_anomaly['bairro_encoded'] = le_bairro.fit_transform(df_anomaly['bairro'])
        
        # Features para detecção
        if 'hora' not in df_anomaly.columns:
            df_anomaly['hora'] = df_anomaly['data_ocorrencia'].dt.hour
        
        features = ['latitude', 'longitude', 'hora', 'tipo_crime_encoded']
        
        # Adicionar features se disponíveis
        if 'quantidade_vitimas' in df_anomaly.columns:
            features.append('quantidade_vitimas')
        if 'quantidade_suspeitos' in df_anomaly.columns:
            features.append('quantidade_suspeitos')
        
        df_anomaly = df_anomaly.dropna(subset=features)
        
        if len(df_anomaly) < 5:
            st.error("Dados insuficientes após limpeza.")
            return
        
        X = df_anomaly[features].values
        
        # Normalizar
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Isolation Forest")
            
            contamination = st.slider("Taxa de Contaminação", 0.05, 0.3, 0.1, 0.05)
            
            iso_forest = IsolationForest(contamination=contamination, random_state=42)
            anomalies_iso = iso_forest.fit_predict(X_scaled)
            
            df_anomaly['anomaly_iso'] = anomalies_iso
            
            n_anomalies_iso = np.sum(anomalies_iso == -1)
            st.metric("Anomalias Detectadas", n_anomalies_iso)
            st.metric("Taxa de Anomalias", f"{(n_anomalies_iso/len(df_anomaly)*100):.1f}%")
            
        with col2:
            st.markdown("#### Local Outlier Factor")
            
            n_neighbors = st.slider("Número de Vizinhos", 5, 20, 10)
            
            lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
            anomalies_lof = lof.fit_predict(X_scaled)
            
            df_anomaly['anomaly_lof'] = anomalies_lof
            
            n_anomalies_lof = np.sum(anomalies_lof == -1)
            st.metric("Anomalias Detectadas", n_anomalies_lof)
            st.metric("Taxa de Anomalias", f"{(n_anomalies_lof/len(df_anomaly)*100):.1f}%")
        
        # Visualização das anomalias
        st.markdown("---")
        st.markdown("### Visualização das Anomalias")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Mapa de Anomalias (Isolation Forest)")
            
            if 'latitude' in df_anomaly.columns and 'longitude' in df_anomaly.columns:
                fig_iso = px.scatter_map(
                    df_anomaly,
                    lat='latitude',
                    lon='longitude',
                    color='anomaly_iso',
                    title="Anomalias Geográficas",
                    color_discrete_map={1: 'blue', -1: 'red'},
                    zoom=10,
                    height=400
                )
                apply_plotly_basemap(fig_iso)
                st.plotly_chart(fig_iso, width='stretch')
        
        with col2:
            st.markdown("#### Distribuição Temporal das Anomalias")
            
            anomalies_by_hour = df_anomaly[df_anomaly['anomaly_iso'] == -1]['hora'].value_counts().sort_index()
            
            if len(anomalies_by_hour) > 0:
                fig_hour = px.bar(
                    x=anomalies_by_hour.index,
                    y=anomalies_by_hour.values,
                    title="Anomalias por Hora do Dia",
                    labels={'x': 'Hora', 'y': 'Número de Anomalias'}
                )
                st.plotly_chart(fig_hour, width='stretch')
        
        # Análise das anomalias
        st.markdown("---")
        st.markdown("### Análise das Anomalias Detectadas")
        
        anomalies_df = df_anomaly[df_anomaly['anomaly_iso'] == -1].copy()
        
        if len(anomalies_df) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Características das Anomalias")
                
                # Tipos de crime nas anomalias
                tipos_anomalias = anomalies_df['tipo_crime'].value_counts()
                st.markdown("**Tipos de crime mais anômalos:**")
                for tipo, count in tipos_anomalias.head(3).items():
                    perc = (count / len(anomalies_df)) * 100
                    st.markdown(f"- {tipo}: {count} casos ({perc:.1f}%)")
                
                # Bairros com anomalias
                bairros_anomalias = anomalies_df['bairro'].value_counts()
                st.markdown("**Bairros com mais anomalias:**")
                for bairro, count in bairros_anomalias.head(3).items():
                    st.markdown(f"- {bairro}: {count} casos")
            
            with col2:
                st.markdown("#### Casos Anômalos Específicos")
                
                # Mostrar alguns casos anômalos
                colunas_mostrar = ['data_ocorrencia', 'tipo_crime', 'bairro', 'hora']
                anomalies_sample = anomalies_df[colunas_mostrar].head(5)
                
                st.dataframe(anomalies_sample, width='stretch')
                
                # Insights sobre anomalias
                st.markdown("**Possíveis razões para anomalias:**")
                st.markdown("- Horários incomuns para o tipo de crime")
                st.markdown("- Localização atípica para o padrão")
                st.markdown("- Combinação incomum de características")
                st.markdown("- Casos com múltiplas vítimas/suspeitos")
        
        # Recomendações operacionais
        st.markdown("---")
        st.markdown("### Recomendações Operacionais")
        
        if len(anomalies_df) > 0:
            st.info("💡 **Investigação Prioritária:** Casos anômalos podem indicar padrões criminais emergentes ou situações de alto risco.")
            st.warning("⚠️ **Atenção Especial:** Monitorar locais e horários onde anomalias são frequentes.")
            
            # Alertas específicos
            if len(anomalies_df[anomalies_df['hora'].between(22, 6)]) > len(anomalies_df) * 0.5:
                st.error("🌙 **Alerta Noturno:** Muitas anomalias no período noturno - Reforçar patrulhamento.")
            
            bairros_criticos = anomalies_df['bairro'].value_counts()
            if len(bairros_criticos) > 0 and bairros_criticos.iloc[0] > len(anomalies_df) * 0.3:
                bairro_critico = bairros_criticos.index[0]
                st.error(f"📍 **Alerta Geográfico:** Concentração de anomalias em {bairro_critico} - Investigação especial necessária.")
    
    except ImportError:
        st.error("Bibliotecas de Machine Learning não instaladas. Execute: pip install scikit-learn")
    except Exception as e:
        st.error(f"Erro na detecção de anomalias: {str(e)}")


def show_supervised_model(df):
    """Modelo Supervisionado Aprimorado"""
    st.subheader("Modelo Supervisionado - Predição e Análise")
    
    if len(df) < 20:
        st.warning("Dados insuficientes para modelo supervisionado (mínimo 20 casos).")
        return
    
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
        from sklearn.preprocessing import LabelEncoder
        from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
        
        st.markdown("### Configuração do Modelo")
        
        # Seleção do target
        target_options = {
            "Gravidade do Caso": "gravidade",
            "Tipo de Crime": "tipo_crime",
            "Uso de Arma": "arma_utilizada"
        }
        
        target_choice = st.selectbox("Escolha o que prever:", list(target_options.keys()))
        target_column = target_options[target_choice]
        
        # Preparar dados
        df_model = df.copy()
        
        # Feature engineering
        if 'hora' not in df_model.columns:
            df_model['hora'] = df_model['data_ocorrencia'].dt.hour
        
        # Criar target baseado na escolha
        if target_choice == "Gravidade do Caso":
            # Criar score de gravidade
            df_model['gravidade_score'] = 0
            if 'arma_utilizada' in df_model.columns:
                df_model.loc[df_model['arma_utilizada'] == 'Arma de Fogo', 'gravidade_score'] += 3
                df_model.loc[df_model['arma_utilizada'] == 'Faca', 'gravidade_score'] += 2
            if 'quantidade_vitimas' in df_model.columns:
                df_model['gravidade_score'] += df_model['quantidade_vitimas'] - 1
            
            df_model['gravidade'] = pd.cut(
                df_model['gravidade_score'], 
                bins=[-2, 0, 2, 10],  # o score mínimo é -1 (0 vítimas e sem arma)
                labels=['Baixa', 'Média', 'Alta']
            )
            target_column = 'gravidade'
        
        # Features para o modelo
        features = ['latitude', 'longitude', 'hora']
        
        # Encoding de variáveis categóricas
        le_bairro = LabelEncoder()
        df_model['bairro_encoded'] = le_bairro.fit_transform(df_model['bairro'])
        features.append('bairro_encoded')
        
        # A quantidade de vítimas só entra como feature quando NÃO faz parte do alvo.
        # A "Gravidade do Caso" é calculada a partir dela, então usá-la como entrada
        # seria vazamento de alvo (target leakage).
        if 'quantidade_vitimas' in df_model.columns and target_choice != "Gravidade do Caso":
            features.append('quantidade_vitimas')
        else:
            st.caption("ℹ️ `quantidade_vitimas` não é usada como entrada aqui porque faz parte "
                       "do cálculo da gravidade (evita vazamento de alvo).")

        # Remover NaN
        df_model = df_model.dropna(subset=features + [target_column])

        if len(df_model) < 10:
            st.error("Dados insuficientes após limpeza.")
            return

        # Preparar X e y
        X = df_model[features]
        le_target = LabelEncoder()
        y = pd.Series(le_target.fit_transform(df_model[target_column].astype(str)),
                      index=df_model.index)

        # Split dos dados
        test_size = st.slider("Tamanho do conjunto de teste", 0.1, 0.4, 0.2, 0.05)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Treinamento do Modelo")
            
            # Opções de tunagem
            tune_hyperparams = st.checkbox("Tunagem de Hiperparâmetros", False)
            
            if tune_hyperparams:
                st.info("Executando Grid Search...")
                
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [3, 5, 10, None],
                    'min_samples_split': [2, 5, 10]
                }
                
                rf = RandomForestClassifier(random_state=42)
                grid_search = GridSearchCV(rf, param_grid, cv=3, scoring='accuracy')
                grid_search.fit(X_train, y_train)
                
                best_model = grid_search.best_estimator_
                st.success(f"Melhores parâmetros: {grid_search.best_params_}")
            else:
                best_model = RandomForestClassifier(n_estimators=100, random_state=42)
                best_model.fit(X_train, y_train)
            
            # Predições
            y_pred = best_model.predict(X_test)
            
            # Métricas
            accuracy = accuracy_score(y_test, y_pred)

            # Baseline: sempre prever a classe mais frequente
            from sklearn.dummy import DummyClassifier
            baseline_acc = DummyClassifier(strategy='most_frequent').fit(X_train, y_train).score(X_test, y_test)

            st.metric("Acurácia", f"{accuracy:.3f}",
                      delta=f"{accuracy - baseline_acc:+.3f} vs. baseline")
            st.caption(f"Baseline (sempre a classe mais frequente): {baseline_acc:.3f}. "
                       "Se a acurácia não supera o baseline, o modelo não aprendeu padrão real.")
            
            # Cross-validation
            cv_scores = cross_val_score(best_model, X_train, y_train, cv=5)
            st.metric("CV Score Médio", f"{cv_scores.mean():.3f}")
            st.metric("CV Desvio Padrão", f"{cv_scores.std():.3f}")
        
        with col2:
            st.markdown("#### Importância das Features")
            
            feature_importance = pd.DataFrame({
                'feature': features,
                'importance': best_model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            fig_importance = px.bar(
                feature_importance,
                x='importance',
                y='feature',
                orientation='h',
                title="Importância das Variáveis"
            )
            st.plotly_chart(fig_importance, width='stretch')
        
        # Matriz de confusão
        st.markdown("---")
        st.markdown("### Avaliação do Modelo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Matriz de Confusão")
            
            cm = confusion_matrix(y_test, y_pred)
            fig_cm = px.imshow(
                cm,
                title="Matriz de Confusão",
                color_continuous_scale='Blues',
                text_auto=True
            )
            st.plotly_chart(fig_cm, width='stretch')
        
        with col2:
            st.markdown("#### Relatório de Classificação")
            
            report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
            
            # Mostrar métricas principais
            st.metric("Precisão Macro", f"{report['macro avg']['precision']:.3f}")
            st.metric("Recall Macro", f"{report['macro avg']['recall']:.3f}")
            st.metric("F1-Score Macro", f"{report['macro avg']['f1-score']:.3f}")
        
        # Análise de Fairness
        st.markdown("---")
        st.markdown("### Análise de Fairness")
        
        if 'bairro' in df_model.columns:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Erro por Bairro")
                
                # Calcular erro por bairro
                df_test = df_model.loc[X_test.index].copy()
                df_test['y_pred'] = y_pred
                df_test['y_true'] = y_test.values
                df_test['erro'] = (df_test['y_pred'] != df_test['y_true']).astype(int)
                
                erro_por_bairro = df_test.groupby('bairro')['erro'].mean().sort_values(ascending=False)
                
                fig_fairness = px.bar(
                    x=erro_por_bairro.values,
                    y=erro_por_bairro.index,
                    orientation='h',
                    title="Taxa de Erro por Bairro"
                )
                st.plotly_chart(fig_fairness, width='stretch')
            
            with col2:
                st.markdown("#### Análise de Viés")
                
                # Verificar se há viés significativo
                erro_medio = df_test['erro'].mean()
                bairros_alto_erro = erro_por_bairro[erro_por_bairro > erro_medio * 1.5]
                
                if len(bairros_alto_erro) > 0:
                    st.warning("⚠️ **Possível viés detectado:**")
                    for bairro, erro in bairros_alto_erro.items():
                        st.markdown(f"- {bairro}: {erro:.1%} de erro")
                    
                    st.markdown("**Recomendações:**")
                    st.markdown("- Coletar mais dados desses bairros")
                    st.markdown("- Revisar features específicas")
                    st.markdown("- Considerar balanceamento")
                else:
                    st.success("✅ **Modelo aparenta ser justo entre bairros**")
        
        # Predições em tempo real
        st.markdown("---")
        st.markdown("### Predição em Tempo Real")
        
        with st.expander("Fazer Predição"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                pred_lat = st.number_input("Latitude", value=-8.1)
                pred_lon = st.number_input("Longitude", value=-34.9)
            
            with col2:
                pred_hora = st.slider("Hora", 0, 23, 12)
                pred_bairro = st.selectbox("Bairro", df_model['bairro'].unique())
            
            with col3:
                if 'quantidade_vitimas' in features:
                    pred_vitimas = st.number_input("Quantidade de Vítimas", 0, 10, 1)
                else:
                    pred_vitimas = 1
            
            if st.button("Fazer Predição"):
                # Preparar dados para predição
                pred_bairro_encoded = le_bairro.transform([pred_bairro])[0]
                
                pred_features = [pred_lat, pred_lon, pred_hora, pred_bairro_encoded]
                if 'quantidade_vitimas' in features:
                    pred_features.append(pred_vitimas)
                
                pred_X = pd.DataFrame([pred_features], columns=features)
                pred_result = best_model.predict(pred_X)[0]
                pred_proba = best_model.predict_proba(pred_X)[0]
                pred_label = le_target.inverse_transform([pred_result])[0]
                
                st.success(f"**Predição:** {pred_label}")
                st.info(f"**Confiança:** {max(pred_proba):.1%}")
    
    except ImportError:
        st.error("Bibliotecas de Machine Learning não instaladas. Execute: pip install scikit-learn")
    except Exception as e:
        st.error(f"Erro no modelo supervisionado: {str(e)}")
