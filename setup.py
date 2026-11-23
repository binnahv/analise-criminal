"""
Script de configuração inicial do Sistema de Análise Criminal
Versão: 1.0.0
"""

import os
import subprocess
import sys
from pathlib import Path

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    print("🐍 Verificando versão do Python...")
    if sys.version_info < (3, 9):
        print(f"❌ Python {sys.version_info.major}.{sys.version_info.minor} não suportado")
        print("   Versão mínima requerida: Python 3.9+")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} - OK")
    return True

def install_requirements():
    """Instala as dependências necessárias"""
    print("📦 Instalando dependências...")
    try:
        cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--upgrade"]
        # "--user" só funciona fora de ambiente virtual (dentro do venv causa erro)
        if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
            cmd.append("--user")
        subprocess.check_call(cmd)
        print("✅ Dependências instaladas com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        print("💡 Tente executar: pip install --upgrade pip")
        return False

def create_directories():
    """Cria diretórios necessários"""
    print("📁 Criando estrutura de diretórios...")
    directories = [
        "data",
        ".streamlit",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Diretório criado/verificado: {directory}/")

def create_security_key():
    """Cria chave de segurança se não existir"""
    if not os.path.exists("security.key"):
        print("🔐 Gerando chave de segurança...")
        try:
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            with open("security.key", "wb") as key_file:
                key_file.write(key)
            print("✅ Chave de segurança criada!")
        except ImportError:
            print("❌ Erro: cryptography não instalada")
            return False
    else:
        print("✅ Chave de segurança já existe!")
    return True

def check_data_file():
    """Verifica se o arquivo de dados existe"""
    data_path = "data/dataset_ocorrencias_delegacia_5.csv"
    if os.path.exists(data_path):
        print(f"✅ Arquivo de dados encontrado: {data_path}")
        # Verificar tamanho do arquivo
        size_mb = os.path.getsize(data_path) / (1024 * 1024)
        print(f"   Tamanho: {size_mb:.1f} MB")
        return True
    else:
        print(f"❌ Arquivo de dados não encontrado: {data_path}")
        print("💡 Coloque o arquivo CSV na pasta 'data/' para usar o sistema")
        return False

def setup_user():
    """Configura usuário padrão"""
    print("👤 Configurando usuário padrão...")
    try:
        from security_utils import SecurityManager
        security_manager = SecurityManager()
        
        existed = os.path.exists("users.pkl")
        if security_manager.ensure_default_user():
            if existed:
                print("✅ Base de usuários já existe!")
            else:
                print("✅ Usuário de demonstração criado (veja a senha acima)")
        else:
            print("❌ Erro ao criar usuário admin")
            return False
        return True
    except Exception as e:
        print(f"❌ Erro na configuração de usuário: {e}")
        return False

def run_initial_analysis():
    """Executa análise inicial se possível"""
    if os.path.exists("data/dataset_ocorrencias_delegacia_5.csv"):
        print("🤖 Executando análise inicial...")
        try:
            subprocess.run([sys.executable, "advanced_analysis.py"], 
                         timeout=300, check=True)
            print("✅ Análise inicial concluída!")
            return True
        except subprocess.TimeoutExpired:
            print("⚠️ Análise demorou mais que esperado, mas pode ter funcionado")
            return True
        except subprocess.CalledProcessError:
            print("⚠️ Erro na análise inicial - execute manualmente depois")
            return True
    else:
        print("⚠️ Análise inicial pulada - arquivo de dados não encontrado")
        return True

def main():
    """Função principal de setup"""
    print("🚀 Sistema de Análise Criminal - Setup v1.0.0")
    print("=" * 60)
    
    # 1. Verificar Python
    if not check_python_version():
        return False
    
    # 2. Criar diretórios
    create_directories()
    
    # 3. Instalar dependências
    if not install_requirements():
        print("❌ Falha na instalação. Verifique sua conexão e tente novamente.")
        return False
    
    # 4. Criar chave de segurança
    if not create_security_key():
        return False
    
    # 5. Verificar arquivo de dados
    has_data = check_data_file()
    
    # 6. Configurar usuário
    if not setup_user():
        return False
    
    # 7. Executar análise inicial (se tiver dados)
    if has_data:
        run_initial_analysis()
    
    print("=" * 60)
    print("🎉 Configuração concluída com sucesso!")
    print("\n📋 Como usar:")
    print("1. 🚀 Iniciar: streamlit run enhanced_app.py")
    print("2. 🌐 Acessar: http://localhost:8501")
    print("3. 🔑 Login: admin / senha exibida no terminal (ou ADMIN_PASSWORD)")
    
    if not has_data:
        print("\n⚠️ Lembre-se de adicionar o dataset em data/")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Setup cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)