# Projeto Administrativo-Financeiro — Etapas 1 e 2

Projeto desenvolvido para a disciplina de **Prática de Engenharia de Software**.

Na primeira etapa foi implementado um processador de notas fiscais em PDF utilizando **Agents de IA** e a API do **Google Gemini**.

O usuário envia uma nota fiscal pela interface web e o sistema:

1. extrai os dados da nota fiscal;
2. interpreta os produtos;
3. classifica o tipo de despesa;
4. devolve os dados em formato JSON na tela.

Na segunda etapa, após a extração, o sistema analisa os dados no banco de dados:

1. consulta se o **FORNECEDOR** existe;
2. consulta se o **FATURADO** existe;
3. consulta se a classificação da **DESPESA** existe;
4. mostra na tela o resultado da consulta (`EXISTE – ID: X` ou `NÃO EXISTE`);
5. cria o fornecedor, o faturado e a despesa que ainda não existirem;
6. cria o registro do movimento (contas a pagar) e suas parcelas;
7. informa ao usuário que o registro foi lançado com sucesso.

---

## Tecnologias utilizadas

- Python
- Flask
- JavaScript
- HTML
- CSS
- Google Gemini API
- python-dotenv
- SQLAlchemy
- PostgreSQL (Render) / SQLite (local)

---

## Arquitetura

O projeto utiliza dois agentes principais.

### Agent1 — Extração

Responsável por receber a nota fiscal em PDF e extrair:

- Razão Social do fornecedor
- Nome Fantasia
- CNPJ
- Nome do faturado/destinatário
- CPF
- Número da Nota Fiscal
- Data de emissão
- Descrição dos produtos
- Parcelas
- Datas de vencimento e valores das parcelas
- Valor total

### Agent2 — Classificação

Responsável por analisar os produtos extraídos pelo Agent1 e classificar a despesa conforme as categorias definidas pelo projeto.

Exemplos:

- INSUMOS AGRÍCOLAS
- MANUTENÇÃO E OPERAÇÃO
- RECURSOS HUMANOS
- SERVIÇOS OPERACIONAIS
- INFRAESTRUTURA E UTILIDADES
- ADMINISTRATIVAS
- SEGUROS E PROTEÇÃO
- IMPOSTOS E TAXAS
- INVESTIMENTOS

Caso os produtos não tenham informação suficiente para uma classificação confiável, nenhuma categoria é atribuída.

### Análise e lançamento (Etapa 2)

Implementados em `services/lancamento_service.py`:

- `analisar_dados`: consulta fornecedor (por CNPJ), faturado (por CPF) e classificação da despesa (pela descrição). Sem documento na nota, a pessoa é consultada pelo nome.
- `lancar_registro`: em uma única transação, cria o que não existir e registra o movimento com suas parcelas.

Caso falte razão social do fornecedor, nome do faturado, classificação da despesa ou valor total, nada é gravado e a tela informa o que não foi identificado.

---

## Banco de dados

Entidades afetadas (`database/modelos.py`):

| Tabela | Conteúdo gravado |
|---|---|
| `pessoas` | Tipo `CLIENTE-FORNECEDOR` (fornecedor) ou `FATURADO`, razão social, fantasia, CPF/CNPJ, status |
| `classificacao` | Tipo `DESPESA`, descrição (ex.: `MANUTENÇÃO E OPERAÇÃO`), status |
| `movimentocontas` | Tipo `APAGAR`, número da nota, data de emissão, descrição dos produtos, valor total, status, fornecedor e faturado |
| `parcelacontas` | Identificação (`ÚNICA` ou `1/2`, `2/2`...), data de vencimento, valor da parcela |
| `movimentocontas_classificacao` | Classificações do movimento (um movimento pode ter uma ou mais) |

Cadastros criados recebem status `ATIVO`. As tabelas são criadas automaticamente na inicialização da aplicação.

---

## Fluxo da aplicação

```text
Usuário
   ↓
Upload da Nota Fiscal
   ↓
Flask
   ↓
Agent1
   ↓
Gemini
   ↓
Dados extraídos
   ↓
Agent2
   ↓
Gemini
   ↓
Classificação da despesa
   ↓
Consulta no banco (fornecedor, faturado, despesa)
   ↓
Resultado da consulta na tela
   ↓
Criação dos cadastros inexistentes + movimento + parcelas
   ↓
"Registro lançado com sucesso."
```

---

## Como executar

### 1. Clone o repositório

```bash
git clone https://github.com/Matheusv1007/projeto-administrativo-financeiro.git
```

### 2. Entre na pasta

```bash
cd projeto-administrativo-financeiro
```

### 3. Crie e ative o ambiente virtual

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 4. Instale as dependências

```bash
pip install -r requirements.txt
```

### 5. Configure o `.env`

Crie um arquivo `.env` na raiz do projeto:

```env
APP_USERNAME=professor
APP_PASSWORD=SUA_SENHA_AQUI
SECRET_KEY=UMA_CHAVE_ALEATORIA_LONGA
GEMINI_MODEL=gemini-3.5-flash-lite
DATABASE_URL=
```

Sem `DATABASE_URL`, a aplicação usa o arquivo SQLite local `financeiro.db`.

Na aplica&ccedil;&atilde;o web, a chave Gemini &eacute; informada pelo
usu&aacute;rio depois do login. Ela &eacute; usada apenas durante a
requisi&ccedil;&atilde;o e n&atilde;o &eacute; armazenada pelo sistema.

Para executar diretamente os scripts de teste pelo terminal,
adicione tamb&eacute;m `GEMINI_API_KEY` ao `.env` local.

### 6. Execute

```bash
python app.py
```

Acesse no navegador:

```text
http://127.0.0.1:5000
```

### 7. Testes

```bash
python -m unittest tests.test_app
```

---

## Deploy no Render

1. No Render, crie um **PostgreSQL** (New → PostgreSQL).
2. Copie a **Internal Database URL** do banco.
3. No serviço web, em **Environment**, adicione `DATABASE_URL` com essa URL.
4. Faça o deploy da branch atualizada. As tabelas são criadas na primeira inicialização.
