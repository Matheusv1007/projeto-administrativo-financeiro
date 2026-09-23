# Projeto Administrativo-Financeiro — Etapa 1

Projeto desenvolvido para a disciplina de **Prática de Engenharia de Software**.

Nesta primeira etapa foi implementado um processador de notas fiscais em PDF utilizando **Agents de IA** e a API do **Google Gemini**.

O usuário envia uma nota fiscal pela interface web e o sistema:

1. extrai os dados da nota fiscal;
2. interpreta os produtos;
3. classifica o tipo de despesa;
4. devolve os dados em formato JSON na tela.

---

## Tecnologias utilizadas

- Python
- Flask
- JavaScript
- HTML
- CSS
- Google Gemini API
- python-dotenv

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
- Datas de vencimento
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
JSON
   ↓
Interface Web

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
GEMINI_API_KEY=SUA_CHAVE_AQUI
GEMINI_MODEL=gemini-3.5-flash-lite
```

### 6. Execute

```bash
python app.py
```

Acesse no navegador:

```text
http://127.0.0.1:5000
```