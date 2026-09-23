const form = document.getElementById("formNota");
const arquivoInput = document.getElementById("arquivo");
const resultado = document.getElementById("resultado");
const statusTexto = document.getElementById("status");
const botao = document.getElementById("botaoExtrair");

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const arquivo = arquivoInput.files[0];

    if (!arquivo) {
        statusTexto.textContent = "Selecione um PDF.";
        return;
    }

    const formData = new FormData();

    formData.append("arquivo", arquivo);

    try {
        botao.disabled = true;

        statusTexto.textContent =
            "Processando nota fiscal...";

        resultado.textContent = "";

        const response = await fetch("/extrair", {
            method: "POST",
            body: formData
        });

        const dados = await response.json();

        if (!response.ok) {
            throw new Error(
                dados.erro || "Erro ao processar nota."
            );
        }

        statusTexto.textContent =
            "Extração concluída com sucesso.";

        resultado.textContent =
            JSON.stringify(dados, null, 2);

    } catch (erro) {

        statusTexto.textContent =
            "Erro durante o processamento.";

        resultado.textContent =
            erro.message;

    } finally {
        botao.disabled = false;
    }
});