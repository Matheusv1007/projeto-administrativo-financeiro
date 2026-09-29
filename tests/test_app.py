import io
import unittest
from unittest.mock import patch

from app import app


class AppTestCase(unittest.TestCase):

    def setUp(self):
        app.config.update(
            TESTING=True,
            SECRET_KEY="segredo-de-teste",
            APP_USERNAME="professor",
            APP_PASSWORD="senha-teste"
        )

        self.client = app.test_client()

    def fazer_login(self):
        return self.client.post(
            "/login",
            data={
                "usuario": "professor",
                "senha": "senha-teste"
            }
        )

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
            response.get_json()["tiposDespesa"],
            ["ADMINISTRATIVAS"]
        )
        agent1_mock.assert_called_once_with(
            api_key="chave-temporaria"
        )
        agent2_mock.assert_called_once_with(
            api_key="chave-temporaria"
        )

        with self.client.session_transaction() as sessao:
            self.assertNotIn("api_key", sessao)

if __name__ == "__main__":
    unittest.main()
