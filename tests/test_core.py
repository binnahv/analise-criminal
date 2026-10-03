"""Testes básicos do projeto. Execute com:  pytest -q"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security_utils import DataValidator, SecurityManager  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "dataset_ocorrencias_delegacia_5.csv")


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """SecurityManager isolado em uma pasta temporária (não toca nos arquivos reais)."""
    monkeypatch.chdir(tmp_path)
    return SecurityManager()


def test_usuario_demo_criado_automaticamente(manager):
    ok, user = manager.authenticate_user("admin", "admin123")
    assert ok and user["role"] == "admin"


def test_login_com_senha_errada_falha(manager):
    ok, user = manager.authenticate_user("admin", "senha-errada")
    assert not ok and user is None


def test_create_user_e_duplicado(manager):
    assert manager.create_user("aluna", "123456") is True
    assert manager.create_user("aluna", "outra") is False
    assert manager.authenticate_user("aluna", "123456")[0] is True


def test_criptografia_ida_e_volta(manager):
    payload = {"a": 1, "b": [1, 2, 3]}
    assert manager.decrypt_data(manager.encrypt_data(payload)) == payload


def test_coordenadas_invalidas_sao_rejeitadas():
    assert DataValidator.validate_coordinates(0, 0) is False


def test_dataset_tem_colunas_esperadas():
    df = pd.read_csv(DATA)
    esperadas = {"id_ocorrencia", "data_ocorrencia", "bairro", "tipo_crime",
                 "latitude", "longitude", "status_investigacao"}
    assert esperadas.issubset(df.columns)
    assert len(df) == 5000


def test_limpeza_remove_registros_invalidos():
    df = pd.read_csv(DATA)
    limpo = DataValidator.clean_and_validate_data(df)
    assert 0 < len(limpo) < len(df)


def test_alvo_do_modelo_nao_depende_so_das_features():
    """Garante que não há vazamento de alvo: o mesmo bairro aparece com
    ocorrências graves e não graves (o alvo não é função do bairro)."""
    from advanced_analysis import AdvancedCriminalAnalysis
    df = pd.read_csv(DATA)
    df["grave"] = df["tipo_crime"].isin(AdvancedCriminalAnalysis.CRIMES_GRAVES)
    por_bairro = df.groupby("bairro")["grave"].nunique()
    assert (por_bairro == 2).all()
