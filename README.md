# 🚔 Sistema de Análise Criminal

> Projeto acadêmico (PI) — dashboard interativo em Streamlit para análise exploratória de ocorrências criminais, com validação de dados, clustering, detecção de anomalias e um modelo de classificação.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)

## 🎯 Sobre o projeto

Trabalho desenvolvido na faculdade (curso de Análise e Desenvolvimento de Sistemas) para praticar o ciclo completo de um projeto de dados: **carregar, validar, limpar, analisar e visualizar** informações de ocorrências policiais.

> ⚠️ **Aviso importante:** o dataset foi fornecido pelo professor e é **fictício**. Todos os nomes de delegacias, bairros e registros são usados apenas para fins didáticos. O sistema **não** representa dados reais da Polícia Civil nem de nenhum órgão público.

## 📦 Sobre os dados

O arquivo `data/dataset_ocorrencias_delegacia_5.csv` tem **5.000 ocorrências** (2022–2025) em **10 bairros do Recife**, com 14 colunas (tipo de crime, modus operandi, arma, vítimas, suspeitos, delegacia, status da investigação, coordenadas etc.).

O dataset contém **inconsistências propositais ou naturais de dados sintéticos**, e parte do trabalho foi identificá-las e tratá-las:

| Inconsistência encontrada | O que o projeto faz |
|---|---|
| Coordenadas que não correspondem ao bairro informado (apenas ~6% batem com o bairro) | Validação por bairro e por limites geográficos (`DataValidator`) |
| Coordenadas fora da área urbana considerada (~30% dos registros) | Registros removidos na limpeza: de 5.000 sobram **3.482** |
| Combinações incoerentes entre tipo de crime e modus operandi (ex.: furto com "Estupro Coletivo") | Identificado como limitação; não é possível corrigir sem a fonte |
| Ocorrências com 0 vítimas (inclusive homicídios) e com 0 suspeitos mas sexo do suspeito preenchido | Identificado como limitação dos dados |
| Delegacia responsável sem relação com o bairro da ocorrência | Identificado como limitação dos dados |

> 🔎 Como os dados parecem gerados aleatoriamente, **não existem padrões reais para os modelos aprenderem**. Os resultados de clustering e previsão devem ser lidos como demonstração técnica, e não como conclusão sobre criminalidade.

## ✨ Funcionalidades

- **Dashboard com 10 abas:** geográfica, temporal, clusters, anomalias, previsão, investigação, perfil de suspeitos, gravidade, modus operandi e estatísticas.
- **Filtros globais:** período, bairros, tipos de crime, faixa horária e dias da semana.
- **Mapas:** mapa de calor, clusters e pontos individuais (Folium / PyDeck).
- **Machine Learning (scikit-learn, XGBoost, LightGBM):** K-Means, Isolation Forest e classificador de nível de risco.
- **Módulo de segurança (demonstrativo):** login, criptografia Fernet dos arquivos gerados e log de auditoria.
- **Dashboard extra** de Violência Doméstica (`dashboard_violencia_domestica.py`).

## 🧪 Limitações conhecidas

Transparência sobre o estado atual do projeto:

- **Modelo de risco:** o "nível de risco" é definido pela contagem de ocorrências por bairro, e o bairro também é uma variável de entrada. Por isso a acurácia chega a ~100%, o que indica **vazamento de alvo (*target leakage*)** e não um bom desempenho preditivo. *(A corrigir.)*
- **Clustering:** silhouette score ≈ 0,10, o que indica clusters pouco definidos, coerente com dados sintéticos.
- **Segurança é apenas didática:** o login `admin/admin123` é um usuário de demonstração; as senhas usam SHA-256 sem sal e os arquivos usam `pickle`. **Não use em produção.** O texto sobre LGPD é ilustrativo e não constitui conformidade legal.
- Não há testes automatizados.

## 🛠️ Stack

Python · Streamlit · Pandas · NumPy · scikit-learn · XGBoost · LightGBM · Plotly · Folium · PyDeck · Matplotlib/Seaborn · cryptography

## 🚀 Como executar

```bash
# 1. Clonar o repositório
git clone https://github.com/<seu-usuario>/<nome-do-repositorio>.git
cd <nome-do-repositorio>

# 2. (Recomendado) criar ambiente virtual
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Gerar os resultados da análise
python advanced_analysis.py

# 5. Iniciar o dashboard principal
streamlit run enhanced_app.py

# 6. (Opcional) dashboard de Violência Doméstica
streamlit run dashboard_violencia_domestica.py
```

Acesso local: <http://localhost:8501>

**Login de demonstração:** usuário `admin`, senha `admin123` (criado automaticamente na primeira execução; é só um exemplo e não deve ser usado em produção).

## 📁 Estrutura

```
├── enhanced_app.py                      # Dashboard principal (login + 10 abas)
├── dashboard_tabs.py                    # Funções de cada aba
├── dashboard_violencia_domestica.py     # Dashboard de Violência Doméstica
├── advanced_analysis.py                 # Limpeza, clustering, anomalias e ML
├── security_utils.py                    # Login, criptografia e validação de dados
├── setup.py                             # Script de configuração inicial (em correção)
├── requirements.txt
├── data/
│   └── dataset_ocorrencias_delegacia_5.csv
└── comoExecultar.md
```

## 📄 Licença

Código distribuído sob a licença [MIT](LICENSE). O dataset em `data/` foi fornecido pelo professor e não é coberto por essa licença.
