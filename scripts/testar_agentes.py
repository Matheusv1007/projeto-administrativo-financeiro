import json
import sys
from pathlib import Path

from agents.agent1.manipulacao_dados import Agent1
from agents.agent2.classificacao import Agent2


def main():
    if len(sys.argv) < 2:
        print(
            'Uso: python -m scripts.testar_agentes '
            '"caminho/nota.pdf"'
        )
        return

    caminho_pdf = Path(sys.argv[1])

    if not caminho_pdf.exists():
        print(f"Arquivo não encontrado: {caminho_pdf}")
        return

    print("Lendo PDF...")

    pdf_bytes = caminho_pdf.read_bytes()

    print("Executando Agent1...")

    agent1 = Agent1()
    dados = agent1.extrair_dados(pdf_bytes)

    print("Agent1 concluído.")
    print("Executando Agent2...")

    agent2 = Agent2()

    tipos_despesa = agent2.classificar_despesa(
        dados["descricaoProdutos"]
    )

    dados["tiposDespesa"] = tipos_despesa

    print("\nJSON FINAL:\n")

    print(
        json.dumps(
            dados,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()