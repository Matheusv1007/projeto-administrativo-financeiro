from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship


STATUS_ATIVO = "ATIVO"
STATUS_INATIVO = "INATIVO"

TIPO_PESSOA_FORNECEDOR = "CLIENTE-FORNECEDOR"
TIPO_PESSOA_FATURADO = "FATURADO"
TIPO_CLASSIFICACAO_DESPESA = "DESPESA"
TIPO_MOVIMENTO_APAGAR = "APAGAR"


class Base(DeclarativeBase):
    pass


# Um registro de contas pode ser classificado em uma ou mais
# classificacoes (tipos de despesa ou de receita).
movimentocontas_classificacao = Table(
    "movimentocontas_classificacao",
    Base.metadata,
    Column(
        "id_movimento_contas",
        ForeignKey("movimentocontas.id"),
        primary_key=True
    ),
    Column(
        "id_classificacao",
        ForeignKey("classificacao.id"),
        primary_key=True
    )
)


class Pessoa(Base):
    __tablename__ = "pessoas"
    __table_args__ = (
        UniqueConstraint("tipo", "documento"),
    )

    id = Column(Integer, primary_key=True)
    tipo = Column(String(30), nullable=False)
    razao_social = Column(String(255), nullable=False)
    fantasia = Column(String(255))
    # CPF ou CNPJ armazenado somente com numeros.
    documento = Column(String(14))
    status = Column(String(10), nullable=False, default=STATUS_ATIVO)


class Classificacao(Base):
    __tablename__ = "classificacao"
    __table_args__ = (
        UniqueConstraint("tipo", "descricao"),
    )

    id = Column(Integer, primary_key=True)
    tipo = Column(String(10), nullable=False)
    descricao = Column(String(150), nullable=False)
    status = Column(String(10), nullable=False, default=STATUS_ATIVO)


class MovimentoContas(Base):
    __tablename__ = "movimentocontas"

    id = Column(Integer, primary_key=True)
    tipo = Column(String(10), nullable=False)
    numero_nota_fiscal = Column(String(50))
    data_emissao = Column(Date)
    descricao = Column(Text)
    valor_total = Column(Numeric(12, 2), nullable=False)
    status = Column(String(10), nullable=False, default=STATUS_ATIVO)

    id_fornecedor_cliente = Column(
        ForeignKey("pessoas.id"),
        nullable=False
    )
    id_faturado = Column(
        ForeignKey("pessoas.id"),
        nullable=False
    )

    fornecedor_cliente = relationship(
        Pessoa,
        foreign_keys=[id_fornecedor_cliente]
    )
    faturado = relationship(
        Pessoa,
        foreign_keys=[id_faturado]
    )
    classificacoes = relationship(
        Classificacao,
        secondary=movimentocontas_classificacao
    )
    parcelas = relationship(
        "ParcelaContas",
        back_populates="movimento"
    )


class ParcelaContas(Base):
    __tablename__ = "parcelacontas"

    id = Column(Integer, primary_key=True)
    identificacao = Column(String(20), nullable=False)
    data_vencimento = Column(Date)
    valor_parcela = Column(Numeric(12, 2))

    id_movimento_contas = Column(
        ForeignKey("movimentocontas.id"),
        nullable=False
    )

    movimento = relationship(
        MovimentoContas,
        back_populates="parcelas"
    )
