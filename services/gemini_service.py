import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types, errors


# Carrega as variáveis do arquivo .env
load_dotenv()


class GeminiService:
    """
    Serviço responsável exclusivamente pela comunicação
    com a API do Gemini.

    Os Agents utilizam este serviço, mas não precisam
    conhecer detalhes de autenticação ou configuração da API.
    """

    def __init__(self, api_key=None):
        # A chave pode vir da interface ou do .env local.
        api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "A chave da API Gemini n\u00e3o foi informada."
            )

        # Busca o modelo configurado no .env.
        # Caso nao exista, utiliza o modelo padrao do projeto.
        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite"
        )

        # Cria o cliente responsável por acessar a API Gemini
        self.client = genai.Client(
            api_key=api_key
        )

    def _executar_com_retry(self, funcao, tentativas=4):
        """
        Executa uma chamada à API.

        Caso o Gemini retorne erro 503 por indisponibilidade
        temporária, tenta novamente utilizando espera progressiva.

        Esperas:
        tentativa 1 -> 1 segundo
        tentativa 2 -> 2 segundos
        tentativa 3 -> 4 segundos
        """

        ultimo_erro = None

        for tentativa in range(1, tentativas + 1):

            try:
                return funcao()

            except errors.APIError as erro:
                ultimo_erro = erro

                # Dependendo da versão do SDK, o código pode
                # aparecer em atributos diferentes.
                codigo = getattr(
                    erro,
                    "code",
                    None
                )

                if codigo is None:
                    codigo = getattr(
                        erro,
                        "status_code",
                        None
                    )

                # Se não for erro 503, não adianta tentar novamente.
                if codigo != 503 and "503" not in str(erro):
                    raise

                # Se já atingiu o limite de tentativas,
                # devolve o erro original.
                if tentativa == tentativas:
                    raise

                espera = 2 ** (tentativa - 1)

                print(
                    f"Gemini temporariamente indisponível "
                    f"(tentativa {tentativa}/{tentativas})."
                )

                print(
                    f"Nova tentativa em {espera} segundo(s)..."
                )

                time.sleep(espera)

        # Segurança adicional.
        if ultimo_erro:
            raise ultimo_erro

    def _converter_resposta_para_json(self, response):
        """
        Converte a resposta retornada pelo Gemini
        para um objeto Python.
        """

        # Quando o SDK já conseguiu interpretar o JSON
        if response.parsed is not None:
            return response.parsed

        # Segurança caso a API não devolva conteúdo
        if not response.text:
            raise ValueError(
                "O Gemini não retornou conteúdo."
            )

        # Caso parsed não esteja disponível,
        # convertemos manualmente o texto JSON.
        try:
            return json.loads(
                response.text
            )

        except json.JSONDecodeError as erro:
            raise ValueError(
                "O Gemini retornou uma resposta que "
                "não pôde ser convertida para JSON."
            ) from erro

    def gerar_json_com_pdf(
        self,
        pdf_bytes,
        prompt,
        schema
    ):
        """
        Envia um PDF juntamente com um prompt ao Gemini
        e solicita uma resposta estruturada em JSON.

        Utilizado principalmente pelo Agent1.
        """

        def fazer_requisicao():

            return self.client.models.generate_content(
                model=self.model,

                contents=[
                    # PDF enviado pelo usuário
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf"
                    ),

                    # Instruções do Agent
                    prompt
                ],

                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=schema
                )
            )

        response = self._executar_com_retry(
            fazer_requisicao
        )

        return self._converter_resposta_para_json(
            response
        )

    def gerar_json(
        self,
        prompt,
        schema
    ):
        """
        Envia somente texto ao Gemini e solicita
        uma resposta estruturada em JSON.

        Utilizado principalmente pelo Agent2.
        """

        def fazer_requisicao():

            return self.client.models.generate_content(
                model=self.model,

                contents=prompt,

                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=schema
                )
            )

        response = self._executar_com_retry(
            fazer_requisicao
        )

        return self._converter_resposta_para_json(
            response
        )
