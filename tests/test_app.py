import unittest

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

if __name__ == "__main__":
    unittest.main()
