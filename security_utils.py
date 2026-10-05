"""
Módulo de Segurança e Utilitários para Análise Criminal
Implementa criptografia, controle de acesso e validação de dados (demonstração acadêmica)
"""

import pickle
import os
import hashlib
import secrets
import streamlit as st
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import pandas as pd
import logging

# Configuração de logging para auditoria
logging.basicConfig(
    filename='audit_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SecurityManager:
    """Gerenciador de segurança para o sistema de análise criminal"""
    
    def __init__(self):
        self.key_file = 'security.key'
        self.users_file = 'users.pkl'
        self.session_timeout = 30  # minutos
        
    def generate_key(self):
        """Gera uma nova chave de criptografia"""
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(key)
        return key
    
    def load_key(self):
        """Carrega a chave de criptografia"""
        if not os.path.exists(self.key_file):
            return self.generate_key()
        with open(self.key_file, 'rb') as f:
            return f.read()
    
    def encrypt_data(self, data):
        """Criptografa dados usando Fernet"""
        key = self.load_key()
        f = Fernet(key)
        serialized_data = pickle.dumps(data)
        encrypted_data = f.encrypt(serialized_data)
        return encrypted_data
    
    def decrypt_data(self, encrypted_data):
        """Descriptografa dados usando Fernet"""
        key = self.load_key()
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data)
        return pickle.loads(decrypted_data)
    
    def save_encrypted_model(self, model_data, filename):
        """Salva modelo criptografado"""
        encrypted_data = self.encrypt_data(model_data)
        with open(filename, 'wb') as f:
            f.write(encrypted_data)
        logging.info(f"Modelo salvo criptografado: {filename}")
    
    def load_encrypted_model(self, filename):
        """Carrega modelo criptografado"""
        with open(filename, 'rb') as f:
            encrypted_data = f.read()
        model_data = self.decrypt_data(encrypted_data)
        logging.info(f"Modelo carregado: {filename}")
        return model_data
    
    def hash_password(self, password):
        """Gera hash da senha"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _load_users(self):
        """Carrega os usuários; cria o admin de demonstração se o arquivo não existir.

        A senha do admin NUNCA fica escrita no código:
        - se a variável de ambiente ADMIN_PASSWORD existir, ela é usada;
        - caso contrário, uma senha aleatória é gerada e exibida UMA vez no terminal.
        """
        if not os.path.exists(self.users_file):
            password = os.getenv("ADMIN_PASSWORD")
            generated = not password
            if generated:
                password = secrets.token_urlsafe(9)  # ~12 caracteres aleatórios
            self._save_users({
                'admin': {
                    'password': self.hash_password(password),
                    'role': 'admin',
                    'permissions': ['read', 'write', 'admin']
                }
            })
            if generated:
                print("\n" + "=" * 60)
                print("  LOGIN DE DEMONSTRAÇÃO CRIADO (aparece só desta vez)")
                print("  Usuário: admin")
                print(f"  Senha:   {password}")
                print("  Para definir a sua: use a variável ADMIN_PASSWORD")
                print("=" * 60 + "\n", flush=True)
        with open(self.users_file, 'rb') as f:
            return pickle.load(f)

    def _save_users(self, users):
        with open(self.users_file, 'wb') as f:
            pickle.dump(users, f)

    def ensure_default_user(self):
        """Garante que exista o usuário de demonstração (admin). Retorna True se ok."""
        return 'admin' in self._load_users()

    def create_user(self, username, password, role='analyst', permissions=None):
        """Cria um usuário. Retorna True se criou e False se o usuário já existia
        ou se os dados forem inválidos."""
        if not username or not password:
            return False
        users = self._load_users()
        if username in users:
            return False
        users[username] = {
            'password': self.hash_password(password),
            'role': role,
            'permissions': permissions or ['read'],
        }
        self._save_users(users)
        logging.info(f"Usuário criado: {username}")
        return True

    def authenticate_user(self, username, password):
        """Autentica usuário"""
        users = self._load_users()
        
        if username in users:
            if users[username]['password'] == self.hash_password(password):
                logging.info(f"Login bem-sucedido: {username}")
                return True, users[username]
        
        logging.warning(f"Tentativa de login falhada: {username}")
        return False, None
    
    def check_session_timeout(self):
        """Verifica timeout da sessão"""
        if 'login_time' in st.session_state:
            login_time = st.session_state['login_time']
            if datetime.now() - login_time > timedelta(minutes=self.session_timeout):
                st.session_state.clear()
                return True
        return False

class LGPDCompliance:
    """Classe para conformidade com LGPD"""
    
    @staticmethod
    def anonymize_data(df, sensitive_columns):
        """Anonimiza dados sensíveis"""
        df_anon = df.copy()
        for col in sensitive_columns:
            if col in df_anon.columns:
                # Substituir por hash ou código genérico
                df_anon[col] = df_anon[col].apply(
                    lambda x: hashlib.md5(str(x).encode()).hexdigest()[:8] if pd.notna(x) else x
                )
        return df_anon
    
    @staticmethod
    def get_data_retention_policy():
        """Retorna política de retenção de dados"""
        return {
            'retention_period': '5 anos',
            'description': 'Dados criminais são mantidos por 5 anos conforme legislação',
            'deletion_policy': 'Dados são automaticamente anonimizados após o período'
        }
    
    @staticmethod
    def log_data_access(user, data_type, action):
        """Registra acesso aos dados para auditoria"""
        logging.info(f"LGPD - Usuário: {user}, Dados: {data_type}, Ação: {action}")

class DataValidator:
    """Validador de dados para garantir qualidade e consistência"""
    
    @staticmethod
    def validate_coordinates(lat, lon):
        """Valida coordenadas geográficas para Recife com limites mais restritivos"""
        if pd.isna(lat) or pd.isna(lon):
            return False
        
        # Coordenadas mais restritivas para o centro do Recife
        # Baseado na área urbana principal do Recife
        lat_min, lat_max = -8.12, -8.05  # Mais restritivo
        lon_min, lon_max = -34.95, -34.85  # Mais restritivo
        
        # Verificar se está dentro dos limites mais restritivos
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return True
        
        return False
    
    @staticmethod
    def validate_coordinates_by_neighborhood(lat, lon, bairro):
        """Valida coordenadas baseado no bairro específico"""
        if pd.isna(lat) or pd.isna(lon):
            return False
            
        # Coordenadas aproximadas dos principais bairros do Recife
        bairro_coords = {
            'Pina': {'lat_center': -8.088, 'lon_center': -34.885, 'radius': 0.015},
            'Boa Viagem': {'lat_center': -8.113, 'lon_center': -34.896, 'radius': 0.020},
            'Imbiribeira': {'lat_center': -8.118, 'lon_center': -34.906, 'radius': 0.015},
            'Casa Forte': {'lat_center': -8.038, 'lon_center': -34.925, 'radius': 0.015},
            'Graças': {'lat_center': -8.058, 'lon_center': -34.898, 'radius': 0.012},
            'Espinheiro': {'lat_center': -8.048, 'lon_center': -34.898, 'radius': 0.012},
            'Tamarineira': {'lat_center': -8.028, 'lon_center': -34.908, 'radius': 0.015},
            'Torre': {'lat_center': -8.048, 'lon_center': -34.908, 'radius': 0.012},
            'Afogados': {'lat_center': -8.068, 'lon_center': -34.918, 'radius': 0.015},
            'Santo Amaro': {'lat_center': -8.078, 'lon_center': -34.888, 'radius': 0.012}
        }
        
        if bairro in bairro_coords:
            coords = bairro_coords[bairro]
            # Calcular distância aproximada
            lat_diff = abs(lat - coords['lat_center'])
            lon_diff = abs(lon - coords['lon_center'])
            
            # Verificar se está dentro do raio do bairro
            if lat_diff <= coords['radius'] and lon_diff <= coords['radius']:
                return True
        
        return False
    
    @staticmethod
    def validate_datetime(dt):
        """Valida data e hora"""
        if pd.isna(dt):
            return False
        # Verificar se a data não é futura
        if dt > datetime.now():
            return False
        # Verificar se a data não é muito antiga (ex: antes de 2000)
        if dt.year < 2000:
            return False
        return True
    
    @staticmethod
    def clean_and_validate_data(df):
        """Limpa e valida dataset completo"""
        df_clean = df.copy()
        
        # Validar coordenadas
        valid_coords = df_clean.apply(
            lambda row: DataValidator.validate_coordinates(row.get('latitude'), row.get('longitude')), 
            axis=1
        )
        df_clean = df_clean[valid_coords]
        
        # Validar datas
        if 'data_ocorrencia' in df_clean.columns:
            df_clean['data_ocorrencia'] = pd.to_datetime(df_clean['data_ocorrencia'], errors='coerce')
            valid_dates = df_clean['data_ocorrencia'].apply(DataValidator.validate_datetime)
            df_clean = df_clean[valid_dates]
        
        # Remover duplicatas
        df_clean = df_clean.drop_duplicates()
        
        return df_clean

def show_lgpd_notice():
    """Exibe aviso (demonstrativo) sobre boas práticas de privacidade"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔒 Privacidade (demonstração)")
    with st.sidebar.expander("Política de Privacidade"):
        st.write("""
        **Projeto acadêmico com dados fictícios.**

        Este painel demonstra boas práticas inspiradas na LGPD, como
        anonimização de colunas sensíveis, log de acesso e controle de sessão.
        Ele **não** representa conformidade legal completa e não deve ser usado
        com dados pessoais reais sem uma avaliação jurídica e de segurança.
        """)

def show_model_limitations():
    """Exibe limitações e avisos sobre o modelo"""
    st.warning("""
    ⚠️ **IMPORTANTE - Limitações do Sistema:**
    
    • **Uso Auxiliar:** Este sistema é uma ferramenta de apoio à decisão, não substitui o julgamento profissional
    • **Dados Históricos:** Previsões baseadas em padrões passados podem não refletir situações futuras
    • **Novos Padrões:** O modelo pode não detectar crimes com características inéditas
    • **Validação Necessária:** Sempre cruzar com informações de campo e outras fontes
    • **Atualização Regular:** Modelo deve ser retreinado periodicamente com novos dados
    """)