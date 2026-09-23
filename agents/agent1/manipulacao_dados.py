import re

from services.gemini_service import GeminiService


SCHEMA_NOTA_FISCAL = {
    "type": "object",

    "properties": {
        "fornecedor": {
            "type": "object",

            "properties": {
                "razaoSocial": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"}
                    ]
                },

                "fantasia": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"}
                    ]
                },

                "cnpj": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"}
                    ]
                }
            },

            "required": [
                "razaoSocial",
                "fantasia",
                "cnpj"
            ]
        },

        "faturado": {
            "type": "object",

            "properties": {
                "nomeCompleto": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"}
                    ]
                },

                "cpf": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"}
                    ]
                }
            },

            "required": [
                "nomeCompleto",
                "cpf"
            ]
        },

        "numeroNotaFiscal": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"}
            ]
        },

        "dataEmissao": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"}
            ]
        },

        "descricaoProdutos": {
            "type": "array",

            "items": {
                "type": "string"
            }
        },

        "quantidadeParcelas": {
            "type": "integer"
        },

        "parcelas": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {
                    "numero": {
                        "type": "integer"
                    },

                    "dataVencimento": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"}
                        ]
                    }
                },

                "required": [
                    "numero",
                    "dataVencimento"
                ]
            }
        },

        "valorTotal": {
            "anyOf": [
                {"type": "number"},
                {"type": "null"}
            ]
        }
    },

    "required": [
        "fornecedor",
        "faturado",
        "numeroNotaFiscal",
        "dataEmissao",
        "descricaoProdutos",
        "quantidadeParcelas",
        "parcelas",
        "valorTotal"
    ]
}


class Agent1:
    """
    Agente responsável pela extração dos dados da nota fiscal.
    """

    def __init__(self):
        self.gemini = GeminiService()

    def extrair_dados(self, pdf_bytes):

        prompt = """
        Você é um agente especializado na extração de dados
        de notas fiscais brasileiras.

        Analise exclusivamente o documento PDF enviado.

        Extraia:

        - Razão Social do fornecedor
        - Nome Fantasia do fornecedor
        - CNPJ do fornecedor
        - Nome completo do faturado/destinatário
        - CPF do faturado/destinatário
        - Número da Nota Fiscal
        - Data de Emissão
        - Descrição de todos os produtos
        - Parcelas e suas respectivas datas de vencimento
        - Valor Total da Nota Fiscal

        REGRAS IMPORTANTES:

        1. Não invente informações.

        2. Quando uma informação não estiver presente no documento,
           retorne null.

        3. Em descricaoProdutos, informe somente a descrição dos produtos.

        4. Não classifique a despesa. Essa responsabilidade pertence
           a outro agente.

        5. valorTotal deve representar o VALOR TOTAL DA NOTA,
           e não o valor total dos produtos.

        6. Datas devem permanecer no formato DD/MM/AAAA.

        7. Valores monetários devem ser números.

        8. O campo cpf deve conter somente CPF de pessoa física.
           Se o documento apresentar um CNPJ para o destinatário,
           retorne null no campo cpf.
        """

        dados = self.gemini.gerar_json_com_pdf(
            pdf_bytes=pdf_bytes,
            prompt=prompt,
            schema=SCHEMA_NOTA_FISCAL
        )

        # Calcula a quantidade de parcelas encontrada
        parcelas = dados.get("parcelas", [])

        dados["quantidadeParcelas"] = len(parcelas)

        # Validação adicional do CPF
        cpf = dados.get("faturado", {}).get("cpf")

        if cpf:
            # Remove ponto, traço e qualquer caractere
            # que não seja número.
            somente_numeros = re.sub(
                r"\D",
                "",
                cpf
            )

            # Um CPF possui 11 dígitos.
            # Se vier CNPJ, por exemplo, terá 14.
            if len(somente_numeros) != 11:
                dados["faturado"]["cpf"] = None

        return dados