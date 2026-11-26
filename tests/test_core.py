"""Testes básicos do projeto. Execute com:  pytest -q"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security_utils import DataValidator, SecurityManager  # noqa: E402

SENHA_TESTE = "senha-de-teste-123"
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "dataset_ocorrencias_delegacia_5.csv")


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """SecurityManager isolado em uma pasta temporária (não toca nos arquivos reais)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ADMIN_PASSWORD", SENHA_TESTE)
    return SecurityManager()


def test_admin_usa_senha_da_variavel_de_ambiente(manager):
    ok, user = manager.authenticate_user("admin", SENHA_TESTE)
    assert ok and user["role"] == "admin"


def test_senha_antiga_fixa_nao_funciona(manager):
    assert manager.authenticate_user("admin", "admin123")[0] is False


def test_senha_aleatoria_gerada_e_mostrada_no_terminal(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    manager = SecurityManager()
    manager.ensure_default_user()
    saida = capsys.readouterr().out
    assert "Senha:" in saida
    senha = saida.split("Senha:")[1].split()[0]
    assert len(senha) >= 10 and senha != "admin123"
    assert manager.authenticate_user("admin", senha)[0] is True


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

def test_indice_gravidade_usa_os_valores_reais_do_dataset():
    """Todo crime e toda arma do dataset precisam ter peso definido
    (antes os nomes não batiam e as abas usavam dados aleatórios)."""
    from dashboard_tabs import PESOS_ARMA, PESOS_CRIME, calcular_indice_gravidade
    df = pd.read_csv(DATA)
    assert set(df["tipo_crime"].unique()) <= set(PESOS_CRIME)
    assert set(df["arma_utilizada"].unique()) <= set(PESOS_ARMA)
    indice = calcular_indice_gravidade(df)
    assert indice.notna().all() and (indice > 0).all()


def test_indice_gravidade_calculo():
    from dashboard_tabs import calcular_indice_gravidade
    df = pd.DataFrame({"tipo_crime": ["Homicídio"], "arma_utilizada": ["Faca"],
                       "quantidade_vitimas": [2], "quantidade_suspeitos": [1]})
    assert calcular_indice_gravidade(df).iloc[0] == 10 + 3 + 2 * 2 + 1


def test_upload_converte_data_mesmo_com_pandas_3():
    """No pandas 3 colunas de texto têm dtype `str`, não `object`. A data do
    CSV enviado precisa ser convertida mesmo assim (antes dava erro no `.dt`)."""
    from violencia_domestica import preparar_dataset_upload
    df = pd.DataFrame({"data_ocorrencia": ["2026-01-12", "data-invalida"],
                       "tipo_crime": ["Ameaça", "Estupro"], "bairro": ["Pina", "Torre"],
                       "latitude": ["-8.08", "-8.05"], "longitude": ["-34.88", "-34.90"],
                       "status_atendimento": ["Em análise", "Encerrada"],
                       "idade_suspeito": ["Não informado", "30"]})
    out = preparar_dataset_upload(df)
    assert len(out) == 1  # a linha com data inválida é descartada
    assert pd.api.types.is_datetime64_any_dtype(out["data_ocorrencia"])
    assert out["mes"].iloc[0] == 1 and out["status_caso"].iloc[0] == "Em análise"
    # texto em coluna numérica vira vazio em vez de quebrar os gráficos
    assert pd.api.types.is_numeric_dtype(out["idade_suspeito"])
    assert out["idade_suspeito"].isna().iloc[0]


def test_csv_modelo_de_upload_segue_o_formato_documentado():
    from violencia_domestica import (COLUNAS_OBRIGATORIAS, COLUNAS_OPCIONAIS,
                                               MODELO_UPLOAD, preparar_dataset_upload)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    df = pd.read_csv(os.path.join(raiz, MODELO_UPLOAD))
    esperadas = {c for c, _ in COLUNAS_OBRIGATORIAS + COLUNAS_OPCIONAIS}
    assert set(df.columns) == esperadas
    preparado = preparar_dataset_upload(df)
    assert len(preparado) == len(df)  # todas as datas do modelo são válidas
    from violencia_domestica import clean_geographic_data
    assert len(clean_geographic_data(preparado)) == len(df)  # todos aparecem no mapa


def test_mapa_aceita_bairros_novos_dentro_do_recife():
    # bairro fora da lista original, mas dentro do Recife
    assert DataValidator.validate_coordinates_flexible(-8.0258, -34.9150, "Casa Amarela")
    # bairro da lista original continua sendo conferido pelo centro do bairro
    assert not DataValidator.validate_coordinates_flexible(-8.0258, -34.9150, "Boa Viagem")
    # fora do Recife (Olinda) continua sendo descartado
    assert not DataValidator.validate_coordinates_flexible(-7.90, -34.84, "Bairro Novo")


def test_formatacao_brasileira_de_numeros():
    from ui import formatar_numero
    assert formatar_numero(3482) == "3.482"
    assert formatar_numero(33.7) == "33,7"
    assert formatar_numero(1234567.891, casas=2) == "1.234.567,89"
    assert formatar_numero("33.7%") == "33,7%"
    assert formatar_numero("3,482") == "3.482" and formatar_numero("+1,234") == "+1.234"
    assert formatar_numero("Alto") == "Alto"
    assert formatar_numero(formatar_numero(1468)) == "1.468"  # não formata duas vezes


def test_dataset_tem_horario_constante_e_e_detectado():
    """Inconsistência do dataset: todas as ocorrências às 19h."""
    from ui import horario_constante
    df = pd.read_csv(DATA, parse_dates=["data_ocorrencia"])
    df["hora"] = df["data_ocorrencia"].dt.hour
    assert horario_constante(df)
    df.loc[df.index[0], "hora"] = 3
    assert not horario_constante(df)
