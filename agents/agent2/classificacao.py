import json

from services.gemini_service import GeminiService
from agents.agent2.categorias import CATEGORIAS_DESPESA


class Agent2:
    """
    Agente responsável por interpretar os produtos
    da nota fiscal e classificar a despesa.
    """

    def __init__(self, api_key=None):
        self.gemini = GeminiService(
            api_key=api_key
        )

    def classificar_despesa(self, produtos):
        """
        Recebe a lista de produtos extraída pelo Agent1
        e tenta classificar a despesa em uma das categorias
        permitidas pelo projeto.
        """

        categorias_disponiveis = list(
            CATEGORIAS_DESPESA.keys()
        )

        schema = {
            "type": "object",

            "properties": {
                "tiposDespesa": {
                    "type": "array",

                    "items": {
                        "type": "string",
                        "enum": categorias_disponiveis
                    }
                }
            },

            "required": [
                "tiposDespesa"
            ]
        }

        prompt = f"""
        Você é um agente responsável pela classificação
        financeira de despesas.

        Produtos encontrados na nota fiscal:

        {json.dumps(
            produtos,
            ensure_ascii=False,
            indent=2
        )}

        Categorias disponíveis e exemplos:

        {json.dumps(
            CATEGORIAS_DESPESA,
            ensure_ascii=False,
            indent=2
        )}

        Analise os produtos e determine qual categoria
        representa melhor a despesa.

        REGRAS IMPORTANTES:

        1. Utilize SOMENTE uma das categorias fornecidas.

        2. Não invente novas categorias.

        3. Nesta etapa, retorne no máximo UMA classificação.

        4. Considere a natureza predominante dos produtos.

        5. Só classifique quando a descrição dos produtos
           fornecer informação suficiente para justificar
           uma das categorias disponíveis.

        6. Descrições genéricas como:
           - "Produto"
           - "Produto Teste"
           - códigos sem descrição
           - nomes genéricos sem contexto
           NÃO devem ser classificados por suposição.

        7. Quando não houver informação suficiente para
           classificar a despesa com segurança,
           retorne:

           "tiposDespesa": []

        8. A resposta deve manter a estrutura em lista
           porque futuramente o sistema poderá aceitar
           mais de uma classificação por registro.
        """

        resultado = self.gemini.gerar_json(
            prompt=prompt,
            schema=schema
        )

        tipos = resultado.get(
            "tiposDespesa",
            []
        )

        # Garante que somente categorias realmente
        # existentes no projeto sejam aceitas.
        tipos_validos = [
            tipo
            for tipo in tipos
            if tipo in CATEGORIAS_DESPESA
        ]

        # Se o Gemini não tiver informação suficiente
        # para classificar, retorna lista vazia.
        if not tipos_validos:
            return []

        # Nesta etapa trabalhamos com apenas uma
        # classificação, mas mantemos a estrutura em lista.
        return tipos_validos[:1]
