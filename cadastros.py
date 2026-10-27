from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)
from sqlalchemy import func, or_, select

from database import SessionLocal
from database.modelos import (
    STATUS_ATIVO,
    STATUS_INATIVO,
    TIPO_CLASSIFICACAO_DESPESA,
    TIPO_CLASSIFICACAO_RECEITA,
    TIPO_PESSOA_FATURADO,
    TIPO_PESSOA_FORNECEDOR,
    Classificacao,
    Pessoa
)
from services.lancamento_service import formatar_documento, somente_numeros


cadastros = Blueprint("cadastros", __name__)


PESSOAS = {
    "clientes-fornecedores": {
        "tipo": TIPO_PESSOA_FORNECEDOR,
        "titulo": "Clientes / Fornecedores",
        "singular": "Cliente / Fornecedor",
        "novo": "Inserir Novo Cliente / Fornecedor"
    },
    "faturados": {
        "tipo": TIPO_PESSOA_FATURADO,
        "titulo": "Faturados",
        "singular": "Faturado",
        "novo": "Inserir Novo Faturado"
    }
}

CLASSIFICACOES = {
    "tipos-despesa": {
        "tipo": TIPO_CLASSIFICACAO_DESPESA,
        "titulo": "Tipos de Despesa",
        "singular": "Tipo de Despesa",
        "novo": "Inserir Novo Tipo de Despesa"
    },
    "tipos-receita": {
        "tipo": TIPO_CLASSIFICACAO_RECEITA,
        "titulo": "Tipos de Receita",
        "singular": "Tipo de Receita",
        "novo": "Inserir Novo Tipo de Receita"
    }
}


@cadastros.before_request
def exigir_login():
    if not session.get("autenticado"):
        return redirect(url_for("login"))


def _config(grupo, slug):
    config = grupo.get(slug)

    if config is None:
        abort(404)

    return config


def _obter(sessao, modelo, registro_id, **filtros):
    registro = sessao.get(modelo, registro_id)

    if registro is None or any(
        getattr(registro, campo) != valor
        for campo, valor in filtros.items()
    ):
        abort(404)

    return registro


def _formatar_data(valor):
    return valor.strftime("%d/%m/%Y") if valor else ""


def _formatar_moeda(valor):
    if valor is None:
        return ""

    texto = f"{valor:,.2f}"

    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _parametros_lista():
    return {
        "q": request.args.get("q", "").strip(),
        "todos": request.args.get("todos") == "1",
        "ordem": request.args.get("ordem", ""),
        "direcao": (
            "desc" if request.args.get("direcao") == "desc" else "asc"
        )
    }


def _listar(sessao, consulta, modelo, filtro_termo, colunas, parametros):
    """
    Tabela inicia vazia. TODOS traz apenas registros ATIVOS.
    BUSCAR aceita mais de um termo: cada termo deve aparecer
    em alguma das colunas pesquisadas.
    """

    if not parametros["q"] and not parametros["todos"]:
        return None

    if parametros["todos"]:
        consulta = consulta.where(modelo.status == STATUS_ATIVO)
    else:
        for termo in parametros["q"].split():
            consulta = consulta.where(filtro_termo(termo))

    coluna = colunas.get(parametros["ordem"]) or next(iter(colunas.values()))

    consulta = consulta.order_by(
        coluna.desc() if parametros["direcao"] == "desc" else coluna.asc(),
        modelo.id
    )

    return sessao.scalars(consulta).unique().all()


def _linha(registro, valores, endpoint, **rota):
    return {
        "ativo": registro.status == STATUS_ATIVO,
        "valores": valores,
        "editar": url_for(
            f"cadastros.editar_{endpoint}", registro_id=registro.id, **rota
        ),
        "excluir": url_for(
            f"cadastros.excluir_{endpoint}", registro_id=registro.id, **rota
        ),
        "reativar": url_for(
            f"cadastros.reativar_{endpoint}", registro_id=registro.id, **rota
        )
    }


def _renderizar_lista(config, colunas, linhas, parametros, placeholder, url_novo):
    return render_template(
        "cadastros/lista.html",
        config=config,
        colunas=colunas,
        linhas=linhas,
        parametros=parametros,
        placeholder=placeholder,
        url_novo=url_novo
    )


def _voltar(url_lista):
    retorno = request.form.get("retorno", "")

    if retorno.startswith("/") and not retorno.startswith("//"):
        return redirect(retorno)

    return redirect(url_lista)


def _alterar_status(modelo, registro_id, status, url_lista, **filtros):
    with SessionLocal.begin() as sessao:
        registro = _obter(sessao, modelo, registro_id, **filtros)
        registro.status = status

    flash(
        "Registro inativado com sucesso."
        if status == STATUS_INATIVO
        else "Registro reativado com sucesso.",
        "success"
    )

    return _voltar(url_lista)


# ---------------------------------------------------------------
# MANTER PESSOAS (Clientes / Fornecedores e Faturados)
# ---------------------------------------------------------------

def _filtro_pessoa(termo):
    condicoes = [
        Pessoa.razao_social.ilike(f"%{termo}%"),
        Pessoa.fantasia.ilike(f"%{termo}%")
    ]
    numeros = somente_numeros(termo)

    if numeros:
        condicoes.append(Pessoa.documento.like(f"%{numeros}%"))

    return or_(*condicoes)


@cadastros.route("/pessoas/<slug>")
def listar_pessoas(slug):
    config = _config(PESSOAS, slug)
    parametros = _parametros_lista()

    with SessionLocal() as sessao:
        registros = _listar(
            sessao,
            select(Pessoa).where(Pessoa.tipo == config["tipo"]),
            Pessoa,
            _filtro_pessoa,
            {
                "razao_social": Pessoa.razao_social,
                "fantasia": Pessoa.fantasia,
                "documento": Pessoa.documento
            },
            parametros
        )

    linhas = None if registros is None else [
        _linha(
            pessoa,
            [
                pessoa.razao_social,
                pessoa.fantasia or "",
                formatar_documento(pessoa.documento) or ""
            ],
            "pessoa",
            slug=slug
        )
        for pessoa in registros
    ]

    return _renderizar_lista(
        config,
        [
            ("Raz\u00e3o Social / Nome", "razao_social"),
            ("Fantasia", "fantasia"),
            ("CPF / CNPJ", "documento")
        ],
        linhas,
        parametros,
        "Buscar por raz\u00e3o social, fantasia ou CPF/CNPJ...",
        url_for("cadastros.novo_pessoa", slug=slug)
    )


def _salvar_pessoa(config, slug, pessoa_id=None):
    form = {
        "razao_social": request.form.get("razao_social", "").strip(),
        "fantasia": request.form.get("fantasia", "").strip(),
        "documento": request.form.get("documento", "").strip()
    }
    documento = somente_numeros(form["documento"])
    erros = []

    if not form["razao_social"]:
        erros.append("Informe a raz\u00e3o social / nome.")

    if documento and len(documento) not in (11, 14):
        erros.append("O CPF deve ter 11 d\u00edgitos e o CNPJ, 14.")

    with SessionLocal.begin() as sessao:
        if documento and not erros:
            duplicado = sessao.scalars(
                select(Pessoa.id)
                .where(Pessoa.tipo == config["tipo"])
                .where(Pessoa.documento == documento)
                .where(Pessoa.id != (pessoa_id or 0))
            ).first()

            if duplicado:
                erros.append("J\u00e1 existe um cadastro com este CPF/CNPJ.")

        if erros:
            return render_template(
                "cadastros/pessoa_form.html",
                config=config,
                slug=slug,
                form=form,
                erros=erros,
                editando=pessoa_id is not None
            )

        if pessoa_id is None:
            # No CREATE o STATUS nao aparece no formulario: nasce ATIVO.
            pessoa = Pessoa(tipo=config["tipo"], status=STATUS_ATIVO)
            sessao.add(pessoa)
        else:
            # No UPDATE o STATUS nao aparece e nao e alterado.
            pessoa = _obter(sessao, Pessoa, pessoa_id, tipo=config["tipo"])

        pessoa.razao_social = form["razao_social"]
        pessoa.fantasia = form["fantasia"] or None
        pessoa.documento = documento

    flash("Registro salvo com sucesso.", "success")

    return redirect(url_for("cadastros.listar_pessoas", slug=slug))


@cadastros.route("/pessoas/<slug>/novo", methods=["GET", "POST"])
def novo_pessoa(slug):
    config = _config(PESSOAS, slug)

    if request.method == "POST":
        return _salvar_pessoa(config, slug)

    return render_template(
        "cadastros/pessoa_form.html",
        config=config,
        slug=slug,
        form={},
        erros=[],
        editando=False
    )


@cadastros.route(
    "/pessoas/<slug>/<int:registro_id>/editar",
    methods=["GET", "POST"]
)
def editar_pessoa(slug, registro_id):
    config = _config(PESSOAS, slug)

    if request.method == "POST":
        return _salvar_pessoa(config, slug, registro_id)

    with SessionLocal() as sessao:
        pessoa = _obter(sessao, Pessoa, registro_id, tipo=config["tipo"])
        form = {
            "razao_social": pessoa.razao_social,
            "fantasia": pessoa.fantasia or "",
            "documento": formatar_documento(pessoa.documento) or ""
        }

    return render_template(
        "cadastros/pessoa_form.html",
        config=config,
        slug=slug,
        form=form,
        erros=[],
        editando=True
    )


@cadastros.route("/pessoas/<slug>/<int:registro_id>/excluir", methods=["POST"])
def excluir_pessoa(slug, registro_id):
    config = _config(PESSOAS, slug)

    return _alterar_status(
        Pessoa,
        registro_id,
        STATUS_INATIVO,
        url_for("cadastros.listar_pessoas", slug=slug),
        tipo=config["tipo"]
    )


@cadastros.route("/pessoas/<slug>/<int:registro_id>/reativar", methods=["POST"])
def reativar_pessoa(slug, registro_id):
    config = _config(PESSOAS, slug)

    return _alterar_status(
        Pessoa,
        registro_id,
        STATUS_ATIVO,
        url_for("cadastros.listar_pessoas", slug=slug),
        tipo=config["tipo"]
    )


# ---------------------------------------------------------------
# MANTER CLASSIFICACAO (Tipos de Despesa e Tipos de Receita)
# ---------------------------------------------------------------

def _filtro_classificacao(termo):
    return Classificacao.descricao.ilike(f"%{termo}%")


@cadastros.route("/classificacoes/<slug>")
def listar_classificacoes(slug):
    config = _config(CLASSIFICACOES, slug)
    parametros = _parametros_lista()

    with SessionLocal() as sessao:
        registros = _listar(
            sessao,
            select(Classificacao).where(
                Classificacao.tipo == config["tipo"]
            ),
            Classificacao,
            _filtro_classificacao,
            {"descricao": Classificacao.descricao},
            parametros
        )

    linhas = None if registros is None else [
        _linha(
            classificacao,
            [classificacao.descricao],
            "classificacao",
            slug=slug
        )
        for classificacao in registros
    ]

    return _renderizar_lista(
        config,
        [("Descri\u00e7\u00e3o", "descricao")],
        linhas,
        parametros,
        "Buscar por descri\u00e7\u00e3o...",
        url_for("cadastros.novo_classificacao", slug=slug)
    )


def _salvar_classificacao(config, slug, classificacao_id=None):
    form = {"descricao": request.form.get("descricao", "").strip()}
    erros = []

    if not form["descricao"]:
        erros.append("Informe a descri\u00e7\u00e3o.")

    with SessionLocal.begin() as sessao:
        if not erros:
            duplicado = sessao.scalars(
                select(Classificacao.id)
                .where(Classificacao.tipo == config["tipo"])
                .where(
                    func.upper(Classificacao.descricao)
                    == form["descricao"].upper()
                )
                .where(Classificacao.id != (classificacao_id or 0))
            ).first()

            if duplicado:
                erros.append("J\u00e1 existe um cadastro com esta descri\u00e7\u00e3o.")

        if erros:
            return render_template(
                "cadastros/classificacao_form.html",
                config=config,
                slug=slug,
                form=form,
                erros=erros,
                editando=classificacao_id is not None
            )

        if classificacao_id is None:
            classificacao = Classificacao(
                tipo=config["tipo"],
                status=STATUS_ATIVO
            )
            sessao.add(classificacao)
        else:
            classificacao = _obter(
                sessao,
                Classificacao,
                classificacao_id,
                tipo=config["tipo"]
            )

        classificacao.descricao = form["descricao"]

    flash("Registro salvo com sucesso.", "success")

    return redirect(url_for("cadastros.listar_classificacoes", slug=slug))


@cadastros.route("/classificacoes/<slug>/novo", methods=["GET", "POST"])
def novo_classificacao(slug):
    config = _config(CLASSIFICACOES, slug)

    if request.method == "POST":
        return _salvar_classificacao(config, slug)

    return render_template(
        "cadastros/classificacao_form.html",
        config=config,
        slug=slug,
        form={},
        erros=[],
        editando=False
    )


@cadastros.route(
    "/classificacoes/<slug>/<int:registro_id>/editar",
    methods=["GET", "POST"]
)
def editar_classificacao(slug, registro_id):
    config = _config(CLASSIFICACOES, slug)

    if request.method == "POST":
        return _salvar_classificacao(config, slug, registro_id)

    with SessionLocal() as sessao:
        classificacao = _obter(
            sessao,
            Classificacao,
            registro_id,
            tipo=config["tipo"]
        )
        form = {"descricao": classificacao.descricao}

    return render_template(
        "cadastros/classificacao_form.html",
        config=config,
        slug=slug,
        form=form,
        erros=[],
        editando=True
    )


@cadastros.route(
    "/classificacoes/<slug>/<int:registro_id>/excluir",
    methods=["POST"]
)
def excluir_classificacao(slug, registro_id):
    config = _config(CLASSIFICACOES, slug)

    return _alterar_status(
        Classificacao,
        registro_id,
        STATUS_INATIVO,
        url_for("cadastros.listar_classificacoes", slug=slug),
        tipo=config["tipo"]
    )


@cadastros.route(
    "/classificacoes/<slug>/<int:registro_id>/reativar",
    methods=["POST"]
)
def reativar_classificacao(slug, registro_id):
    config = _config(CLASSIFICACOES, slug)

    return _alterar_status(
        Classificacao,
        registro_id,
        STATUS_ATIVO,
        url_for("cadastros.listar_classificacoes", slug=slug),
        tipo=config["tipo"]
    )
