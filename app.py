from flask import Flask, jsonify, render_template, request

from agents.agent1.manipulacao_dados import Agent1
from agents.agent2.classificacao import Agent2


app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/extrair", methods=["POST"])
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