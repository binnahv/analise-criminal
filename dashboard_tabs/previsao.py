"""Aba de previsão: estimativa de ocorrência grave pelo modelo treinado."""
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from security_utils import SecurityManager


def show_risk_prediction():
    """Aba de previsão de risco"""
    st.header("🔮 Estimativa: ocorrência grave por local e horário")
    st.info("Modelo demonstrativo: estima a probabilidade de uma ocorrência ser um crime grave "
            "(homicídio, latrocínio, estupro ou sequestro) a partir de bairro, dia e hora. "
            "Como o dataset é fictício, o modelo tende a não superar o acaso; veja as métricas abaixo.")
    
    # Tentar carregar modelo
    security_manager = SecurityManager()
    
    try:
        if os.path.exists('risk_model_secure.pkl'):
            model_data = security_manager.load_encrypted_model('risk_model_secure.pkl')
        elif os.path.exists('risk_model.pkl'):
            import pickle
            with open('risk_model.pkl', 'rb') as f:
                model_data = pickle.load(f)
                # Converter formato antigo se necessário
                if isinstance(model_data, tuple):
                    model, model_columns, bairros_list, dias_semana_list = model_data
                    model_data = {
                        'model': model,
                        'model_columns': model_columns,
                        'bairros_list': bairros_list,
                        'dias_semana_list': dias_semana_list
                    }
        else:
            st.error("❌ Modelo de previsão não encontrado.")
            return
            
    except Exception as e:
        st.error(f"Erro ao carregar modelo: {str(e)}")
        return
    
    # Interface de previsão
    st.subheader("🎯 Fazer Previsão de Risco")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_bairro = st.selectbox(
            "Selecione o Bairro",
            options=sorted(model_data['bairros_list'])
        )
    
    with col2:
        selected_dia = st.selectbox(
            "Selecione o Dia da Semana",
            options=model_data['dias_semana_list']
        )
    
    with col3:
        selected_hora = st.slider("Selecione a Hora", 0, 23, 19)
    
    if st.button("🔮 Estimar probabilidade", type="primary"):
        try:
            # Preparar dados para previsão
            input_data = pd.DataFrame(0, index=[0], columns=model_data['model_columns'])
            
            # Preencher features
            bairro_col = f"bairro_{selected_bairro}"
            if bairro_col in input_data.columns:
                input_data[bairro_col] = 1
            
            dia_col = f"dia_semana_{selected_dia}"
            if dia_col in input_data.columns:
                input_data[dia_col] = 1
            
            if 'hora' in input_data.columns:
                input_data['hora'] = selected_hora
            
            # Fazer previsão (probabilidade da classe "ocorrência grave")
            model = model_data['model']
            proba_grave = float(model.predict_proba(input_data)[0][1]) * 100

            st.subheader("📊 Resultado da Estimativa")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Probabilidade de ocorrência grave", f"{proba_grave:.1f}%")
            with col2:
                base = model_data.get('metrics', {}).get('baseline_accuracy')
                if base is not None:
                    st.metric("Referência (baseline)", f"{(1 - base) * 100:.1f}%",
                              help="Proporção de ocorrências graves no conjunto de treino/teste.")

            metrics = model_data.get('metrics')
            if metrics:
                st.caption(
                    f"Validação cruzada: acurácia {metrics['cv_accuracy']:.3f} | "
                    f"baseline {metrics['baseline_accuracy']:.3f} | "
                    f"ROC AUC {metrics['cv_roc_auc']:.3f} (0,5 = acaso). "
                    "Se a acurácia não supera o baseline e o AUC fica perto de 0,5, "
                    "o modelo não encontrou padrão real nos dados."
                )

        except Exception as e:
            st.error(f"Erro na previsão: {str(e)}")

    # Feature Importance
    if 'model' in model_data:
        st.subheader("📈 Importância das Variáveis")
        
        try:
            model = model_data['model']
            if hasattr(model, 'feature_importances_'):
                importance_df = pd.DataFrame({
                    'feature': model_data['model_columns'],
                    'importance': model.feature_importances_
                }).sort_values('importance', ascending=False).head(10)
                
                fig_importance = px.bar(
                    importance_df,
                    x='importance',
                    y='feature',
                    orientation='h',
                    title="Top 10 Variáveis Mais Importantes"
                )
                st.plotly_chart(fig_importance, width='stretch')
                
        except Exception:
            st.warning("Não foi possível exibir a importância das variáveis.")
