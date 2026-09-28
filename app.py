import os
import secrets
from functools import wraps

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from agents.agent1.manipulacao_dados import Agent1
from agents.agent2.classificacao import Agent2


app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
app.config["SECRET_KEY"] = (
    os.getenv("SECRET_KEY") or secrets.token_hex(32)
)
app.config["APP_USERNAME"] = os.getenv("APP_USERNAME")
app.config["APP_PASSWORD"] = os.getenv("APP_PASSWORD")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def login_obrigatorio(funcao):
    """Protege rotas que exigem uma sessao autenticada."""

    @wraps(funcao)
    def funcao_protegida(*args, **kwargs):
        if not session.get("autenticado"):
            if request.path == "/extrair":
                return jsonify({
                    "erro": "Sua sess\u00e3o expirou. Fa\u00e7a login novamente."
                }), 401

            return redirect(url_for("login"))

        return funcao(*args, **kwargs)

    return funcao_protegida


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("autenticado"):
        return redirect(url_for("index"))

    erro = None

    if request.method == "POST":
        usuario_configurado = app.config.get("APP_USERNAME")
        senha_configurada = app.config.get("APP_PASSWORD")

        if not usuario_configurado or not senha_configurada:
            erro = (
                "O acesso ainda n\u00e3o foi configurado. "
                "Defina APP_USERNAME e APP_PASSWORD."
            )
        else:
            usuario = request.form.get("usuario", "").strip()
            senha = request.form.get("senha", "")

            usuario_valido = secrets.compare_digest(
                usuario,
                usuario_configurado
            )
            senha_valida = secrets.compare_digest(
                senha,
                senha_configurada
            )

            if usuario_valido and senha_valida:
                session.clear()
                session["autenticado"] = True

                return redirect(url_for("index"))

            erro = "Usu\u00e1rio ou senha inv\u00e1lidos."

    return render_template(
        "login.html",
        erro=erro
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()

    return redirect(url_for("login"))


@app.route("/")
@login_obrigatorio
def index():
    return render_template("index.html")


@app.route("/extrair", methods=["POST"])
@login_obrigatorio
def extrair():
    if "arquivo" not in request.files:
        return jsonify({
            "erro": "Nenhum arquivo foi enviado."
        }), 400

    arquivo = request.files["arquivo"]

    if not arquivo.filename:
        return jsonify({
            "erro": "Nenhum arquivo foi selecionado."
        }), 400

    if not arquivo.filename.lower().endswith(".pdf"):
        return jsonify({
            "erro": "O arquivo deve estar no formato PDF."
        }), 400

    try:
        pdf_bytes = arquivo.read()

        agent1 = Agent1()

        dados = agent1.extrair_dados(
            pdf_bytes
        )

        agent2 = Agent2()

        dados["tiposDespesa"] = (
            agent2.classificar_despesa(
                dados["descricaoProdutos"]
            )
        )

        return jsonify(dados)

    except Exception as erro:
        return jsonify({
            "erro": str(erro)
        }), 500


if __name__ == "__main__":
    app.run(
        debug=True
    )
