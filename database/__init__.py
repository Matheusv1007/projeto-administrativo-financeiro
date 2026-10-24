from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.modelos import Base


BANCO_LOCAL = Path(__file__).resolve().parent.parent / "financeiro.db"

SessionLocal = sessionmaker(expire_on_commit=False)


def url_do_banco(database_url):
    """
    Usa o banco informado em DATABASE_URL (PostgreSQL no Render).
    Sem DATABASE_URL, utiliza um arquivo SQLite local.
    """

    if not database_url:
        return f"sqlite:///{BANCO_LOCAL.as_posix()}"

    # Alguns provedores ainda informam o prefixo antigo.
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url[len("postgres://"):]

    return database_url


def configurar_banco(database_url=None):
    """Conecta ao banco e cria as tabelas que ainda nao existem."""

    url = url_do_banco(database_url)
    opcoes = {"pool_pre_ping": True}

    # Banco em memoria precisa compartilhar uma unica conexao.
    if url == "sqlite://":
        opcoes = {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False}
        }

    engine = create_engine(url, **opcoes)

    Base.metadata.create_all(engine)
    SessionLocal.configure(bind=engine)

    return engine
