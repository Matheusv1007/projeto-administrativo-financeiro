import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select

from database import SessionLocal
from database.modelos import (
    TIPO_CLASSIFICACAO_DESPESA,
    TIPO_MOVIMENTO_APAGAR,
    TIPO_PESSOA_FATURADO,
    TIPO_PESSOA_FORNECEDOR,
    Classificacao,
    MovimentoContas,
    ParcelaContas,
    Pessoa
)


class DadosInvalidos(ValueError):
    """Dados extraidos insuficientes para lancar o registro."""


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


def _data(valor):
    texto = _texto(valor)

    if not texto:
        return None

    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None


def _valor(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None

    try:
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


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


def _obter_ou_criar_pessoa(sessao, tipo, razao_social, documento, fantasia):
    pessoa = _buscar_pessoa(sessao, tipo, razao_social, documento)

    if pessoa is None:
        pessoa = Pessoa(
            tipo=tipo,
            razao_social=razao_social,
            fantasia=fantasia,
            documento=documento
        )
        sessao.add(pessoa)

    return pessoa


def _obter_ou_criar_despesa(sessao, descricao):
    classificacao = _buscar_despesa(sessao, descricao)

    if classificacao is None:
        classificacao = Classificacao(
            tipo=TIPO_CLASSIFICACAO_DESPESA,
            descricao=descricao
        )
        sessao.add(classificacao)

    return classificacao


def _montar_parcelas(dados, valor_total):
    parcelas = [
        parcela
        for parcela in dados.get("parcelas") or []
        if isinstance(parcela, dict)
    ]

    # Todo movimento possui ao menos uma parcela.
    if not parcelas:
        parcelas = [{}]

    quantidade = len(parcelas)
    resultado = []

    for numero, parcela in enumerate(parcelas, start=1):
        valor = _valor(parcela.get("valor"))

        if valor is None and quantidade == 1:
            valor = valor_total

        resultado.append(ParcelaContas(
            identificacao=(
                "\u00daNICA" if quantidade == 1
                else f"{numero}/{quantidade}"
            ),
            data_vencimento=_data(parcela.get("dataVencimento")),
            valor_parcela=valor
        ))

    return resultado


def lancar_registro(dados):
    """
    Cria o fornecedor, o faturado e a despesa quando ainda nao
    existem e registra o movimento de contas a pagar com suas
    parcelas em uma unica transacao.
    """

    fornecedor_nome, fornecedor_documento = _pessoa(
        dados.get("fornecedor"), "razaoSocial", "cnpj"
    )
    faturado_nome, faturado_documento = _pessoa(
        dados.get("faturado"), "nomeCompleto", "cpf"
    )
    tipos_despesa = _tipos_despesa(dados)
    valor_total = _valor(dados.get("valorTotal"))

    pendencias = []

    if not fornecedor_nome:
        pendencias.append("raz\u00e3o social do fornecedor")
    if not faturado_nome:
        pendencias.append("nome do faturado")
    if not tipos_despesa:
        pendencias.append("classifica\u00e7\u00e3o da despesa")
    if valor_total is None:
        pendencias.append("valor total da nota")

    if pendencias:
        raise DadosInvalidos(
            "Registro n\u00e3o lan\u00e7ado. N\u00e3o foi poss\u00edvel "
            "identificar: " + ", ".join(pendencias) + "."
        )

    produtos = [
        produto
        for produto in map(_texto, dados.get("descricaoProdutos") or [])
        if produto
    ]

    with SessionLocal.begin() as sessao:
        fornecedor = _obter_ou_criar_pessoa(
            sessao,
            TIPO_PESSOA_FORNECEDOR,
            fornecedor_nome,
            fornecedor_documento,
            _texto(_objeto(dados.get("fornecedor")).get("fantasia"))
        )
        faturado = _obter_ou_criar_pessoa(
            sessao,
            TIPO_PESSOA_FATURADO,
            faturado_nome,
            faturado_documento,
            None
        )
        classificacoes = [
            _obter_ou_criar_despesa(sessao, descricao)
            for descricao in tipos_despesa
        ]

        movimento = MovimentoContas(
            tipo=TIPO_MOVIMENTO_APAGAR,
            numero_nota_fiscal=_texto(dados.get("numeroNotaFiscal")),
            data_emissao=_data(dados.get("dataEmissao")),
            descricao="; ".join(produtos) or None,
            valor_total=valor_total,
            fornecedor_cliente=fornecedor,
            faturado=faturado,
            classificacoes=classificacoes,
            parcelas=_montar_parcelas(dados, valor_total)
        )
        sessao.add(movimento)
        sessao.flush()

        return movimento.id
