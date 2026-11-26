"""Testes básicos do projeto. Execute com:  pytest -q"""
import os
import secrets
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security_utils import DataValidator, SecurityManager  # noqa: E402



def nova_senha() -> str:
    """Senha aleatória para os testes (nenhuma senha fixa fica no código)."""
    return secrets.token_urlsafe(12)


SENHA_TESTE = nova_senha()
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
    ok, user = manager.authenticate_user("admin", nova_senha())
    assert not ok and user is None


def test_create_user_e_duplicado(manager):
    senha = nova_senha()
    assert manager.create_user("aluna", senha) is True
    assert manager.create_user("aluna", nova_senha()) is False
    assert manager.authenticate_user("aluna", senha)[0] is True


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
    df["grave"] = df["tipo_crime"].isin(AdvancedCriminalAnalysis.SERIOUS_CRIMES)
    por_bairro = df.groupby("bairro")["grave"].nunique()
    assert (por_bairro == 2).all()

def test_indice_gravidade_usa_os_valores_reais_do_dataset():
    """Todo crime e toda arma do dataset precisam ter peso definido
    (antes os nomes não batiam e as abas usavam dados aleatórios)."""
    from dashboard_tabs import WEAPON_WEIGHTS, CRIME_WEIGHTS, calculate_gravity_index
    df = pd.read_csv(DATA)
    assert set(df["tipo_crime"].unique()) <= set(CRIME_WEIGHTS)
    assert set(df["arma_utilizada"].unique()) <= set(WEAPON_WEIGHTS)
    indice = calculate_gravity_index(df)
    assert indice.notna().all() and (indice > 0).all()


def test_indice_gravidade_calculo():
    from dashboard_tabs import calculate_gravity_index
    df = pd.DataFrame({"tipo_crime": ["Homicídio"], "arma_utilizada": ["Faca"],
                       "quantidade_vitimas": [2], "quantidade_suspeitos": [1]})
    assert calculate_gravity_index(df).iloc[0] == 10 + 3 + 2 * 2 + 1


def test_upload_converte_data_mesmo_com_pandas_3():
    """No pandas 3 colunas de texto têm dtype `str`, não `object`. A data do
    CSV enviado precisa ser convertida mesmo assim (antes dava erro no `.dt`)."""
    from violencia_domestica import prepare_uploaded_dataset
    df = pd.DataFrame({"data_ocorrencia": ["2026-01-12", "data-invalida"],
                       "tipo_crime": ["Ameaça", "Estupro"], "bairro": ["Pina", "Torre"],
                       "latitude": ["-8.08", "-8.05"], "longitude": ["-34.88", "-34.90"],
                       "status_atendimento": ["Em análise", "Encerrada"],
                       "idade_suspeito": ["Não informado", "30"]})
    out = prepare_uploaded_dataset(df)
    assert len(out) == 1  # a linha com data inválida é descartada
    assert pd.api.types.is_datetime64_any_dtype(out["data_ocorrencia"])
    assert out["mes"].iloc[0] == 1 and out["status_caso"].iloc[0] == "Em análise"
    # texto em coluna numérica vira vazio em vez de quebrar os gráficos
    assert pd.api.types.is_numeric_dtype(out["idade_suspeito"])
    assert out["idade_suspeito"].isna().iloc[0]


def test_csv_modelo_de_upload_segue_o_formato_documentado():
    from violencia_domestica import (REQUIRED_COLUMNS, OPTIONAL_COLUMNS,
                                               UPLOAD_TEMPLATE_PATH, prepare_uploaded_dataset)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    df = pd.read_csv(os.path.join(raiz, UPLOAD_TEMPLATE_PATH))
    esperadas = {c for c, _ in REQUIRED_COLUMNS + OPTIONAL_COLUMNS}
    assert set(df.columns) == esperadas
    preparado = prepare_uploaded_dataset(df)
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
    from ui import format_number
    assert format_number(3482) == "3.482"
    assert format_number(33.7) == "33,7"
    assert format_number(1234567.891, casas=2) == "1.234.567,89"
    assert format_number("33.7%") == "33,7%"
    assert format_number("3,482") == "3.482" and format_number("+1,234") == "+1.234"
    assert format_number("Alto") == "Alto"
    assert format_number(format_number(1468)) == "1.468"  # não formata duas vezes


def test_dataset_tem_horario_constante_e_e_detectado():
    """Inconsistência do dataset: todas as ocorrências às 19h."""
    from ui import has_constant_hour
    df = pd.read_csv(DATA, parse_dates=["data_ocorrencia"])
    df["hora"] = df["data_ocorrencia"].dt.hour
    assert has_constant_hour(df)
    df.loc[df.index[0], "hora"] = 3
    assert not has_constant_hour(df)


def test_senha_usa_pbkdf2_com_sal(manager):
    senha = nova_senha()
    h1, h2 = manager.hash_password(senha), manager.hash_password(senha)
    assert h1.startswith("pbkdf2_sha256$") and h1 != h2  # sal diferente a cada hash
    assert manager.verify_password(senha, h1) and not manager.verify_password(nova_senha(), h1)


def test_hash_antigo_sha256_continua_valendo_e_e_atualizado(manager):
    import hashlib
    senha = nova_senha()
    users = manager._load_users()
    users["antigo"] = {"password": hashlib.sha256(senha.encode()).hexdigest(), "role": "analyst",
                       "permissions": ["read"]}
    manager._save_users(users)
    assert manager.authenticate_user("antigo", senha)[0] is True
    assert manager._load_users()["antigo"]["password"].startswith("pbkdf2_sha256$")


def test_linha_de_previsao_preenche_todas_as_variaveis_do_treino():
    """Antes, mês, período do dia e fim de semana iam zerados para o modelo."""
    from dashboard_tabs.previsao import build_input_row
    treino = pd.DataFrame({"bairro": ["Pina", "Torre"], "hora": [19, 8],
                           "dia_semana": ["sábado", "terça-feira"], "mes": [3, 4],
                           "periodo_dia": ["Noite", "Manhã"], "fim_semana": [True, False]})
    colunas = pd.get_dummies(treino, drop_first=True).columns.tolist()
    linha = build_input_row(colunas, "Torre", "terça-feira", 8, 11).iloc[0]
    assert linha["mes"] == 11 and linha["hora"] == 8
    assert linha["bairro_Torre"] == 1 and linha["dia_semana_terça-feira"] == 1
    assert linha["periodo_dia_Noite"] == 0 and not linha["fim_semana"]


def test_relatorio_html_escapa_conteudo_do_csv():
    from violencia_domestica.relatorio import generate_html_report
    df = pd.DataFrame({"tipo_crime": ["<script>alert(1)</script>"], "bairro": ["Pina"],
                       "data_ocorrencia": pd.to_datetime(["2026-01-01 10:00"])})
    html = generate_html_report(df)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
