const form = document.getElementById("formNota");
const apiKeyInput = document.getElementById("apiKey");
const botaoConfirmarChave = document.getElementById(
    "botaoConfirmarChave"
);
const botaoAlterarChave = document.getElementById(
    "botaoAlterarChave"
);
const statusChave = document.getElementById("statusChave");
const arquivoInput = document.getElementById("arquivo");
const resultado = document.getElementById("resultado");
const statusTexto = document.getElementById("status");
const botao = document.getElementById("botaoExtrair");
const analiseContainer = document.getElementById("analise");

let chaveConfirmada = false;

botaoConfirmarChave.addEventListener("click", () => {
    const apiKey = apiKeyInput.value.trim();

    if (!apiKey) {
        statusChave.textContent =
            "Informe uma chave antes de confirmar.";
        statusChave.className = "status-chave status-chave-erro";
        apiKeyInput.focus();
        return;
    }

    chaveConfirmada = true;
    apiKeyInput.readOnly = true;
    arquivoInput.disabled = false;
    botao.disabled = false;
    botaoConfirmarChave.hidden = true;
    botaoAlterarChave.hidden = false;
    statusChave.textContent = "Chave configurada.";
    statusChave.className = "status-chave status-chave-sucesso";
});

botaoAlterarChave.addEventListener("click", () => {
    chaveConfirmada = false;
    apiKeyInput.readOnly = false;
    apiKeyInput.value = "";
    arquivoInput.disabled = true;
    arquivoInput.value = "";
    botao.disabled = true;
    botaoConfirmarChave.hidden = false;
    botaoAlterarChave.hidden = true;
    statusChave.textContent = "Nenhuma chave configurada.";
    statusChave.className = "status-chave";
    apiKeyInput.focus();
});

function situacao(item) {
    return item.existe
        ? `EXISTE \u2013 ID: ${item.id}`
        : "N\u00c3O EXISTE";
}

function adicionarLinha(bloco, texto, negrito = false) {
    const linha = document.createElement("p");

    if (negrito) {
        const destaque = document.createElement("strong");
        destaque.textContent = texto;
        linha.appendChild(destaque);
    } else {
        linha.textContent = texto;
    }

    bloco.appendChild(linha);
}

function criarBloco(titulo) {
    const bloco = document.createElement("div");
    const cabecalho = document.createElement("h3");

    bloco.className = "bloco-analise";
    cabecalho.textContent = titulo;
    bloco.appendChild(cabecalho);
    analiseContainer.appendChild(bloco);

    return bloco;
}

function mostrarPessoa(titulo, rotuloDocumento, pessoa) {
    const bloco = criarBloco(titulo);

    adicionarLinha(
        bloco,
        pessoa.razaoSocial || "N\u00e3o identificado na nota"
    );
    adicionarLinha(
        bloco,
        `${rotuloDocumento}: ${pessoa.documento || "N\u00e3o informado"}`
    );
    adicionarLinha(bloco, situacao(pessoa), true);
}

function mostrarAnalise(analise) {
    analiseContainer.replaceChildren();

    mostrarPessoa("FORNECEDOR:", "CNPJ", analise.fornecedor);
    mostrarPessoa("FATURADO", "CPF", analise.faturado);

    const blocoDespesa = criarBloco("DESPESA");

    if (analise.despesas.length === 0) {
        adicionarLinha(
            blocoDespesa,
            "N\u00e3o foi poss\u00edvel classificar a despesa."
        );
    }

    analise.despesas.forEach((despesa) => {
        adicionarLinha(blocoDespesa, despesa.descricao);
        adicionarLinha(blocoDespesa, situacao(despesa), true);
    });
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const arquivo = arquivoInput.files[0];
    const apiKey = apiKeyInput.value.trim();

    if (!chaveConfirmada || !apiKey) {
        statusTexto.textContent =
            "Confirme a chave da API Gemini.";
        return;
    }

    if (!arquivo) {
        statusTexto.textContent = "Selecione um PDF.";
        return;
    }

    const formData = new FormData();

    formData.append("api_key", apiKey);
    formData.append("arquivo", arquivo);

    try {
        botao.disabled = true;

        statusTexto.textContent =
            "Processando nota fiscal...";

        resultado.textContent = "";
        analiseContainer.replaceChildren();

        const response = await fetch("/extrair", {
            method: "POST",
            body: formData
        });

        const dados = await response.json();

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        if (!response.ok) {
            throw new Error(
                dados.erro || "Erro ao processar nota."
            );
        }

        statusTexto.textContent =
            "Extração concluída com sucesso.";

        resultado.textContent =
            JSON.stringify(dados.dados, null, 2);

        mostrarAnalise(dados.analise);

    } catch (erro) {

        statusTexto.textContent =
            "Erro durante o processamento.";

        resultado.textContent =
            erro.message;

    } finally {
        botao.disabled = !chaveConfirmada;
    }
});
