"""
Análise Criminal Avançada com Modelos Melhorados
Limpeza e validação dos dados, clustering (K-Means), detecção de anomalias
(Isolation Forest) e classificador de ocorrência grave (XGBoost) com baseline
"""

from typing import Optional

import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.neighbors import LocalOutlierFactor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import silhouette_score, classification_report
import xgboost as xgb
import lightgbm as lgb
from security_utils import SecurityManager, LGPDCompliance, DataValidator
import warnings
warnings.filterwarnings('ignore')

class AdvancedCriminalAnalysis:
    """Classe principal para análise criminal avançada"""
    
    def __init__(self, data_path: str) -> None:
        self.data_path = data_path
        self.security_manager = SecurityManager()
        self.lgpd = LGPDCompliance()
        self.validator = DataValidator()
        self.scaler = StandardScaler()
        self.label_encoders = {}
        
    def load_and_preprocess_data(self) -> pd.DataFrame:
        """Carrega e preprocessa os dados com validação robusta"""
        print("Carregando e preprocessando dados...")
        
        # Carregar dados
        df = pd.read_csv(self.data_path, sep=',')
        print(f"Dados carregados: {df.shape[0]} linhas, {df.shape[1]} colunas")
        
        # Normalizar nomes de colunas
        df.columns = df.columns.str.lower().str.strip()
        
        # Validar e limpar dados
        df_clean = self.validator.clean_and_validate_data(df)
        print(f"Após limpeza: {df_clean.shape[0]} linhas válidas")
        
        # Engenharia de features temporais
        df_clean['data_ocorrencia'] = pd.to_datetime(df_clean['data_ocorrencia'], errors='coerce')
        df_clean = df_clean.dropna(subset=['data_ocorrencia'])
        
        df_clean['hora'] = df_clean['data_ocorrencia'].dt.hour
        df_clean['dia_semana'] = df_clean['data_ocorrencia'].dt.day_name()
        df_clean['mes'] = df_clean['data_ocorrencia'].dt.month
        df_clean['ano'] = df_clean['data_ocorrencia'].dt.year
        df_clean['dia_mes'] = df_clean['data_ocorrencia'].dt.day
        
        # Mapeamento de dias da semana
        day_map = {
            'Monday': 'segunda-feira', 'Tuesday': 'terça-feira',
            'Wednesday': 'quarta-feira', 'Thursday': 'quinta-feira',
            'Friday': 'sexta-feira', 'Saturday': 'sábado', 'Sunday': 'domingo'
        }
        df_clean['dia_semana'] = df_clean['dia_semana'].map(day_map)
        
        # Features adicionais
        df_clean['periodo_dia'] = df_clean['hora'].apply(self._categorize_time_period)
        df_clean['fim_semana'] = df_clean['dia_semana'].isin(['sábado', 'domingo'])
        
        # Limpeza de coordenadas
        for col in ['latitude', 'longitude']:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        df_clean = df_clean.dropna(subset=['latitude', 'longitude'])
        
        # Tratamento de valores faltantes em colunas categóricas
        categorical_cols = ['bairro', 'tipo_crime', 'descricao_modus_operandi']
        for col in categorical_cols:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].fillna('Não Informado')
        
        self.df = df_clean
        print("Pré-processamento concluído.")
        return df_clean
    
    def _categorize_time_period(self, hour: int) -> str:
        """Categoriza período do dia"""
        if 6 <= hour < 12:
            return 'Manhã'
        elif 12 <= hour < 18:
            return 'Tarde'
        elif 18 <= hour < 24:
            return 'Noite'
        else:
            return 'Madrugada'
    
    def perform_clustering(self, method: str = 'kmeans') -> float:
        """Realiza clusterização com diferentes métodos"""
        print(f"Executando clusterização com {method}...")
        
        # Preparar dados para clusterização
        features_clustering = ['bairro', 'tipo_crime', 'hora', 'dia_semana', 'latitude', 'longitude']
        df_cluster = self.df.dropna(subset=features_clustering).copy()
        
        if method == 'dbscan':
            # DBSCAN como alternativa ao HDBSCAN
            from sklearn.cluster import DBSCAN
            features_for_dbscan = ['latitude', 'longitude', 'hora']
            X_dbscan = df_cluster[features_for_dbscan].copy()
            X_dbscan_scaled = self.scaler.fit_transform(X_dbscan)
            
            clusterer = DBSCAN(eps=0.3, min_samples=10)
            clusters = clusterer.fit_predict(X_dbscan_scaled)
            
        elif method == 'agglomerative':
            # Clustering Hierárquico Aglomerativo
            from sklearn.cluster import AgglomerativeClustering
            features_for_agg = ['latitude', 'longitude', 'hora']
            X_agg = df_cluster[features_for_agg].copy()
            X_agg_scaled = self.scaler.fit_transform(X_agg)
            
            clusterer = AgglomerativeClustering(n_clusters=5, linkage='ward')
            clusters = clusterer.fit_predict(X_agg_scaled)
            
        else:  # kmeans como método principal
            from sklearn.cluster import KMeans
            # Usar encoding para variáveis categóricas
            df_encoded = pd.get_dummies(df_cluster[features_clustering])
            df_encoded_scaled = self.scaler.fit_transform(df_encoded)
            
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(df_encoded_scaled)
        
        df_cluster['cluster'] = clusters
        
        # Calcular silhouette score se possível
        try:
            if method == 'dbscan':
                sil_score = silhouette_score(X_dbscan_scaled, clusters) if len(set(clusters)) > 1 else 0
            elif method == 'agglomerative':
                sil_score = silhouette_score(X_agg_scaled, clusters) if len(set(clusters)) > 1 else 0
            else:  # kmeans
                sil_score = silhouette_score(df_encoded_scaled, clusters)
        except ValueError:
            sil_score = 0
        
        print(f"Silhouette Score ({method}): {sil_score:.3f}")
        
        # Adicionar clusters ao dataframe principal
        self.df['cluster'] = -1  # Valor padrão
        self.df.loc[df_cluster.index, 'cluster'] = clusters
        
        return sil_score
    
    def detect_anomalies(self, method: str = 'isolation_forest') -> None:
        """Detecta anomalias com diferentes métodos"""
        print(f"Detectando anomalias com {method}...")
        
        features_anomaly = ['latitude', 'longitude', 'hora']
        df_anomaly = self.df.dropna(subset=features_anomaly).copy()
        
        # Escalar features
        X_anomaly = self.scaler.fit_transform(df_anomaly[features_anomaly])
        
        if method == 'isolation_forest':
            model_anomaly = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
        elif method == 'lof':
            model_anomaly = LocalOutlierFactor(n_neighbors=20, contamination=0.05)
        
        anomalies = model_anomaly.fit_predict(X_anomaly)
        df_anomaly['anomalia'] = anomalies
        
        # Adicionar anomalias ao dataframe principal
        self.df['anomalia'] = 1  # Valor padrão (normal)
        self.df.loc[df_anomaly.index, 'anomalia'] = anomalies
        
        print(f"Anomalias detectadas: {sum(anomalies == -1)} de {len(anomalies)} ({sum(anomalies == -1)/len(anomalies)*100:.1f}%)")
    
    # Tipos de crime considerados graves (alvo do modelo). O alvo NÃO é derivado
    # de bairro/hora/dia, portanto não há vazamento de informação (target leakage).
    CRIMES_GRAVES = ['Homicídio', 'Latrocínio', 'Estupro', 'Sequestro']

    def train_risk_prediction_model(self, model_type: str = 'xgboost') -> tuple[dict, float]:
        """Treina modelo que estima a probabilidade de uma ocorrência ser GRAVE
        a partir de onde (bairro) e quando (hora, dia, mês) ela acontece.

        Observações metodológicas:
        - O alvo (crime grave: sim/não) é definido pelo tipo de crime, que não é
          usado como feature. Na versão anterior o alvo era calculado a partir do
          bairro e o bairro também era feature, o que gerava acurácia de 100%
          (vazamento de alvo).
        - O resultado é comparado com um baseline (sempre prever a classe
          majoritária) e avaliado por ROC AUC, para mostrar se o modelo realmente
          aprende algo além do acaso.
        """
        from sklearn.dummy import DummyClassifier

        print(f"Treinando modelo de ocorrência grave com {model_type}...")

        # Classificação DESCRITIVA por densidade de ocorrências no bairro
        # (usada apenas nos gráficos; NÃO é o alvo do modelo)
        bairro_counts = self.df['bairro'].value_counts()
        q33, q66 = bairro_counts.quantile(0.33), bairro_counts.quantile(0.66)

        def classify_density(bairro: str) -> str:
            count = bairro_counts.get(bairro, 0)
            if count <= q33:
                return 'Baixo Risco'
            elif count <= q66:
                return 'Médio Risco'
            return 'Alto Risco'

        self.df['nivel_risco'] = self.df['bairro'].apply(classify_density)

        # Alvo do modelo: ocorrência grave (1) ou não (0)
        self.df['ocorrencia_grave'] = self.df['tipo_crime'].isin(self.CRIMES_GRAVES).astype(int)

        features_pred = ['bairro', 'hora', 'dia_semana', 'mes', 'periodo_dia', 'fim_semana']
        target = 'ocorrencia_grave'

        df_model = self.df.dropna(subset=features_pred + [target]).copy()
        X = pd.get_dummies(df_model[features_pred], drop_first=True)
        y = df_model[target]
        self.model_columns = X.columns.tolist()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        if model_type == 'xgboost':
            model = xgb.XGBClassifier(
                random_state=42, n_estimators=100, max_depth=3,
                learning_rate=0.05, eval_metric='logloss'
            )
        elif model_type == 'lightgbm':
            model = lgb.LGBMClassifier(
                random_state=42, n_estimators=100, max_depth=3,
                learning_rate=0.05, verbose=-1
            )
        else:
            model = RandomForestClassifier(
                random_state=42, n_estimators=100, max_depth=5,
                class_weight='balanced'
            )

        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        class_report = classification_report(y_test, pred, output_dict=True, zero_division=0)

        # Baseline: sempre prever a classe mais frequente
        baseline = DummyClassifier(strategy='most_frequent').fit(X_train, y_train)
        baseline_acc = float(baseline.score(X_test, y_test))

        # Validação cruzada (acurácia e ROC AUC)
        cv_acc = cross_val_score(model, X, y, cv=5, scoring='accuracy')
        cv_auc = cross_val_score(model, X, y, cv=5, scoring='roc_auc')

        print(f"Baseline (classe majoritária): {baseline_acc:.3f}")
        print(f"Acurácia média (CV): {cv_acc.mean():.3f} (+/- {cv_acc.std() * 2:.3f})")
        print(f"ROC AUC médio (CV): {cv_auc.mean():.3f}  (0.5 = equivalente ao acaso)")
        if cv_auc.mean() < 0.55:
            print("Aviso: o modelo não supera o acaso de forma relevante. "
                  "Isso é esperado se os dados forem sintéticos/aleatórios.")

        self.model_metrics = {
            'baseline_accuracy': baseline_acc,
            'cv_accuracy': float(cv_acc.mean()),
            'cv_roc_auc': float(cv_auc.mean()),
        }

        model_data = {
            'model': model,
            'model_columns': self.model_columns,
            'bairros_list': df_model['bairro'].unique().tolist(),
            'dias_semana_list': df_model['dia_semana'].unique().tolist(),
            'feature_names': features_pred,
            'model_type': model_type,
            'target_name': target,
            'cv_scores': cv_acc,
            'class_report': class_report,
            'metrics': self.model_metrics,
        }

        self.security_manager.save_encrypted_model(model_data, 'risk_model_secure.pkl')
        return class_report, cv_acc.mean()

    def get_feature_importance(self, model_data: dict) -> Optional[pd.DataFrame]:
        """Obtém importância das features do modelo"""
        model = model_data['model']
        
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            feature_names = model_data['model_columns']
            
            importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False)
            
            return importance_df
        
        return None
    
    def save_results(self) -> None:
        """Salva resultados da análise"""
        results = {
            'data': self.df,
            'silhouette_score': getattr(self, 'silhouette_score', 0),
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'analysis_timestamp': pd.Timestamp.now()
        }
        
        # Salvar resultados criptografados
        self.security_manager.save_encrypted_model(results, 'analysis_results_secure.pkl')
        
        print("Resultados salvos com segurança.")

def main() -> None:
    """Função principal"""
    print("=== Análise Criminal Avançada ===")
    
    # Inicializar análise
    analysis = AdvancedCriminalAnalysis('data/dataset_ocorrencias_delegacia_5.csv')
    
    # Carregar e preprocessar dados
    df = analysis.load_and_preprocess_data()
    
    # Clusterização
    sil_score = analysis.perform_clustering(method='kmeans')
    analysis.silhouette_score = sil_score
    
    # Detecção de anomalias
    analysis.detect_anomalies(method='isolation_forest')
    
    # Modelo de previsão de risco
    class_report, cv_accuracy = analysis.train_risk_prediction_model(model_type='xgboost')
    
    # Salvar resultados
    analysis.save_results()
    
    print("\n=== Resumo da Análise ===")
    print(f"Total de registros processados: {len(df)}")
    print(f"Silhouette Score: {sil_score:.3f}")
    m = analysis.model_metrics
    print(f"Modelo de ocorrência grave -> acurácia CV: {cv_accuracy:.3f} | "
          f"baseline: {m['baseline_accuracy']:.3f} | ROC AUC: {m['cv_roc_auc']:.3f}")
    print(f"Anomalias detectadas: {sum(df['anomalia'] == -1)}")
    
    print("\nAnálise concluída! Execute o dashboard com:")
    print("streamlit run enhanced_app.py")

if __name__ == "__main__":
    main()
