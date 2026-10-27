import copy
import io
import os
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"

from sqlalchemy import func, select

from app import app
from database import SessionLocal, configurar_banco
from database.modelos import (
    Classificacao,
    MovimentoContas,
    ParcelaContas,
    Pessoa
)
from services.lancamento_service import analisar_dados


NOTA = {
    "fornecedor": {
        "razaoSocial": "IGUA\u00c7U MAQUINAS LTDA",
        "fantasia": "IGUA\u00c7U",
        "cnpj": "11.111.111/0001-00"
    },
    "faturado": {
        "nomeCompleto": "BELTRANO DA SILVA",
        "cpf": "999.999.999-99"
    },
    "numeroNotaFiscal": "123",
    "dataEmissao": "10/10/2026",
    "descricaoProdutos": ["Filtro de \u00f3leo"],
    "quantidadeParcelas": 1,
    "parcelas": [
        {"numero": 1, "dataVencimento": "10/11/2026", "valor": None}
    ],
    "valorTotal": 350.5,
    "tiposDespesa": ["MANUTEN\u00c7\u00c3O E OPERA\u00c7\u00c3O"]
}


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        app.config.update(
            TESTING=True,
            SECRET_KEY="segredo-de-teste",
            APP_USERNAME="professor",
            APP_PASSWORD="senha-teste"
        )

        self.engine = configurar_banco("sqlite://")
        self.client = app.test_client()

    def tearDown(self):
        self.engine.dispose()

    def fazer_login(self):
        return self.client.post(
            "/login",
            data={
                "usuario": "professor",
                "senha": "senha-teste"
            }
        )


class AppTestCase(BaseTestCase):

    def test_index_redireciona_para_login(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_extracao_sem_login_retorna_401(self):
        response = self.client.post("/extrair")

        self.assertEqual(response.status_code, 401)
        self.assertIn("sess\u00e3o", response.get_json()["erro"])

    def test_login_com_credenciais_invalidas(self):
        response = self.client.post(
            "/login",
            data={
                "usuario": "professor",
                "senha": "incorreta"
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Usu\u00e1rio ou senha inv\u00e1lidos.".encode(),
            response.data
        )

    def test_login_e_logout(self):
        response = self.fazer_login()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/"))

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Extrair Dados", response.data)

        response = self.client.post("/logout")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_extracao_exige_chave(self):
        self.fazer_login()

        response = self.client.post(
            "/extrair",
            data={
                "arquivo": (io.BytesIO(b"pdf"), "nota.pdf")
            },
            content_type="multipart/form-data"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["erro"],
            "Informe a chave da API Gemini."
        )

    @patch("app.Agent2")
    @patch("app.Agent1")
    def test_extracao_usa_chave_informada(
        self,
        agent1_mock,
        agent2_mock
    ):
        self.fazer_login()

        agent1_mock.return_value.extrair_dados.return_value = {
            "descricaoProdutos": ["Produto de teste"]
        }
        agent2_mock.return_value.classificar_despesa.return_value = [
            "ADMINISTRATIVAS"
        ]

        response = self.client.post(
            "/extrair",
            data={
                "api_key": "chave-temporaria",
                "arquivo": (io.BytesIO(b"pdf"), "nota.pdf")
            },
            content_type="multipart/form-data"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["dados"]["tiposDespesa"],
            ["ADMINISTRATIVAS"]
        )
        self.assertIn("analise", response.get_json())
        agent1_mock.assert_called_once_with(
            api_key="chave-temporaria"
        )
        agent2_mock.assert_called_once_with(
            api_key="chave-temporaria"
        )

        with self.client.session_transaction() as sessao:
            self.assertNotIn("api_key", sessao)


class LancamentoTestCase(BaseTestCase):

    def lancar(self, dados):
        return self.client.post("/lancar", json={"dados": dados})

    def contar(self, modelo):
        with SessionLocal() as sessao:
            return sessao.scalar(select(func.count()).select_from(modelo))

    def test_lancar_sem_login_retorna_401(self):
        response = self.lancar(NOTA)

        self.assertEqual(response.status_code, 401)

    def test_lancamento_cria_registros_e_consulta_passa_a_encontrar(self):
        analise = analisar_dados(NOTA)

        self.assertFalse(analise["fornecedor"]["existe"])
        self.assertFalse(analise["faturado"]["existe"])
        self.assertFalse(analise["despesas"][0]["existe"])

        self.fazer_login()
        response = self.lancar(NOTA)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["mensagem"],
            "Registro lan\u00e7ado com sucesso."
        )

        analise = analisar_dados(NOTA)

        with SessionLocal() as sessao:
            movimento = sessao.scalars(select(MovimentoContas)).one()

            self.assertEqual(movimento.tipo, "APAGAR")
            self.assertEqual(movimento.data_emissao, date(2026, 10, 10))
            self.assertEqual(movimento.valor_total, Decimal("350.50"))
            self.assertEqual(movimento.status, "ATIVO")

            fornecedor = movimento.fornecedor_cliente
            self.assertEqual(fornecedor.tipo, "CLIENTE-FORNECEDOR")
            self.assertEqual(fornecedor.documento, "11111111000100")
            self.assertEqual(fornecedor.status, "ATIVO")
            self.assertEqual(
                analise["fornecedor"],
                {
                    "razaoSocial": "IGUA\u00c7U MAQUINAS LTDA",
                    "documento": "11.111.111/0001-00",
                    "existe": True,
                    "id": fornecedor.id
                }
            )

            self.assertEqual(movimento.faturado.tipo, "FATURADO")
            self.assertEqual(
                analise["faturado"]["id"],
                movimento.faturado.id
            )

            [classificacao] = movimento.classificacoes
            self.assertEqual(classificacao.tipo, "DESPESA")
            self.assertEqual(
                analise["despesas"],
                [{
                    "descricao": "MANUTEN\u00c7\u00c3O E OPERA\u00c7\u00c3O",
                    "existe": True,
                    "id": classificacao.id
                }]
            )

            [parcela] = movimento.parcelas
            self.assertEqual(parcela.identificacao, "\u00daNICA")
            self.assertEqual(parcela.data_vencimento, date(2026, 11, 10))
            self.assertEqual(parcela.valor_parcela, Decimal("350.50"))

    def test_novo_lancamento_reutiliza_cadastros_existentes(self):
        self.fazer_login()

        self.assertEqual(self.lancar(NOTA).status_code, 200)
        self.assertEqual(self.lancar(NOTA).status_code, 200)

        self.assertEqual(self.contar(Pessoa), 2)
        self.assertEqual(self.contar(Classificacao), 1)
        self.assertEqual(self.contar(MovimentoContas), 2)

    def test_parcelas_com_vencimentos_distintos(self):
        nota = copy.deepcopy(NOTA)
        nota["parcelas"] = [
            {"numero": 1, "dataVencimento": "10/11/2026", "valor": 175.25},
            {"numero": 2, "dataVencimento": "10/12/2026", "valor": 175.25}
        ]

        self.fazer_login()
        self.assertEqual(self.lancar(nota).status_code, 200)

        with SessionLocal() as sessao:
            parcelas = sessao.scalars(
                select(ParcelaContas).order_by(ParcelaContas.id)
            ).all()

        self.assertEqual(
            [
                (p.identificacao, p.data_vencimento, p.valor_parcela)
                for p in parcelas
            ],
            [
                ("1/2", date(2026, 11, 10), Decimal("175.25")),
                ("2/2", date(2026, 12, 10), Decimal("175.25"))
            ]
        )

    def test_sem_classificacao_nao_lanca_nada(self):
        nota = copy.deepcopy(NOTA)
        nota["tiposDespesa"] = []

        self.fazer_login()
        response = self.lancar(nota)

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "classifica\u00e7\u00e3o da despesa",
            response.get_json()["erro"]
        )
        self.assertEqual(self.contar(Pessoa), 0)
        self.assertEqual(self.contar(MovimentoContas), 0)


class CadastrosTestCase(BaseTestCase):

    URL = "/pessoas/clientes-fornecedores"

    def setUp(self):
        super().setUp()
        self.fazer_login()

    def criar_pessoa(self, razao_social, documento):
        return self.client.post(
            self.URL + "/novo",
            data={"razao_social": razao_social, "documento": documento}
        )

    def status_da_pessoa(self, razao_social):
        with SessionLocal() as sessao:
            return sessao.scalars(
                select(Pessoa.status)
                .where(Pessoa.razao_social == razao_social)
            ).one()

    def test_cadastros_exigem_login(self):
        self.client.post("/logout")

        response = self.client.get(self.URL + "?todos=1")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_tabela_inicia_vazia_e_todos_traz_somente_ativos(self):
        self.criar_pessoa("ALFA LTDA", "11.111.111/0001-11")
        self.criar_pessoa("BETA LTDA", "22.222.222/0001-22")
        self.assertEqual(self.status_da_pessoa("ALFA LTDA"), "ATIVO")

        with SessionLocal() as sessao:
            beta = sessao.scalars(
                select(Pessoa.id).where(Pessoa.razao_social == "BETA LTDA")
            ).one()

        self.client.post(f"{self.URL}/{beta}/excluir")

        inicial = self.client.get(self.URL).get_data(as_text=True)
        todos = self.client.get(self.URL + "?todos=1").get_data(as_text=True)

        self.assertNotIn("ALFA LTDA", inicial)
        self.assertIn("ALFA LTDA", todos)
        self.assertNotIn("BETA LTDA", todos)

    def test_excluir_inativa_e_reativar_volta_a_ativo(self):
        self.criar_pessoa("ALFA LTDA", "11.111.111/0001-11")

        with SessionLocal() as sessao:
            alfa = sessao.scalars(select(Pessoa.id)).one()

        self.client.post(f"{self.URL}/{alfa}/excluir")

        self.assertEqual(self.contar_pessoas(), 1)
        self.assertEqual(self.status_da_pessoa("ALFA LTDA"), "INATIVO")

        busca = self.client.get(self.URL + "?q=alfa").get_data(as_text=True)
        self.assertIn("Reativar", busca)

        self.client.post(f"{self.URL}/{alfa}/reativar")

        self.assertEqual(self.status_da_pessoa("ALFA LTDA"), "ATIVO")

    def contar_pessoas(self):
        with SessionLocal() as sessao:
            return sessao.scalar(select(func.count()).select_from(Pessoa))

    def test_busca_exige_todos_os_termos(self):
        self.criar_pessoa("ALFA COMERCIO LTDA", "11.111.111/0001-11")
        self.criar_pessoa("ALFA SERVICOS LTDA", "22.222.222/0001-22")

        pagina = self.client.get(
            self.URL + "?q=alfa+22222222"
        ).get_data(as_text=True)

        self.assertIn("ALFA SERVICOS LTDA", pagina)
        self.assertNotIn("ALFA COMERCIO LTDA", pagina)

    def test_conta_com_parcelas_de_vencimento_repetido_e_recusada(self):
        self.criar_pessoa("ALFA LTDA", "11.111.111/0001-11")
        self.client.post(
            "/pessoas/faturados/novo",
            data={"razao_social": "FULANO", "documento": ""}
        )
        self.client.post(
            "/classificacoes/tipos-despesa/novo",
            data={"descricao": "ADMINISTRATIVAS"}
        )

        with SessionLocal() as sessao:
            fornecedor, faturado = sessao.scalars(
                select(Pessoa.id).order_by(Pessoa.id)
            ).all()
            despesa = sessao.scalars(select(Classificacao.id)).one()

        dados = {
            "id_pessoa": fornecedor,
            "id_faturado": faturado,
            "valor_total": "200.00",
            "classificacoes": [despesa],
            "parcela_vencimento": ["2026-11-10", "2026-11-10"],
            "parcela_valor": ["100.00", "100.00"]
        }

        response = self.client.post("/contas/pagar/novo", data=dados)

        self.assertIn(
            "datas de vencimento distintas",
            response.get_data(as_text=True)
        )
        self.assertEqual(self.contar_movimentos(), 0)

        dados["parcela_vencimento"] = ["2026-11-10", "2026-12-10"]
        response = self.client.post("/contas/pagar/novo", data=dados)

        self.assertEqual(response.status_code, 302)

        with SessionLocal() as sessao:
            movimento = sessao.scalars(select(MovimentoContas)).one()

            self.assertEqual(movimento.tipo, "APAGAR")
            self.assertEqual(movimento.status, "ATIVO")
            self.assertEqual(
                [p.identificacao for p in movimento.parcelas],
                ["1/2", "2/2"]
            )

    def contar_movimentos(self):
        with SessionLocal() as sessao:
            return sessao.scalar(
                select(func.count()).select_from(MovimentoContas)
            )



if __name__ == "__main__":
    unittest.main()
