import re

from sqlalchemy import func, select

from database import SessionLocal
from database.modelos import (
    TIPO_CLASSIFICACAO_DESPESA,
    TIPO_PESSOA_FATURADO,
    TIPO_PESSOA_FORNECEDOR,
    Classificacao,
    Pessoa
)


def _objeto(valor):
    return valor if isinstance(valor, dict) else {}


def _texto(valor):
    if not isinstance(valor, str):
        return None

    valor = valor.strip()

    return valor or None


def _somente_numeros(valor):
    texto = _texto(valor)

    if not texto:
        return None

    return re.sub(r"\D", "", texto) or None


def _formatar_documento(documento):
    if documento and len(documento) == 14:
        return (
            f"{documento[:2]}.{documento[2:5]}.{documento[5:8]}/"
            f"{documento[8:12]}-{documento[12:]}"
        )

    if documento and len(documento) == 11:
        return (
            f"{documento[:3]}.{documento[3:6]}."
            f"{documento[6:9]}-{documento[9:]}"
        )

    return documento


def _pessoa(dados, chave_nome, chave_documento):
    pessoa = _objeto(dados)

    return (
        _texto(pessoa.get(chave_nome)),
        _somente_numeros(pessoa.get(chave_documento))
    )


def _tipos_despesa(dados):
    tipos = dados.get("tiposDespesa")

    if not isinstance(tipos, list):
        return []

    return list(dict.fromkeys(
        tipo for tipo in map(_texto, tipos) if tipo
    ))


def _buscar_pessoa(sessao, tipo, razao_social, documento):
    consulta = select(Pessoa).where(Pessoa.tipo == tipo)

    if documento:
        consulta = consulta.where(Pessoa.documento == documento)
    elif razao_social:
        consulta = consulta.where(
            func.upper(Pessoa.razao_social) == razao_social.upper()
        )
    else:
        return None

    return sessao.scalars(consulta.limit(1)).first()


def _buscar_despesa(sessao, descricao):
    return sessao.scalars(
        select(Classificacao)
        .where(Classificacao.tipo == TIPO_CLASSIFICACAO_DESPESA)
        .where(
            func.upper(Classificacao.descricao) == descricao.upper()
        )
        .limit(1)
    ).first()


def _resultado_pessoa(sessao, tipo, razao_social, documento):
    pessoa = _buscar_pessoa(sessao, tipo, razao_social, documento)

    return {
        "razaoSocial": razao_social,
        "documento": _formatar_documento(documento),
        "existe": pessoa is not None,
        "id": pessoa.id if pessoa else None
    }


def analisar_dados(dados):
    """
    Consulta no banco se o fornecedor, o faturado e a
    classificacao da despesa extraidos da nota ja existem.
    """

    fornecedor = _pessoa(dados.get("fornecedor"), "razaoSocial", "cnpj")
    faturado = _pessoa(dados.get("faturado"), "nomeCompleto", "cpf")

    with SessionLocal() as sessao:
        despesas = []

        for descricao in _tipos_despesa(dados):
            classificacao = _buscar_despesa(sessao, descricao)

            despesas.append({
                "descricao": descricao,
                "existe": classificacao is not None,
                "id": classificacao.id if classificacao else None
            })

        return {
            "fornecedor": _resultado_pessoa(
                sessao,
                TIPO_PESSOA_FORNECEDOR,
                *fornecedor
            ),
            "faturado": _resultado_pessoa(
                sessao,
                TIPO_PESSOA_FATURADO,
                *faturado
            ),
            "despesas": despesas
        }
